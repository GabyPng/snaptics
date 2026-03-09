import ply.yacc as yacc
from lexer import tokens, make_lexer
from typing import Dict, Any, List
from symbol_table import SymbolTable

"""
Analizador Sintáctico para snaptics
Análisis de datos probabilístico con razonamiento lógico
Implementa panic mode recovery con códigos de error específicos
"""

# ==================== CÓDIGOS Y CATEGORÍAS DE ERRORES SINTÁCTICOS ====================

class SyntaxErrorCode:
    """Códigos de error sintáctico del compilador snaptics"""
    
    # Errores de declaraciones (SYN-100 series)
    INCOMPLETE_DATASET = ("SYN-101", "Declaración de dataset incompleta")
    INCOMPLETE_FACT = ("SYN-102", "Declaración de hecho incompleta")
    INCOMPLETE_RULE = ("SYN-103", "Declaración de regla incompleta")
    INCOMPLETE_QUERY = ("SYN-104", "Declaración de consulta incompleta")
    MISSING_ASSIGNMENT = ("SYN-105", "Falta operador de asignación")
    
    # Errores de expresiones (SYN-200 series)
    MISSING_OPERAND = ("SYN-201", "Falta operando en expresión")
    INVALID_EXPRESSION = ("SYN-202", "Expresión inválida")
    UNEXPECTED_TOKEN = ("SYN-204", "Token inesperado en expresión")
    
    # Errores de paréntesis y delimitadores (SYN-300 series)
    MISSING_RPAREN = ("SYN-302", "Falta paréntesis de cierre")
    UNMATCHED_PAREN = ("SYN-303", "Paréntesis sin correspondencia")
    UNEXPECTED_COMMA = ("SYN-305", "Coma inesperada")
    
    # Errores de cláusulas (SYN-400 series)
    MISSING_FROM = ("SYN-401", "Falta cláusula FROM")
    MISSING_WHERE = ("SYN-402", "Condición WHERE incompleta")
    MISSING_GIVEN = ("SYN-404", "Falta cláusula GIVEN en probabilidad condicional")
    
    # Errores de identificadores (SYN-500 series)
    MISSING_IDENTIFIER = ("SYN-501", "Falta identificador")
    INVALID_IDENTIFIER = ("SYN-502", "Identificador inválido")
    
    # Errores de valores y literales (SYN-600 series)
    INVALID_NUMBER = ("SYN-602", "Número inválido")
    INVALID_STRING = ("SYN-603", "Cadena inválida")
    
    # Errores de probabilidad (SYN-800 series)
    INVALID_PROBABILITY = ("SYN-801", "Expresión de probabilidad inválida")
    
    # Errores de estructura (SYN-900 series)
    UNEXPECTED_EOF = ("SYN-901", "Final inesperado del archivo")

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
        # Filtrar None (errores recuperados)
        if p[1] is not None:
            p[0] = ASTNode('Programa', sentencias=[p[1]], line=p.lineno(1) if p[1] else 0)
        else:
            p[0] = ASTNode('Programa', sentencias=[], line=0)
    else:
        if p[1]:
            # Filtrar None (errores recuperados)
            if p[2] is not None:
                p[1].properties['sentencias'].append(p[2])
            p[0] = p[1]
        else:
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
    # Si es un error recuperado por panic mode, retornar None
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
    # Registrar símbolo
    p.parser.symbol_table.add(p[2], None, None, p.lineno(2))

def p_preprocesamiento_completo(p):
    '''preprocesamiento : DATASET ID ASIG SELECT lista_cols_tipadas FROM ID condicion_opt agrupacion_opt descubrimiento_opt'''
    p[0] = ASTNode('Preprocesamiento',
                   dataset_id=p[2],
                   columnas=p[5],
                   source=p[7],
                   condicion=p[8],
                   agrupacion=p[9],
                   descubrimiento=p[10],
                   line=p.lineno(1))
    # Registrar símbolo del dataset
    p.parser.symbol_table.add(p[2], 'dataset', 'dataset', p.lineno(2))
    # Registrar cada columna con su tipo
    for col_name, col_type in p[5]:
        # columnas se asocian al dataset actual p[2]
        p.parser.symbol_table.add(col_name, 'column', col_type, p.lineno(2), dataset=p[2])

def p_lista_ids(p):
    '''lista_ids : ID
                 | ID COMMA lista_ids'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_lista_cols_tipadas(p):
    '''lista_cols_tipadas : col_tipada
                          | col_tipada COMMA lista_cols_tipadas'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_col_tipada(p):
    '''col_tipada : ID COLON tipo
                  | ID'''
    if len(p) == 4:
        p[0] = (p[1], p[3])
    else:
        p[0] = (p[1], None)

