"""
Verificación de Tipos — Fanny (SEM-2xx)
========================================
Funciones que el SemanticAnalyzer llama para validar tipos en expresiones.

Errores manejados aquí:
  SEM-201  Tipos incompatibles          (operaciones aritméticas)
  SEM-202  Operador lógico con tipo inválido
  SEM-203  Comparación inválida

Tipos del lenguaje snaptics:
  'int', 'real', 'bool', 'string', 'dataset', 'unknown'
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from semantic.semantic_analyzer import SemanticAnalyzer
    from parser import ASTNode

from semantic.semantic_errors import SemanticErrorCode


def infer_type(node: "ASTNode", analyzer: "SemanticAnalyzer") -> str:
    """
    Determina el tipo resultante de una expresión.

    Reglas de promoción:
      int  + int  → int
      int  + real → real
      real + real → real

    Args:
        node:     nodo de expresión del AST
        analyzer: instancia del SemanticAnalyzer (acceso a symbol_table)

    Returns:
        Cadena con el tipo: 'int', 'real', 'bool', 'string', 'dataset', 'unknown'
    """
    # TODO (Fanny): implementar inferencia de tipos por tipo de nodo
    return 'unknown'


def check_arithmetic_operation(analyzer: "SemanticAnalyzer", node: "ASTNode"):
    """
    Verifica que los operandos de una operación aritmética sean numéricos.

    Operadores: +  -  *  /  ^
    Tipos válidos: 'int', 'real'
    Lanza SEM-201 si algún operando no es numérico.

    Ejemplo inválido:  3 + ventas   (ventas es 'dataset')

    Args:
        analyzer: instancia del SemanticAnalyzer
        node:     nodo OperacionAritmetica del AST
    """
    # TODO (Fanny): obtener tipo de izq y der con infer_type()
    # Si alguno no es 'int' ni 'real' → add_error(SemanticErrorCode.TYPE_MISMATCH, ...)
    pass


def check_logical_operation(analyzer: "SemanticAnalyzer", node: "ASTNode"):
    """
    Verifica que los operandos de AND / OR / NOT sean booleanos.

    Tipos válidos: 'bool'
    Lanza SEM-202 si algún operando no es booleano.

    Ejemplo inválido:  ventas OR 4

    Args:
        analyzer: instancia del SemanticAnalyzer
        node:     nodo OperacionLogica del AST
    """
    # TODO (Fanny): obtener tipo de izq/der/operando con infer_type()
    # Si alguno no es 'bool' → add_error(SemanticErrorCode.INVALID_LOGICAL_TYPE, ...)
    pass


def check_relational_operation(analyzer: "SemanticAnalyzer", node: "ASTNode"):
    """
    Verifica compatibilidad de tipos en operaciones relacionales.

    Reglas:
      - 'int'  y 'real' son comparables entre sí
      - 'string' solo comparable con 'string'
      - 'bool'  solo comparable con 'bool' (== y !=)
      - 'dataset' nunca es comparable

    Lanza SEM-203 si los tipos no son compatibles.

    Ejemplo inválido:  "hola" > 5

    Args:
        analyzer: instancia del SemanticAnalyzer
        node:     nodo OperacionRelacional del AST
    """
    # TODO (Fanny): obtener tipo de izq y der con infer_type()
    # Si los tipos son incompatibles → add_error(SemanticErrorCode.INVALID_COMPARISON, ...)
    pass
