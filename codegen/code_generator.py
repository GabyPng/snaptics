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
    - queries (basic, explain, why)    — explain/why emiten pantallas extra
                                          con desglose tecnico y razonamiento
                                          causal
    - paginacion + navegacion por flechas (← anterior, → siguiente, ESC sale)
    - export del log de queries a un .txt en C:\emu8086\vdrive\C\output\
    - import de un dataset CSV         (parsing en runtime via Biblioteca.lib)
    - select ... where condicion       (filtra dataset; el where se inyecta como
                                        pre-check en cada count_<fact> del dataset)

NO soportado (se reporta como error de generación):
    - mean / var / std / correlation
    - auto_discover
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
    'AUTO_DISCOVER',
    'ADD', 'SUB', 'MUL', 'DIV', 'POW',
    'UNARY_MINUS', 'UNARY_PLUS',
}

# Ruta default del archivo .txt que el programa escribe en runtime.
DEFAULT_LOG_PATH = r'C:\emu8086\vdrive\C\output\queries.txt'

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

    def __init__(self, symbol_table=None, dataset_path: str | None = None,
                 output_log_path: str | None = None):
        self.symbol_table = symbol_table
        self.dataset_path = dataset_path or DEFAULT_DATASET_PATH
        self.output_log_path = output_log_path or DEFAULT_LOG_PATH

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
        # queries: lista de tuplas (nombre, nivel). nivel in {basic,explain,why}.
        self.queries: list[tuple[str, str]] = []
        # rule_name -> arbol estructural (para explain/why)
        self.rule_structures: dict[str, dict] = {}
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
        # Contador de pantallas emitidas (cada query+nivel = 1 pantalla).
        self._screen_counter = 0
        # Contador de mensajes auxiliares para explain/why (labels unicos).
        self._aux_msg_counter = 0
        # Mensajes auxiliares emitidos por explain/why: lista de (label, db_line)
        self._aux_msgs: list[tuple[str, str]] = []

        # Buffers de salida
        self._data_lines: list[str] = []
        self._code_lines: list[str] = []

    # ---------------- API pública ----------------

    def generate(self, quadruples: list[Quadruple]) -> str:
        """Genera el .asm completo a partir de la IR optimizada."""
        self._reset(quadruples)
        self._analyze()
        # OJO: el codigo emite primero porque registra mensajes auxiliares
        # (DB '...') de explain/why en self._aux_msgs, y esos mensajes deben
        # aparecer en la seccion .DATA emitida despues.
        self._emit_code()
        self._emit_data()
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
        self.rule_structures = {}
        self.temps = set()
        self.datasets = {}
        self.datasets_with_filter = {}
        self.column_aliases = {}
        self.column_datasets = {}
        self.absorbed_cmp_temps = set()
        self._cmp_label_counter = 0
        self._screen_counter = 0
        self._aux_msg_counter = 0
        self._aux_msgs = []
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
                    # Reconstruir el arbol estructural de la regla
                    # caminando hacia atras desde el temp asignado.
                    self.rule_structures[q.result] = (
                        self._build_rule_tree(q.arg1, i)
                    )
                continue

            if op == 'QUERY':
                if isinstance(q.arg1, str):
                    self.queries.append((q.arg1, 'basic'))
                continue

            if op == 'QUERY_EXPLAIN':
                if isinstance(q.arg1, str):
                    self.queries.append((q.arg1, 'explain'))
                continue

            if op == 'QUERY_WHY':
                if isinstance(q.arg1, str):
                    self.queries.append((q.arg1, 'why'))
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

    def _build_rule_tree(self, value, end_idx: int) -> dict:
        """Reconstruye el arbol AST de una regla caminando hacia atras
        por la IR. Devuelve un dict con 'kind' in {'logic','cmp','fact_ref','literal','unknown'}.
        """
        # Si es un literal numerico / booleano, devolverlo
        if isinstance(value, (int, float)):
            return {'kind': 'literal', 'value': value}
        if not isinstance(value, str):
            return {'kind': 'unknown', 'value': value}

        # Si NO es un temporal tN, debe ser un nombre (fact, rule, columna, etc.)
        if not (value.startswith('t') and value[1:].isdigit()):
            cat = self._category(value)
            if cat == 'fact':
                return {'kind': 'fact_ref', 'name': value}
            if cat == 'rule':
                return {'kind': 'rule_ref', 'name': value}
            return {'kind': 'name', 'value': value}

        # Es un temp -- buscar el quad que lo produce
        for j in range(end_idx - 1, -1, -1):
            q = self.quads[j]
            if q.result != value:
                continue
            if q.op in ('AND', 'OR'):
                return {
                    'kind': 'logic',
                    'op': q.op,
                    'left':  self._build_rule_tree(q.arg1, j),
                    'right': self._build_rule_tree(q.arg2, j),
                }
            if q.op == 'NOT':
                return {
                    'kind': 'logic',
                    'op': 'NOT',
                    'operand': self._build_rule_tree(q.arg1, j),
                }
            if q.op in _CMP_OP_INFO:
                _, _, sym = _CMP_OP_INFO[q.op]
                return {
                    'kind': 'cmp',
                    'op': q.op,
                    'sym': sym,
                    'left':  self._build_rule_tree(q.arg1, j),
                    'right': self._build_rule_tree(q.arg2, j),
                }
            if q.op == 'ASSIGN':
                return self._build_rule_tree(q.arg1, j)
            # PROB, PROB_GIVEN, etc. no aparecen en arbol de reglas
            break
        return {'kind': 'unknown', 'value': value}

    def _category(self, name: str) -> str | None:
        if self.symbol_table is None or not isinstance(name, str):
            return None
        sym = self.symbol_table.get(name)
        return sym.category if sym else None

    # ---------------- helpers de explain / why ----------------

    @staticmethod
    def _fmt_threshold(node: dict) -> str:
        """Da formato a un nodo literal/name de umbral para mostrarlo."""
        if not isinstance(node, dict):
            return '?'
        kind = node.get('kind')
        if kind == 'literal':
            v = node.get('value')
            if isinstance(v, float):
                # Mostramos como porcentaje 0..100 si parece probabilidad
                if 0.0 <= v <= 1.0:
                    return f"{int(round(v * 100))}"
                return f"{v}"
            return f"{v}"
        if kind == 'fact_ref':
            return node.get('name', '?')
        if kind == 'name':
            return str(node.get('value', '?'))
        return '?'

    def _serialize_rule_expr(self, tree: dict) -> str:
        """Convierte el arbol de una regla en texto legible."""
        if not isinstance(tree, dict):
            return '?'
        kind = tree.get('kind')
        if kind == 'logic':
            op = tree.get('op')
            if op == 'NOT':
                return f"not {self._serialize_rule_expr(tree.get('operand', {}))}"
            left  = self._serialize_rule_expr(tree.get('left', {}))
            right = self._serialize_rule_expr(tree.get('right', {}))
            sym = {'AND': 'and', 'OR': 'or'}.get(op, op.lower() if op else '?')
            return f"({left} {sym} {right})"
        if kind == 'cmp':
            left  = self._serialize_rule_expr(tree.get('left', {}))
            right = self._fmt_threshold(tree.get('right', {}))
            return f"{left} {tree.get('sym','?')} {right}"
        if kind == 'fact_ref':
            return tree.get('name', '?')
        if kind == 'rule_ref':
            return tree.get('name', '?')
        if kind == 'literal':
            return self._fmt_threshold(tree)
        if kind == 'name':
            return str(tree.get('value', '?'))
        return '?'

    def _collect_cmps(self, tree: dict, out: list[dict]):
        """Recoge nodos de comparacion (fact > umbral) en orden in-order."""
        if not isinstance(tree, dict):
            return
        kind = tree.get('kind')
        if kind == 'logic':
            if tree.get('op') == 'NOT':
                self._collect_cmps(tree.get('operand', {}), out)
            else:
                self._collect_cmps(tree.get('left', {}), out)
                self._collect_cmps(tree.get('right', {}), out)
        elif kind == 'cmp':
            out.append(tree)

    def _collect_fact_refs(self, tree: dict, out: list[str]):
        """Recoge nombres de facts referenciados (en orden, sin duplicados)."""
        if not isinstance(tree, dict):
            return
        kind = tree.get('kind')
        if kind == 'logic':
            if tree.get('op') == 'NOT':
                self._collect_fact_refs(tree.get('operand', {}), out)
            else:
                self._collect_fact_refs(tree.get('left', {}), out)
                self._collect_fact_refs(tree.get('right', {}), out)
        elif kind == 'cmp':
            self._collect_fact_refs(tree.get('left', {}), out)
            self._collect_fact_refs(tree.get('right', {}), out)
        elif kind == 'fact_ref':
            name = tree.get('name')
            if name and name not in out:
                out.append(name)

    def _new_msg_label(self) -> str:
        label = f"em{self._aux_msg_counter}"
        self._aux_msg_counter += 1
        return label

    @staticmethod
    def _quote_asm_text(text: str) -> str:
        """Convierte un texto Python a una lista de tokens DB que emu8086
        sabe interpretar. Se separan comillas embebidas si las hubiera.
        """
        if "'" in text:
            text = text.replace("'", "`")
        return f"'{text}'"

    def _emit_msg(self, text: str, newline: bool = False) -> str:
        """Reserva una etiqueta unica en .DATA con el texto + '$'.
        Si `text` contiene '\\n', cada salto se traduce a CRLF (13,10) entre
        fragmentos DB. Si newline=True, agrega un CRLF extra antes del '$'.
        Devuelve el label.
        """
        label = self._new_msg_label()
        parts: list[str] = []
        if text:
            segments = text.split('\n')
            for i, seg in enumerate(segments):
                if seg:
                    parts.append(self._quote_asm_text(seg))
                if i < len(segments) - 1:
                    parts.append('13')
                    parts.append('10')
        if newline:
            parts.append('13')
            parts.append('10')
        parts.append("'$'")
        db_line = f"    {label:<10} DB {', '.join(parts)}"
        self._aux_msgs.append((label, db_line))
        return label

    @staticmethod
    def _entity_noun(dataset_name: str | None) -> str:
        """Sustantivo generico para hablar de las filas del dataset en el
        razonamiento. Si el nombre tiene underscore tomamos el primer
        segmento ('alumnos_foco' -> 'alumnos'); si no, devolvemos
        'registros' como palabra neutra.
        """
        if not isinstance(dataset_name, str) or not dataset_name:
            return 'registros'
        head = dataset_name.split('_', 1)[0]
        return head if head else 'registros'

    def _fact_cond_text(self, meta: dict) -> str:
        """Texto puro de la condicion '<col> <op> <value>' (sin 'P(...)')."""
        kind = meta.get('kind', 'simple')
        if kind == 'given':
            a = f"{meta.get('col_a','?')} {meta.get('op_a','?')} {meta.get('value_a','?')}"
            b = f"{meta.get('col_b','?')} {meta.get('op_b','?')} {meta.get('value_b','?')}"
            return f"{a} dado {b}"
        return f"{meta.get('col','?')} {meta.get('op','?')} {meta.get('value','?')}"

    def _fact_cond_a(self, meta: dict) -> str:
        return f"{meta.get('col_a','?')} {meta.get('op_a','?')} {meta.get('value_a','?')}"

    def _fact_cond_b(self, meta: dict) -> str:
        return f"{meta.get('col_b','?')} {meta.get('op_b','?')} {meta.get('value_b','?')}"

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
                # Conteos crudos usados por explain/why para la 'lectura'
                # natural: cnt = filas que cumplen, tot = filas evaluadas
                # (para 'given', cnt = A AND B, tot = B).
                D(f"    fact_{name}_cnt DW 0    ; matches")
                D(f"    fact_{name}_tot DW 0    ; total considerado")
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
            # Solo emitir una vez por nombre aunque haya varios niveles
            # (basic/explain/why) sobre el mismo query; preservamos el
            # orden de aparicion para que el .asm sea determinista.
            seen: set[str] = set()
            for name, _level in self.queries:
                if name in seen:
                    continue
                seen.add(name)
                D(f"    msg_{name:<16} DB '{name} = $'")
            D("")

        # Mensajes de evidencia: deben estar en DATA (no en CODE), porque
        # show_result los imprime con INT 21h/9h que usa DS:DX. Si vivieran
        # en CODE (que es donde está output_devices.asm tras el include),
        # DS:DX apuntaría a memoria equivocada y la búsqueda del '$' falla.
        # El texto coincide con el formato que espera show_result de Fanny.
        # CRLF al inicio Y al final para que con múltiples queries cada
        # resultado quede en su propia línea (sin pegarse con el siguiente).
        D("    msg_evid_baja DB 13, 10, 'Evidencia: BAJA', 13, 10, '$'")
        D("    msg_evid_mod  DB 13, 10, 'Evidencia: MODERADA', 13, 10, '$'")
        D("    msg_evid_alta DB 13, 10, 'Evidencia: ALTA', 13, 10, '$'")
        # Prompt para pausar entre queries y dar tiempo a ver el LED+semáforo.
        # show_result lo imprime y espera una tecla con INT 21h/AH=07h.
        # CRLF al principio Y dos al final → el prompt queda con una línea
        # en blanco arriba y otra abajo, separando visualmente cada bloque
        # de query cuando hay varios.
        D("    msg_continuar DB 13, 10, '>> Presiona una tecla para continuar...', 13, 10, 13, 10, '$'")
        D("    msg_err_file  DB 'Error abriendo el dataset.', 13, 10, '$'")
        D("")
        D("    ; -- Logging a archivo y paginacion por flechas --")
        D(f"    OUTPUT_PATH  DB '{self.output_log_path}', 0")
        D("    LOG_HANDLE   DW 0")
        D("    cur_page     DB 0")
        D("    max_page     DB 0")
        D("    nav_prompt   DB 13, 10, '>> Flechas: <- anterior, -> siguiente, ESC para salir', 13, 10, '$'")
        D("    itoa_buf     DB '       ', '$', 0  ; espacio para hasta 6 digitos + '$'")
        D("    msg_true     DB ' SE CUMPLE', 13, 10, '$'")
        D("    msg_false    DB ' NO SE CUMPLE', 13, 10, '$'")
        D("")

        # Mensajes auxiliares para explain/why (generados por los emisores).
        if self._aux_msgs:
            D("    ; -- Mensajes para explain/why --")
            for _, line in self._aux_msgs:
                D(line)
            D("")

    # ---------------- pase 2.b: sección CODE ----------------

    def _emit_code(self):
        def C(s: str):
            # Etiquetas (token único terminado en ':') van a columna 0;
            # el resto se indenta con 4 espacios.
            if s and s.endswith(':') and ' ' not in s:
                self._code_lines.append(s)
            else:
                self._code_lines.append("    " + s if s else "")

        # 0) Abrir archivo de log para escribir los queries en disco
        C("; ---- Abrir archivo de log (queries -> .txt) ----")
        C("CALL open_log_file")
        C("")

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

        # 3) Despues del ultimo screen: max_page = el indice de la ultima
        #    pagina que de verdad tiene contenido (acotado a 3 porque solo
        #    hay 4 paginas; con mas screens estas se sobrescriben en wrap,
        #    pero el .txt log conserva todo).
        if self._screen_counter == 0:
            max_page = 0
        else:
            max_page = min(self._screen_counter - 1, 3)
        C("; ---- Navegacion libre por flechas tras los queries ----")
        C(f"MOV BYTE PTR max_page, {max_page}")
        C("CALL final_nav_loop")
        C("CALL close_log_file")
        C("")

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
            return self._emit_query(q, level='basic')
        if op == 'QUERY_EXPLAIN':
            return self._emit_query(q, level='explain')
        if op == 'QUERY_WHY':
            return self._emit_query(q, level='why')
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

    def _emit_query(self, q: Quadruple, level: str = 'basic') -> list[str]:
        target = q.arg1
        # Paginacion: cada pantalla (basic/explain/why) ocupa su propia
        # pagina; con wrap 0..3 cuando hay mas pantallas que paginas
        # disponibles. El .txt log siempre captura todo.
        page = self._screen_counter % 4
        self._screen_counter += 1

        page_prefix = [
            f"; --- pantalla {self._screen_counter - 1} (pagina {page}) "
            f"query {target} [{level}] ---",
            f"MOV AL, {page}",
            "CALL switch_to_page",
            "",
        ]

        if level == 'explain':
            return page_prefix + self._emit_explain_body(target)
        if level == 'why':
            return page_prefix + self._emit_why_body(target)
        return page_prefix + self._emit_basic_body(target)

    # ---- emisores de las tres pantallas ----

    def _emit_basic_body(self, target: str) -> list[str]:
        slot = self._slot_of(target)
        return [
            f"; query {target} (basico)",
            f"MOV AX, {slot}",
            f"LEA SI, msg_{target}",
            "CALL show_result",
            "",
        ]

    def _slot_of(self, target: str) -> str:
        cat = self._category(target)
        if cat == 'rule':
            return f"rule_{target}"
        return f"fact_{target}"

    def _emit_print_str(self, label: str) -> list[str]:
        return [f"LEA SI, {label}", "CALL print_log_str"]

    def _emit_print_int(self, slot: str) -> list[str]:
        return [f"MOV AX, {slot}", "CALL print_log_int"]

    # ---- helpers compartidos por explain / why ----

    def _emit_fact_lectura(self, fname: str, meta: dict,
                           indent: str = '   ') -> list[str]:
        """Imprime el bloque 'lectura' de un fact en runtime.

        Forma simple ('fact = P(col op val)'):
            <fact> = <pct>%
              <cnt> de <tot> <entidad> de <dataset>
              cumplen <col> <op> <val>.

        Forma 'given' (P(A given B)):
            <fact> = <pct>%
              de los <tot> <entidad> con <B>,
              <cnt> tambien cumplen <A>.
        """
        lines: list[str] = []
        kind = meta.get('kind', 'simple')
        dataset = meta.get('dataset') or ''
        entidad = self._entity_noun(dataset)
        ds_phrase = f" de {dataset}" if dataset else ''

        # Linea 1: "<fact> = <pct>%"
        head = self._emit_msg(f'{indent}{fname} = ', newline=False)
        tail = self._emit_msg('%', newline=True)
        lines.extend(self._emit_print_str(head))
        lines.extend(self._emit_print_int(f'fact_{fname}'))
        lines.extend(self._emit_print_str(tail))

        if kind == 'given':
            cond_a = self._fact_cond_a(meta)
            cond_b = self._fact_cond_b(meta)
            lectura_head = self._emit_msg(
                f'{indent}  de los ', newline=False
            )
            lectura_mid = self._emit_msg(
                f' {entidad}{ds_phrase} con {cond_b},', newline=True
            )
            lectura_cnt_pre = self._emit_msg(
                f'{indent}  ', newline=False
            )
            lectura_tail = self._emit_msg(
                f' tambien cumplen {cond_a}.', newline=True
            )
            lines.extend(self._emit_print_str(lectura_head))
            lines.extend(self._emit_print_int(f'fact_{fname}_tot'))
            lines.extend(self._emit_print_str(lectura_mid))
            lines.extend(self._emit_print_str(lectura_cnt_pre))
            lines.extend(self._emit_print_int(f'fact_{fname}_cnt'))
            lines.extend(self._emit_print_str(lectura_tail))
        else:
            cond = self._fact_cond_text(meta)
            lectura_head = self._emit_msg(
                f'{indent}  ', newline=False
            )
            lectura_mid = self._emit_msg(
                f' de ', newline=False
            )
            lectura_tail = self._emit_msg(
                f' {entidad}{ds_phrase} cumplen {cond}.', newline=True
            )
            lines.extend(self._emit_print_str(lectura_head))
            lines.extend(self._emit_print_int(f'fact_{fname}_cnt'))
            lines.extend(self._emit_print_str(lectura_mid))
            lines.extend(self._emit_print_int(f'fact_{fname}_tot'))
            lines.extend(self._emit_print_str(lectura_tail))
        return lines

    def _emit_cmp_eval(self, fact_name: str, sym: str, threshold: str,
                       ir_op: str, indent: str = '   ') -> list[str]:
        """Imprime '<fact> = <val>% (umbral <sym> <th>%) -> SE CUMPLE/NO SE CUMPLE'
        decidiendo en runtime cual de los dos imprimir.
        """
        true_jmp = _CMP_OP_INFO.get(ir_op, ('JE', 'JNE', sym))[0]
        label_id = self._cmp_label_counter
        self._cmp_label_counter += 1
        label_true = f"xt_{label_id}"
        label_done = f"xd_{label_id}"

        head = self._emit_msg(f'{indent}{fact_name} = ', newline=False)
        mid  = self._emit_msg(f'% (umbral {sym} {threshold}%) ->', newline=False)
        lines: list[str] = []
        lines.extend(self._emit_print_str(head))
        lines.extend(self._emit_print_int(f'fact_{fact_name}'))
        lines.extend(self._emit_print_str(mid))
        # Decision runtime: TRUE vs FALSE
        lines.append(f"MOV AX, fact_{fact_name}")
        lines.append(f"CMP AX, {threshold}")
        lines.append(f"{true_jmp} {label_true}")
        lines.append("LEA SI, msg_false")
        lines.append("CALL print_log_str")
        lines.append(f"JMP {label_done}")
        lines.append(f"{label_true}:")
        lines.append("LEA SI, msg_true")
        lines.append("CALL print_log_str")
        lines.append(f"{label_done}:")
        return lines

    def _emit_explain_body(self, target: str) -> list[str]:
        """Pantalla 'explain': desglose tecnico del query.

        Diseno (independiente del dominio del dataset; todo el vocabulario
        viene del programa Snaptics):
            =========================================================
              EXPLAIN: <target> = <val>%
            =========================================================
              HECHOS:
                <fact> = <val>%
                  <cnt> de <tot> <entidad> de <dataset>
                  cumplen <col> <op> <val>.
                ...
              REGLA:
                <target> := <expr>
              EVALUACION:
                <fact> = <val>% (umbral <op> <th>%) -> SE CUMPLE / NO SE CUMPLE
                ...
              CONCLUSION: <target> = <val>%
            =========================================================
        """
        cat = self._category(target)
        slot = self._slot_of(target)
        lines: list[str] = []

        sep_label = self._emit_msg(
            '=========================================================',
            newline=True,
        )
        head_pre = self._emit_msg(f'  EXPLAIN: {target} = ', newline=False)
        head_pct = self._emit_msg('%', newline=True)

        lines.append("; explain: encabezado")
        lines.extend(self._emit_print_str(sep_label))
        lines.extend(self._emit_print_str(head_pre))
        lines.extend(self._emit_print_int(slot))
        lines.extend(self._emit_print_str(head_pct))
        lines.extend(self._emit_print_str(sep_label))

        if cat == 'rule' and target in self.rule_structures:
            tree = self.rule_structures[target]

            facts_label = self._emit_msg(' HECHOS:', newline=True)
            lines.extend(self._emit_print_str(facts_label))

            fact_refs: list[str] = []
            self._collect_fact_refs(tree, fact_refs)
            for fname in fact_refs:
                meta = self.facts_derived.get(fname)
                if meta:
                    lines.extend(self._emit_fact_lectura(fname, meta))
                else:
                    # fact con valor constante: solo mostrar valor
                    head = self._emit_msg(f'   {fname} = ', newline=False)
                    tail = self._emit_msg('%', newline=True)
                    lines.extend(self._emit_print_str(head))
                    lines.extend(self._emit_print_int(f'fact_{fname}'))
                    lines.extend(self._emit_print_str(tail))

            # Regla evaluada
            expr_txt = self._serialize_rule_expr(tree)
            rule_block = self._emit_msg(
                f' REGLA:\n   {target} := {expr_txt}', newline=True
            )
            lines.extend(self._emit_print_str(rule_block))

            # Evaluacion: una linea por comparacion crisp en la regla
            cmps: list[dict] = []
            self._collect_cmps(tree, cmps)
            if cmps:
                eval_lbl = self._emit_msg(' EVALUACION:', newline=True)
                lines.extend(self._emit_print_str(eval_lbl))
                for cmp_node in cmps:
                    left = cmp_node.get('left', {})
                    right = cmp_node.get('right', {})
                    sym = cmp_node.get('sym', '?')
                    ir_op = cmp_node.get('op', '')
                    fact_name = left.get('name') if isinstance(left, dict) else None
                    threshold = self._fmt_threshold(right)
                    if fact_name:
                        lines.extend(self._emit_cmp_eval(
                            fact_name, sym, threshold, ir_op
                        ))

                # Linea explicativa del operador raiz (si es AND/OR)
                root_op = tree.get('op') if tree.get('kind') == 'logic' else None
                if root_op == 'OR':
                    op_lbl = self._emit_msg(
                        '\n   OR: basta que una condicion se cumpla\n'
                        '   para que la regla se active.',
                        newline=True,
                    )
                    lines.extend(self._emit_print_str(op_lbl))
                elif root_op == 'AND':
                    op_lbl = self._emit_msg(
                        '\n   AND: todas las condiciones deben\n'
                        '   cumplirse para que la regla se active.',
                        newline=True,
                    )
                    lines.extend(self._emit_print_str(op_lbl))
        else:
            # query directo a un fact: mostrar su lectura
            meta = self.facts_derived.get(target)
            if meta:
                fact_hdr = self._emit_msg(' HECHO:', newline=True)
                lines.extend(self._emit_print_str(fact_hdr))
                lines.extend(self._emit_fact_lectura(target, meta))
                desc_lbl = self._emit_msg(
                    f'\n DEFINICION: {self._describe_fact(meta)}',
                    newline=True,
                )
                lines.extend(self._emit_print_str(desc_lbl))

        # Conclusion
        concl_pre = self._emit_msg(
            '\n CONCLUSION: ' + target + ' = ', newline=False
        )
        concl_pct = self._emit_msg('%', newline=True)
        lines.extend(self._emit_print_str(concl_pre))
        lines.extend(self._emit_print_int(slot))
        lines.extend(self._emit_print_str(concl_pct))
        lines.extend(self._emit_print_str(sep_label))

        lines.append("CALL nav_pause")
        lines.append("")
        return lines

    def _emit_why_body(self, target: str) -> list[str]:
        """Pantalla 'why': razonamiento causal con conteos reales.

        =========================================================
          WHY: <target> = <val>%
        =========================================================
          Origen: <dataset> (<where_cond>)
          HECHO 1: <fact> = <val>%
            <cnt> de <tot> <entidad> de <dataset>
            cumplen <cond>.
            Umbral: <op> <th>%. SE CUMPLE / NO SE CUMPLE.
          ...
          --------------------------------------------------------
          RAZONAMIENTO:
            La regla combina los hechos con <OR/AND>.
          FACTOR DECISIVO (cuando hay 2 hechos):
            <fact_dominante> — <cnt> de <tot> <entidad> cumplen.
          --------------------------------------------------------
          CONCLUSION: <target> = <val>%
        =========================================================
        """
        cat = self._category(target)
        slot = self._slot_of(target)
        lines: list[str] = []

        sep_label = self._emit_msg(
            '=========================================================',
            newline=True,
        )
        head_pre = self._emit_msg(f'  WHY: {target} = ', newline=False)
        head_pct = self._emit_msg('%', newline=True)

        lines.append("; why: encabezado")
        lines.extend(self._emit_print_str(sep_label))
        lines.extend(self._emit_print_str(head_pre))
        lines.extend(self._emit_print_int(slot))
        lines.extend(self._emit_print_str(head_pct))
        lines.extend(self._emit_print_str(sep_label))

        if cat == 'rule' and target in self.rule_structures:
            tree = self.rule_structures[target]

            # 1) Origen: dataset del primer fact con metadata
            fact_refs: list[str] = []
            self._collect_fact_refs(tree, fact_refs)

            origen_text = self._build_origen_text(fact_refs)
            if origen_text:
                origen_lbl = self._emit_msg(' ' + origen_text, newline=True)
                lines.extend(self._emit_print_str(origen_lbl))
                lines.append("")

            # 2) Cada hecho: lectura + evaluacion vs umbral
            cmps: list[dict] = []
            self._collect_cmps(tree, cmps)
            cmps_by_fact = {}
            for c in cmps:
                left = c.get('left', {})
                fn = left.get('name') if isinstance(left, dict) else None
                if fn:
                    cmps_by_fact[fn] = c

            for idx, fname in enumerate(fact_refs, start=1):
                meta = self.facts_derived.get(fname)
                hdr = self._emit_msg(f' HECHO {idx}: {fname}', newline=True)
                lines.extend(self._emit_print_str(hdr))
                if meta:
                    lines.extend(self._emit_fact_lectura(fname, meta, indent='   '))
                cmp_node = cmps_by_fact.get(fname)
                if cmp_node:
                    sym = cmp_node.get('sym', '?')
                    ir_op = cmp_node.get('op', '')
                    threshold = self._fmt_threshold(cmp_node.get('right', {}))
                    umbral_lbl = self._emit_msg(
                        f'   Umbral exigido: {sym} {threshold}%. ',
                        newline=False,
                    )
                    lines.extend(self._emit_print_str(umbral_lbl))
                    lines.extend(self._emit_cmp_decision(
                        fname, threshold, ir_op
                    ))
                lines.append("")

            # 3) Razonamiento + factor decisivo
            root_op = tree.get('op') if tree.get('kind') == 'logic' else None
            sep2 = self._emit_msg(
                ' ---------------------------------------------------------',
                newline=True,
            )
            lines.extend(self._emit_print_str(sep2))

            if root_op == 'OR':
                razon_lbl = self._emit_msg(
                    ' RAZONAMIENTO:\n'
                    '   La regla combina los hechos con OR.\n'
                    '   Basta una condicion verdadera para\n'
                    '   activar la regla.',
                    newline=True,
                )
                lines.extend(self._emit_print_str(razon_lbl))
            elif root_op == 'AND':
                razon_lbl = self._emit_msg(
                    ' RAZONAMIENTO:\n'
                    '   La regla combina los hechos con AND.\n'
                    '   Todas las condiciones deben cumplirse\n'
                    '   para activar la regla.',
                    newline=True,
                )
                lines.extend(self._emit_print_str(razon_lbl))
            else:
                razon_lbl = self._emit_msg(
                    f' RAZONAMIENTO:\n'
                    f'   La regla evalua la expresion:\n'
                    f'   {self._serialize_rule_expr(tree)}',
                    newline=True,
                )
                lines.extend(self._emit_print_str(razon_lbl))

            # Factor decisivo: solo si hay exactamente 2 facts referenciados
            if len(fact_refs) == 2 and root_op in ('OR', 'AND'):
                lines.extend(self._emit_factor_decisivo(
                    fact_refs[0], fact_refs[1], root_op
                ))

            lines.extend(self._emit_print_str(sep2))
        else:
            meta = self.facts_derived.get(target)
            if meta:
                hdr = self._emit_msg(' HECHO:', newline=True)
                lines.extend(self._emit_print_str(hdr))
                lines.extend(self._emit_fact_lectura(target, meta))
                desc_lbl = self._emit_msg(
                    f'\n Este hecho mide: {self._describe_fact(meta)}',
                    newline=True,
                )
                lines.extend(self._emit_print_str(desc_lbl))

        # Conclusion final
        concl_pre = self._emit_msg(
            '\n CONCLUSION: ' + target + ' = ', newline=False
        )
        concl_pct = self._emit_msg('%', newline=True)
        lines.extend(self._emit_print_str(concl_pre))
        lines.extend(self._emit_print_int(slot))
        lines.extend(self._emit_print_str(concl_pct))
        lines.extend(self._emit_print_str(sep_label))

        lines.append("CALL nav_pause")
        lines.append("")
        return lines

    def _build_origen_text(self, fact_refs: list[str]) -> str:
        """Construye el texto 'Origen: <dataset> (con <where>)'.
        Toma el dataset del primer fact con metadata.
        """
        for fname in fact_refs:
            meta = self.facts_derived.get(fname)
            if meta:
                dataset = meta.get('dataset')
                if dataset:
                    entidad = self._entity_noun(dataset)
                    filt = self.datasets_with_filter.get(dataset)
                    if filt:
                        return (
                            f"Origen: {dataset} ({entidad} con "
                            f"{filt['col']} {filt['op']} {filt['value']})"
                        )
                    return f"Origen: {dataset} ({entidad})"
        return ''

    def _emit_cmp_decision(self, fact_name: str, threshold: str,
                           ir_op: str) -> list[str]:
        """Solo imprime 'SE CUMPLE' / 'NO SE CUMPLE' decidiendo en runtime."""
        true_jmp = _CMP_OP_INFO.get(ir_op, ('JE', 'JNE', '?'))[0]
        label_id = self._cmp_label_counter
        self._cmp_label_counter += 1
        label_true = f"xc_{label_id}"
        label_done = f"xe_{label_id}"
        return [
            f"MOV AX, fact_{fact_name}",
            f"CMP AX, {threshold}",
            f"{true_jmp} {label_true}",
            "LEA SI, msg_false",
            "CALL print_log_str",
            f"JMP {label_done}",
            f"{label_true}:",
            "LEA SI, msg_true",
            "CALL print_log_str",
            f"{label_done}:",
        ]

    def _emit_factor_decisivo(self, fact_a: str, fact_b: str,
                              op: str) -> list[str]:
        """Determina en runtime cual de dos facts es el factor decisivo.
        Para OR: el de mayor cobertura. Para AND: el de menor (mas justo).
        Imprime una descripcion concreta con sus conteos.
        """
        meta_a = self.facts_derived.get(fact_a) or {}
        meta_b = self.facts_derived.get(fact_b) or {}
        entidad_a = self._entity_noun(meta_a.get('dataset'))
        entidad_b = self._entity_noun(meta_b.get('dataset'))

        if op == 'OR':
            header_text = (
                ' FACTOR DECISIVO:\n'
                '   La condicion con mayor cobertura\n'
                '   es la que mas peso aporta:'
            )
            jump_if_a_wins = 'JG'   # fact_a > fact_b
        else:  # AND
            header_text = (
                ' CONDICION MAS AJUSTADA:\n'
                '   La condicion con menor cobertura\n'
                '   es la que limita la regla:'
            )
            jump_if_a_wins = 'JL'   # fact_a < fact_b

        # Mensajes describiendo cada caso (estaticos, generados en compile).
        msg_a = self._emit_msg(
            f'   -> {fact_a}: ', newline=False
        )
        msg_a_mid = self._emit_msg(
            f' de ', newline=False
        )
        msg_a_tail = self._emit_msg(
            f' {entidad_a} cumplen.', newline=True
        )
        msg_b = self._emit_msg(
            f'   -> {fact_b}: ', newline=False
        )
        msg_b_mid = self._emit_msg(
            f' de ', newline=False
        )
        msg_b_tail = self._emit_msg(
            f' {entidad_b} cumplen.', newline=True
        )
        header_lbl = self._emit_msg(header_text, newline=True)

        label_id = self._cmp_label_counter
        self._cmp_label_counter += 1
        lbl_a = f"fd_a_{label_id}"
        lbl_done = f"fd_d_{label_id}"

        lines: list[str] = []
        lines.extend(self._emit_print_str(header_lbl))
        lines.append(f"MOV AX, fact_{fact_a}")
        lines.append(f"CMP AX, fact_{fact_b}")
        lines.append(f"{jump_if_a_wins} {lbl_a}")
        # B gana: imprimir descripcion de B
        lines.extend(self._emit_print_str(msg_b))
        lines.extend(self._emit_print_int(f'fact_{fact_b}_cnt'))
        lines.extend(self._emit_print_str(msg_b_mid))
        lines.extend(self._emit_print_int(f'fact_{fact_b}_tot'))
        lines.extend(self._emit_print_str(msg_b_tail))
        lines.append(f"JMP {lbl_done}")
        lines.append(f"{lbl_a}:")
        # A gana
        lines.extend(self._emit_print_str(msg_a))
        lines.extend(self._emit_print_int(f'fact_{fact_a}_cnt'))
        lines.extend(self._emit_print_str(msg_a_mid))
        lines.extend(self._emit_print_int(f'fact_{fact_a}_tot'))
        lines.extend(self._emit_print_str(msg_a_tail))
        lines.append(f"{lbl_done}:")
        return lines

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
                  dataset_path: str | None = None,
                  output_log_path: str | None = None) -> dict:
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

    gen = CodeGenerator(symbol_table=symbol_table,
                        dataset_path=dataset_path,
                        output_log_path=output_log_path)
    asm = gen.generate(quads)

    return {
        'asm':           asm,
        'success':       len(gen.errors) == 0,
        'errors':        [e.format() for e in gen.errors],
        'derived_facts': gen.derived_facts_metadata(),
        'metadata':      gen.metadata(),
    }
