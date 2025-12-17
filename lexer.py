import ply.lex as lex
from typing import List, Dict, Any
import contextlib
import io
import sys
import re
import difflib

"""
    Como construír nuestro léxico:
        Se tiene que escribir un conjunto de cada nombre de los tokens,
        Por cada token escrito en el conjunto, se representa con una expresión regular,
        compatible con re module de python.
        Cada de una de estas reglas están definidas por declaraciones con el prefijo t_ para
        indicar que define un token 
        Las palabras reservadas deben escribirse 
   TODO:
   QSyntaxHighlighter Para resaltar Tokens o errores     
"""

# ============================================================================
# CÓDIGOS Y CATEGORÍAS DE ERRORES LÉXICOS
# ============================================================================

class LexicalErrorCode:
    """Códigos de error léxico del compilador snaptics"""
    
    # Errores de caracteres especiales (LEX-100)
    SPANISH_PUNCTUATION = ("LEX-101", "Signo de puntuación español no permitido")
    AT_SYMBOL = ("LEX-102", "Símbolo '@' no válido")
    DOLLAR_SYMBOL = ("LEX-103", "Símbolo '$' no permitido")
    PERCENT_SYMBOL = ("LEX-104", "Símbolo '%' no válido")
    
    # Errores de delimitadores (LEX-200)
    SQUARE_BRACKETS = ("LEX-201", "Corchetes no soportados")
    CURLY_BRACES = ("LEX-202", "Llaves no soportadas")
    
    # Errores de operadores (LEX-300)
    PIPE_OPERATOR = ("LEX-301", "Operador '|' no válido")
    AMPERSAND_OPERATOR = ("LEX-303", "Operador '&' no válido")
    INCOMPLETE_NOT = ("LEX-305", "Operador '!' incompleto")
    
    # Errores de sintaxis (LEX-400)
    SEMICOLON = ("LEX-401", "Punto y coma innecesario")
    BACKSLASH = ("LEX-402", "Barra invertida fuera de contexto")
    
    # Errores de caracteres (LEX-500)
    ACCENTED_CHAR = ("LEX-501", "Carácter acentuado no válido")
    UNICODE_CHAR = ("LEX-502", "Carácter Unicode no permitido")
    BACKTICK_TILDE = ("LEX-503", "Carácter no válido")
    
    # Errores de cadenas y comentarios (LEX-600)
    UNCLOSED_STRING = ("LEX-601", "Cadena sin cerrar")
    STRING_ERROR = ("LEX-602", "Error en cadena de texto")
    UNCLOSED_BLOCK_COMMENT = ("LEX-603", "Comentario de bloque sin cerrar")
    BLOCK_COMMENT_ERROR = ("LEX-604", "Error en comentario de bloque")
    
    # Errores de números (LEX-650) - NUEVA CATEGORÍA
    MALFORMED_NUMBER = ("LEX-651", "Número malformado")
    MULTIPLE_DECIMALS = ("LEX-652", "Número con múltiples puntos decimales")
    
    # Errores de palabras reservadas (LEX-700)
    RESERVED_TYPO = ("LEX-701", "Error de escritura en palabra reservada")
    
    # Error genérico (LEX-999)
    ILLEGAL_CHAR = ("LEX-999", "Carácter ilegal")


reserved = {
    # Estructura de datos y análisis
    'dataset': 'DATASET',
    'import': 'IMPORT',
    'from': 'FROM',
    'select': 'SELECT',
    'where': 'WHERE',
    'group': 'GROUP',
    'filter': 'FILTER',
    'auto_discover': 'AUTO_DISCOVER',

    # Lógica y conocimiento
    'fact': 'FACT',
    'rule': 'RULE',
    'query': 'QUERY',
    'evidence': 'EVIDENCE',
    'confidence': 'CONFIDENCE',

    # Probabilidad y estadística
    'P': 'PROB',
    'distribution': 'DISTRIBUTION',
    'mean': 'MEAN',
    'var': 'VAR',
    'std': 'STD',
    'correlation': 'CORRELATION',

    # Explicabilidad
    'explain': 'EXPLAIN',
    'why': 'WHY',

    # Conectores y lógica
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    'if': 'IF',
    'then': 'THEN',
    'else': 'ELSE',
    'given': 'GIVEN',

    # Booleanos
    'true': 'TRUE',
    'false': 'FALSE',
}

