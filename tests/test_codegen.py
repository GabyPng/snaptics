"""
Pruebas del generador de código objeto (emu8086).

Ejecuta:
    python tests/test_codegen.py
o:
    python -m tests.test_codegen

Estrategia (espejo de tests/test_optimizer.py): se construyen cuádruplas
y una symbol_table a mano para probar SOLO la fase de codegen, sin
depender del resto del pipeline.

Al final se intenta también una corrida del pipeline completo a partir
de un .snp; si falla en fases previas (por ejemplo el type_checker
trata los facts como 'real' y rechaza fact AND fact), se reporta como
'esperado: pendiente' y no se considera fallo del codegen.

Los .asm generados se escriben en tests/out/ para abrirlos en emu8086.
"""

from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

from ir_generator import Quadruple
from symbol_table import SymbolTable
from code_generator import generate_code, CodeGenerator


# ==================== helpers ====================

OUT_DIR = os.path.join(_ROOT, 'tests', 'out')
os.makedirs(OUT_DIR, exist_ok=True)


def _wrap(quads: list[Quadruple]) -> dict:
    """Envoltorio del estilo `optimize_ir` para alimentar al codegen."""
    return {
        'success':    True,
        'quadruples': quads,
        'formatted':  '',
        'original':   list(quads),
        'report':     '',
        'stats':      {},
        'reduction':  0,
    }


def _symbol_table(*entries) -> SymbolTable:
    """entries: secuencia de tuplas (name, category, data_type)."""
    st = SymbolTable()
    for name, cat, dt in entries:
        st.add(name, cat, dt, line=0)
    return st


def _write(name: str, asm: str):
    path = os.path.join(OUT_DIR, name + '.asm')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(asm)
    return path


# ==================== aserciones simples ====================

class AssertionTracker:
    def __init__(self):
        self.passed = 0
        self.failed: list[str] = []

    def check(self, cond: bool, label: str):
        if cond:
            self.passed += 1
        else:
            self.failed.append(label)

    def report(self) -> str:
        if not self.failed:
            return f"  {self.passed} aserción(es) ok"
        lines = [f"  {self.passed} ok, {len(self.failed)} FALLOS:"]
        for f in self.failed:
            lines.append(f"    - {f}")
        return "\n".join(lines)


# ==================== caso 1: fact derivado + query ====================

