import ply.yacc as yacc
from lexer import tokens, make_lexer
from typing import Dict, Any, List

"""
Analizador Sintáctico para snaptics
Análisis de datos probabilístico con razonamiento lógico
"""

# ==================== PRECEDENCIA Y ASOCIATIVIDAD ====================
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQ', 'NEQ', 'LESSTHAN', 'GREATERTHAN', 'LEQ', 'GEQ'),
    ('left', 'ADD', 'SUB'),
    ('left', 'MUL', 'DIV'),
    ('right', 'UMINUS', 'UPLUS'),
    ('right', 'POW'),
)

# ==================== CLASES PARA EL AST ====================

class ASTNode:
    """Clase base para nodos del AST"""
    def __init__(self, node_type, **kwargs):
        self.type = node_type
        self.properties = kwargs
        self.line = kwargs.get('line', 0)
    
    def __repr__(self):
        props = ', '.join(f"{k}={v}" for k, v in self.properties.items())
        return f"{self.type}({props})"
    
    def to_dict(self):
        """Convierte el nodo a diccionario para serialización"""
        result = {'type': self.type}
        for k, v in self.properties.items():
            if isinstance(v, ASTNode):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [item.to_dict() if isinstance(item, ASTNode) else item for item in v]
            else:
                result[k] = v
        return result

# ==================== REGLAS DE LA GRAMÁTICA ====================

def p_programa_sentencia(p):
    '''programa : sentencia'''
    p[0] = ASTNode('Programa', sentencias=[p[1]], line=p.lineno(1))

def p_programa_multiple(p):
    '''programa : programa sentencia'''
    p[1].properties['sentencias'].append(p[2])
    p[0] = p[1]

def p_sentencia(p):
    '''sentencia : importacion
                 | preprocesamiento
                 | declaracion_hecho
                 | declaracion_regla
                 | consulta'''
    p[0] = p[1]

def p_importacion(p):
    '''importacion : DATASET ID ASIG IMPORT FROM STRING'''
    p[0] = ASTNode('Importacion', 
                   dataset_id=p[2],
                   source_file=p[6],
                   line=p.lineno(1))

def p_preprocesamiento_completo(p):
    '''preprocesamiento : DATASET ID ASIG SELECT lista_ids FROM ID condicion_opt agrupacion_opt descubrimiento_opt'''
    p[0] = ASTNode('Preprocesamiento',
                   dataset_id=p[2],
                   columnas=p[5],
                   source=p[7],
                   condicion=p[8],
                   agrupacion=p[9],
                   descubrimiento=p[10],
                   line=p.lineno(1))

def p_lista_ids_single(p):
    '''lista_ids : ID'''
    p[0] = [p[1]]

def p_lista_ids_multiple(p):
    '''lista_ids : ID COMMA lista_ids'''
    p[0] = [p[1]] + p[3]

def p_condicion_opt(p):
    '''condicion_opt : WHERE expresion
                    | empty'''
    p[0] = p[2] if len(p) == 3 else None

def p_agrupacion_opt(p):
    '''agrupacion_opt : GROUP lista_ids
                     | empty'''
    p[0] = p[2] if len(p) == 3 else None

def p_descubrimiento_opt(p):
    '''descubrimiento_opt : AUTO_DISCOVER lista_hechos
                         | empty'''
    p[0] = p[2] if len(p) == 3 else None

def p_lista_hechos(p):
    '''lista_hechos : DATASET LPAREN ID RPAREN WHERE CORRELATION operador_relacional REAL'''
    p[0] = ASTNode('ListaHechos',
                   dataset=p[3],
                   operador=p[7],
                   threshold=p[8],
                   line=p.lineno(1))

def p_declaracion_hecho_probabilidad(p):
    '''declaracion_hecho : FACT ID ASIG PROB LPAREN expresion RPAREN'''
    p[0] = ASTNode('DeclaracionHecho',
                   fact_id=p[2],
                   probabilidad=p[6],
                   line=p.lineno(1))