tokens = [
    'ID',
    
    'LPAREN',
    'RPAREN',
    
    'ADD',
    'SUB',
    'MUL',
    'DIV',
    'POW',
    
    'EQ',
    'NEQ',
    'LESSTHAN',
    'GREATERTHAN',
    'LEQ',
    'GEQ',
    
    'ASIG', # =
    'COND', # :-
    'RANGE', # ..
    'COMMA', # ,
    'DOT', # .
    
    'INT',
    'REAL',
    'STRING'
    
] + list(reserved.values())

t_ignore = ' \t'

def t_COMMENT(t):
    r'\#.*'
    pass
    # No return value. Token discarded

def t_COMENTARIO_BLOQUE(t):
    r'/\*([^*]|\*+[^*/])*\*/'
    t.lexer.lineno += t.value.count('\n')
    pass

t_LPAREN = r'\('
t_RPAREN = r'\)'
t_ADD = r'\+'
t_SUB = r'-'
t_MUL = r'\*'
t_DIV = r'/'
t_POW = r'\^'
t_EQ = r'=='
t_NEQ = r'!='
t_LEQ = r'<='
t_GEQ = r'>='
t_LESSTHAN = r'<'
t_GREATERTHAN = r'>'
t_ASIG = r'='

# Operador de implicación/condición
t_COND = r':-'
t_RANGE = r'\.\.'
t_COMMA = r','
t_DOT = r'\.'

# IMPORTANTE: Esta función DEBE ir ANTES de t_REAL y t_INT
# para que detect_malformed_number tenga prioridad
def t_MALFORMED_NUMBER(t):
    r'\d+(\.\d+){2,}'
    """Detecta números con múltiples puntos decimales como 0.60.0"""
    code, category = LexicalErrorCode.MULTIPLE_DECIMALS
    line = t.lineno
    column = find_column(t.lexer.lexdata, t)
    line_text = t.lexer.lexdata.splitlines()[line - 1] if line - 1 < len(t.lexer.lexdata.splitlines()) else ""
    
    error = {
        'type': 'lexical',
        'code': code,
        'category': category,
        'line': line,
        'column': column,
        'line_text': line_text,
        'message': f"Número con múltiples puntos decimales: '{t.value}'. Los números decimales solo pueden tener un punto."
    }
    t.lexer.errors.append(error)
    # No retornar token, solo registrar error y continuar
    return None

def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9.]*'
    if t.value in reserved:
        t.type = reserved[t.value]
    else:
        reserved_words = list(reserved.keys())
        # Ajustar cutoff basado en longitud de la palabra
        cutoff = 0.85 if len(t.value) > 3 else 0.75
        suggestions = difflib.get_close_matches(t.value.lower(), reserved_words, n=1, cutoff=cutoff)
        if suggestions:
            code, category = LexicalErrorCode.RESERVED_TYPO
            error = {
                'type': 'lexical',
                'code': code,
                'category': category,
                'line': t.lineno,
                'column': find_column(t.lexer.lexdata, t),
                'line_text': t.lexer.lexdata.splitlines()[t.lineno - 1] if t.lineno - 1 < len(t.lexer.lexdata.splitlines()) else "",
                'message': f"Posible error de escritura en palabra reservada: '{t.value}'. ¿Quizás quisiste decir '{suggestions[0]}'?"
            }
            t.lexer.errors.append(error)
    return t

