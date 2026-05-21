"""
Pase 7 — Eliminación de Temporales Muertos
==========================================
Elimina cuádruplas puras cuyo resultado es un temporal `tN`
que NUNCA se vuelve a usar en el resto del programa.

Es el barrido final que limpia los residuos generados por los
pases previos. Tras `constant_propagation` muchos temporales
quedan huérfanos: se les asignaba un valor que ya fue inlineado
en cada uso, por lo que la asignación original se vuelve basura.

Ejemplo de cadena completa:

    (ADD,    5,  3, t1)            <-- constant_folding ->
    (ASSIGN, 8,  None, t1)         <-- constant_propagation ->
    (ASSIGN, t1, None, x)
        +
    (ASSIGN, 8,  None, x)
    (ASSIGN, 8,  None, t1)         <-- dead_temp_elimination ->
    (ASSIGN, 8,  None, x)

Reglas de seguridad:
    - Solo se eliminan cuádruplas con op PURA (lista en _utils).
    - Solo se eliminan si el `result` es un temporal `tN`.
    - Operaciones con efectos colaterales (LOAD_DATASET, SELECT,
      FILTER, QUERY, PROB, MEAN, etc.) NUNCA se eliminan, aunque
      su resultado parezca muerto.

Complejidad: O(n) (un barrido para contar usos + un barrido para filtrar).
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes._utils import PURE_OPS, is_temp


def run(quads: list[Quadruple]) -> tuple[list[Quadruple], bool]:
    # 1. Conteo de usos: cuántas veces aparece cada símbolo como
    #    arg1 o arg2 a lo largo del programa.
    uses: dict[str, int] = {}
    for q in quads:
        for arg in (q.arg1, q.arg2):
            if isinstance(arg, str):
                uses[arg] = uses.get(arg, 0) + 1

    # 2. Filtrado: descarta cuádruplas puras cuyo resultado es un
    #    temporal con cero usos.
    out: list[Quadruple] = []
    changed = False
    for q in quads:
        if (
            q.op in PURE_OPS
            and is_temp(q.result)
            and uses.get(q.result, 0) == 0
        ):
            changed = True
            continue
        out.append(q)

    return out, changed
