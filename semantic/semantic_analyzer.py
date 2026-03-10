"""
Analizador Semántico — snaptics
================================
Implementa el patrón Visitor para recorrer el AST y coordinar
todas las verificaciones semánticas del compilador.

Arquitectura:
  ASTVisitor          — clase base del patrón Visitor
  SemanticAnalyzer    — visitor concreto; orquesta los módulos de uno
  analyze(result)     — función de integración con el pipeline del compilador

Módulos de verificación:
  semantic/symbol_checks.py  — Carim   (SEM-1xx)
  semantic/type_checker.py   — Fanny   (SEM-2xx)
  semantic/DRQ_checks.py     — Gibran  (SEM-3xx / 4xx / 5xx)
"""

import sys
import os

# Asegura que la raíz del proyecto esté en el path cuando se importa
# como submódulo desde la carpeta semantic/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from parser import ASTNode
from symbol_table import SymbolTable
from semantic.semantic_errors import SemanticError


# ========================================
#           CLASE BASE: VISITOR AST
# ========================================

class ASTVisitor:
    """
    Clase base para el patrón Visitor sobre el AST 

    Uso:
        Cada nodo del AST tiene un atributo `type` (str).
        `visit(node)` busca el método `visit_<type>` en la subclase;
        si no existe, cae en `generic_visit` que recorre todos los hijos.

    Ejemplo para una subclase:
        def visit_Literal(self, node):
            return node.properties.get('tipo')
    """

    def visit(self, node):
        """Despacha la visita al método específico del tipo de nodo."""
        if node is None or not isinstance(node, ASTNode):
            return None
        method = getattr(self, f'visit_{node.type}', self.generic_visit)
        return method(node)

    def generic_visit(self, node):
        """
        Visita genérica: recorre recursivamente todos los hijos ASTNode.
        Llamado cuando no hay un método visit_<tipo> específico.
        """
        if node is None:
            return
        for value in node.properties.values():
            if isinstance(value, ASTNode):
                self.visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ASTNode):
                        self.visit(item)


# ==================== ANALIZADOR SEMÁNTICO ====================