def t_REAL(t):
    r'\d+\.\d+([eE][-+]?\d+)?'
    try:
        t.value = float(t.value)
        return t
    except ValueError:
        code, category = LexicalErrorCode.MALFORMED_NUMBER
        line = t.lineno
        column = find_column(t.lexer.lexdata, t)
        line_text = t.lexer.lexdata.splitlines()[line - 1] if line - 1 < len(t.lexer.lexdata.splitlines()) else ""
        
        error = {
            'type': 'lexical',
            'code': code,
            'category': category,
            'line': line,
            'column': column,
            'line_text': line_text,
            'message': f"Número real malformado: '{t.value}'"
        }
        t.lexer.errors.append(error)
        return None

def t_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_STRING(t):
    r'\"([^\\"]|\\.)*\"'
    t.value = t.value[1:-1]  # remove quotes
    return t


# Cuenta las líneas para trackearlas
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Compute column.
#     input is the input text string
#     token is a token instance
def find_column(input, token):
    line_start = input.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1

def categorize_char_error(char, line_text, column):
    """
    Categoriza el tipo de error léxico según el carácter.
    
    Args:
        char: El carácter ilegal
        line_text: Texto de la línea completa
        column: Posición de la columna
    
    Returns:
        Tupla (code, category, message) con el código, categoría y mensaje de error
    """
    # Signos de puntuación español
    if char in '¿¡':
        code, category = LexicalErrorCode.SPANISH_PUNCTUATION
        return (code, category, f"Signo de puntuación español no permitido '{char}'")
    
    # Símbolos especiales comunes
    elif char == '@':
        code, category = LexicalErrorCode.AT_SYMBOL
        return (code, category, f"Símbolo '@' no válido (solo permitido dentro de cadenas)")
    
    elif char == '$':
        code, category = LexicalErrorCode.DOLLAR_SYMBOL
        return (code, category, f"Símbolo '$' no permitido (use el nombre de la moneda o cadenas)")
    
    elif char == '%':
        code, category = LexicalErrorCode.PERCENT_SYMBOL
        return (code, category, f"Símbolo '%' no es un operador válido")
    
    # Delimitadores no soportados
    elif char in '[]':
        code, category = LexicalErrorCode.SQUARE_BRACKETS
        return (code, category, f"Corchetes '{char}' no están soportados (use paréntesis)")
    
    elif char in '{}':
        code, category = LexicalErrorCode.CURLY_BRACES
        return (code, category, f"Llaves '{char}' no están soportadas (use paréntesis para agrupar)")
    
    # Operadores lógicos incorrectos
    elif char == '|':
        code, category = LexicalErrorCode.PIPE_OPERATOR
        return (code, category, f"Operador '|' no válido (use 'or' para operaciones lógicas)")
    
    elif char == '&':
        code, category = LexicalErrorCode.AMPERSAND_OPERATOR
        return (code, category, f"Operador '&' no válido (use 'and' para operaciones lógicas)")
    
    # Punto y coma innecesario
    elif char == ';':
        code, category = LexicalErrorCode.SEMICOLON
        return (code, category, f"Punto y coma ';' no es necesario (no se requieren terminadores de línea)")
    
    # Barra invertida fuera de cadena
    elif char == '\\':
        code, category = LexicalErrorCode.BACKSLASH
        return (code, category, f"Barra invertida '\\' solo válida dentro de cadenas")
    
    # Caracteres con acento
    elif char in 'áéíóúÁÉÍÓÚñÑ':
        base = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u',
                'Á':'A', 'É':'E', 'Í':'I', 'Ó':'O', 'Ú':'U',
                'ñ':'n', 'Ñ':'N'}
        replacement = base.get(char, char)
        code, category = LexicalErrorCode.ACCENTED_CHAR
        return (code, category, f"Carácter acentuado '{char}' no válido (use '{replacement}' sin acento)")
    
    # Otros caracteres Unicode
    elif ord(char) > 127:
        code, category = LexicalErrorCode.UNICODE_CHAR
        return (code, category, f"Carácter Unicode '{char}' no permitido (código: {ord(char)})")
    
    # Backticks y tildes
    elif char in '`~':
        code, category = LexicalErrorCode.BACKTICK_TILDE
        return (code, category, f"Carácter '{char}' no es válido en este lenguaje")
    
    # Carácter por defecto
    else:
        code, category = LexicalErrorCode.ILLEGAL_CHAR
        return (code, category, f"Carácter ilegal '{char}'")

