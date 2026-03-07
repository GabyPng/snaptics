"""
Verificación de Datasets, Reglas y Consultas — Gibran (SEM-3xx / 4xx / 5xx)
=============================================================================
Funciones que el SemanticAnalyzer llama para validar datasets,
métricas estadísticas, reglas y consultas.

Errores manejados aquí:
  SEM-301  Dataset fuente inexistente
  SEM-302  Dataset no declarado
  SEM-401  Regla inválida
  SEM-501  Consulta a símbolo inexistente
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from semantic.semantic_analyzer import SemanticAnalyzer
    from parser import ASTNode

from semantic.semantic_errors import SemanticErrorCode

# Categorías que acepta `query`
_QUERYABLE_CATEGORIES = ('fact', 'rule', 'metric')


def check_dataset_source(analyzer: "SemanticAnalyzer", source_name: str, line: int):
    """
    Verifica que el dataset fuente en un preprocesamiento esté declarado.

    Contexto: `dataset ventas = select ... from clientes`
              → `clientes` debe existir como dataset.

    Lanza SEM-301 si `source_name` no está en la tabla de símbolos.

    Args:
        analyzer:    instancia del SemanticAnalyzer
        source_name: nombre del dataset fuente (ID después de FROM)
        line:        línea del código fuente
    """
    # TODO (Gibran): verificar con analyzer.symbol_table.exists(source_name)
    # Si no existe → add_error(SemanticErrorCode.DATASET_SOURCE_NOT_FOUND, line, ...)
    pass


def check_dataset_access(analyzer: "SemanticAnalyzer", dataset_name: str, line: int):
    """
    Verifica que el dataset referenciado en un acceso de columna exista.

    Contexto: `ventas.region`  → `ventas` debe estar declarado.

    Lanza SEM-302 si `dataset_name` no está en la tabla de símbolos.

    Args:
        analyzer:     instancia del SemanticAnalyzer
        dataset_name: nombre del dataset (parte izquierda del '.')
        line:         línea del código fuente
    """
    # TODO (Gibran): verificar con analyzer.symbol_table.exists(dataset_name)
    # Si no existe → add_error(SemanticErrorCode.DATASET_NOT_DECLARED, line, ...)
    pass


def check_metric_dataset(analyzer: "SemanticAnalyzer", dataset_name: str, line: int):
    """
    Verifica que el dataset usado en una métrica estadística exista.

    Contexto: `mean(ventas.region)` → `ventas` debe estar declarado.

    Lanza SEM-302 si `dataset_name` no está en la tabla de símbolos.

    Args:
        analyzer:     instancia del SemanticAnalyzer
        dataset_name: nombre del dataset
        line:         línea del código fuente
    """
    # TODO (Gibran): reutilizar check_dataset_access o verificar directamente
    check_dataset_access(analyzer, dataset_name, line)


def check_query_symbol(analyzer: "SemanticAnalyzer", name: str, line: int):
    """
    Verifica que el símbolo en una consulta exista y sea consultable.

    Un símbolo es consultable si su categoría es: 'fact', 'rule' o 'metric'.

    Contexto: `query rentabilidad` → `rentabilidad` debe existir como
              fact, rule o metric (no como dataset).

    Lanza SEM-501 si `name` no existe o no es consultable.

    Args:
        analyzer: instancia del SemanticAnalyzer
        name:     identificador de la consulta
        line:     línea del código fuente
    """
    # TODO (Gibran): verificar con analyzer.symbol_table.exists(name)
    # Verificar también la categoría con analyzer.symbol_table.get_category(name)
    # Si no existe o categoría no está en _QUERYABLE_CATEGORIES:
    #   → add_error(SemanticErrorCode.QUERY_SYMBOL_NOT_FOUND, line, ...)
    pass
