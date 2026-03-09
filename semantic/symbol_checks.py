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
    if not analyzer.symbol_table.exists(name):
        analyzer.add_error(
            SemanticErrorCode.SYMBOL_NOT_DECLARED,
            line,
            f"El símbolo '{name}' no ha sido declarado."
        )


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
    # verificar si ya fue procesado por el semantico (redeclaración verdadera)
    if name in analyzer._processed_symbols:
        analyzer.add_error(
            SemanticErrorCode.SYMBOL_REDECLARED,
            line,
            f"El símbolo '{name}' ya ha sido declarado."
        )
        return
    
    # Marcar como procesado
    analyzer._processed_symbols.add(name)
    
    if analyzer.symbol_table.exists(name):
        # El simbolo ya existe en la tabla 
        existing_symbol = analyzer.symbol_table.get(name)
        
        # Si no tiene categoria, asignarla
        if existing_symbol and existing_symbol.category is None:
            existing_symbol.category = category
        elif existing_symbol and existing_symbol.category != category:
            # Redeclaracion con categoria diferente
            analyzer.add_error(
                SemanticErrorCode.SYMBOL_REDECLARED,
                line,
                f"El símbolo '{name}' fue declarado anteriormente como '{existing_symbol.category}', "
                f"pero aquí se intenta declarar como '{category}'."
            )
    else:
        # No existe, agregarlo con la categoria indicada
        analyzer.symbol_table.add(name, category, None, line)


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
    actual_category = analyzer.symbol_table.get_category(name)
    
    if actual_category is None:
        # El símbolo no existe; check_symbol_declared debería haber lanzado SEM-101
        return
    
    if actual_category not in expected_categories:
        expected_str = ", ".join(expected_categories)
        analyzer.add_error(
            SemanticErrorCode.INVALID_SYMBOL_USE,
            line,
            f"El símbolo '{name}' es '{actual_category}', pero se esperaba uno de: {expected_str}."
        )
