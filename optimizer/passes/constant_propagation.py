"""
Pase 5 — Propagación de Constantes y Copias
===========================================
Cubre dos formas relacionadas de propagación:

(a) Propagación de constantes:
    (ASSIGN, 5, None, t1)
    (ADD,    t1, 3, t2)        -> (ADD, 5, 3, t2)

(b) Propagación de copias (alias entre identificadores):
    (ASSIGN, x, None, t1)
    (ASSIGN, t1, None, y)      -> (ASSIGN, x, None, y)

Ambas se modelan con un único diccionario `aliases: name -> value`,
donde `value` puede ser un literal (int/float/bool) o un nombre.
Esto es el caso porque, en Snaptics, los temporales `tN` son SSA:
se asignan exactamente una vez, así que un alias `t1 -> x` solo es
inválido cuando el propio `x` cambia.

Invalidación:
    Cuando una cuádrupla redefine el símbolo `r`:
      1. Cualquier alias `a -> r` se borra (la referencia caducó).
      2. La entrada de `r` se borra (será reescrita).
    Luego, si el efecto neto es `(ASSIGN, src, None, r)` con src
    literal o identificador, se registra `aliases[r] = src`.

Notas:
    - La propagación se hace SIN resolver cadenas en una sola pasada:
      el fixed-point del orquestador resuelve cadenas de longitud k
      en O(k) iteraciones.
    - Operaciones con efectos colaterales (LOAD_DATASET, QUERY, etc.)
      no producen alias; simplemente invalidan su `result`.

Complejidad: O(n) por barrida; O(n * k) globalmente por el conteo de
invalidaciones, con k = #aliases vivos (acotado por #temporales).
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes._utils import is_const, is_temp


def run(quads: list[Quadruple]) -> tuple[list[Quadruple], bool]:
    out: list[Quadruple] = []
    changed = False
    aliases: dict[str, object] = {}

    for q in quads:
        # 1. Propagación hacia los operandos
        new_arg1 = _propagate(q.arg1, aliases)
        new_arg2 = _propagate(q.arg2, aliases)

        if new_arg1 != q.arg1 or new_arg2 != q.arg2:
            changed = True
            q = Quadruple(q.op, new_arg1, new_arg2, q.result)

        # 2. Invalidación por redefinición del resultado
        if isinstance(q.result, str):
            # (a) cualquier alias cuyo valor sea q.result queda obsoleto
            stale = [k for k, v in aliases.items() if v == q.result]
            for k in stale:
                del aliases[k]
            # (b) la entrada del propio q.result también se invalida
            aliases.pop(q.result, None)

        # 3. Registro del nuevo alias si la cuádrupla es ASSIGN.
        #    Reglas conservadoras para preservar los nombres del usuario:
        #      (a) ASSIGN con rhs constante  -> registra siempre (cualquier target)
        #      (b) ASSIGN con rhs identificador y target temporal -> registra
        #          (caso típico tras algebraic_simplification: X * 1 -> ASSIGN X t)
        #      (c) ASSIGN con rhs identificador y target NO temporal -> NO registra
        #          (preserva nombres como alumnos_foco, asistencia_critica, ...)
        if q.op == 'ASSIGN' and isinstance(q.result, str):
            if is_const(q.arg1):
                aliases[q.result] = q.arg1
            elif isinstance(q.arg1, str) and is_temp(q.result):
                aliases[q.result] = q.arg1

        out.append(q)

    return out, changed


def _propagate(arg, aliases: dict[str, object]):
    """Sustituye arg por su valor conocido, si existe."""
    if isinstance(arg, str) and arg in aliases:
        return aliases[arg]
    return arg
