"""
Pase 3 — Simplificación Lógica
==============================
Identidades de álgebra booleana / lógica difusa aplicables aun
cuando uno de los operandos NO es constante.

Identidades:
    X AND true   -> X         true AND X   -> X
    X AND false  -> false     false AND X  -> false
    X OR  true   -> true      true OR  X   -> true
    X OR  false  -> X         false OR X   -> X
    X AND X      -> X         (idempotencia)
    X OR  X      -> X
    NOT NOT X    -> X         (delegado a peephole con find_def)

La regla NOT NOT X requiere conocer la cuádrupla que define el
operando, por lo que vive en el pase `peephole`. Aquí se mantiene
puro: solo mira la cuádrupla actual.

Complejidad: O(n).
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes._utils import is_const, replace_with_assign


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

    if op == 'AND':
        if a1 is True:                       # true AND X -> X
            return replace_with_assign(q, a2)
        if a2 is True:                       # X AND true -> X
            return replace_with_assign(q, a1)
        if a1 is False or a2 is False:       # _ AND false / false AND _
            return replace_with_assign(q, False)
        if a1 == a2 and not is_const(a1):    # X AND X -> X  (idempotencia)
            return replace_with_assign(q, a1)

    elif op == 'OR':
        if a1 is False:                      # false OR X -> X
            return replace_with_assign(q, a2)
        if a2 is False:                      # X OR false -> X
            return replace_with_assign(q, a1)
        if a1 is True or a2 is True:         # _ OR true / true OR _
            return replace_with_assign(q, True)
        if a1 == a2 and not is_const(a1):    # X OR X -> X  (idempotencia)
            return replace_with_assign(q, a1)

    return q
