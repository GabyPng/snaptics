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
    if not analyzer.symbol_table.exists(source_name):
        analyzer.add_error(
            SemanticErrorCode.DATASET_SOURCE_NOT_FOUND,
            line,
            f"El dataset fuente '{source_name}' no está declarado."
        )


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
    if not analyzer.symbol_table.exists(dataset_name):
        analyzer.add_error(
            SemanticErrorCode.DATASET_NOT_DECLARED,
            line,
            f"El dataset '{dataset_name}' no está declarado."
        )


def check_metric_dataset(analyzer: "SemanticAnalyzer", dataset_name: str, line: int):
    """
    Verifica que el dataset usado en una métrica estadística exista y sea de categoría 'dataset'.

    Contexto: `mean(ventas.region)` → 'ventas' debe existir y ser un dataset.

    Lanza SEM-302 si no existe, SEM-103 si no es dataset.

    Args:
        analyzer:     instancia del SemanticAnalyzer
        dataset_name: nombre del dataset
        line:         línea del código fuente
    """
    if not analyzer.symbol_table.exists(dataset_name):
        analyzer.add_error(
            SemanticErrorCode.DATASET_NOT_DECLARED,
            line,
            f"El dataset '{dataset_name}' no está declarado."
        )
        return
    
    category = analyzer.symbol_table.get_category(dataset_name)
    if category != 'dataset':
        analyzer.add_error(
            SemanticErrorCode.INVALID_SYMBOL_USE,
            line,
            f"El símbolo '{dataset_name}' no es un dataset válido."
        )


def check_column_exists(analyzer: "SemanticAnalyzer", column_name: str, line: int, dataset_name: str | None = None):
    """
    Verifica que la columna exista y sea de categoría 'column',
    opcionalmente comprueba que pertenezca al dataset dado.

    Contexto: `mean(dataset.col)` → 'col' debe existir como columna
    y *si se pasa dataset_name*, debe ser columna de ese dataset.

    Lanza SEM-101 si no existe, SEM-103 si no es columna o no pertenece.

    Args:
        analyzer:     instancia del SemanticAnalyzer
        column_name:  nombre de la columna
        line:         línea del código fuente
        dataset_name: nombre del dataset esperado (opcional)
    """
    if not analyzer.symbol_table.exists(column_name):
        analyzer.add_error(
            SemanticErrorCode.SYMBOL_NOT_DECLARED,
            line,
            f"La columna '{column_name}' no está declarada."
        )
        return
    
    symbol = analyzer.symbol_table.get(column_name)
    if symbol.category != 'column':
        analyzer.add_error(
            SemanticErrorCode.INVALID_SYMBOL_USE,
            line,
            f"El símbolo '{column_name}' no es una columna válida."
        )
        return
    
    if dataset_name is not None and getattr(symbol, 'dataset', None) != dataset_name:
        analyzer.add_error(
            SemanticErrorCode.INVALID_SYMBOL_USE,
            line,
            f"La columna '{column_name}' no pertenece al dataset '{dataset_name}'."
        )


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
    if not analyzer.symbol_table.exists(name):
        analyzer.add_error(
            SemanticErrorCode.QUERY_SYMBOL_NOT_FOUND,
            line,
            f"No se puede consultar '{name}': no está declarado."
        )
        return
    
    category = analyzer.symbol_table.get_category(name)
    if category not in _QUERYABLE_CATEGORIES:
        analyzer.add_error(
            SemanticErrorCode.QUERY_SYMBOL_NOT_FOUND,
            line,
            f"No se puede consultar '{name}': es de tipo '{category}' (solo se pueden consultar facts, rules y metrics)."
        )


def check_rule_identifier(analyzer: "SemanticAnalyzer", name: str, line: int):
    """
    Verifica que el identificador en una regla exista y sea válido.

    Un identificador en regla debe existir como 'fact', 'rule' o 'metric'.
    No se permiten columnas (ni simples ni via dataset.columna) en reglas.

    Contexto: `rule baja_rentabilidad :- ventas_altas < 0.5` → `ventas_altas` debe existir como
              fact.

    Lanza SEM-401 si `name` no existe o no es de tipo queryable.
    Agregar más tipos queryables a las rules, de momento solo facts, pero podrían ser rules o metrics también.

    Args:
        analyzer: instancia del SemanticAnalyzer
        name:     identificador en la regla
        line:     línea del código fuente
    """
    if not analyzer.symbol_table.exists(name):
        analyzer.add_error(
            SemanticErrorCode.INVALID_RULE,
            line,
            f"Identificador '{name}' en regla no está declarado."
        )
        return
    
    category = analyzer.symbol_table.get_category(name)
    if category != 'fact':
        analyzer.add_error(
            SemanticErrorCode.INVALID_RULE,
            line,
            f"En reglas solo se pueden usar hechos; '{name}' es de tipo '{category}'."
        )


def check_fact_identifier(analyzer: "SemanticAnalyzer", name: str, line: int):
    """
    Verifica que el identificador en un fact (dentro de prob(expr)) exista y sea válido.

    En facts se pueden usar identificadores de cualquier categoría EXCEPTO columnas simples.
    Las columnas DEBEN accederse como dataset.columna.

    Contexto: `fact p_reprobacion = P(alumnos.asistencia_baja given alumnos.promedio)`
              → Acceso a columnas: `fact p = P(alumnos.promedio < 60)` (dataset.columna)

    Lanza SEM-103 si es una columna simple (debe usar dataset.columna).
    Lanza SEM-101 si no existe.

    Args:
        analyzer: instancia del SemanticAnalyzer
        name:     identificador en el fact
        line:     línea del código fuente
    """
    if not analyzer.symbol_table.exists(name):
        analyzer.add_error(
            SemanticErrorCode.SYMBOL_NOT_DECLARED,
            line,
            f"Identificador '{name}' no está declarado."
        )
        return
    
    category = analyzer.symbol_table.get_category(name)
    if category == 'column':
        analyzer.add_error(
            SemanticErrorCode.INVALID_SYMBOL_USE,
            line,
            f"La columna '{name}' no puede usarse como identificador simple. Use la sintaxis dataset.columna (ej: alumnos.promedio)."
        )