def p_declaracion_hecho_metrica(p):
    '''declaracion_hecho : declaracion_metrica'''
    p[0] = p[1]

def p_declaracion_metrica(p):
    '''declaracion_metrica : ID ASIG metrica_estatica'''
    p[0] = ASTNode('DeclaracionMetrica',
                   var_id=p[1],
                   metrica=p[3],
                   line=p.lineno(1))

def p_metrica_estatica_mean(p):
    '''metrica_estatica : MEAN LPAREN ID DOT ID RPAREN'''
    p[0] = ASTNode('Mean', dataset=p[3], columna=p[5], line=p.lineno(1))

def p_metrica_estatica_var(p):
    '''metrica_estatica : VAR LPAREN ID DOT ID RPAREN'''
    p[0] = ASTNode('Variance', dataset=p[3], columna=p[5], line=p.lineno(1))

def p_metrica_estatica_std(p):
    '''metrica_estatica : STD LPAREN ID DOT ID RPAREN'''
    p[0] = ASTNode('StdDev', dataset=p[3], columna=p[5], line=p.lineno(1))

def p_metrica_estatica_correlation(p):
    '''metrica_estatica : CORRELATION LPAREN ID DOT ID COMMA ID DOT ID RPAREN'''
    p[0] = ASTNode('Correlation',
                   dataset1=p[3], columna1=p[5],
                   dataset2=p[7], columna2=p[9],
                   line=p.lineno(1))

def p_declaracion_regla(p):
    '''declaracion_regla : RULE ID COND expresion'''
    p[0] = ASTNode('DeclaracionRegla',
                   rule_id=p[2],
                   condicion=p[4],
                   line=p.lineno(1))

def p_consulta(p):
    '''consulta : QUERY ID explicacion_opt'''
    p[0] = ASTNode('Consulta',
                   query_id=p[2],
                   explicacion=p[3],
                   line=p.lineno(1))

def p_explicacion_opt(p):
    '''explicacion_opt : EXPLAIN
                      | empty'''
    p[0] = p[1] if len(p) == 2 and p[1] else None

def p_expresion_or(p):
    '''expresion : expresion OR termino_comparacion'''
    p[0] = ASTNode('OperacionLogica', operador='OR', izq=p[1], der=p[3], line=p.lineno(2))

def p_expresion_termino(p):
    '''expresion : termino_comparacion'''
    p[0] = p[1]

def p_termino_comparacion_and(p):
    '''termino_comparacion : termino_comparacion AND termino_logico'''
    p[0] = ASTNode('OperacionLogica', operador='AND', izq=p[1], der=p[3], line=p.lineno(2))

def p_termino_comparacion_logico(p):
    '''termino_comparacion : termino_logico'''
    p[0] = p[1]

def p_termino_logico_not(p):
    '''termino_logico : NOT factor_logico'''
    p[0] = ASTNode('OperacionLogica', operador='NOT', operando=p[2], line=p.lineno(1))

def p_termino_logico_factor(p):
    '''termino_logico : factor_logico'''
    p[0] = p[1]

def p_factor_logico_parentesis(p):
    '''factor_logico : LPAREN expresion RPAREN'''
    p[0] = p[2]

def p_factor_logico_relacional(p):
    '''factor_logico : termino_relacional'''
    p[0] = p[1]

def p_factor_logico_probabilidad(p):
    '''factor_logico : probabilidad_condicional'''
    p[0] = p[1]

def p_factor_logico_id(p):
    '''factor_logico : ID'''
    p[0] = ASTNode('Identificador', nombre=p[1], line=p.lineno(1))

def p_factor_logico_booleano(p):
    '''factor_logico : TRUE
                    | FALSE'''
    p[0] = ASTNode('Literal', tipo='bool', valor=(p[1] == 'true'), line=p.lineno(1))

def p_termino_relacional(p):
    '''termino_relacional : termino_aritmetico operador_relacional termino_aritmetico'''
    p[0] = ASTNode('OperacionRelacional',
                   operador=p[2],
                   izq=p[1],
                   der=p[3],
                   line=p[1].line if isinstance(p[1], ASTNode) else 0)

