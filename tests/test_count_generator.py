"""
tests/test_count_generator.py
Pruebas para count_generator.generate_counts().

Ejecutar:
    python tests/test_count_generator.py

Estrategia: construye quads a mano que reflejen lo que produce el
pipeline para alumnosTEC.snp y verifica que:
  - Se genera asm para cada fact derivado
  - El where-block se inyecta cuando el dataset tiene filtro
  - Los índices de columna son correctos
  - Las etiquetas llevan el sufijo del fact (sin duplicados)
  - Un fact sin filtro no tiene snippet de where
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
from count_generator import generate_counts


# ==================== helpers ====================

def _wrap(quads):
    return {
        'success':    True,
        'quadruples': quads,
        'formatted':  '',
        'original':   list(quads),
        'report':     '',
        'stats':      {},
        'reduction':  0,
    }

def _st(*entries):
    st = SymbolTable()
    for name, cat, dt in entries:
        st.add(name, cat, dt, line=0)
    return st


class T:
    def __init__(self): self.ok = 0; self.fail = []
    def check(self, cond, label):
        if cond: self.ok += 1
        else: self.fail.append(label)
    def report(self):
        if not self.fail:
            return f"  {self.ok} ok"
        return f"  {self.ok} ok, {len(self.fail)} FALLOS:\n" + \
               "\n".join(f"    - {f}" for f in self.fail)


# ==================== caso 1: fact simple sin filtro ====================

def caso_simple_sin_where(t: T):
    print("\n[1] fact simple, dataset sin WHERE")
    quads = [
        Quadruple('LOAD_DATASET', 'alumnos.csv', None, 'alumnos_raw'),
        Quadruple('SELECT', 'alumnos_raw', 'asistencia:real, promedio:real', 't0'),
        Quadruple('MEMBER_ACCESS', 'alumnos_raw', 'asistencia', 't1'),
        Quadruple('LT', 't1', 60, 't2'),
        Quadruple('PROB', 't2', None, 't3'),
        Quadruple('ASSIGN', 't3', None, 'asistencia_critica'),
        Quadruple('QUERY', 'asistencia_critica', None, None),
    ]
    st = _st(
        ('alumnos_raw',        'dataset', 'dataset'),
        ('asistencia',         'column',  'real'),
        ('promedio',           'column',  'real'),
        ('asistencia_critica', 'fact',    'real'),
    )
    res = generate_counts(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'],                              "sin errores")
    t.check('count_asistencia_critica PROC' in asm,      "PROC generado")
    t.check('CMP AX, 60' in asm,                         "umbral 60 presente")
    t.check('JGE no_match_asistencia_critica' in asm,    "jump_neg correcto")
    t.check('MOV AL, 1' in asm,                          "columna asistencia -> idx 1")
    t.check('skip_where_asistencia_critica' not in asm,  "sin snippet where")
    t.check('fila_loop_asistencia_critica:' in asm,      "etiqueta con sufijo fact")
    print(t.report())


# ==================== caso 2: fact simple con filtro WHERE ====================

def caso_simple_con_where(t: T):
    print("\n[2] fact simple, dataset CON WHERE (promedio < 80)")
    quads = [
        Quadruple('LOAD_DATASET', 'alumnos.csv', None, 'alumnos_raw'),
        Quadruple('SELECT', 'alumnos_raw', 'asistencia:real, promedio:real', 't0'),
        Quadruple('LT', 'promedio', 80, 't1'),
        Quadruple('FILTER', 't0', 't1', 't2'),
        Quadruple('ASSIGN', 't2', None, 'alumnos_foco'),
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'asistencia', 't3'),
        Quadruple('LT', 't3', 60, 't4'),
        Quadruple('PROB', 't4', None, 't5'),
        Quadruple('ASSIGN', 't5', None, 'asistencia_critica'),
        Quadruple('QUERY', 'asistencia_critica', None, None),
    ]
    st = _st(
        ('alumnos_raw',        'dataset', 'dataset'),
        ('alumnos_foco',       'dataset', 'dataset'),
        ('asistencia',         'column',  'real'),
        ('promedio',           'column',  'real'),
        ('asistencia_critica', 'fact',    'real'),
    )
    res = generate_counts(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'],                              "sin errores")
    t.check('count_asistencia_critica PROC' in asm,      "PROC generado")
    t.check('skip_where_asistencia_critica:' in asm,     "etiqueta where con sufijo fact")
    t.check('check_done_asistencia_critica:' in asm,     "etiqueta check_done con sufijo")
    t.check('CMP AX, 80' in asm,                         "umbral del filtro (80) presente")
    t.check('CMP AX, 60' in asm,                         "umbral del fact (60) presente")
    # promedio es idx 5 en el CSV real -> MOV AL, 5 para el where
    t.check('MOV AL, 5' in asm,                          "filtro usa columna promedio -> idx 5")
    # asistencia es idx 1 en el CSV real -> MOV AL, 1 para el fact
    t.check('MOV AL, 1' in asm,                          "fact usa columna asistencia -> idx 1")
    print(t.report())


# ==================== caso 3: fact given con filtro ====================

def caso_given_con_where(t: T):
    print("\n[3] fact given P(promedio<60 given asistencia<60), dataset con WHERE")
    quads = [
        Quadruple('LOAD_DATASET', 'alumnos.csv', None, 'alumnos_raw'),
        Quadruple('SELECT', 'alumnos_raw', 'asistencia:real, promedio:real', 't0'),
        Quadruple('LT', 'promedio', 80, 't1'),
        Quadruple('FILTER', 't0', 't1', 't2'),
        Quadruple('ASSIGN', 't2', None, 'alumnos_foco'),
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'promedio',   't3'),
        Quadruple('LT', 't3', 60, 't4'),
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'asistencia', 't5'),
        Quadruple('LT', 't5', 60, 't6'),
        Quadruple('PROB_GIVEN', 't4', 't6', 't7'),
        Quadruple('ASSIGN', 't7', None, 'p_reprob'),
        Quadruple('QUERY', 'p_reprob', None, None),
    ]
    st = _st(
        ('alumnos_raw',  'dataset', 'dataset'),
        ('alumnos_foco', 'dataset', 'dataset'),
        ('asistencia',   'column',  'real'),
        ('promedio',     'column',  'real'),
        ('p_reprob',     'fact',    'real'),
    )
    res = generate_counts(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'],                    "sin errores")
    t.check('count_p_reprob PROC' in asm,      "PROC given generado")
    t.check('fila_loop_p_reprob:' in asm,      "etiqueta fila_loop con sufijo")
    t.check('no_a_p_reprob:' in asm,           "etiqueta no_a con sufijo")
    t.check('no_b_p_reprob:' in asm,           "etiqueta no_b con sufijo")
    t.check('skip_where_p_reprob:' in asm,     "snippet where inyectado")
    # col_b = asistencia idx 1, col_a = promedio idx 5
    t.check(asm.count('MOV AL, 1') >= 1,       "asistencia -> idx 1 usado")
    t.check(asm.count('MOV AL, 5') >= 1,       "promedio   -> idx 5 usado")
    print(t.report())


# ==================== caso 4: dos facts, sin duplicate labels ====================

def caso_dos_facts_sin_colisiones(t: T):
    print("\n[4] dos facts en el mismo asm -> etiquetas no colisionan")
    quads = [
        Quadruple('LOAD_DATASET', 'alumnos.csv', None, 'alumnos_raw'),
        Quadruple('SELECT', 'alumnos_raw', 'asistencia:real, promedio:real', 't0'),
        Quadruple('LT', 'promedio', 80, 't1'),
        Quadruple('FILTER', 't0', 't1', 't2'),
        Quadruple('ASSIGN', 't2', None, 'alumnos_foco'),
        # fact A: asistencia_critica
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'asistencia', 't3'),
        Quadruple('LT', 't3', 60, 't4'),
        Quadruple('PROB', 't4', None, 't5'),
        Quadruple('ASSIGN', 't5', None, 'asistencia_critica'),
        # fact B: promedio_bajo
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'promedio', 't6'),
        Quadruple('LT', 't6', 60, 't7'),
        Quadruple('PROB', 't7', None, 't8'),
        Quadruple('ASSIGN', 't8', None, 'promedio_bajo'),
        Quadruple('QUERY', 'asistencia_critica', None, None),
        Quadruple('QUERY', 'promedio_bajo', None, None),
    ]
    st = _st(
        ('alumnos_raw',        'dataset', 'dataset'),
        ('alumnos_foco',       'dataset', 'dataset'),
        ('asistencia',         'column',  'real'),
        ('promedio',           'column',  'real'),
        ('asistencia_critica', 'fact',    'real'),
        ('promedio_bajo',      'fact',    'real'),
    )
    res = generate_counts(_wrap(quads), {'symbol_table': st})
    asm = res['asm']

    t.check(res['success'], "sin errores")
    # Cada fact tiene su propio PROC
    t.check('count_asistencia_critica PROC' in asm, "PROC asistencia_critica")
    t.check('count_promedio_bajo PROC' in asm,      "PROC promedio_bajo")
    # Las etiquetas deben ser distintas
    t.check('fila_loop_asistencia_critica:' in asm, "label fila_loop_asistencia_critica")
    t.check('fila_loop_promedio_bajo:' in asm,      "label fila_loop_promedio_bajo")
    t.check(asm.count('fila_loop_asistencia_critica:') == 1, "label A no duplicada")
    t.check(asm.count('fila_loop_promedio_bajo:') == 1,      "label B no duplicada")
    print(t.report())


# ==================== main ====================

def main():
    t = T()
    caso_simple_sin_where(t)
    caso_simple_con_where(t)
    caso_given_con_where(t)
    caso_dos_facts_sin_colisiones(t)

    print("\n========================================")
    total_fail = sum(len(tt.fail) for tt in [])  # ya se imprime arriba por caso
    if t.fail:
        print(f"RESUMEN GLOBAL: {t.ok} ok, {len(t.fail)} FALLOS")
        sys.exit(1)
    else:
        print(f"RESUMEN GLOBAL: {t.ok} aserciones, todas ok")

if __name__ == '__main__':
    main()
