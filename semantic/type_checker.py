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
    # (Fanny): implementar inferencia de tipos por tipo de nodo
    if node is None:
        return 'unknown'

    # Guard: el parser puede pasar valores Python crudos por conflictos de gramática
    if not hasattr(node, 'type'):
        if isinstance(node, bool):   return 'bool'
        if isinstance(node, int):    return 'int'
        if isinstance(node, float):  return 'real'
        if isinstance(node, str):    return 'string'
        return 'unknown'

    #Literales: El parser debe guardar el tipo en properties (ej: 'int', 'string')
    if node.type == 'Literal':
        return node.properties.get('tipo','unknown')
    
    #Indetificar, este se busca en la tabla de simbolos
    if node.type == 'Identificador':
        nombre=node.properties.get('nombre')
        # Usamos el método get_type que definimos 
        symbol = analyzer.symbol_table.get(nombre)
        if not symbol or not symbol.data_type:
            return 'unknown'
        # Normalizar tokens de tipo a strings del lenguaje
        _TYPE_MAP = {'TYPE_INT': 'int', 'TYPE_REAL': 'real', 'TYPE_STRING': 'string', 'TYPE_BOOL': 'bool'}
        return _TYPE_MAP.get(symbol.data_type, symbol.data_type)
    
    #Aritmético: Reglas (int+real=real)
    if node.type == 'OperacionAritmetica':
        t_izq=infer_type(node.properties.get('izq'),analyzer)
        t_der=infer_type(node.properties.get('der'),analyzer)
        #Si uno es real, el resultado es real
        if 'real' in [t_izq,t_der]: return 'real'
        if t_izq == 'int' and t_der == 'int': return 'int'
        return 'unknown'
    
    #Lógicas y Relacionales: Siempre devuelven bool si son válidos
    if node.type in ['OperacionLogica', 'OperacionRelacional']: 
        return 'bool'
    
    #Acceso a dataset.columna
    if node.type == 'AccesoMiembro':
        return 'dataset'
    
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
    # (Fanny): obtener tipo de izq y der con infer_type()
    # Si alguno no es 'int' ni 'real' → add_error(SemanticErrorCode.TYPE_MISMATCH, ...)
    t_izq = infer_type(node.properties.get('izq'),analyzer)
    t_der = infer_type(node.properties.get('der'),analyzer)
    
    validos = ['int', 'real']

    if 'unknown' in (t_izq, t_der):
        return  # tipo no resuelto, no hay suficiente info para reportar error

    if t_izq not in validos or t_der not in validos:
        detail = f"No se puede realizar operación aritmética entre '{t_izq}' y '{t_der}'."
        analyzer.add_error(SemanticErrorCode.TYPE_MISMATCH, node.line, detail)
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
    
    # Revisamos operandos según existan (NOT solo tiene 'operando')
    partes = {
        'izq': node.properties.get('izq'),
        'der': node.properties.get('der'),
        'operando': node.properties.get('operando')
    }
    for nombre, subnodo in partes.items():
        if subnodo:
            tipo = infer_type(subnodo, analyzer)
            if tipo == 'unknown':
                continue  # tipo no resuelto, no hay suficiente info para reportar error
            if tipo != 'bool':
                detail = f"Operador lógico requiere bool, pero se encontró '{tipo}' en {nombre}."
                analyzer.add_error(SemanticErrorCode.INVALID_LOGICAL_TYPE, node.line, detail)
            
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
    t_izq = infer_type(node.properties.get('izq'), analyzer)
    t_der = infer_type(node.properties.get('der'), analyzer)
    
    if 'unknown' in (t_izq, t_der):
        return  # tipo no resuelto, no hay suficiente info para reportar error

    compatibles = False

    # Reglas de compatibilidad
    if t_izq in ['int', 'real'] and t_der in ['int', 'real']:
        compatibles = True
    elif t_izq == t_der and t_izq in ['string', 'bool']:
        compatibles = True

    if not compatibles:
        detail = f"Comparación inválida entre '{t_izq}' y '{t_der}'."
        analyzer.add_error(SemanticErrorCode.INVALID_COMPARISON, node.line, detail)
    
    pass