def p_tipo(p):
    '''tipo : TYPE_INT
            | TYPE_REAL
            | TYPE_STRING
            | TYPE_BOOL'''
    p[0] = p[1]

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
    '''declaracion_hecho : FACT ID ASIG probabilidad_condicional
                         | declaracion_metrica'''
    if len(p) > 2:
        p[0] = ASTNode('DeclaracionHecho',
                       fact_id=p[2],
                       probabilidad=p[4],
                       line=p.lineno(1))
        # Registrar símbolo
        p.parser.symbol_table.add(p[2], None, None, p.lineno(2))
    else:
        p[0] = p[1]

def p_declaracion_metrica(p):
    '''declaracion_metrica : ID ASIG metrica_estatica'''
    p[0] = ASTNode('DeclaracionMetrica',
                   var_id=p[1],
                   metrica=p[3],
                   line=p.lineno(1))
    # Registrar símbolo
    p.parser.symbol_table.add(p[1], None, None, p.lineno(1))

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
    # Registrar símbolo
    p.parser.symbol_table.add(p[2], None, None, p.lineno(2))

def p_consulta(p):
    '''consulta : QUERY ID explicacion_opt'''
    p[0] = ASTNode('Consulta',
                   query_id=p[2],
                   explicacion=p[3],
                   line=p.lineno(1))
    # Registrar símbolo (opcional, como referencia)
    p.parser.symbol_table.add(p[2], None, None, p.lineno(2))

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

# ==================== MANEJO DE ERRORES CON PANIC MODE ====================

def p_error(p):
    """
    Maneja errores sintácticos con panic mode recovery y códigos específicos.
    
    Estrategia de Panic Mode:
    1. Registra el error con código SYN-XXX específico
    2. Descarta tokens hasta encontrar un punto de sincronización
    3. Permite que la regla 'sentencia : error' recupere el análisis
    4. Continúa parseando el resto del código
    """
    if p:
        # Obtener contexto del parser
        context = _get_parser_context(p)
        
        # Determinar código de error basado en el contexto
        error_code, error_category = _determine_error_code(p, context)
        
        # Construir mensaje de error descriptivo
        message = _build_error_message(p, context)
        
        # Registrar el error
        error = {
            'type': 'syntax_error',
            'code': error_code,
            'category': error_category,
            'line': p.lineno,
            'column': find_column(p),
            'token': p.type,
            'value': p.value,
            'message': message,
            'context': context
        }
        parser.errors.append(error)
        
        # ===== PANIC MODE RECOVERY =====
        # Tokens de sincronización: inicio de nuevas declaraciones
        sync_tokens = {'DATASET', 'FACT', 'RULE', 'QUERY'}
        
        # Buscar punto de sincronización descartando tokens
        while True:
            tok = parser.token()
            if not tok:
                # Llegamos al final del archivo sin encontrar sincronización
                break
            
            if tok.type in sync_tokens:
                # Devolver el token al buffer para que PLY lo procese
                # como nueva sentencia tras la recuperación natural del stack
                parser._token_buffer.append(tok)
                return None  # Sin errok(): PLY usa sentencia:error y luego el buffer

        # Si llegamos aquí, alcanzamos EOF
        # El parser continuará con la regla 'sentencia : error'
        
    else:
        # Error al final del archivo
        code, category = SyntaxErrorCode.UNEXPECTED_EOF
        error = {
            'type': 'syntax_error',
            'code': code,
            'category': category,
            'line': 'EOF',
            'column': 0,
            'token': 'EOF',
            'value': None,
            'message': "Final inesperado del archivo. Puede que falte cerrar una estructura o completar una declaración.",
            'context': "fin de archivo"
        }
        parser.errors.append(error)