def p_probabilidad_condicional_simple(p):
    '''probabilidad_condicional : PROB LPAREN termino_relacional RPAREN'''
    p[0] = ASTNode('Probabilidad', condicion=p[3], dado=None, line=p.lineno(1))

def p_probabilidad_condicional_given(p):
    '''probabilidad_condicional : PROB LPAREN termino_relacional GIVEN termino_relacional RPAREN'''
    p[0] = ASTNode('Probabilidad', condicion=p[3], dado=p[5], line=p.lineno(1))

def p_operador_relacional(p):
    '''operador_relacional : EQ
                          | NEQ
                          | LEQ
                          | GEQ
                          | LESSTHAN
                          | GREATERTHAN'''
    p[0] = p[1]

def p_termino_aritmetico_add(p):
    '''termino_aritmetico : termino_aritmetico ADD factor_aritmetico'''
    p[0] = ASTNode('OperacionAritmetica', operador='+', izq=p[1], der=p[3], line=p.lineno(2))

def p_termino_aritmetico_sub(p):
    '''termino_aritmetico : termino_aritmetico SUB factor_aritmetico'''
    p[0] = ASTNode('OperacionAritmetica', operador='-', izq=p[1], der=p[3], line=p.lineno(2))

def p_termino_aritmetico_factor(p):
    '''termino_aritmetico : factor_aritmetico'''
    p[0] = p[1]

def p_factor_aritmetico_mul(p):
    '''factor_aritmetico : factor_aritmetico MUL unario_aritmetico'''
    p[0] = ASTNode('OperacionAritmetica', operador='*', izq=p[1], der=p[3], line=p.lineno(2))

def p_factor_aritmetico_div(p):
    '''factor_aritmetico : factor_aritmetico DIV unario_aritmetico'''
    p[0] = ASTNode('OperacionAritmetica', operador='/', izq=p[1], der=p[3], line=p.lineno(2))

def p_factor_aritmetico_unario(p):
    '''factor_aritmetico : unario_aritmetico'''
    p[0] = p[1]

def p_unario_aritmetico_minus(p):
    '''unario_aritmetico : SUB potencia %prec UMINUS'''
    p[0] = ASTNode('OperacionUnaria', operador='-', operando=p[2], line=p.lineno(1))

def p_unario_aritmetico_plus(p):
    '''unario_aritmetico : ADD potencia %prec UPLUS'''
    p[0] = ASTNode('OperacionUnaria', operador='+', operando=p[2], line=p.lineno(1))

def p_unario_aritmetico_potencia(p):
    '''unario_aritmetico : potencia'''
    p[0] = p[1]

def p_potencia_pow(p):
    '''potencia : valor_base POW unario_aritmetico'''
    p[0] = ASTNode('OperacionAritmetica', operador='^', izq=p[1], der=p[3], line=p.lineno(2))

def p_potencia_valor(p):
    '''potencia : valor_base'''
    p[0] = p[1]

def p_valor_base_int(p):
    '''valor_base : INT'''
    p[0] = ASTNode('Literal', tipo='int', valor=p[1], line=p.lineno(1))

def p_valor_base_real(p):
    '''valor_base : REAL'''
    p[0] = ASTNode('Literal', tipo='real', valor=p[1], line=p.lineno(1))

def p_valor_base_string(p):
    '''valor_base : STRING'''
    p[0] = ASTNode('Literal', tipo='string', valor=p[1], line=p.lineno(1))

def p_valor_base_true(p):
    '''valor_base : TRUE'''
    p[0] = ASTNode('Literal', tipo='bool', valor=True, line=p.lineno(1))

def p_valor_base_false(p):
    '''valor_base : FALSE'''
    p[0] = ASTNode('Literal', tipo='bool', valor=False, line=p.lineno(1))

def p_valor_base_id(p):
    '''valor_base : ID'''
    p[0] = ASTNode('Identificador', nombre=p[1], line=p.lineno(1))

