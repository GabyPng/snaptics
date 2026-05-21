"""
Utilidades compartidas por los pases de optimización.
======================================================
Definiciones de constantes, predicados y helpers usados por
múltiples pases. Concentrarlos aquí evita inconsistencias.
"""

from __future__ import annotations
from ir_generator import Quadruple


# ---------- predicados de tipo ----------

def is_numeric_const(v) -> bool:
    """True si v es int o float (excluye bool, que se trata aparte)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_bool_const(v) -> bool:
    """True si v es un booleano literal (Python bool)."""
    return isinstance(v, bool)


def is_const(v) -> bool:
    """True si v es cualquier literal evaluable: int, float o bool."""
    return isinstance(v, (int, float, bool))


def is_temp(name) -> bool:
    """
    True si name corresponde al patrón de temporal del IRGenerator:
    't' seguido de uno o más dígitos (t0, t1, t12, ...).
    """
    if not isinstance(name, str) or len(name) < 2:
        return False
    return name[0] == 't' and name[1:].isdigit()


# ---------- operadores ----------

ARITHMETIC_OPS = {'ADD', 'SUB', 'MUL', 'DIV', 'POW'}
RELATIONAL_OPS = {'EQ', 'NEQ', 'LT', 'GT', 'LEQ', 'GEQ'}
LOGICAL_BINARY_OPS = {'AND', 'OR'}
UNARY_OPS = {'NOT', 'UNARY_MINUS', 'UNARY_PLUS'}

# Operaciones puras: sin efectos colaterales. Pueden eliminarse cuando
# su resultado no se utiliza.
PURE_OPS = (
    ARITHMETIC_OPS
    | RELATIONAL_OPS
    | LOGICAL_BINARY_OPS
    | UNARY_OPS
    | {'ASSIGN'}
)


# ---------- búsqueda en el flujo lineal ----------

def find_def(quads: list[Quadruple], idx: int, name) -> Quadruple | None:
    """
    Busca hacia atrás (desde idx-1 hasta 0) la cuádrupla que define `name`.

    Como Snaptics no tiene flujo de control, cada bloque básico se
    corresponde con una secuencia lineal de cuádruplas y la última
    asignación a `name` antes de idx es la definición vigente.

    Retorna None si no se encuentra o si name no es una cadena.
    Complejidad: O(idx).
    """
    if not isinstance(name, str):
        return None
    for j in range(idx - 1, -1, -1):
        if quads[j].result == name:
            return quads[j]
    return None


# ---------- factory que preserva inmutabilidad lógica ----------

def replace_with_assign(q: Quadruple, value) -> Quadruple:
    """
    Reemplaza la cuádrupla `q` por (ASSIGN, value, None, q.result).
    Patrón usado por casi todos los pases al simplificar una expresión
    a un valor inmediato.
    """
    return Quadruple('ASSIGN', value, None, q.result)