def _determine_error_code(p, context):
    """Determina el código de error apropiado basado en el token y contexto."""
    token_type = p.type if hasattr(p, 'type') else None
    token_value = p.value if hasattr(p, 'value') else None
    
    # Mapeo de contextos y tokens a códigos de error SYN-XXX
    
    # Errores de paréntesis (SYN-300 series)
    if token_type == 'RPAREN':
        return SyntaxErrorCode.UNMATCHED_PAREN
    elif token_type == 'LPAREN':
        return SyntaxErrorCode.MISSING_RPAREN
    
    # Errores en declaraciones de dataset (SYN-100 series)
    if 'dataset' in context.lower():
        if token_type == 'ASIG':
            return SyntaxErrorCode.MISSING_IDENTIFIER
        elif token_type in ('IMPORT', 'SELECT'):
            return SyntaxErrorCode.MISSING_ASSIGNMENT
        return SyntaxErrorCode.INCOMPLETE_DATASET
    
    # Errores en declaraciones de hechos
    if 'hecho' in context.lower() or 'fact' in context.lower():
        if token_type == 'ASIG':
            return SyntaxErrorCode.MISSING_IDENTIFIER
        return SyntaxErrorCode.INCOMPLETE_FACT
    
    # Errores en declaraciones de reglas
    if 'regla' in context.lower() or 'rule' in context.lower():
        if token_type == 'COND':
            return SyntaxErrorCode.MISSING_IDENTIFIER
        return SyntaxErrorCode.INCOMPLETE_RULE
    
    # Errores en consultas
    if 'consulta' in context.lower() or 'query' in context.lower():
        return SyntaxErrorCode.INCOMPLETE_QUERY
    
    # Errores en expresiones (SYN-200 series)
    if 'expresión' in context.lower():
        if token_type in ('ADD', 'SUB', 'MUL', 'DIV', 'POW'):
            return SyntaxErrorCode.MISSING_OPERAND
        elif token_type in ('EQ', 'NEQ', 'LESSTHAN', 'GREATERTHAN', 'LEQ', 'GEQ'):
            return SyntaxErrorCode.MISSING_OPERAND
        elif token_type == 'COMMA':
            return SyntaxErrorCode.UNEXPECTED_COMMA
        return SyntaxErrorCode.INVALID_EXPRESSION
    
    # Errores de comas (SYN-300 series)
    if token_type == 'COMMA':
        return SyntaxErrorCode.UNEXPECTED_COMMA
    
    # Errores de cláusulas (SYN-400 series)
    if context == 'cláusula FROM' or token_type == 'FROM':
        return SyntaxErrorCode.MISSING_FROM
    
    if context == 'condición WHERE' or token_type == 'WHERE':
        return SyntaxErrorCode.MISSING_WHERE
    
    if token_type == 'GIVEN':
        return SyntaxErrorCode.MISSING_GIVEN
    
    # Errores de probabilidad (SYN-800 series)
    if 'prob' in context.lower() or token_type == 'PROB':
        return SyntaxErrorCode.INVALID_PROBABILITY
    
    # Errores de identificadores (SYN-500 series)
    if token_type == 'ID':
        return SyntaxErrorCode.INVALID_IDENTIFIER
    
    # Errores de valores (SYN-600 series)
    if token_type in ('INT', 'REAL'):
        return SyntaxErrorCode.INVALID_NUMBER
    elif token_type == 'STRING':
        return SyntaxErrorCode.INVALID_STRING
    
    # Error genérico si no se puede determinar
    return SyntaxErrorCode.UNEXPECTED_TOKEN

def _get_parser_context(p):
    """Determina el contexto del parser basado en el estado actual."""
    token_context_map = {
        'DATASET': 'declaración de dataset',
        'FACT': 'declaración de hecho',
        'RULE': 'declaración de regla',
        'QUERY': 'consulta',
        'SELECT': 'selección de datos',
        'WHERE': 'condición WHERE',
        'GROUP': 'agrupación',
        'AUTO_DISCOVER': 'descubrimiento de reglas',
        'IF': 'condición IF',
        'GIVEN': 'condición GIVEN',
        'IMPORT': 'importación de datos',
        'FROM': 'cláusula FROM',
        'PROB': 'probabilidad',
        'MEAN': 'métrica estadística',
        'VAR': 'métrica estadística',
        'STD': 'métrica estadística',
        'CORRELATION': 'métrica estadística',
        'COND': 'definición de regla',
    }
    
    token_type = p.type if hasattr(p, 'type') else None
    if token_type in token_context_map:
        return token_context_map[token_type]
    
    return "expresión"

