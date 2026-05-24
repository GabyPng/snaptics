"""
Generador de código objeto — emu8086 (8086)
============================================
Última fase del pipeline. Recorre la lista de cuádruplas optimizadas
(post-IROptimizer) y emite un programa 8086 ensamblable en emu8086.

Pipeline:
    parse -> semantic -> ir -> optimizer -> [CODEGEN]

Sigue la misma convención que `ir_generator.generate_ir()` y
`optimizer.optimize_ir()`: una función pública (`generate_code`) que
recibe el resultado del paso previo y devuelve un dict normalizado.

ALCANCE V1 (acuerdo de equipo, 3 días)
--------------------------------------
Soportado:
    - facts derivados de un dataset:   fact x = P(col OP valor)
    - facts con valor constante       (resultado de plegado del optimizer)
    - facts con probabilidad condicional:  fact x = P(A given B)
    - reglas con and / or / not        (incluido anidamiento)
    - reglas con comparación contra literal (fact > 0.30)
    - queries
    - import de un dataset CSV         (parsing en runtime via Biblioteca.lib)
    - select ... where condicion       (filtra dataset; el where se inyecta como
                                        pre-check en cada count_<fact> del dataset)

NO soportado (se reporta como error de generación):
    - mean / var / std / correlation
    - auto_discover
    - query ... explain | why
    - aritmética dentro de expresiones probabilísticas

CONVENCIÓN DE REGISTROS (acordada con el equipo)
------------------------------------------------
- Toda probabilidad viaja en AX como entero 0..100.
- Las rutinas auxiliares preservan CX, DX, SI, DI con push/pop.
- AX y BX son volátiles.

PIEZAS QUE ESTE MÓDULO **NO** EMITE
-----------------------------------
Este generador solamente arma el esqueleto del programa, la sección
.DATA y la secuencia de CALLs en .CODE. Las rutinas auxiliares vienen
de los otros tres módulos del equipo:

- Gibran   -> fuzzy_and, fuzzy_or, fuzzy_not
- Carim    -> count_<fact> (una por cada fact derivado del dataset),
              y opcionalmente la propia .DATA que él inyecte
- Fanny    -> show_result, print_int, show_led, show_traffic,
              parse_int, skip_to_col_N, skip_to_eol

El .asm de salida deja TODOs marcados donde cada quien debe
inyectar/INCLUDEar su parte.
"""

from __future__ import annotations

# Bootstrap: este módulo vive en codegen/, pero importa cosas del front-end
# que están en la raíz del proyecto (ir_generator, etc.). Añadimos la raíz
# al sys.path para que los imports flat sigan funcionando.
import os as _os, sys as _sys
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

from ir_generator import Quadruple


# ==================== CONSTANTES ====================

SCALE = 100                       # probabilidad 0..1 -> entero 0..100
BUFFER_SIZE = 4096                # tamaño del buffer de lectura del CSV
DEFAULT_DATASET_PATH = r"C:\emu8086\vdrive\C\dataset.txt"

# Operaciones de la IR que SÍ emite este codegen
_LOGIC_OPS = {'AND', 'OR', 'NOT'}
_COMPARE_OPS = {'GT', 'LT', 'EQ', 'NEQ', 'LEQ', 'GEQ'}

# Operaciones declaradas explícitamente fuera de alcance v1
_UNSUPPORTED_OPS = {
    'MEAN', 'VARIANCE', 'STDDEV', 'CORRELATION',
    'AUTO_DISCOVER', 'QUERY_EXPLAIN',
    'ADD', 'SUB', 'MUL', 'DIV', 'POW',
    'UNARY_MINUS', 'UNARY_PLUS',
}

# Operaciones que el codegen acepta pero NO traduce a asm:
#   - SELECT: solo declara columnas (metadatos para el semantic/IR);
#             el runtime usa un único archivo CSV, no hace falta nada.
#   - MEMBER_ACCESS: resuelve "dataset.columna" a un temporal; el
#             codegen lo "absorbe" mapeando ese temporal a la columna real.
_NOOP_OPS = {'SELECT', 'MEMBER_ACCESS'}

