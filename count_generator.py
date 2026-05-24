"""
count_generator.py
==================
Genera las rutinas count_<fact> en ensamblador 8086 a partir del
metadato producido por code_generator.py.

Para cada fact derivado de un dataset:
  - kind == 'simple' -> plantilla_count_simple.asm
  - kind == 'given'  -> plantilla_count_given.asm

Si el dataset del fact tiene cláusula WHERE, se inyecta el bloque
snippet_where_precheck.asm como {where_block} en la plantilla.
"""
from __future__ import annotations
import os
import sys

from code_generator import generate_code

_LIB_DIR = os.path.join(os.path.dirname(__file__), 'lib')

# Mapeo hardcodeado nombre de columna -> índice 0-based en el CSV.
# Se complementa con lo que se extrae de los quadruples SELECT.
COLUMNAS: dict[str, int] = {
    'alumno':       0,
    'asistencia':   1,
    'calificacion': 2,
    'grupo':        3,
    'tareas':       4,
    'promedio':     5,
}


# ==================== helpers internos ====================

def _load_template(filename: str) -> str:
    path = os.path.join(_LIB_DIR, filename)
    with open(path, encoding='utf-8') as f:
        return f.read()


def _build_column_map(quads) -> dict[str, int]:
    """Extrae columna->índice de los quadruples SELECT.
    Complementa (no sobrescribe) COLUMNAS.
    """
    col_map: dict[str, int] = dict(COLUMNAS)
    for q in quads:
        if q.op == 'SELECT' and isinstance(q.arg2, str):
            # arg2 == 'asistencia:real, promedio:real'
            cols = [c.split(':')[0].strip() for c in q.arg2.split(',')]
            for idx, name in enumerate(cols):
                if name and name not in col_map:
                    col_map[name] = idx
    return col_map


def _build_where_block(fact_name: str, filter_meta: dict, col_map: dict[str, int]) -> str:
    """Rellena snippet_where_precheck.asm con los parámetros del filtro."""
    template = _load_template('snippet_where_precheck.asm')
    filter_col = filter_meta['col']
    return template.format(
        name=fact_name,
        filter_col_idx=col_map.get(filter_col, 0),
        filter_value=filter_meta['value'],
        filter_jump_neg=filter_meta['jump_neg'],
    )


def _generate_simple(
    fact_name: str,
    fact_meta: dict,
    where_block: str,
    col_map: dict[str, int],
) -> str:
    template = _load_template('plantilla_count_simple.asm')
    col = fact_meta['col']
    return template.format(
        name=fact_name,
        col_idx=col_map.get(col, 0),
        value=fact_meta['value'],
        jump_neg=fact_meta['jump_neg'],
        where_block=where_block,
    )


def _generate_given(
    fact_name: str,
    fact_meta: dict,
    where_block: str,
    col_map: dict[str, int],
) -> str:
    template = _load_template('plantilla_count_given.asm')
    col_a = fact_meta['col_a']
    col_b = fact_meta['col_b']
    return template.format(
        name=fact_name,
        col_a_idx=col_map.get(col_a, 0),
        value_a=fact_meta['value_a'],
        jump_a_neg=fact_meta['jump_a_neg'],
        col_b_idx=col_map.get(col_b, 0),
        value_b=fact_meta['value_b'],
        jump_b_neg=fact_meta['jump_b_neg'],
        where_block=where_block,
    )


# ==================== API pública ====================

def generate_counts(opt_result: dict, parse_result: dict | None = None) -> dict:
    """
    Genera las rutinas count_<fact> en ensamblador 8086.

    Args:
        opt_result:   dict de optimizer.optimize_ir()
        parse_result: dict de parser.parse() (opcional; aporta symbol_table)

    Returns:
        dict:
            'asm':     str — rutinas count_* concatenadas, listas para
                            pegarse/incluirse en el .asm final
            'success': bool
            'errors':  list[str]
    """
    result = generate_code(opt_result, parse_result)
    meta = result['metadata']

    quads = opt_result.get('quadruples', [])
    col_map = _build_column_map(quads)

    errors: list[str] = []
    parts: list[str] = []

    for fact_name, fact_meta in meta['facts'].items():
        dataset_name = fact_meta.get('dataset')
        dataset_meta = meta['datasets'].get(dataset_name, {}) if dataset_name else {}

        # Construir where_block si el dataset del fact tiene filtro WHERE
        where_block = ''
        if 'filter' in dataset_meta:
            try:
                where_block = _build_where_block(
                    fact_name, dataset_meta['filter'], col_map
                )
            except Exception as e:
                errors.append(f"[CGEN] where-block para '{fact_name}': {e}")

        # Rellenar la plantilla según el kind del fact
        kind = fact_meta.get('kind', 'simple')
        try:
            if kind == 'given':
                asm = _generate_given(fact_name, fact_meta, where_block, col_map)
            else:
                asm = _generate_simple(fact_name, fact_meta, where_block, col_map)
            parts.append(asm)
        except Exception as e:
            errors.append(f"[CGEN] rutina count_{fact_name}: {e}")

    return {
        'asm':     '\n'.join(parts),
        'success': len(errors) == 0,
        'errors':  errors,
    }


# ==================== demo ====================

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

    from ir_generator import Quadruple
    from symbol_table import SymbolTable

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

    # Demo: alumnos_foco (con where) + fact simple + fact given
    quads = [
        Quadruple('LOAD_DATASET', 'alumnos.csv', None, 'alumnos_raw'),
        Quadruple('SELECT', 'alumnos_raw', 'asistencia:real, promedio:real', 't0'),
        Quadruple('LT', 'promedio', 80, 't1'),
        Quadruple('FILTER', 't0', 't1', 't2'),
        Quadruple('ASSIGN', 't2', None, 'alumnos_foco'),
        # fact simple
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'asistencia', 't3'),
        Quadruple('LT', 't3', 60, 't4'),
        Quadruple('PROB', 't4', None, 't5'),
        Quadruple('ASSIGN', 't5', None, 'asistencia_critica'),
        # fact given
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'promedio',   't6'),
        Quadruple('LT', 't6', 60, 't7'),
        Quadruple('MEMBER_ACCESS', 'alumnos_foco', 'asistencia', 't8'),
        Quadruple('LT', 't8', 60, 't9'),
        Quadruple('PROB_GIVEN', 't7', 't9', 't10'),
        Quadruple('ASSIGN', 't10', None, 'p_reprob'),
        Quadruple('QUERY', 'asistencia_critica', None, None),
        Quadruple('QUERY', 'p_reprob',           None, None),
    ]
    st = _st(
        ('alumnos_raw',        'dataset', 'dataset'),
        ('alumnos_foco',       'dataset', 'dataset'),
        ('asistencia',         'column',  'real'),
        ('promedio',           'column',  'real'),
        ('asistencia_critica', 'fact',    'real'),
        ('p_reprob',           'fact',    'real'),
    )

    res = generate_counts(_wrap(quads), {'symbol_table': st})

    print("=== count_generator demo ===")
    if res['errors']:
        print("ERRORES:")
        for e in res['errors']:
            print(" ", e)
    else:
        print("OK — rutinas generadas:\n")
        print(res['asm'])