def detect_malformed_number(t):
    """
    Detecta números malformados como 0.60.0 (múltiples puntos decimales).
    
    Returns:
        True si se detectó y manejó un error, False en caso contrario
    """
    # Buscar patrones de números con múltiples puntos
    # Ejemplo: 0.60.0, 3.14.159, etc.
    import re
    
    line = t.lineno
    column = find_column(t.lexer.lexdata, t)
    lines = t.lexer.lexdata.splitlines()
    line_text = lines[line - 1] if line - 1 < len(lines) else ""
    
    # Obtener el resto de la línea desde la posición actual
    pos_in_line = column - 1
    rest_of_line = line_text[pos_in_line:]
    
    # Regex para detectar número con múltiples puntos decimales
    # Captura patrones como: 0.60.0, 123.45.67, etc.
    malformed_pattern = r'^(\d+\.\d+)(\.\d+)+'
    match = re.match(malformed_pattern, rest_of_line)
    
    if match:
        malformed_number = match.group(0)
        code, category = LexicalErrorCode.MULTIPLE_DECIMALS
        
        error = {
            'type': 'lexical',
            'code': code,
            'category': category,
            'line': line,
            'column': column,
            'line_text': line_text,
            'message': f"Número con múltiples puntos decimales: '{malformed_number}'. Los números decimales solo pueden tener un punto."
        }
        t.lexer.errors.append(error)
        
        # Saltar todo el número malformado
        t.lexer.skip(len(malformed_number))
        return True
    
    return False

def t_error(t):
    """Maneja errores léxicos con categorización detallada y códigos."""
    
    # PRIMERO: Verificar si es un número malformado
    if t.value[0].isdigit():
        if detect_malformed_number(t):
            return  # Ya se manejó el error
    
    line = t.lexer.lineno
    column = find_column(t.lexer.lexdata, t)
    lines = t.lexer.lexdata.splitlines()
    line_text = lines[line - 1] if line - 1 < len(lines) else ""
    
    char = t.value[0]
    code = None
    category = None
    message = None
    
    # Caso especial 1: Cadena no cerrada
    if char == '"':
        rest_of_line = line_text[column - 1:]
        # Si solo hay una comilla en lo que resta de línea, probablemente no está cerrada
        if rest_of_line.count('"') == 1:
            code, category = LexicalErrorCode.UNCLOSED_STRING
            message = "Cadena no cerrada (falta comilla de cierre)"
        else:
            code, category = LexicalErrorCode.STRING_ERROR
            message = "Error en cadena de texto (verifique las comillas)"
    
    # Caso especial 2: Comentario de bloque no cerrado
    elif t.value.startswith('/*'):
        rest_of_text = t.lexer.lexdata[t.lexpos:]
        if '*/' not in rest_of_text:
            code, category = LexicalErrorCode.UNCLOSED_BLOCK_COMMENT
            message = "Comentario de bloque sin cierre (falta */)"
        else:
            code, category = LexicalErrorCode.BLOCK_COMMENT_ERROR
            message = "Error en comentario de bloque"
    
    # Caso especial 3: Operador '!' incompleto
    elif char == '!' and column < len(line_text):
        next_char = line_text[column] if column < len(line_text) else ''
        if next_char != '=':
            code, category = LexicalErrorCode.INCOMPLETE_NOT
            message = "Operador '!' incompleto (use '!=' para desigualdad o 'not' para negación)"
    
    # Categorización por carácter
    if not message:
        code, category, message = categorize_char_error(char, line_text, column)
    
    # Sugerir palabra reservada similar
    reserved_words = list(reserved.keys())
    suggestions = difflib.get_close_matches(t.value.lower(), reserved_words, n=1, cutoff=0.8)
    if suggestions:
        suggestion = suggestions[0]
        message += f" ¿Quizás quisiste decir '{suggestion}'?"
    
    error = {
        'type': 'lexical',
        'code': code,
        'category': category,
        'line': line,
        'column': column,
        'line_text': line_text,
        'message': message
    }
    t.lexer.errors.append(error)
    t.lexer.skip(1)

