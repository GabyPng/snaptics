"""
Pase 4 — Identidades Probabilísticas
====================================
Reglas específicas del dominio lógico-probabilístico de Snaptics.

Identidades:
    PROB(true)        -> 1.0
    PROB(false)       -> 0.0
    PROB(A AND NOT A) -> 0.0     (contradicción)
    PROB(A OR  A)     -> PROB(A) (idempotencia probabilística)

Las dos últimas requieren consultar la definición del operando
de PROB porque éste es típicamente un temporal (no un literal).
Se usa `find_def` para localizar la cuádrupla que produce ese
temporal en el mismo "bloque básico" (un fact/rule/query).

Complejidad: O(n^2) en el peor caso por las búsquedas hacia atrás,
pero en la práctica O(n*k) con k pequeño (los temporales viven
pocas instrucciones).
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes._utils import find_def, replace_with_assign


def run(quads: list[Quadruple]) -> tuple[list[Quadruple], bool]:
    out: list[Quadruple] = []
    changed = False
    for i, q in enumerate(quads):
        new_q = _simplify(q, quads, i)
        if new_q is not q:
            changed = True
        out.append(new_q)
    return out, changed


def _simplify(q: Quadruple, quads: list[Quadruple], i: int) -> Quadruple:
    if q.op != 'PROB':
        return q

    arg = q.arg1

    # PROB(true) / PROB(false)
    if arg is True:
        return replace_with_assign(q, 1.0)
    if arg is False:
        return replace_with_assign(q, 0.0)

    # Inspección estructural del operando
    src = find_def(quads, i, arg)
    if src is None:
        return q

    # PROB(A AND NOT A) -> 0.0
    if src.op == 'AND' and _are_complementary(quads, i, src.arg1, src.arg2):
        return replace_with_assign(q, 0.0)

    # PROB(A OR A) -> PROB(A)
    if src.op == 'OR' and src.arg1 == src.arg2 and src.arg1 is not None:
        return Quadruple('PROB', src.arg1, None, q.result)

    return q


def _are_complementary(quads: list[Quadruple], i: int, a, b) -> bool:
    """True si uno de los operandos es la negación lógica del otro."""
    da = find_def(quads, i, a)
    db = find_def(quads, i, b)
    if da is not None and da.op == 'NOT' and da.arg1 == b:
        return True
    if db is not None and db.op == 'NOT' and db.arg1 == a:
        return True
    return False
