"""
Verificación de Símbolos — Carim (SEM-1xx)
==========================================
Funciones que el SemanticAnalyzer llama para validar el uso de símbolos.

Errores manejados aquí:
  SEM-101  Símbolo no declarado
  SEM-102  Redeclaración de símbolo
  SEM-103  Uso incorrecto de símbolo
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from semantic.semantic_analyzer import SemanticAnalyzer

from semantic.semantic_errors import SemanticErrorCode


def check_symbol_declared(analyzer: "SemanticAnalyzer", name: str, line: int):
    """
    Verifica que `name` esté declarado en la tabla de símbolos.

    Lanza SEM-101 si el símbolo no existe.

    Args:
        analyzer: instancia del SemanticAnalyzer (para registrar errores)
        name:     nombre del identificador a verificar
        line:     línea del código fuente
    """
    # TODO (Carim): implementar usando analyzer.symbol_table.exists(name)
    pass


def check_redeclaration(
    analyzer: "SemanticAnalyzer",
    name: str,
    category: str,
    line: int,
):
    """
    Verifica que `name` no haya sido declarado previamente.

    Si ya existe en la tabla de símbolos lanza SEM-102.
    Si no existe, lo registra con la categoría indicada.

    Args:
        analyzer: instancia del SemanticAnalyzer
        name:     nombre del símbolo a declarar
        category: categoría del símbolo ('dataset', 'fact', 'rule', 'metric')
        line:     línea del código fuente
    """
    # TODO (Carim): implementar usando analyzer.symbol_table.exists(name)
    # Si existe → add_error(SemanticErrorCode.SYMBOL_REDECLARED, line, ...)
    # Si no existe → analyzer.symbol_table.add(name, category, None, line)
    pass


def check_symbol_category(
    analyzer: "SemanticAnalyzer",
    name: str,
    expected_categories: list[str],
    line: int,
):
    """
    Verifica que `name` tenga una de las categorías esperadas.

    Lanza SEM-103 si la categoría no coincide.

    Ejemplo: en `query ventas`, ventas debe ser 'fact', 'rule' o 'metric',
    no 'dataset'.

    Args:
        analyzer:            instancia del SemanticAnalyzer
        name:                nombre del símbolo
        expected_categories: lista de categorías válidas para este contexto
        line:                línea del código fuente
    """
    # TODO (Carim): implementar usando analyzer.symbol_table.get_category(name)
    # Si la categoría no está en expected_categories → add_error(SEM-103, ...)
    pass