def make_lexer():
    """Construye y devuelve una instancia de lexer PLY para este módulo."""
    return lex.lex(
        module=sys.modules[__name__],
        optimize=False,
        debug=False
    )

def tokenize(text: str) -> Dict[str, Any]:
    """
    Tokeniza el texto y retorna tokens y errores.
    
    Returns:
        Dict con 'tokens', 'errors' y 'output'
    """
    lexer = make_lexer()
    lexer.errors = []
    lexer.input(text)

    tokens = []

    while True:
        tok = lexer.token()
        if not tok:
            break

        start = tok.lexpos
        end = lexer.lexpos
        lexeme = text[start:end]

        tokens.append({
            'type': tok.type,
            'value': tok.value,
            'line': tok.lineno,
            'column': find_column(text, tok),
            'lexpos': tok.lexpos,
            'lexeme': lexeme,
            'length': len(lexeme)
        })

    return {
        'tokens': tokens,
        'errors': lexer.errors,
        'output': ""  
    }

def print_errors(errors: List[Dict[str, Any]]):
    """
    Imprime los errores de manera formateada con código, línea, columna, texto y flecha.
    """
    for error in errors:
        code = error.get('code', 'LEX-???')
        category = error.get('category', 'Error léxico')
        print(f"[{code}] {category}")
        print(f"  Línea {error['line']}, Columna {error['column']}: {error['message']}")
        print(f"  {error['line_text']}")
        print(f"  {' ' * (error['column'] - 1)}^")

def format_errors(errors: List[Dict[str, Any]]) -> str:
    """Devuelve una cadena formateada con los errores para la interfaz del compilador"""
    if not errors:
        return ""
    lines = []
    for error in errors:
        code = error.get('code', 'LEX-???')
        category = error.get('category', 'Error léxico')
        lines.append(f"[{code}] {category}")
        lines.append(f"  Línea {error['line']}, Columna {error['column']}: {error['message']}")
        lines.append(f"  {error['line_text']}")
        lines.append(f"  {' ' * (error['column'] - 1)}^")
        lines.append("")
    return "\n".join(lines)

if __name__ == '__main__':
    # Ejemplo de uso
#     code = """    import dataset ventas from "ventas.csv"
#     fact ventas_altas = P(ventas > 500) = 0.72
#     rule baja_rentabilidad :- ventas_altas < 0.5 and margen_bajo > 0.3
#     query rentabilidad_general ¿ ?$%mis_datoa
# """
#     result = tokenize(code)
#     print("Tokens:")
#     for token in result['tokens']:
#         print(token)
#     print("\nErrores:")
#     print_errors(result['errors'])
#     print("\nMensajes:")
#     print(result['output'])
    #Ejemplo de errores
    # code = """
    # # Prueba de análisis léxico
    # fact ventas_altas = P(ventas > 500) = 0.72

    # # Errores de caracteres especiales
    # rule análisis@ :- precio$ < 100 and margen% > 0.3

    # # Operadores incorrectos
    # resultado = verdadero & falso | otro

    # # Símbolos españoles
    # pregunta¿ = true
    # valor¡ = 123

    # # Cadena no cerrada
    # nombre = "esto no cierra

    # # Caracteres raros
    # variable` = 10
    # otro~ = 20
    # """
    # result = tokenize(code)
    # print("Tokens:")
    # for token in result['tokens']:
    #     print(token)
    # print("\nErrores:")
    # print_errors(result['errors'])
    # print("\nMensajes:")
    # print(result['output'])

    pass