def p_valor_base_id_dot(p):
    '''valor_base : ID DOT ID'''
    p[0] = ASTNode('AccesoMiembro', objeto=p[1], miembro=p[3], line=p.lineno(1))

def p_valor_base_parentesis(p):
    '''valor_base : LPAREN expresion RPAREN'''
    p[0] = p[2]

def p_empty(p):
    '''empty :'''
    pass

# ==================== MANEJO DE ERRORES ====================

def p_error(p):
    """Maneja errores sintácticos"""
    if p:
        error = {
            'type': 'syntax_error',
            'line': p.lineno,
            'column': find_column(p),
            'token': p.type,
            'value': p.value,
            'message': f"Error de sintaxis: token inesperado '{p.value}' (tipo: {p.type})"
        }
        parser.errors.append(error)
        parser.errok()
    else:
        error = {
            'type': 'syntax_error',
            'line': 'EOF',
            'column': 0,
            'token': 'EOF',
            'value': None,
            'message': "Error de sintaxis: final inesperado del archivo"
        }
        parser.errors.append(error)

def find_column(token):
    """Encuentra la columna de un token"""
    if not hasattr(token, 'lexpos'):
        return 0
    input_text = token.lexer.lexdata
    line_start = input_text.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1

# ==================== CONSTRUCCIÓN DEL PARSER ====================

parser = None

def make_parser():
    """Construye y devuelve una instancia del parser"""
    global parser
    parser = yacc.yacc()
    parser.errors = []
    return parser

# ==================== FUNCIÓN DE PARSING ====================

def parse(text: str, debug=False) -> Dict[str, Any]:
    """
    Parsea el texto y devuelve el AST y errores.
    
    Returns:
        Dict con:
        - 'ast': Árbol de sintaxis abstracta
        - 'errors': Lista de errores sintácticos
        - 'success': Boolean indicando éxito
    """
    lexer_instance = make_lexer()
    parser_instance = make_parser()
    parser_instance.errors = []
    
    try:
        ast = parser_instance.parse(text, lexer=lexer_instance, debug=debug)
        
        return {
            'ast': ast,
            'errors': parser_instance.errors,
            'success': len(parser_instance.errors) == 0
        }
    except Exception as e:
        return {
            'ast': None,
            'errors': parser_instance.errors + [{
                'type': 'critical_error',
                'message': f"Error crítico: {str(e)}"
            }],
            'success': False
        }

# ==================== UTILIDADES ====================

def print_ast(node, indent=0):
    """Imprime el AST de forma legible"""
    if node is None:
        return
    
    prefix = "  " * indent
    if isinstance(node, ASTNode):
        print(f"{prefix}{node.type}")
        for key, value in node.properties.items():
            if key == 'line':
                continue
            print(f"{prefix}  {key}:")
            if isinstance(value, ASTNode):
                print_ast(value, indent + 2)
            elif isinstance(value, list):
                for item in value:
                    print_ast(item, indent + 2)
            else:
                print(f"{prefix}    {value}")
    else:
        print(f"{prefix}{node}")

def format_syntax_errors(errors: List[Dict]) -> str:
    """Formatea errores sintácticos para mostrar en consola"""
    if not errors:
        return ""
    
    lines = []
    lines.append("=" * 70)
    lines.append(f"  SE ENCONTRARON {len(errors)} ERROR(ES) SINTÁCTICO(S)")
    lines.append("=" * 70)
    lines.append("")
    
    for i, error in enumerate(errors, 1):
        lines.append(f"[Error #{i}]")
        if error.get('line') == 'EOF':
            lines.append(f"  Posición: Final del archivo")
        else:
            lines.append(f"  Línea {error.get('line', '?')}, Columna {error.get('column', '?')}")
        lines.append(f"  Problema: {error.get('message', 'Error desconocido')}")
        lines.append("")
        lines.append("-" * 70)
        lines.append("")
    
    return "\n".join(lines)