def caso_1_query_simple(t: AssertionTracker):
    print("\n[caso 1] fact derivado + query directa")
    # Snaptics equivalente:
    #     dataset ventas = import from "ventas.csv"
    #     dataset v = select monto: real from ventas
    #     fact altas = P(ventas.monto > 500)
    #     query altas
    quads = [
        Quadruple('LOAD_DATASET', 'ventas.csv', None, 'ventas'),
        Quadruple('GT',   'monto', 500, 't0'),
        Quadruple('PROB', 't0',    None, 't1'),
        Quadruple('ASSIGN', 't1',  None, 'altas'),
        Quadruple('QUERY',  'altas', None, None),
    ]
    st = _symbol_table(
        ('ventas', 'dataset', 'dataset'),
        ('monto',  'column',  'real'),
        ('altas',  'fact',    'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})

    t.check(res['success'],
            "codegen no produjo errores")
    t.check('altas' in res['derived_facts'],
            "se detectó 'altas' como fact derivado")
    t.check(res['derived_facts'].get('altas', {}).get('col') == 'monto',
            "metadatos del fact: columna = monto")
    t.check(res['derived_facts'].get('altas', {}).get('value') == 500,
            "metadatos del fact: umbral = 500")
    t.check(res['derived_facts'].get('altas', {}).get('op') == '>',
            "metadatos del fact: operador = >")
    t.check('CALL count_altas' in res['asm'],
            "código llama a count_altas")
    t.check('LEA SI, msg_altas' in res['asm'],
            "código carga el mensaje de la query")
    t.check('CALL show_result' in res['asm'],
            "código llama a show_result")
    t.check('abrirArchivo 2, RUTA' in res['asm'],
            "código abre el dataset")

    path = _write('caso1_query_simple', res['asm'])
    print(f"  -> {path}")
    print(t.report())


# ==================== caso 2: regla con AND ====================

def caso_2_and(t: AssertionTracker):
    print("\n[caso 2] regla con AND (and binario)")
    # rule problema :- altas and margen_bajo
    quads = [
        Quadruple('LOAD_DATASET', 'ventas.csv', None, 'ventas'),
        Quadruple('GT',   'monto',  500, 't0'),
        Quadruple('PROB', 't0',     None, 't1'),
        Quadruple('ASSIGN', 't1',   None, 'altas'),
        Quadruple('LT',   'margen', 10,  't2'),
        Quadruple('PROB', 't2',     None, 't3'),
        Quadruple('ASSIGN', 't3',   None, 'margen_bajo'),
        Quadruple('AND',  'altas',  'margen_bajo', 't4'),
        Quadruple('RULE_DEF', 't4', None, 'problema'),
        Quadruple('QUERY', 'problema', None, None),
    ]
    st = _symbol_table(
        ('ventas',      'dataset', 'dataset'),
        ('monto',       'column',  'real'),
        ('margen',      'column',  'real'),
        ('altas',       'fact',    'real'),
        ('margen_bajo', 'fact',    'real'),
        ('problema',    'rule',    'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'], "codegen no produjo errores")
    t.check(len(res['derived_facts']) == 2,
            "se detectaron 2 facts derivados")
    t.check('CALL fuzzy_and' in asm,
            "código invoca fuzzy_and")
    t.check('MOV AX, fact_altas' in asm and 'MOV BX, fact_margen_bajo' in asm,
            "AND carga los facts en AX/BX")
    t.check('MOV rule_problema, AX' in asm,
            "RULE_DEF guarda en rule_problema")
    t.check('MOV AX, rule_problema' in asm,
            "QUERY carga el valor de la regla")

    path = _write('caso2_and', asm)
    print(f"  -> {path}")
    print(t.report())


# ==================== caso 3: regla con NOT y anidamiento ====================

def caso_3_not_anidado(t: AssertionTracker):
    print("\n[caso 3] regla con NOT anidado: altas and not margen_bajo")
    # rule sano :- altas and not margen_bajo
    quads = [
        Quadruple('LOAD_DATASET', 'ventas.csv', None, 'ventas'),
        Quadruple('GT',   'monto',  500, 't0'),
        Quadruple('PROB', 't0',     None, 't1'),
        Quadruple('ASSIGN', 't1',   None, 'altas'),
        Quadruple('LT',   'margen', 10,  't2'),
        Quadruple('PROB', 't2',     None, 't3'),
        Quadruple('ASSIGN', 't3',   None, 'margen_bajo'),
        Quadruple('NOT',  'margen_bajo', None, 't4'),
        Quadruple('AND',  'altas',  't4', 't5'),
        Quadruple('RULE_DEF', 't5', None, 'sano'),
        Quadruple('QUERY', 'sano',  None, None),
    ]
    st = _symbol_table(
        ('ventas',      'dataset', 'dataset'),
        ('monto',       'column',  'real'),
        ('margen',      'column',  'real'),
        ('altas',       'fact',    'real'),
        ('margen_bajo', 'fact',    'real'),
        ('sano',        'rule',    'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'], "codegen no produjo errores")
    t.check('CALL fuzzy_not' in asm,
            "código invoca fuzzy_not")
    t.check('CALL fuzzy_and' in asm,
            "código invoca fuzzy_and")
    # El NOT escribe en t4 y luego AND lo consume
    t.check('MOV t4, AX' in asm,
            "el resultado del NOT se almacena en t4")
    t.check('MOV BX, t4' in asm,
            "el AND consume t4 como operando derecho")

    path = _write('caso3_not_anidado', asm)
    print(f"  -> {path}")
    print(t.report())


# ==================== caso 4: múltiples queries (fact y reglas) ====================

def caso_4_multi_query(t: AssertionTracker):
    print("\n[caso 4] múltiples queries (fact directo + regla)")
    quads = [
        Quadruple('LOAD_DATASET', 'ventas.csv', None, 'ventas'),
        Quadruple('GT',   'monto',  500, 't0'),
        Quadruple('PROB', 't0',     None, 't1'),
        Quadruple('ASSIGN', 't1',   None, 'altas'),
        Quadruple('LT',   'margen', 10,  't2'),
        Quadruple('PROB', 't2',     None, 't3'),
        Quadruple('ASSIGN', 't3',   None, 'margen_bajo'),
        Quadruple('AND',  'altas',  'margen_bajo', 't4'),
        Quadruple('RULE_DEF', 't4', None, 'problema'),
        Quadruple('QUERY', 'altas',    None, None),  # query directa a un fact
        Quadruple('QUERY', 'problema', None, None),  # query a una regla
    ]
    st = _symbol_table(
        ('ventas',      'dataset', 'dataset'),
        ('monto',       'column',  'real'),
        ('margen',      'column',  'real'),
        ('altas',       'fact',    'real'),
        ('margen_bajo', 'fact',    'real'),
        ('problema',    'rule',    'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'], "codegen no produjo errores")
    t.check(asm.count('CALL show_result') == 2,
            "se emiten DOS llamadas a show_result")
    t.check('MOV AX, fact_altas\n    LEA SI, msg_altas' in asm
            or ('MOV AX, fact_altas' in asm and 'LEA SI, msg_altas' in asm),
            "query a fact directo se traduce correctamente")
    t.check('MOV AX, rule_problema' in asm,
            "query a regla carga rule_problema")

    path = _write('caso4_multi_query', asm)
    print(f"  -> {path}")
    print(t.report())


# ==================== caso 4b: comparación contra literal en regla ====================

def caso_4b_cmp_en_regla(t: AssertionTracker):
    print("\n[caso 4b] regla con comparación contra literal: fact > 0.30")
    # rule alerta :- altas > 0.30 or altas > 0.50
    quads = [
        Quadruple('LOAD_DATASET', 'ventas.csv', None, 'ventas'),
        # fact altas (la cmp interna queda absorbida por PROB)
        Quadruple('GT',   'monto', 500, 't0'),
        Quadruple('PROB', 't0',    None, 't1'),
        Quadruple('ASSIGN', 't1',  None, 'altas'),
        # rule alerta :- altas > 0.30 or altas > 0.50
        Quadruple('GT', 'altas', 0.30, 't2'),   # NO absorbida → asm crisp
        Quadruple('GT', 'altas', 0.50, 't3'),   # NO absorbida → asm crisp
        Quadruple('OR', 't2',    't3',  't4'),
        Quadruple('RULE_DEF', 't4', None, 'alerta'),
        Quadruple('QUERY', 'alerta', None, None),
    ]
    st = _symbol_table(
        ('ventas', 'dataset', 'dataset'),
        ('monto',  'column',  'real'),
        ('altas',  'fact',    'real'),
        ('alerta', 'rule',    'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'], "codegen no produjo errores")
    # La cmp DENTRO del PROB (monto > 500) NO debe estar en el asm
    t.check('CMP AX, 500' not in asm,
            "la cmp absorbida por PROB no se emite como crisp")
    # Las cmp DENTRO de la regla SÍ deben estar
    t.check('CMP AX, 30' in asm,
            "se emite CMP AX, 30 (0.30 escalado)")
    t.check('CMP AX, 50' in asm,
            "se emite CMP AX, 50 (0.50 escalado)")
    # Etiquetas únicas para cada cmp
    t.check(asm.count('cmp_t_0:') == 1 and asm.count('cmp_t_1:') == 1,
            "etiquetas de comparación son únicas")
    # Las etiquetas tienen que estar en columna 0
    t.check('\ncmp_t_0:' in asm and '\ncmp_d_0:' in asm,
            "etiquetas en columna 0, no indentadas")
    # El OR sigue ahí
    t.check('CALL fuzzy_or' in asm,
            "el OR de los resultados de cmp sigue funcionando")

    path = _write('caso4b_cmp_en_regla', asm)
    print(f"  -> {path}")
    print(t.report())


# ==================== caso 6: fact con given (probabilidad condicional) ====================

def caso_6_given(t: AssertionTracker):
    print("\n[caso 6] fact con given: P(promedio<60 given asistencia<60)")
    # rule alerta :- p_reprob > 0.50
    # IR equivalente al que genera el pipeline real:
    quads = [
        Quadruple('LOAD_DATASET', 'alumnos.csv', None, 'alumnos'),
        Quadruple('MEMBER_ACCESS', 'alumnos', 'promedio',    't0'),
        Quadruple('LT',  't0', 60,  't1'),
        Quadruple('MEMBER_ACCESS', 'alumnos', 'asistencia',  't2'),
        Quadruple('LT',  't2', 60,  't3'),
        Quadruple('PROB_GIVEN', 't1', 't3', 't4'),
        Quadruple('ASSIGN', 't4', None, 'p_reprob'),
        Quadruple('QUERY',  'p_reprob', None, None),
    ]
    st = _symbol_table(
        ('alumnos',    'dataset', 'dataset'),
        ('promedio',   'column',  'int'),
        ('asistencia', 'column',  'int'),
        ('p_reprob',   'fact',    'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})
    meta = res['metadata']['facts']

    t.check(res['success'], "codegen no produjo errores")
    t.check('p_reprob' in meta, "p_reprob se detectó como fact derivado")
    t.check(meta['p_reprob']['kind'] == 'given', "kind = 'given'")
    t.check(meta['p_reprob']['col_a'] == 'promedio',
            "numerador (col_a) = promedio")
    t.check(meta['p_reprob']['value_a'] == 60,
            "umbral numerador (value_a) = 60")
    t.check(meta['p_reprob']['col_b'] == 'asistencia',
            "denominador (col_b) = asistencia")
    t.check(meta['p_reprob']['value_b'] == 60,
            "umbral denominador (value_b) = 60")
    t.check(meta['p_reprob']['dataset'] == 'alumnos',
            "dataset asociado = alumnos")
    t.check('CALL count_p_reprob' in res['asm'],
            "se emite CALL a count_p_reprob (la rutina la implementa Carim/Gibran)")
    t.check('given' in res['asm'],
            "el comentario del .asm menciona 'given'")

    path = _write('caso6_given', res['asm'])
    print(f"  -> {path}")
    print(t.report())


# ==================== caso 7: dataset con where (filtro) ====================

def caso_7_where(t: AssertionTracker):
    print("\n[caso 7] dataset con where: alumnos_foco = ... where promedio < 80")
    quads = [
        Quadruple('LOAD_DATASET', 'alumnos.csv', None, 'alumnos_raw'),
        Quadruple('SELECT', 'alumnos_raw', 'asistencia:real, promedio:real', 't0'),
        Quadruple('LT', 'promedio', 80, 't1'),         # condición del where
        Quadruple('FILTER', 't0', 't1', 't2'),
        Quadruple('ASSIGN', 't2', None, 'alumnos_foco'),
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'asistencia', 't3'),
        Quadruple('LT', 't3', 60, 't4'),
        Quadruple('PROB', 't4', None, 't5'),
        Quadruple('ASSIGN', 't5', None, 'asistencia_critica'),
        Quadruple('QUERY', 'asistencia_critica', None, None),
    ]
    st = _symbol_table(
        ('alumnos_raw',        'dataset', 'dataset'),
        ('alumnos_foco',       'dataset', 'dataset'),
        ('asistencia',         'column',  'real'),
        ('promedio',           'column',  'real'),
        ('asistencia_critica', 'fact',    'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})
    md = res['metadata']

    t.check(res['success'], "codegen no produjo errores")
    t.check('alumnos_foco' in md['datasets'],
            "alumnos_foco aparece en metadata.datasets")
    t.check('filter' in md['datasets'].get('alumnos_foco', {}),
            "alumnos_foco tiene filtro registrado")
    f = md['datasets'].get('alumnos_foco', {}).get('filter', {})
    t.check(f.get('col') == 'promedio',
            "filtro: columna = promedio")
    t.check(f.get('op') == '<',
            "filtro: operador = <")
    t.check(f.get('value') == 80,
            "filtro: umbral = 80")
    t.check(md['facts']['asistencia_critica']['dataset'] == 'alumnos_foco',
            "el fact apunta al dataset filtrado")
    t.check(md['facts']['asistencia_critica']['kind'] == 'simple',
            "el fact sigue siendo 'simple' (el where es del dataset)")

    path = _write('caso7_where', res['asm'])
    print(f"  -> {path}")
    print(t.report())


# ==================== caso 5: operación no soportada ====================

def caso_5_no_soportado(t: AssertionTracker):
    print("\n[caso 5] operación no soportada (MEAN) — debe reportar error claro")
    quads = [
        Quadruple('LOAD_DATASET', 'ventas.csv', None, 'ventas'),
        Quadruple('MEAN', 'ventas', 'monto', 't0'),
        Quadruple('ASSIGN', 't0',   None, 'promedio'),
        Quadruple('QUERY', 'promedio', None, None),
    ]
    st = _symbol_table(
        ('ventas',   'dataset', 'dataset'),
        ('promedio', 'metric',  'real'),
    )
    res = generate_code(_wrap(quads), {'symbol_table': st})

    t.check(not res['success'],
            "el codegen reporta fallo")
    t.check(any("'MEAN'" in e for e in res['errors']),
            "el error menciona la operación MEAN")
    t.check('include Biblioteca.lib' in res['asm'],
            "aun así emite un .asm parcial (degradación amable)")

    path = _write('caso5_no_soportado', res['asm'])
    print(f"  -> {path}  (con errores)")
    print(t.report())


# ==================== pipeline real (opcional/informativo) ====================

def caso_pipeline_real(t: AssertionTracker):
    """Intenta correr el pipeline completo. Si la fase semántica aún no
    permite usar facts en operaciones lógicas (real vs bool), se reporta
    como pendiente, NO como fallo del codegen."""
    print("\n[pipeline real] ejecución end-to-end desde fuente Snaptics")
    import lexer
    import parser as syntax_parser
    from semantic.semantic_analyzer import analyze as semantic_analyze
    from ir_generator import generate_ir
    from optimizer import optimize_ir

    src = (
        'dataset ventas_raw = import from "ventas.csv"\n'
        'dataset ventas = select monto: real, margen: real from ventas_raw\n'
        'fact altas = P(ventas.monto > 500)\n'
        'fact margen_bajo = P(ventas.margen < 10)\n'
        'rule problema :- altas and margen_bajo\n'
        'query problema\n'
    )
    lex_result = lexer.tokenize(src)
    if lex_result.get('errors'):
        print("  lex: errores presentes, pipeline detenido")
        return
    pr = syntax_parser.parse(src)
    if any(str(e.get('code','')).startswith('SYN-') for e in pr.get('errors', [])):
        print("  parser: errores sintácticos")
        return
    sr = semantic_analyze(pr)
    if sr.get('errors'):
        print("  semántica: pendiente arreglo en type_checker (facts 'real' vs 'bool')")
        print("  -> esto NO afecta al codegen; cuando se arregle, este test pasa automáticamente.")
        return
    ir = generate_ir(sr, pr)
    opt = optimize_ir(ir)
    res = generate_code(opt, pr)

    t.check(res['success'], "pipeline completo: codegen sin errores")
    if res['success']:
        path = _write('pipeline_real', res['asm'])
        print(f"  -> {path}")
    print(t.report())


# ==================== main ====================

def main():
    t = AssertionTracker()
    caso_1_query_simple(t)
    caso_2_and(t)
    caso_3_not_anidado(t)
    caso_4_multi_query(t)
    caso_4b_cmp_en_regla(t)
    caso_6_given(t)
    caso_7_where(t)
    caso_5_no_soportado(t)
    caso_pipeline_real(t)

    print("\n========================================")
    if t.failed:
        print(f"RESUMEN: {t.passed} ok, {len(t.failed)} FALLOS")
        for f in t.failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"RESUMEN: {t.passed} aserciones, todas ok")


if __name__ == '__main__':
    main()
