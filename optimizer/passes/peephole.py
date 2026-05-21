"""
Pase 6 — Peephole Optimization
==============================
Optimiza pequeñas secuencias de instrucciones (la "mirilla")
detectando patrones que cruzan más de una cuádrupla.

Patrones implementados:
    NOT NOT X                      -> X
    (ASSIGN, k, None, t)
    (ASSIGN, t, None, x)           -> (ASSIGN, k, None, x)   (vía copy)

La mayoría de patrones de mirilla "atómicos" (ADD x 0, MUL x 1,
NOT true, ...) ya están cubiertos por algebraic_simplification,
logic_simplification y constant_folding. Este pase se centra en
patrones que requieren mirar al pasado.

Complejidad: O(n^2) en el peor caso (find_def), pero típicamente
O(n*k) con k pequeño.
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes._utils import find_def


def run(quads: list[Quadruple]) -> tuple[list[Quadruple], bool]:
    out: list[Quadruple] = []
    changed = False
    for i, q in enumerate(quads):
        new_q = _peephole(q, quads, i)
        if new_q is not q:
            changed = True
        out.append(new_q)
    return out, changed


def _peephole(q: Quadruple, quads: list[Quadruple], i: int) -> Quadruple:
    # ---- NOT NOT X -> X ----
    if q.op == 'NOT':
        src = find_def(quads, i, q.arg1)
        if src is not None and src.op == 'NOT':
            return Quadruple('ASSIGN', src.arg1, None, q.result)

    return q
