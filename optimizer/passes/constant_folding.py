"""
Pase 1 — Constant Folding
=========================
Evalúa en tiempo de compilación cualquier cuádrupla cuyos
operandos sean todos literales (int, float, bool).

Ejemplos:
    (ADD,  5,   3,   t1)   -> (ASSIGN, 8,    None, t1)
    (MUL,  0.5, 0.4, t1)   -> (ASSIGN, 0.2,  None, t1)
    (GT,   5,   3,   t1)   -> (ASSIGN, True, None, t1)
    (NOT,  True, None, t1) -> (ASSIGN, False, None, t1)

Cobertura:
    - Aritméticas: ADD, SUB, MUL, DIV, POW
    - Relacionales: EQ, NEQ, LT, GT, LEQ, GEQ
    - Lógicas binarias: AND, OR (cuando AMBOS lados son const)
    - Unarias: NOT, UNARY_MINUS, UNARY_PLUS

Casos cuidados:
    - División entre cero: no se pliega; se deja al runtime.
    - Bool en aritmética: Python lo aceptaría (True == 1), pero el
      pase lo bloquea para no introducir conversiones implícitas
      ajenas a la semántica de Snaptics.

Complejidad: O(n).
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes._utils import (
    is_const,
    is_numeric_const,
    is_bool_const,
    replace_with_assign,
)


# Tablas de evaluación. Las funciones devuelven None ante condiciones
# que deben dejarse al runtime (división por cero, overflow, etc.).

_ARITH = {
    'ADD': lambda a, b: a + b,
    'SUB': lambda a, b: a - b,
    'MUL': lambda a, b: a * b,
    'DIV': lambda a, b: (a / b) if b != 0 else None,
    'POW': lambda a, b: a ** b,
}

_REL = {
    'EQ':  lambda a, b: a == b,
    'NEQ': lambda a, b: a != b,
    'LT':  lambda a, b: a <  b,
    'GT':  lambda a, b: a >  b,
    'LEQ': lambda a, b: a <= b,
    'GEQ': lambda a, b: a >= b,
}

_LOGIC = {
    'AND': lambda a, b: bool(a) and bool(b),
    'OR':  lambda a, b: bool(a) or  bool(b),
}

_UNARY = {
    'NOT':         lambda a: not bool(a),
    'UNARY_MINUS': lambda a: -a,
    'UNARY_PLUS':  lambda a: +a,
}


def run(quads: list[Quadruple]) -> tuple[list[Quadruple], bool]:
    """Aplica constant folding a la lista entera."""
    out: list[Quadruple] = []
    changed = False
    for q in quads:
        new_q = _fold(q)
        if new_q is not q:
            changed = True
        out.append(new_q)
    return out, changed


def _fold(q: Quadruple) -> Quadruple:
    op = q.op
    a1, a2 = q.arg1, q.arg2

    # --- Aritmética: ambos operandos numéricos (no bool) ---
    if op in _ARITH and is_numeric_const(a1) and is_numeric_const(a2):
        try:
            val = _ARITH[op](a1, a2)
        except (ZeroDivisionError, OverflowError, ValueError):
            return q
        if val is None:
            return q
        return replace_with_assign(q, val)

    # --- Relacional: pliega si ambos son const (numérico o bool) ---
    if op in _REL and is_const(a1) and is_const(a2):
        try:
            val = _REL[op](a1, a2)
        except TypeError:
            return q
        return replace_with_assign(q, bool(val))

    # --- Lógico binario: ambos lados const ---
    if op in _LOGIC and is_const(a1) and is_const(a2):
        return replace_with_assign(q, _LOGIC[op](a1, a2))

    # --- Unarios ---
    if op == 'NOT' and is_const(a1):
        return replace_with_assign(q, _UNARY['NOT'](a1))
    if op in ('UNARY_MINUS', 'UNARY_PLUS') and is_numeric_const(a1):
        return replace_with_assign(q, _UNARY[op](a1))

    return q
