import ply.yacc as yacc
from lexer import tokens, make_lexer
from typing import Dict, Any, List

"""
Analizador Sintáctico para snaptics
Análisis de datos probabilístico con razonamiento lógico

TODO
-
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

def p_programa(p):
    '''programa : sentencia
                | programa sentencia'''
    if len(p) == 2:
        # Filtrar None (errores)
        if p[1] is not None:
            p[0] = ASTNode('Programa', sentencias=[p[1]], line=p.lineno(1) if p[1] else 0)
        else:
            p[0] = ASTNode('Programa', sentencias=[], line=0)
    else:
        if p[1]:
            # Filtrar None (errores)
            if p[2] is not None:
                p[1].properties['sentencias'].append(p[2])
            p[0] = p[1]
        else: # pragma: no cover
            if p[2] is not None:
                p[0] = ASTNode('Programa', sentencias=[p[2]], line=p.lineno(1) if p[2] else 0)
            else:
                p[0] = ASTNode('Programa', sentencias=[], line=0)

def p_sentencia(p):
    '''sentencia : importacion
                 | preprocesamiento
                 | declaracion_hecho
                 | declaracion_regla
                 | consulta
                 | error'''
    # Si es un error, retornar None para que no se agregue al AST
    if len(p) == 2 and p.slice[1].type == 'error':
        p[0] = None
    else:
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

def p_lista_ids(p):
    '''lista_ids : ID
                 | ID COMMA lista_ids'''
    if len(p) == 2:  # Regla: lista_ids : ID
        p[0] = [p[1]]
    else:  # Regla: lista_ids : ID COMMA lista_ids
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

def p_declaracion_hecho(p):
    '''declaracion_hecho : FACT ID ASIG PROB LPAREN expresion RPAREN
                         | declaracion_metrica'''
    if len(p) > 2:
        p[0] = ASTNode('DeclaracionHecho',
                       fact_id=p[2],
                       probabilidad=p[6],
                       line=p.lineno(1))
    else:
        p[0] = p[1]

def p_declaracion_metrica(p):
    '''declaracion_metrica : ID ASIG metrica_estatica'''
    p[0] = ASTNode('DeclaracionMetrica',
                   var_id=p[1],
                   metrica=p[3],
                   line=p.lineno(1))

def p_metrica_estatica(p):
    '''metrica_estatica : MEAN LPAREN ID DOT ID RPAREN
                        | VAR LPAREN ID DOT ID RPAREN
                        | STD LPAREN ID DOT ID RPAREN
                        | CORRELATION LPAREN ID DOT ID COMMA ID DOT ID RPAREN'''
    if p[1] == 'mean':
        p[0] = ASTNode('Mean', dataset=p[3], columna=p[5], line=p.lineno(1))
    elif p[1] == 'var':
        p[0] = ASTNode('Variance', dataset=p[3], columna=p[5], line=p.lineno(1))
    elif p[1] == 'std':
        p[0] = ASTNode('StdDev', dataset=p[3], columna=p[5], line=p.lineno(1))
    elif p[1] == 'correlation':
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

def p_expresion(p):
    '''expresion : expresion OR termino_comparacion
                 | termino_comparacion'''
    if len(p) == 4:
        p[0] = ASTNode('OperacionLogica', operador='OR', izq=p[1], der=p[3], line=p.lineno(2))
    else:
        p[0] = p[1]

def p_termino_comparacion(p):
    '''termino_comparacion : termino_comparacion AND termino_logico
                           | termino_logico'''
    if len(p) == 4:
        p[0] = ASTNode('OperacionLogica', operador='AND', izq=p[1], der=p[3], line=p.lineno(2))
    else:
        p[0] = p[1]

def p_termino_logico(p):
    '''termino_logico : NOT factor_logico
                      | factor_logico'''
    if len(p) == 3:
        p[0] = ASTNode('OperacionLogica', operador='NOT', operando=p[2], line=p.lineno(1))
    else:
        p[0] = p[1]

def p_factor_logico(p):
    '''factor_logico : LPAREN expresion RPAREN
                     | termino_relacional
                     | probabilidad_condicional
                     | ID
                     | TRUE
                     | FALSE'''
    if p.slice[1].type == 'LPAREN':
        p[0] = p[2]
    elif p.slice[1].type == 'ID':
        p[0] = ASTNode('Identificador', nombre=p[1], line=p.lineno(1))
    elif p.slice[1].type in ('TRUE', 'FALSE'):
        p[0] = ASTNode('Literal', tipo='bool', valor=(p[1] == 'true'), line=p.lineno(1))
    else:
        p[0] = p[1]

def p_termino_relacional(p):
    '''termino_relacional : termino_aritmetico operador_relacional termino_aritmetico'''
    p[0] = ASTNode('OperacionRelacional',
                   operador=p[2],
                   izq=p[1],
                   der=p[3],
                   line=p[1].line if isinstance(p[1], ASTNode) else 0)

def p_probabilidad_condicional_simple(p):
    '''probabilidad_condicional : PROB LPAREN expresion RPAREN'''
    p[0] = ASTNode('Probabilidad', condicion=p[3], dado=None, line=p.lineno(1))

def p_probabilidad_condicional_given(p):
    '''probabilidad_condicional : PROB LPAREN expresion GIVEN expresion RPAREN'''
    p[0] = ASTNode('Probabilidad', condicion=p[3], dado=p[5], line=p.lineno(1))

def p_operador_relacional(p):
    '''operador_relacional : EQ
                          | NEQ
                          | LEQ
                          | GEQ
                          | LESSTHAN
                          | GREATERTHAN'''
    p[0] = p[1]

def p_termino_aritmetico(p):
    '''termino_aritmetico : termino_aritmetico ADD factor_aritmetico
                          | termino_aritmetico SUB factor_aritmetico
                          | factor_aritmetico'''
    if len(p) == 4:
        op = '+' if p[2] == '+' else '-'
        p[0] = ASTNode('OperacionAritmetica', operador=op, izq=p[1], der=p[3], line=p.lineno(2))
    else:
        p[0] = p[1]

def p_factor_aritmetico(p):
    '''factor_aritmetico : factor_aritmetico MUL unario_aritmetico
                         | factor_aritmetico DIV unario_aritmetico
                         | unario_aritmetico'''
    if len(p) == 4:
        op = '*' if p[2] == '*' else '/'
        p[0] = ASTNode('OperacionAritmetica', operador=op, izq=p[1], der=p[3], line=p.lineno(2))
    else:
        p[0] = p[1]

def p_unario_aritmetico(p):
    '''unario_aritmetico : SUB potencia %prec UMINUS
                         | ADD potencia %prec UPLUS
                         | potencia'''
    if len(p) == 3:
        op = '-' if p[1] == '-' else '+'
        p[0] = ASTNode('OperacionUnaria', operador=op, operando=p[2], line=p.lineno(1))
    else:
        p[0] = p[1]

def p_potencia(p):
    '''potencia : valor_base POW unario_aritmetico
                | valor_base'''
    if len(p) == 4:
        p[0] = ASTNode('OperacionAritmetica', operador='^', izq=p[1], der=p[3], line=p.lineno(2))
    else:
        p[0] = p[1]

def p_valor_base(p):
    '''valor_base : INT
                  | REAL
                  | STRING
                  | TRUE
                  | FALSE
                  | ID
                  | ID DOT ID
                  | LPAREN expresion RPAREN
                  | probabilidad_condicional'''
    if p.slice[1].type in ('INT', 'REAL', 'STRING'):
        tipo = {'INT': 'int', 'REAL': 'real', 'STRING': 'string'}[p.slice[1].type]
        p[0] = ASTNode('Literal', tipo=tipo, valor=p[1], line=p.lineno(1))
    elif p.slice[1].type in ('TRUE', 'FALSE'):
        p[0] = ASTNode('Literal', tipo='bool', valor=(p[1] == 'true'), line=p.lineno(1))
    elif p.slice[1].type == 'ID' and len(p) == 2:
        p[0] = ASTNode('Identificador', nombre=p[1], line=p.lineno(1))
    elif p.slice[1].type == 'ID' and len(p) == 4:
        p[0] = ASTNode('AccesoMiembro', objeto=p[1], miembro=p[3], line=p.lineno(1))
    elif p.slice[1].type == 'LPAREN':
        p[0] = p[2]
    elif p.slice[1].type == 'PROB':
        p[0] = p[1]

def p_empty(p):
    '''empty :'''
    pass

# ==================== MANEJO DE ERRORES ====================

def p_error(p):
    """Maneja errores sintácticos con panic mode recovery.
    
    Esta función registra el error y permite que la gramática continúe
    procesando con la regla 'sentencia : error'.
    """
    if p:
        # Obtener contexto del parser state
        context = _get_parser_context(p)
        
        # Construir mensaje de error descriptivo
        message = _build_error_message(p, context)
        
        error = {
            'type': 'syntax_error',
            'line': p.lineno,
            'column': find_column(p),
            'token': p.type,
            'value': p.value,
            'message': message,
            'context': context
        }
        parser.errors.append(error)
    else:
        # Error al final del archivo
        error = {
            'type': 'syntax_error',
            'line': 'EOF',
            'column': 0,
            'token': 'EOF',
            'value': None,
            'message': "Final inesperado del archivo. Puede que falte cerrar una estructura o completar una declaración.",
            'context': "fin de archivo"
        }
        parser.errors.append(error)

def _get_parser_context(p):
    """Determina el contexto del parser basado en el estado actual."""
    # Mapeo de tipos de tokens a contextos conocidos
    token_context_map = {
        'DATASET': 'declaración de dataset',
        'FACT': 'declaración de hecho',
        'RULE': 'declaración de regla',
        'QUERY': 'consulta',
        'SELECT': 'selección de datos',
        'WHERE': 'condición WHERE',
        'GROUPBY': 'agrupación',
        'DISCOVER': 'descubrimiento de reglas',
        'IF': 'condición IF',
        'GIVEN': 'condición GIVEN',
        'IMPORT': 'importación de datos',
        'FROM': 'cláusula FROM',
    }
    
    # Intentar determinar contexto por el token actual
    token_type = p.type if hasattr(p, 'type') else None
    if token_type in token_context_map:
        return token_context_map[token_type]
    
    # Contexto genérico
    return "expresión"

def _build_error_message(p, context):
    """Construye un mensaje de error descriptivo basado en el token y contexto."""
    token_value = p.value if hasattr(p, 'value') else '?'
    token_type = p.type if hasattr(p, 'type') else '?'
    
    # Mensajes específicos según el tipo de token
    specific_messages = {
        'ID': f"Identificador '{token_value}' inesperado en {context}",
        'NUMBER': f"Número '{token_value}' inesperado en {context}",
        'STRING': f"Cadena '{token_value}' inesperada en {context}",
        'COMMA': f"Coma inesperada en {context}. Puede que falte un operando",
        'LPAREN': f"Paréntesis de apertura inesperado en {context}",
        'RPAREN': f"Paréntesis de cierre inesperado en {context}. Puede que falte el paréntesis de apertura",
        'ASIG': f"Operador de asignación '=' inesperado en {context}",
    }
    
    if token_type in specific_messages:
        return specific_messages[token_type]
    
    # Mensaje genérico pero informativo
    return f"Token inesperado '{token_value}' (tipo: {token_type}) en {context}"

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
    lexer_instance.errors = []
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
            'errors': parser_instance.errors + lexer_instance.errors + [{
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

def format_syntax_errors(errors: List[Dict], source_text: str = "") -> str:
    """Formatea errores sintácticos para mostrar en consola, similar al formato léxico"""
    if not errors:
        return ""
    
    lines = []
    source_lines = source_text.splitlines() if source_text else []
    
    for error in errors:
        line_num = error.get('line')
        col_num = error.get('column', 1)
        token_type = error.get('token', '?')
        token_value = error.get('value', '')
        message = error.get('message', 'Error desconocido')
        
        if line_num == 'EOF':
            lines.append(f"Error sintáctico al final del archivo: {message}")
        else:
            # Formato similar al léxico
            lines.append(f"Error sintáctico en línea {line_num}, columna {col_num}: {message}")
            
            # Mostrar la línea de código si está disponible
            if source_lines and isinstance(line_num, int) and 0 < line_num <= len(source_lines):
                line_text = source_lines[line_num - 1]
                lines.append(f"  {line_text}")
                # Indicador de posición
                if isinstance(col_num, int) and col_num > 0:
                    lines.append(f"  {' ' * (col_num - 1)}^")
            
            # Sugerencia basada en el tipo de error
            if token_value:
                lines.append(f"  Token problemático: '{token_value}' (tipo: {token_type})")
        
        lines.append("")  # Línea en blanco entre errores
    
    return "\n".join(lines)