class SemanticAnalyzer(ASTVisitor):
    """
    Analizador semántico principal de snaptics.

    Recorre el AST con el patrón Visitor y delega las verificaciones
    concretas a los módulos
      - symbol_checks  => Carim  (SEM-1xx)
      - type_checker   => Fanny  (SEM-2xx)
      - DRQ_checks     => Gibran (SEM-3xx / 4xx / 5xx)
    """

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self.errors: list[SemanticError] = []
        self._processed_symbols = set()  # simbolos procesados por el semantico, usado para revisar redeclaraciones en symbol_checks.py
        self._in_rule = False
        self._in_fact = False

    # ---------- interfaz pública ----------

    def analyze(self, ast: ASTNode) -> dict:
        """
        Punto de entrada del análisis semántico.

        Args:
            ast: nodo raíz del AST (tipo 'Programa')

        Returns:
            {'errors': list[SemanticError], 'success': bool}
        """
        self.errors = []
        self.visit(ast)
        return {
            'errors': self.errors,
            'success': len(self.errors) == 0,
        }

    def add_error(self, code_tuple: tuple, line: int, detail: str = ""):
        """
        Registra un error semántico.

        Args:
            code_tuple: tupla (código, descripción) de SemanticErrorCode
            line:       línea del código fuente donde ocurre el error
            detail:     descripción concreta del problema
        """
        code, description = code_tuple
        self.errors.append(SemanticError(code, description, line, detail))

    # ==================== VISITA: SENTENCIAS ====================

    def visit_Programa(self, node: ASTNode):
        """Punto de entrada: recorre todas las sentencias del programa."""
        for sentencia in node.properties.get('sentencias', []):
            self.visit(sentencia)

    def visit_Importacion(self, node: ASTNode):
        """
        dataset id = import from "archivo"
        Carim: verificar redeclaración de símbolo (SEM-102)
        """
        from semantic.symbol_checks import check_redeclaration
        check_redeclaration(
            self,
            name=node.properties.get('dataset_id'),
            category='dataset',
            line=node.line,
        )

    def visit_Preprocesamiento(self, node: ASTNode):
        """
        dataset id = select ... from id [where ...] [group ...] [auto_discover ...]
        Carim:  verificar redeclaración              (SEM-102)
        Gibran: verificar que el dataset fuente exista (SEM-301)
        """
        from semantic.symbol_checks import check_redeclaration
        from semantic.DRQ_checks import check_dataset_source

        check_redeclaration(
            self,
            name=node.properties.get('dataset_id'),
            category='dataset',
            line=node.line,
        )
        check_dataset_source(
            self,
            source_name=node.properties.get('source'),
            line=node.line,
        )
        # Verificar que todas las columnas tengan tipo declarado (SEM-204)
        from semantic.semantic_errors import SemanticErrorCode
        for col_name, col_type in (node.properties.get('columnas') or []):
            if col_type is None:
                self.add_error(
                    SemanticErrorCode.MISSING_COLUMN_TYPE,
                    node.line,
                    f"La columna '{col_name}' requiere declaración de tipo (ej: {col_name}: real)."
                )
        self.visit(node.properties.get('condicion'))
        self.visit(node.properties.get('descubrimiento'))

    def visit_DeclaracionHecho(self, node: ASTNode):
        """
        fact id = prob(expr)
        Carim: verificar redeclaración (SEM-102)
        Fanny: verificar tipo de la probabilidad
        Gibran: verificar identificadores en expr (SEM-401)
        """
        from semantic.symbol_checks import check_redeclaration
        check_redeclaration(
            self,
            name=node.properties.get('fact_id'),
            category='fact',
            line=node.line,
        )
        # Los facts siempre son probabilidades → tipo real
        symbol = self.symbol_table.get(node.properties.get('fact_id'))
        if symbol:
            symbol.data_type = 'real'
        self._in_fact = True
        self.visit(node.properties.get('probabilidad'))
        self._in_fact = False

    def visit_DeclaracionMetrica(self, node: ASTNode):
        """
        id = mean(dataset.col) | var(...) | std(...) | correlation(...)
        Carim:  verificar redeclaración (SEM-102)
        Gibran: verificar que el dataset exista
        """
        from semantic.symbol_checks import check_redeclaration
        check_redeclaration(
            self,
            name=node.properties.get('var_id'),
            category='metric',
            line=node.line,
        )
        self.visit(node.properties.get('metrica'))

    def visit_DeclaracionRegla(self, node: ASTNode):
        """
        rule id cond expr
        Carim:  verificar redeclaración                  (SEM-102)
        Gibran: verificar símbolos referenciados en expr (SEM-401)
        """
        from semantic.symbol_checks import check_redeclaration
        check_redeclaration(
            self,
            name=node.properties.get('rule_id'),
            category='rule',
            line=node.line,
        )
        # Las reglas siempre evalúan a verdadero/falso → tipo bool
        symbol = self.symbol_table.get(node.properties.get('rule_id'))
        if symbol:
            symbol.data_type = 'bool'
        self._in_rule = True
        self.visit(node.properties.get('condicion'))
        self._in_rule = False

    def visit_Consulta(self, node: ASTNode):
        """
        query id [explain]
        Gibran: verificar que id exista como fact/rule/metric (SEM-501)
        """
        from semantic.DRQ_checks import check_query_symbol
        check_query_symbol(
            self,
            name=node.properties.get('query_id'),
            line=node.line,
        )

    # ==================== VISITA: EXPRESIONES ====================

    def visit_OperacionLogica(self, node: ASTNode):
        """
        expr AND/OR/NOT expr
        Fanny: verificar tipos válidos para operadores lógicos (SEM-202)
        """
        from semantic.type_checker import check_logical_operation
        self.visit(node.properties.get('izq'))
        self.visit(node.properties.get('der'))
        self.visit(node.properties.get('operando'))   # solo en NOT
        check_logical_operation(self, node)

    def visit_OperacionRelacional(self, node: ASTNode):
        """
        expr < / > / == / != / <= / >= expr
        Fanny: verificar compatibilidad de tipos (SEM-203)
        """
        from semantic.type_checker import check_relational_operation
        self.visit(node.properties.get('izq'))
        self.visit(node.properties.get('der'))
        check_relational_operation(self, node)

    def visit_OperacionAritmetica(self, node: ASTNode):
        """
        expr + / - / * / / / ^ expr
        Fanny: verificar tipos numéricos compatibles (SEM-201)
        """
        from semantic.type_checker import check_arithmetic_operation
        self.visit(node.properties.get('izq'))
        self.visit(node.properties.get('der'))
        check_arithmetic_operation(self, node)

    def visit_OperacionUnaria(self, node: ASTNode):
        """Operación unaria -x / +x: visita el operando."""
        self.visit(node.properties.get('operando'))

    def visit_Identificador(self, node: ASTNode):
        """
        Referencia a un identificador.
        Carim: verificar que el símbolo esté declarado (SEM-101) en contexto normal
        Gibran: 
          - En reglas: verificar que sea fact válido (SEM-401)
          - En facts: verificar que sea válido y tenga el formato correcto
        """
        if self._in_rule:
            from semantic.DRQ_checks import check_rule_identifier
            check_rule_identifier(
                self,
                name=node.properties.get('nombre'),
                line=node.line,
            )
        elif self._in_fact:
            from semantic.DRQ_checks import check_fact_identifier
            check_fact_identifier(
                self,
                name=node.properties.get('nombre'),
                line=node.line,
            )
        else:
            from semantic.symbol_checks import check_symbol_declared
            check_symbol_declared(
                self,
                name=node.properties.get('nombre'),
                line=node.line,
            )

    # visit_Literal no es necesario: generic_visit lo maneja correctamente
    # ya que los nodos Literal no tienen hijos ASTNode.

    def visit_AccesoMiembro(self, node: ASTNode):
        """
        dataset.columna
        Gibran: verificar que el dataset exista (SEM-302), columna pertenezca a él (SEM-103), y no se use en rules
        """
        if self._in_rule:
            self.add_error(
                ("SEM-401", "Regla inválida"),
                node.line,
                "En reglas no se permiten accesos directos a columnas de dataset. Use solo identificadores de facts"
            )
            return
        
        from semantic.DRQ_checks import check_dataset_access, check_column_exists
        objeto = node.properties.get('objeto')
        miembro = node.properties.get('miembro')
        check_dataset_access(self, objeto, node.line)
        check_column_exists(self, miembro, node.line, objeto)

    def visit_Probabilidad(self, node: ASTNode):
        """prob(expr) o prob(expr given expr): visita ambas subexpresiones."""
        self.visit(node.properties.get('condicion'))
        self.visit(node.properties.get('dado'))

    # ==================== VISITA: MÉTRICAS ESTADÍSTICAS ====================

    def visit_Mean(self, node: ASTNode):
        """
        mean(dataset.col)
        Gibran: verificar que el dataset exista y sea válido, y la columna exista
        """
        from semantic.DRQ_checks import check_metric_dataset, check_column_exists
        ds = node.properties.get('dataset')
        check_metric_dataset(self, dataset_name=ds, line=node.line)
        check_column_exists(self, column_name=node.properties.get('columna'), line=node.line, dataset_name=ds)

    def visit_Variance(self, node: ASTNode):
        """var(dataset.col)"""
        from semantic.DRQ_checks import check_metric_dataset, check_column_exists
        ds = node.properties.get('dataset')
        check_metric_dataset(self, dataset_name=ds, line=node.line)
        check_column_exists(self, column_name=node.properties.get('columna'), line=node.line, dataset_name=ds)

    def visit_StdDev(self, node: ASTNode):
        """std(dataset.col)"""
        from semantic.DRQ_checks import check_metric_dataset, check_column_exists
        ds = node.properties.get('dataset')
        check_metric_dataset(self, dataset_name=ds, line=node.line)
        check_column_exists(self, column_name=node.properties.get('columna'), line=node.line, dataset_name=ds)

    def visit_Correlation(self, node: ASTNode):
        """correlation(ds1.col1, ds2.col2)"""
        from semantic.DRQ_checks import check_metric_dataset, check_column_exists
        ds1 = node.properties.get('dataset1')
        ds2 = node.properties.get('dataset2')
        check_metric_dataset(self, dataset_name=ds1, line=node.line)
        check_column_exists(self, column_name=node.properties.get('columna1'), line=node.line, dataset_name=ds1)
        check_metric_dataset(self, dataset_name=ds2, line=node.line)
        check_column_exists(self, column_name=node.properties.get('columna2'), line=node.line, dataset_name=ds2)

    def visit_ListaHechos(self, node: ASTNode):
        """auto_discover dataset(id) where correlation ..."""
        from semantic.DRQ_checks import check_metric_dataset
        check_metric_dataset(self, dataset_name=node.properties.get('dataset'), line=node.line)