def _build_error_message(p, context):
    """Construye un mensaje de error descriptivo basado en el token y contexto."""
    token_value = p.value if hasattr(p, 'value') else '?'
    token_type = p.type if hasattr(p, 'type') else '?'
    
    # Mensajes específicos según el tipo de token
    specific_messages = {
        'ID': f"Identificador '{token_value}' inesperado en {context}",
        'INT': f"Número '{token_value}' inesperado en {context}",
        'REAL': f"Número '{token_value}' inesperado en {context}",
        'STRING': f"Cadena '{token_value}' inesperada en {context}",
        'COMMA': f"Coma inesperada en {context}. Puede que falte un operando",
        'LPAREN': f"Paréntesis de apertura inesperado en {context}",
        'RPAREN': f"Paréntesis de cierre inesperado en {context}. Puede que falte el paréntesis de apertura",
        'ASIG': f"Operador de asignación '=' inesperado en {context}",
        'ADD': f"Operador '+' inesperado. Puede que falte un operando",
        'SUB': f"Operador '-' inesperado. Puede que falte un operando",
        'MUL': f"Operador '*' inesperado. Puede que falte un operando",
        'DIV': f"Operador '/' inesperado. Puede que falte un operando",
        'POW': f"Operador '^' inesperado. Puede que falte un operando",
        'EQ': f"Operador '==' inesperado. Puede que falte un operando",
        'NEQ': f"Operador '!=' inesperado. Puede que falte un operando",
        'LESSTHAN': f"Operador '<' inesperado. Puede que falte un operando",
        'GREATERTHAN': f"Operador '>' inesperado. Puede que falte un operando",
        'LEQ': f"Operador '<=' inesperado. Puede que falte un operando",
        'GEQ': f"Operador '>=' inesperado. Puede que falte un operando",
        'AND': f"Operando inválido para 'and'. Se esperaba una comparación (ej: asistencia < 60), un identificador, P(...) o 'true'/'false'",
        'OR': f"Operando inválido para 'or'. Se esperaba una comparación (ej: asistencia < 60), un identificador, P(...) o 'true'/'false'",
        'NOT': f"Operador 'not' inesperado",
        'FROM': f"Palabra clave 'from' inesperada. Verifique la sintaxis de importación o selección",
        'WHERE': f"Palabra clave 'where' inesperada. Verifique la condición",
        'GIVEN': f"Palabra clave 'given' inesperada. Verifique la sintaxis de probabilidad condicional",
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
    parser.symbol_table = SymbolTable()
    return parser

# ==================== FUNCIÓN DE PARSING ====================

def parse(text: str, debug=False) -> Dict[str, Any]:
    """
    Parsea el texto y devuelve el AST y errores.
    
    Args:
        text: Código fuente a parsear
        debug: Si True, muestra información de depuración
    
    Returns:
        Dict con:
        - 'ast': Árbol de sintaxis abstracta (None si hay errores)
        - 'errors': Lista de errores sintácticos con códigos SYN-XXX
        - 'success': Boolean indicando éxito
    """
    lexer_instance = make_lexer()
    lexer_instance.errors = []
    parser_instance = make_parser()
    parser_instance.errors = []

    # Buffer para que p_error pueda "devolver" tokens al stream
    token_buffer = []
    parser_instance._token_buffer = token_buffer

    def _buffered_token():
        if token_buffer:
            return token_buffer.pop(0)
        return lexer_instance.token()

    try:
        ast = parser_instance.parse(text, lexer=lexer_instance, tokenfunc=_buffered_token, debug=debug)
        
        # Combinar errores del lexer y parser
        all_errors = lexer_instance.errors + parser_instance.errors
        
        # IMPORTANTE: Solo retornar AST si NO hay errores
        # Si hay errores, retornar None aunque se haya generado un AST parcial
        final_ast = ast if len(all_errors) == 0 else None
        final_symbol_table = parser_instance.symbol_table if len(all_errors) == 0 else None
        
        return {
            'ast': final_ast,
            'errors': all_errors,
            'symbol_table': final_symbol_table,
            'success': len(all_errors) == 0 and ast is not None
        }
    except Exception as e:
        return {
            'ast': None,
            'errors': parser_instance.errors + lexer_instance.errors + [{
                'type': 'critical_error',
                'code': 'SYN-999',
                'category': 'Error crítico',
                'message': f"Error crítico durante el análisis sintáctico: {str(e)}"
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
    """
    Formatea errores sintácticos para mostrar en consola con códigos SYN-XXX.
    
    Args:
        errors: Lista de diccionarios con información de errores
        source_text: Código fuente original (para mostrar contexto)
    
    Returns:
        String formateado con los errores, códigos y contexto
    """
    if not errors:
        return ""
    
    lines = []
    source_lines = source_text.splitlines() if source_text else []
    
    for i, error in enumerate(errors, 1):
        code = error.get('code', 'SYN-???')
        category = error.get('category', 'Error sintáctico')
        line_num = error.get('line')
        col_num = error.get('column', 1)
        message = error.get('message', 'Error desconocido')
        context = error.get('context', '')
        
        # Encabezado del error con código
        lines.append(f"[Error {i}] [{code}] {category}")
        
        if line_num == 'EOF':
            lines.append(f"  Final del archivo: {message}")
        else:
            lines.append(f"  Línea {line_num}, Columna {col_num}: {message}")
            
            # Mostrar la línea de código si está disponible
            if source_lines and isinstance(line_num, int) and 0 < line_num <= len(source_lines):
                line_text = source_lines[line_num - 1]
                lines.append(f"  {line_text}")
                # Indicador de posición
                if isinstance(col_num, int) and col_num > 0:
                    lines.append(f"  {' ' * (col_num - 1)}^")
        
            # Información adicional
            if context:
                lines.append(f"  Contexto: {context}")
        
        lines.append("")  # Línea en blanco entre errores
    
    return "\n".join(lines)
