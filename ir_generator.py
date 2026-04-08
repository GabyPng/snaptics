"""
Generador de Representación Intermedia — Cuádruplas
====================================================
Recorre el AST validado y genera una lista de cuádruplas
(operador, arg1, arg2, resultado).

Usa el mismo patrón Visitor del SemanticAnalyzer.
"""

from __future__ import annotations
from parser import ASTNode
from symbol_table import SymbolTable
from semantic.semantic_analyzer import ASTVisitor


class Quadruple:
    """Una instrucción de código intermedio."""

    __slots__ = ('op', 'arg1', 'arg2', 'result')

    def __init__(self, op: str, arg1=None, arg2=None, result=None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result

    def __repr__(self):
        return f"({self.op}, {self.arg1}, {self.arg2}, {self.result})"


class IRGenerator(ASTVisitor):
    """Genera cuádruplas a partir del AST anotado."""

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self.quadruples: list[Quadruple] = []
        self._temp_counter = 0
        self._label_counter = 0

    # ---------- utilidades ----------

    def new_temp(self) -> str:
        """Genera un nombre de temporal único: t0, t1, t2..."""
        name = f"t{self._temp_counter}"
        self._temp_counter += 1
        return name

    def new_label(self) -> str:
        """Genera una etiqueta única: L0, L1, L2..."""
        name = f"L{self._label_counter}"
        self._label_counter += 1
        return name

    def emit(self, op: str, arg1=None, arg2=None, result=None) -> str:
        """Emite una cuádrupla y retorna el resultado."""
        quad = Quadruple(op, arg1, arg2, result)
        self.quadruples.append(quad)
        return result

    # ---------- interfaz pública ----------

    def generate(self, ast: ASTNode) -> list[Quadruple]:
        """Punto de entrada: genera IR a partir del AST."""
        self.quadruples = []
        self._temp_counter = 0
        self._label_counter = 0
        self.visit(ast)
        return self.quadruples

    # ---------- visita: sentencias ----------

    def visit_Programa(self, node: ASTNode):
        for sentencia in node.properties.get('sentencias', []):
            self.visit(sentencia)

    def visit_Importacion(self, node: ASTNode):
        """dataset id = import from 'archivo'"""
        dataset_id = node.properties.get('dataset_id')
        source_file = node.properties.get('source_file')
        self.emit('LOAD_DATASET', source_file, None, dataset_id)

    def visit_Preprocesamiento(self, node: ASTNode):
        """dataset id = select cols from source [where cond]"""
        dataset_id = node.properties.get('dataset_id')
        source = node.properties.get('source')
        columnas = node.properties.get('columnas', [])

        # Columnas como string para la cuádrupla
        cols_str = ', '.join(f"{name}:{typ}" if typ else name
                             for name, typ in columnas)

        # SELECT base
        t_select = self.new_temp()
        self.emit('SELECT', source, cols_str, t_select)

        # WHERE opcional
        condicion = node.properties.get('condicion')
        if condicion:
            cond_result = self.visit(condicion)
            t_filtered = self.new_temp()
            self.emit('FILTER', t_select, cond_result, t_filtered)
            t_select = t_filtered

        # Asignar al dataset destino
        self.emit('ASSIGN', t_select, None, dataset_id)

    def visit_DeclaracionHecho(self, node: ASTNode):
        """fact id = P(expr) o fact id = P(expr given expr)"""
        fact_id = node.properties.get('fact_id')
        prob_result = self.visit(node.properties.get('probabilidad'))
        self.emit('ASSIGN', prob_result, None, fact_id)

    def visit_DeclaracionMetrica(self, node: ASTNode):
        """id = mean(ds.col) | var(...) | std(...) | correlation(...)"""
        var_id = node.properties.get('var_id')
        metric_result = self.visit(node.properties.get('metrica'))
        self.emit('ASSIGN', metric_result, None, var_id)

    def visit_DeclaracionRegla(self, node: ASTNode):
        """rule id :- expresion"""
        rule_id = node.properties.get('rule_id')
        cond_result = self.visit(node.properties.get('condicion'))
        self.emit('RULE_DEF', cond_result, None, rule_id)

    def visit_Consulta(self, node: ASTNode):
        """query id [explain]"""
        query_id = node.properties.get('query_id')
        explain = node.properties.get('explicacion')
        if explain:
            self.emit('QUERY_EXPLAIN', query_id, None, None)
        else:
            self.emit('QUERY', query_id, None, None)

    # ---------- visita: expresiones ----------

    def visit_OperacionAritmetica(self, node: ASTNode):
        izq = self.visit(node.properties.get('izq'))
        der = self.visit(node.properties.get('der'))
        op_map = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV', '^': 'POW'}
        op = op_map.get(node.properties.get('operador'), 'OP')
        t = self.new_temp()
        self.emit(op, izq, der, t)
        return t

    def visit_OperacionRelacional(self, node: ASTNode):
        izq = self.visit(node.properties.get('izq'))
        der = self.visit(node.properties.get('der'))
        op_map = {
            '==': 'EQ', '!=': 'NEQ',
            '<': 'LT', '>': 'GT',
            '<=': 'LEQ', '>=': 'GEQ'
        }
        op = op_map.get(node.properties.get('operador'), 'CMP')
        t = self.new_temp()
        self.emit(op, izq, der, t)
        return t

    def visit_OperacionLogica(self, node: ASTNode):
        operador = node.properties.get('operador')

        if operador == 'NOT':
            operando = self.visit(node.properties.get('operando'))
            t = self.new_temp()
            self.emit('NOT', operando, None, t)
            return t

        izq = self.visit(node.properties.get('izq'))
        der = self.visit(node.properties.get('der'))
        t = self.new_temp()
        self.emit(operador, izq, der, t)  # 'AND' u 'OR'
        return t

    def visit_OperacionUnaria(self, node: ASTNode):
        operando = self.visit(node.properties.get('operando'))
        t = self.new_temp()
        op = 'UNARY_MINUS' if node.properties.get('operador') == '-' else 'UNARY_PLUS'
        self.emit(op, operando, None, t)
        return t

    def visit_Identificador(self, node: ASTNode):
        return node.properties.get('nombre')

    def visit_Literal(self, node: ASTNode):
        return node.properties.get('valor')

    def visit_AccesoMiembro(self, node: ASTNode):
        """dataset.columna → acceso a columna"""
        obj = node.properties.get('objeto')
        member = node.properties.get('miembro')
        t = self.new_temp()
        self.emit('MEMBER_ACCESS', obj, member, t)
        return t

    # ---------- visita: probabilidad ----------

    def visit_Probabilidad(self, node: ASTNode):
        condicion = self.visit(node.properties.get('condicion'))
        dado = node.properties.get('dado')
        t = self.new_temp()

        if dado:
            dado_result = self.visit(dado)
            self.emit('PROB_GIVEN', condicion, dado_result, t)
        else:
            self.emit('PROB', condicion, None, t)

        return t

    # ---------- visita: métricas estadísticas ----------

    def visit_Mean(self, node: ASTNode):
        t = self.new_temp()
        ds = node.properties.get('dataset')
        col = node.properties.get('columna')
        self.emit('MEAN', ds, col, t)
        return t

    def visit_Variance(self, node: ASTNode):
        t = self.new_temp()
        self.emit('VARIANCE', node.properties.get('dataset'),
                  node.properties.get('columna'), t)
        return t

    def visit_StdDev(self, node: ASTNode):
        t = self.new_temp()
        self.emit('STDDEV', node.properties.get('dataset'),
                  node.properties.get('columna'), t)
        return t

    def visit_Correlation(self, node: ASTNode):
        t = self.new_temp()
        ds1_col1 = f"{node.properties.get('dataset1')}.{node.properties.get('columna1')}"
        ds2_col2 = f"{node.properties.get('dataset2')}.{node.properties.get('columna2')}"
        self.emit('CORRELATION', ds1_col1, ds2_col2, t)
        return t

    def visit_ListaHechos(self, node: ASTNode):
        ds = node.properties.get('dataset')
        op = node.properties.get('operador')
        threshold = node.properties.get('threshold')
        t = self.new_temp()
        self.emit('AUTO_DISCOVER', ds, f"{op} {threshold}", t)
        return t


# ==================== GENERACIÓN DE IR ====================

def generate_ir(semantic_result: dict, parse_result: dict) -> dict:
    """
    Función de integración con el pipeline del compilador.

    Se llama DESPUÉS del análisis semántico exitoso.

    Args:
        semantic_result: dict retornado por semantic_analyzer.analyze()
        parse_result:    dict retornado por parser.parse()

    Returns:
        dict:
            'quadruples': list[Quadruple]
            'success':    bool
            'formatted':  str (representación legible)
    """
    if not semantic_result.get('success'):
        return {
            'quadruples': [],
            'success': False,
            'formatted': 'No se puede generar IR: hay errores semánticos.'
        }

    ast = parse_result.get('ast')
    symbol_table = parse_result.get('symbol_table')

    generator = IRGenerator(symbol_table)
    quads = generator.generate(ast)

    return {
        'quadruples': quads,
        'success': True,
        'formatted': format_quadruples(quads)
    }


def format_quadruples(quads: list[Quadruple]) -> str:
    """Formatea las cuádruplas como tabla legible."""
    if not quads:
        return "Sin instrucciones."

    lines = []
    lines.append(f"{'#':<4} {'Operador':<16} {'Arg1':<20} {'Arg2':<20} {'Resultado':<15}")
    lines.append("─" * 75)

    for i, q in enumerate(quads):
        a1 = str(q.arg1) if q.arg1 is not None else '—'
        a2 = str(q.arg2) if q.arg2 is not None else '—'
        res = str(q.result) if q.result is not None else '—'
        lines.append(f"{i:<4} {q.op:<16} {a1:<20} {a2:<20} {res:<15}")

    return '\n'.join(lines)