# ==================== INTEGRACIÓN CON EL COMPILADOR ====================

def analyze(parse_result: dict) -> dict:
    """
    Función de integración con el pipeline del compilador.

    Recibe el resultado del parser y ejecuta el análisis semántico.
    Si el parser falló no hay AST que analizar, por lo que se retorna
    un resultado vacío indicando fallo.

    Args:
        parse_result: dict retornado por parser.parse()
            - 'ast':          ASTNode raíz (None si hubo errores)
            - 'symbol_table': SymbolTable construida por el parser
            - 'success':      bool
            - 'errors':       lista de errores léxicos/sintácticos

    Returns:
        dict:
            - 'errors':     list[SemanticError]  — errores semánticos
            - 'success':    bool
            - 'all_errors': todos los errores (sintácticos + semánticos como dict)
    """
    syntax_errors = parse_result.get('errors', [])

    if not parse_result.get('success'):
        return {
            'errors': [],
            'success': False,
            'all_errors': syntax_errors,
        }

    ast = parse_result.get('ast')
    symbol_table = parse_result.get('symbol_table')

    if ast is None or symbol_table is None:
        return {
            'errors': [],
            'success': False,
            'all_errors': syntax_errors,
        }

    analyzer = SemanticAnalyzer(symbol_table)
    result = analyzer.analyze(ast)

    semantic_dicts = [e.to_dict() for e in result['errors']]

    return {
        'errors': result['errors'],
        'success': result['success'],
        'all_errors': syntax_errors + semantic_dicts,
    }
