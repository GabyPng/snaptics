"""
Pase 2 — Simplificación Algebraica
==================================
Aplica identidades aritméticas para eliminar operaciones inútiles
incluso cuando uno de los operandos NO es constante.

Identidades implementadas:
    X + 0  -> X        0 + X  -> X
    X - 0  -> X
    X * 1  -> X        1 * X  -> X
    X * 0  -> 0        0 * X  -> 0
    X / 1  -> X
    X ^ 1  -> X
    X ^ 0  -> 1

No se transforma `0 - X -> -X` porque introduciría una nueva
cuádrupla unaria; el beneficio es marginal frente al coste de
romper la cardinalidad de la lista en un solo pase.

Complejidad: O(n).
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes._utils import is_numeric_const, replace_with_assign


def _is(v, target) -> bool:
    """Compara v con target solo si v es numérico (descarta bools)."""
    return is_numeric_const(v) and v == target


def run(quads: list[Quadruple]) -> tuple[list[Quadruple], bool]:
    out: list[Quadruple] = []
    changed = False
    for q in quads:
        new_q = _simplify(q)
        if new_q is not q:
            changed = True
        out.append(new_q)
    return out, changed


def _simplify(q: Quadruple) -> Quadruple:
    op, a1, a2 = q.op, q.arg1, q.arg2

    if op == 'ADD':
        if _is(a2, 0): return replace_with_assign(q, a1)
        if _is(a1, 0): return replace_with_assign(q, a2)

    elif op == 'SUB':
        if _is(a2, 0): return replace_with_assign(q, a1)

    elif op == 'MUL':
        if _is(a1, 0) or _is(a2, 0):
            return replace_with_assign(q, 0)
        if _is(a2, 1): return replace_with_assign(q, a1)
        if _is(a1, 1): return replace_with_assign(q, a2)

    elif op == 'DIV':
        if _is(a2, 1): return replace_with_assign(q, a1)

    elif op == 'POW':
        if _is(a2, 0): return replace_with_assign(q, 1)
        if _is(a2, 1): return replace_with_assign(q, a1)

    return q