# Op IR -> (salto "si verdadero", salto "si falso/negado", símbolo Snaptics)
# El salto negado es lo que necesita Carim en las plantillas
# count_<fact>: "si NO se cumple la condición, salta y no cuentes".
_CMP_OP_INFO = {
    'GT':  ('JG',  'JLE', '>'),
    'LT':  ('JL',  'JGE', '<'),
    'EQ':  ('JE',  'JNE', '=='),
    'NEQ': ('JNE', 'JE',  '!='),
    'LEQ': ('JLE', 'JG',  '<='),
    'GEQ': ('JGE', 'JL',  '>='),
}


# ==================== ERRORES ====================

class CodeGenError(Exception):
    """Error de generación de código objeto."""

    def __init__(self, code: str, message: str, quad_index: int = -1):
        self.code = code
        self.message = message
        self.quad_index = quad_index
        super().__init__(self.format())

    def format(self) -> str:
        loc = f" (cuádrupla #{self.quad_index})" if self.quad_index >= 0 else ""
        return f"[{self.code}]{loc} {self.message}"


# ==================== GENERADOR ====================

class CodeGenerator:
    """Genera código objeto 8086 (sintaxis emu8086) a partir de IR optimizada."""

    def __init__(self, symbol_table=None, dataset_path: str | None = None):
        self.symbol_table = symbol_table
        self.dataset_path = dataset_path or DEFAULT_DATASET_PATH

        # Estado por compilación
        self.quads: list[Quadruple] = []
        self.errors: list[CodeGenError] = []

        # Clasificación de símbolos detectada al analizar la IR
        self.facts_literal: dict[str, int] = {}       # nombre -> valor escalado 0..100
        # Para facts simples:    {col, op, value, ir_op, jump, dataset, kind: 'simple'}
        # Para facts con given:  {col_a, op_a, value_a, jump_a,
        #                         col_b, op_b, value_b, jump_b,
        #                         dataset, kind: 'given'}
        self.facts_derived: dict[str, dict] = {}
        self.rules: list[str] = []                    # nombres de reglas en orden
        self.queries: list[str] = []                  # targets de query en orden
        self.temps: set[str] = set()                  # tN que requieren slot DW
        self.datasets: dict[str, str] = {}            # dataset_id -> ruta de archivo (raíz)
        # Datasets derivados de un select+where:
        #   nombre_dataset -> {col, op, value, ir_op, jump}
        # Carim inyecta un "where pre-check" al inicio de cada count_<fact>
        # cuyo fact pertenezca a un dataset listado aquí.
        self.datasets_with_filter: dict[str, dict] = {}
        # tN producido por MEMBER_ACCESS -> nombre real de la columna
        self.column_aliases: dict[str, str] = {}
        # tN producido por MEMBER_ACCESS -> dataset al que pertenece la columna
        self.column_datasets: dict[str, str] = {}
        # Temps que son resultado de una comparación absorbida por un PROB,
        # PROB_GIVEN o FILTER. No deben emitirse como cmp crisp en asm.
        self.absorbed_cmp_temps: set[str] = set()
        # Contador para etiquetas únicas en comparaciones dentro de reglas.
        self._cmp_label_counter = 0

        # Buffers de salida
        self._data_lines: list[str] = []
        self._code_lines: list[str] = []

    # ---------------- API pública ----------------

    def generate(self, quadruples: list[Quadruple]) -> str:
        """Genera el .asm completo a partir de la IR optimizada."""
        self._reset(quadruples)
        self._analyze()
        self._emit_data()
        self._emit_code()
        return self._assemble()

    def derived_facts_metadata(self) -> dict:
        """Metadatos planos de facts derivados (legacy, sin info de dataset filters).
        Para nuevos usos preferir `metadata()`.
        """
        return dict(self.facts_derived)

    def metadata(self) -> dict:
        """Metadatos completos para Gibran/Carim:

            {
                'datasets': {
                    'alumnos_foco': {
                        'filter': {'col': 'promedio', 'op': '<', 'value': 80, 'jump': 'JL'},
                    },
                    ...
                },
                'facts': {
                    'asistencia_critica': {
                        'kind': 'simple', 'dataset': 'alumnos_foco',
                        'col': 'asistencia', 'op': '<', 'value': 60, 'jump': 'JL',
                    },
                    'p_reprobacion_dada': {
                        'kind': 'given', 'dataset': 'alumnos_foco',
                        'col_a': 'promedio',    'op_a': '<', 'value_a': 60, 'jump_a': 'JL',
                        'col_b': 'asistencia',  'op_b': '<', 'value_b': 60, 'jump_b': 'JL',
                    },
                },
            }

        Con esto el `count_generator.py` de Carim decide:
          - qué plantilla usar (simple vs given) por `kind`
          - si inyectar el "where pre-check" según `facts[X].dataset`
            tenga entrada en `datasets`
        """
        datasets = {}
        for name, filt in self.datasets_with_filter.items():
            datasets[name] = {'filter': dict(filt)}
        return {
            'datasets': datasets,
            'facts': dict(self.facts_derived),
        }

    # ---------------- estado ----------------

    def _reset(self, quadruples: list[Quadruple]):
        self.quads = list(quadruples)
        self.errors = []
        self.facts_literal = {}
        self.facts_derived = {}
        self.rules = []
        self.queries = []
        self.temps = set()
        self.datasets = {}
        self.datasets_with_filter = {}
        self.column_aliases = {}
        self.column_datasets = {}
        self.absorbed_cmp_temps = set()
        self._cmp_label_counter = 0
        self._data_lines = []
        self._code_lines = []

    # ---------------- pase 1: análisis ----------------

    def _analyze(self):
        """Clasifica símbolos y detecta operaciones no soportadas."""
        # 1) marcar TODOS los temporales referenciados (para reservar slots DW)
        for q in self.quads:
            for arg in (q.arg1, q.arg2, q.result):
                if isinstance(arg, str) and arg.startswith('t') and arg[1:].isdigit():
                    self.temps.add(arg)

        # 2) recorrer la IR clasificando declaraciones
        for i, q in enumerate(self.quads):
            op = q.op

            if op in _UNSUPPORTED_OPS:
                self.errors.append(CodeGenError(
                    'GEN-001',
                    f"Operación '{op}' fuera del alcance v1.",
                    i
                ))
                continue

            if op == 'LOAD_DATASET':
                # arg1 = nombre de archivo, result = dataset_id
                if isinstance(q.arg1, str):
                    self.datasets[q.result] = q.arg1.strip("'\"")
                continue

            if op == 'MEMBER_ACCESS':
                # dataset.columna -> tN. Guardamos AMBOS: el nombre de la
                # columna (para resolver en condiciones) y el nombre del
                # dataset (para saber a quién pertenece el fact).
                if isinstance(q.result, str):
                    if isinstance(q.arg2, str):
                        self.column_aliases[q.result] = q.arg2
                    if isinstance(q.arg1, str):
                        self.column_datasets[q.result] = q.arg1
                continue

            if op == 'SELECT':
                # Solo declara columnas; sin efecto en runtime.
                continue

            if op == 'FILTER':
                # FILTER tselect tcond tfilt. No emitimos asm aquí; el
                # filtro se resolverá cuando aparezca el ASSIGN del temp
                # a un dataset (via _classify_dataset_assign).
                continue

            if op == 'ASSIGN':
                self._classify_assign(q, i)
                continue

            if op == 'RULE_DEF':
                if isinstance(q.result, str):
                    self.rules.append(q.result)
                continue

            if op == 'QUERY':
                if isinstance(q.arg1, str):
                    self.queries.append(q.arg1)
                continue

            if op in _LOGIC_OPS or op in _COMPARE_OPS or op in ('PROB', 'PROB_GIVEN'):
                # Se emiten/consumen en el pase 2; nada que clasificar aquí.
                continue

            # Op desconocida: marcar como error pero seguir
            self.errors.append(CodeGenError(
                'GEN-002',
                f"Operación de IR desconocida: '{op}'.",
                i
            ))

    def _classify_assign(self, q: Quadruple, idx: int):
        """Decide qué hace un ASSIGN: definir fact, atar dataset filtrado, etc."""
        target = q.result
        src = q.arg1

        if not isinstance(target, str):
            return

        category = self._category(target)

        if category == 'fact':
            # Caso A: source es número literal (constant_folding / constant_propagation)
            if isinstance(src, (int, float)):
                self.facts_literal[target] = self._scale(src)
                return

            # Caso B: source es un temp producido por PROB (simple)
            if isinstance(src, str):
                condition = self._trace_fact_condition(src, idx)
                if condition is not None:
                    condition['kind'] = 'simple'
                    self.facts_derived[target] = condition
                    return

                # Caso C: source es un temp producido por PROB_GIVEN
                condition = self._trace_fact_given(src, idx)
                if condition is not None:
                    condition['kind'] = 'given'
                    self.facts_derived[target] = condition
                    return

            self.errors.append(CodeGenError(
                'GEN-101',
                f"No se pudo derivar la condición del fact '{target}'. "
                f"Forma esperada: fact {target} = P(<columna> <op> <valor>) "
                f"o fact {target} = P(A given B).",
                idx
            ))
            # Aun así reservamos un slot para que el .asm ensamble
            self.facts_derived[target] = {
                'col': '?', 'op': '?', 'value': 0,
                'ir_op': '?', 'jump': 'JMP', 'kind': 'simple',
            }
            return

        if category == 'dataset':
            # ASSIGN tX -> dataset_name. Si tX viene de un FILTER, registramos
            # el dataset como "filtrado" con la condición del where.
            if isinstance(src, str):
                self._classify_dataset_assign(target, src, idx)
            return

    def _find_cmp_info(self, cmp_temp: str, end_idx: int) -> dict | None:
        """Helper: localiza la comparación que produjo `cmp_temp` y devuelve
        su info {col, dataset, op, value, ir_op, jump}, marcando el temp
        como absorbido. Devuelve None si no se encuentra.
        """
        if not isinstance(cmp_temp, str):
            return None
        for j in range(end_idx - 1, -1, -1):
            q = self.quads[j]
            if q.result == cmp_temp and q.op in _CMP_OP_INFO:
                jump, jump_neg, sym = _CMP_OP_INFO[q.op]
                col = q.arg1
                dataset = None
                if isinstance(col, str):
                    dataset = self.column_datasets.get(col)
                    if col in self.column_aliases:
                        col = self.column_aliases[col]
                self.absorbed_cmp_temps.add(cmp_temp)
                return {
                    'col':      col,
                    'dataset':  dataset,
                    'op':       sym,
                    'value':    int(q.arg2) if isinstance(q.arg2, (int, float)) else q.arg2,
                    'ir_op':    q.op,
                    'jump':     jump,
                    'jump_neg': jump_neg,
                }
        return None

    def _trace_fact_condition(self, temp: str, end_idx: int) -> dict | None:
        """
        Busca hacia atrás el patrón:
            <cmp_op>, col, val, t_cmp
            PROB,     t_cmp, _,  temp
        Devuelve {col, op, value, ir_op, jump, dataset} si lo encuentra.
        """
        prob_q, prob_idx = None, -1
        for j in range(end_idx - 1, -1, -1):
            q = self.quads[j]
            if q.op == 'PROB' and q.result == temp:
                prob_q, prob_idx = q, j
                break
        if prob_q is None:
            return None
        return self._find_cmp_info(prob_q.arg1, prob_idx)

    def _trace_fact_given(self, temp: str, end_idx: int) -> dict | None:
        """
        Busca hacia atrás el patrón:
            <cmp_a>,    col_a, val_a, t_a
            <cmp_b>,    col_b, val_b, t_b
            PROB_GIVEN, t_a,   t_b,   temp
        En P(A given B): arg1 = A (numerador), arg2 = B (denominador).
        Devuelve {col_a, op_a, value_a, jump_a, col_b, op_b, value_b, jump_b,
                  dataset, ir_op_a, ir_op_b} si lo encuentra.
        """
        pg_q, pg_idx = None, -1
        for j in range(end_idx - 1, -1, -1):
            q = self.quads[j]
            if q.op == 'PROB_GIVEN' and q.result == temp:
                pg_q, pg_idx = q, j
                break
        if pg_q is None:
            return None

        info_a = self._find_cmp_info(pg_q.arg1, pg_idx)
        info_b = self._find_cmp_info(pg_q.arg2, pg_idx)
        if info_a is None or info_b is None:
            return None

        return {
            'col_a':      info_a['col'],     'op_a':      info_a['op'],
            'value_a':    info_a['value'],   'jump_a':    info_a['jump'],
            'jump_a_neg': info_a['jump_neg'], 'ir_op_a':   info_a['ir_op'],
            'col_b':      info_b['col'],     'op_b':      info_b['op'],
            'value_b':    info_b['value'],   'jump_b':    info_b['jump'],
            'jump_b_neg': info_b['jump_neg'], 'ir_op_b':   info_b['ir_op'],
            'dataset':    info_a.get('dataset') or info_b.get('dataset'),
        }

    def _classify_dataset_assign(self, target: str, src: str, idx: int):
        """ASSIGN tX -> dataset_name donde tX viene de FILTER. Extrae el
        where y lo registra como filtro del dataset destino.
        """
        # Buscar el FILTER que produjo `src`
        for j in range(idx - 1, -1, -1):
            q = self.quads[j]
            if q.op == 'FILTER' and q.result == src:
                cond_info = self._find_cmp_info(q.arg2, j)
                if cond_info is not None:
                    self.datasets_with_filter[target] = {
                        'col':      cond_info['col'],
                        'op':       cond_info['op'],
                        'value':    cond_info['value'],
                        'ir_op':    cond_info['ir_op'],
                        'jump':     cond_info['jump'],
                        'jump_neg': cond_info['jump_neg'],
                    }
                return
        # Si no hay FILTER, no es un dataset filtrado; nada que hacer.

    def _category(self, name: str) -> str | None:
        if self.symbol_table is None or not isinstance(name, str):
            return None
        sym = self.symbol_table.get(name)
        return sym.category if sym else None

    def _describe_fact(self, meta: dict) -> str:
        """Comentario legible para un fact, usado en .DATA y .CODE."""
        kind = meta.get('kind', 'simple')
        if kind == 'given':
            a = f"{meta.get('col_a','?')} {meta.get('op_a','?')} {meta.get('value_a','?')}"
            b = f"{meta.get('col_b','?')} {meta.get('op_b','?')} {meta.get('value_b','?')}"
            return f"P({a} given {b})"
        return f"P({meta.get('col','?')} {meta.get('op','?')} {meta.get('value','?')})"

    @staticmethod
    def _scale(value) -> int:
        """Convierte probabilidad 0..1 a entero 0..100."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 0
        v = max(0.0, min(1.0, v))
        return int(round(v * SCALE))

    # ---------------- pase 2.a: sección DATA ----------------

    def _emit_data(self):
        D = self._data_lines.append
        D("    ; ---- Sección DATA generada por codegen ----")

        # Ruta del dataset, buffer y handle (solo si hay dataset usado por facts)
        if self.facts_derived:
            path = next(iter(self.datasets.values()), self.dataset_path)
            D(f"    RUTA         DB '{path}', 0")
            D( "    ID_ARCHIVO   DW 0")
            # IMPORTANTE: inicializar con 0, NO con espacios. skip_to_eol usa
            # null como guard de fin de buffer. Si el CSV no termina con LF,
            # los espacios harían que el loop nunca termine.
            D(f"    BUFFER       DB {BUFFER_SIZE} DUP(0)")
            D( "    BYTES_LEIDOS DW 0")
            D("")

        if self.facts_literal:
            D("    ; -- Facts con valor constante (resueltos por el optimizer) --")
            for name, val in self.facts_literal.items():
                D(f"    fact_{name:<16} DW {val}")
            D("")

        if self.facts_derived:
            D("    ; -- Facts derivados del dataset (los llena count_<fact>) --")
            for name, meta in self.facts_derived.items():
                D(f"    fact_{name:<16} DW 0    ; {self._describe_fact(meta)}")
            D("")

        if self.rules:
            D("    ; -- Resultado de evaluación de cada regla --")
            for name in self.rules:
                D(f"    rule_{name:<16} DW 0")
            D("")

        if self.temps:
            D("    ; -- Temporales del IR --")
            for t in sorted(self.temps, key=lambda s: int(s[1:])):
                D(f"    {t:<20} DW 0")
            D("")

        if self.queries:
            D("    ; -- Mensajes de queries (consumidos por show_result) --")
            for name in self.queries:
                D(f"    msg_{name:<16} DB '{name} = $'")
            D("")

        # Mensajes de evidencia: deben estar en DATA (no en CODE), porque
        # show_result los imprime con INT 21h/9h que usa DS:DX. Si vivieran
        # en CODE (que es donde está output_devices.asm tras el include),
        # DS:DX apuntaría a memoria equivocada y la búsqueda del '$' falla.
        # El texto coincide con el formato que espera show_result de Fanny.
        D("    msg_evid_baja DB 13, 10, 'Evidencia: BAJA$'")
        D("    msg_evid_mod  DB 13, 10, 'Evidencia: MODERADA$'")
        D("    msg_evid_alta DB 13, 10, 'Evidencia: ALTA$'")
        D("    msg_err_file  DB 'Error abriendo el dataset.', 13, 10, '$'")

    # ---------------- pase 2.b: sección CODE ----------------

    def _emit_code(self):
        def C(s: str):
            # Etiquetas (token único terminado en ':') van a columna 0;
            # el resto se indenta con 4 espacios.
            if s and s.endswith(':') and ' ' not in s:
                self._code_lines.append(s)
            else:
                self._code_lines.append("    " + s if s else "")

        # 1) Si hay dataset y facts derivados, abrir/leer el archivo y calcular cada fact
        if self.facts_derived:
            C("; ---- Apertura y lectura del CSV ----")
            C("abrirArchivo 2, RUTA          ; modo 2 = lectura/escritura")
            C("MOV ID_ARCHIVO, AX")
            C("JC error_archivo")
            C(f"leerArchivo {BUFFER_SIZE}, BUFFER, ID_ARCHIVO")
            C("JC error_archivo")
            C("MOV BYTES_LEIDOS, AX")
            C("")
            C("; ---- Cálculo de facts derivados (rutinas emitidas por Carim) ----")
            for name, meta in self.facts_derived.items():
                C(f"CALL count_{name}             ; {self._describe_fact(meta)}")
            C("")

        # 2) Evaluación de reglas y queries siguiendo el orden del IR
        C("; ---- Evaluación de reglas y queries ----")
        for i, q in enumerate(self.quads):
            block = self._emit_quad(q, i)
            if not block:
                continue
            for line in block:
                C(line)

    def _emit_quad(self, q: Quadruple, idx: int) -> list[str] | None:
        op = q.op

        if op == 'AND':
            return self._emit_binary_logic(q, 'fuzzy_and')
        if op == 'OR':
            return self._emit_binary_logic(q, 'fuzzy_or')
        if op == 'NOT':
            return self._emit_not(q)
        if op == 'RULE_DEF':
            return self._emit_rule_def(q)
        if op == 'QUERY':
            return self._emit_query(q)
        if op == 'ASSIGN':
            return self._emit_assign(q)

        if op in _COMPARE_OPS:
            # Si la cmp fue absorbida por una PROB (es la condición de un fact),
            # no se emite asm: el conteo lo hace count_<fact>.
            # En caso contrario, está dentro de una regla (ej: fact > 0.30) y
            # se emite como booleano crisp 0/100.
            if isinstance(q.result, str) and q.result in self.absorbed_cmp_temps:
                return None
            return self._emit_compare(q)

        # PROB, LOAD_DATASET, etc. ya están absorbidos en el análisis
        return None

    def _emit_binary_logic(self, q: Quadruple, routine: str) -> list[str]:
        return [
            f"; {q.op} {q.arg1}, {q.arg2} -> {q.result}",
            f"MOV AX, {self._operand(q.arg1)}",
            f"MOV BX, {self._operand(q.arg2)}",
            f"CALL {routine}",
            f"MOV {self._target(q.result)}, AX",
            "",
        ]

    def _emit_not(self, q: Quadruple) -> list[str]:
        return [
            f"; NOT {q.arg1} -> {q.result}",
            f"MOV AX, {self._operand(q.arg1)}",
            "CALL fuzzy_not",
            f"MOV {self._target(q.result)}, AX",
            "",
        ]

    def _emit_rule_def(self, q: Quadruple) -> list[str]:
        return [
            f"; rule {q.result} := {q.arg1}",
            f"MOV AX, {self._operand(q.arg1)}",
            f"MOV rule_{q.result}, AX",
            "",
        ]

    def _emit_query(self, q: Quadruple) -> list[str]:
        target = q.arg1
        category = self._category(target)
        if category == 'rule':
            slot = f"rule_{target}"
        else:
            slot = f"fact_{target}"
        return [
            f"; query {target}",
            f"MOV AX, {slot}",
            f"LEA SI, msg_{target}",
            "CALL show_result",
            "",
        ]

    def _emit_compare(self, q: Quadruple) -> list[str]:
        """Comparación dentro de una regla: emite booleano crisp 0/100.

        Ejemplo: `fact > 0.30` se traduce a "AX = 100 si fact > 30, si no AX = 0".
        El resultado entra normal a fuzzy_and / fuzzy_or como cualquier
        otro grado de verdad (0 o 100 son extremos válidos en lógica difusa).
        """
        op = q.op
        jump = _CMP_OP_INFO[op][0]
        label_id = self._cmp_label_counter
        self._cmp_label_counter += 1
        label_true = f"cmp_t_{label_id}"
        label_done = f"cmp_d_{label_id}"
        return [
            f"; {op} {q.arg1}, {q.arg2} -> {q.result}  (cmp crisp en regla)",
            f"MOV AX, {self._operand(q.arg1)}",
            f"CMP AX, {self._operand(q.arg2)}",
            f"{jump} {label_true}",
            "MOV AX, 0",
            f"JMP {label_done}",
            f"{label_true}:",
            "MOV AX, 100",
            f"{label_done}:",
            f"MOV {self._target(q.result)}, AX",
            "",
        ]

    def _emit_assign(self, q: Quadruple) -> list[str] | None:
        target = q.result
        if not isinstance(target, str):
            return None
        # Los ASSIGN a facts ya quedaron resueltos en DATA (.facts_literal / .facts_derived).
        # Los ASSIGN cuyo target es un dataset/columna/metric solo existen al nivel
        # del IR (aliasing del SELECT, etc.) y no tienen entidad en runtime.
        # Sólo emitimos ASSIGN cuando el target es un temporal real (tN).
        if not (target.startswith('t') and target[1:].isdigit()):
            return None
        return [
            f"; ASSIGN {q.arg1} -> {target}",
            f"MOV AX, {self._operand(q.arg1)}",
            f"MOV {target}, AX",
            "",
        ]

    # ---------------- traducción de operandos ----------------

    def _operand(self, name) -> str:
        """Devuelve la forma textual con la que cargar un argumento en AX/BX."""
        if isinstance(name, (int, float)):
            # Solo escalamos si parece probabilidad (0..1). Otros enteros van tal cual.
            if isinstance(name, float) or 0 <= name <= 1:
                return str(self._scale(name))
            return str(int(name))
        if not isinstance(name, str):
            return "0"
        if name.startswith('t') and name[1:].isdigit():
            return name
        cat = self._category(name)
        if cat == 'fact':
            return f"fact_{name}"
        if cat == 'rule':
            return f"rule_{name}"
        return name  # variable libre / fallback

    def _target(self, name) -> str:
        if not isinstance(name, str):
            return "0"
        if name.startswith('t') and name[1:].isdigit():
            return name
        cat = self._category(name)
        if cat == 'fact':
            return f"fact_{name}"
        if cat == 'rule':
            return f"rule_{name}"
        return name

    # ---------------- ensamblado final ----------------

    def _assemble(self) -> str:
        data_section = "\n".join(self._data_lines)
        code_section = "\n".join(self._code_lines)

        errs_header = ""
        if self.errors:
            errs_header = "; --- ERRORES DE GENERACIÓN ---\n"
            for e in self.errors:
                errs_header += f"; {e.format()}\n"
            errs_header += "; -----------------------------\n\n"

        stubs_carim_lines = []
        for name, m in self.facts_derived.items():
            kind = m.get('kind', 'simple')
            tipo = 'count_given_<fact>' if kind == 'given' else 'count_<fact>'
            ds = m.get('dataset')
            extra = ''
            if ds and ds in self.datasets_with_filter:
                f = self.datasets_with_filter[ds]
                extra = f"   [+ where {f['col']} {f['op']} {f['value']} sobre {ds}]"
            stubs_carim_lines.append(
                f";   count_{name} PROC  ; {self._describe_fact(m)}  ({tipo}){extra}\n"
            )
        stubs_carim = "".join(stubs_carim_lines) or \
            ";   (no hay facts derivados de dataset en este programa)\n"

        return (
            "; ============================================================\n"
            "; Programa generado por el codegen de Snaptics -> emu8086\n"
            "; ============================================================\n"
            f"{errs_header}"
            "include Biblioteca.lib\n\n"
            ".MODEL SMALL\n"
            ".STACK 100h\n"
            ".DATA\n"
            f"{data_section}\n\n"
            ".CODE\n"
            "INICIO:\n"
            "    MOV AX, @DATA\n"
            "    MOV DS, AX\n"
            "    MOV ES, AX\n\n"
            f"{code_section}\n"
            "    JMP fin\n\n"
            "error_archivo:\n"
            "    MOV AH, 09h\n"
            "    LEA DX, msg_err_file\n"
            "    INT 21h\n\n"
            "fin:\n"
            "    MOV AX, 4C00h\n"
            "    INT 21h\n\n"
            "; ============================================================\n"
            "; Rutinas externas requeridas (deben incluirse / pegarse)\n"
            "; ============================================================\n"
            "; Gibran:\n"
            ";   fuzzy_and PROC  (AX, BX -> AX = MIN(AX, BX))\n"
            ";   fuzzy_or  PROC  (AX, BX -> AX = MAX(AX, BX))\n"
            ";   fuzzy_not PROC  (AX     -> AX = 100 - AX)\n"
            ";\n"
            "; Fanny:\n"
            ";   show_result   PROC  (AX = prob, SI = offset de msg_<query>)\n"
            ";   print_int     PROC  (AX = entero 0..100)\n"
            ";   show_led      PROC  (AX = entero 0..100 -> puerto LED)\n"
            ";   show_traffic  PROC  (AX = entero 0..100 -> puerto semáforo)\n"
            ";\n"
            "; Carim (generadas por su módulo, una por cada fact derivado):\n"
            f"{stubs_carim}"
            "\n"
            "END INICIO\n"
        )


# ==================== INTEGRACIÓN CON EL PIPELINE ====================

def generate_code(opt_result: dict,
                  parse_result: dict | None = None,
                  dataset_path: str | None = None) -> dict:
    """
    Punto de entrada del codegen. Sigue el mismo patrón que las fases anteriores.

    Args:
        opt_result:     dict retornado por optimizer.optimize_ir().
        parse_result:   dict retornado por parser.parse() (opcional, da symbol_table).
        dataset_path:   ruta absoluta al CSV; si no se pasa se usa DEFAULT_DATASET_PATH.

    Returns:
        dict:
            'asm':            str — programa completo .asm (puede estar parcial si hubo errores).
            'success':        bool.
            'errors':         list[str].
            'derived_facts':  dict — metadatos para Carim (col, op, value, ir_op, jump).
    """
    if not opt_result.get('success'):
        return {
            'asm': '',
            'success': False,
            'errors': ['No se puede generar código objeto: la fase de optimización falló.'],
            'derived_facts': {},
        }

    symbol_table = (parse_result or {}).get('symbol_table')
    quads = opt_result.get('quadruples', [])

    gen = CodeGenerator(symbol_table=symbol_table, dataset_path=dataset_path)
    asm = gen.generate(quads)

    return {
        'asm':           asm,
        'success':       len(gen.errors) == 0,
        'errors':        [e.format() for e in gen.errors],
        'derived_facts': gen.derived_facts_metadata(),
        'metadata':      gen.metadata(),
    }
