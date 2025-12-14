import ply.lex as lex
from typing import List, Dict, Any
import contextlib
import io
import sys
import re

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
    'COND', # :=
    'RANGE', # ..
    'COMMA', # ,
    'DOT', # .
    
    'INT',
    'REAL',
    'STRING'
    
] + list(reserved.values())

t_ignore  = ' \t'

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

def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9.]*'
    t.type = reserved.get(t.value,'ID')    # Check for reserved words
    return t

def t_REAL(t):
    r'\d+\.\d+([eE][-+]?\d+)?'
    t.value = float(t.value)
    return t

def t_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_STRING(t):
    r'\"([^\\"]|\\.)*\"'
    t.value = t.value[1:-1]  # remove quotes
    return t


# def t_BOOL(t):
#     r'(true|false)'
#     t.value = True if t.value == 'true' else False
#     return t

# Cuenta las líenas para trackearlas
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
        String con el mensaje de error categorizado
    """
    # Signos de puntuación español
    if char in '¿¡':
        return f"Signo de puntuación español no permitido '{char}'"
    
    # Símbolos especiales comunes
    elif char == '@':
        return f"Símbolo '@' no válido (solo permitido dentro de cadenas)"
    
    elif char == '$':
        return f"Símbolo '$' no permitido (use el nombre de la moneda o cadenas)"
    
    elif char == '%':
        return f"Símbolo '%' no es un operador válido"
    
    # Delimitadores no soportados
    elif char in '[]':
        return f"Corchetes '{char}' no están soportados (use paréntesis)"
    
    elif char in '{}':
        return f"Llaves '{char}' no están soportadas (use paréntesis para agrupar)"
    
    # Operadores lógicos incorrectos
    elif char == '|':
        return f"Operador '|' no válido (use 'or' para operaciones lógicas)"
    
    elif char == '||':
        return f"Operador '||' no válido (use 'or' para operaciones lógicas)"
    
    elif char == '&':
        return f"Operador '&' no válido (use 'and' para operaciones lógicas)"
    
    elif char == '&&':
        return f"Operador '&&' no válido (use 'and' para operaciones lógicas)"
    
    # Punto y coma innecesario
    elif char == ';':
        return f"Punto y coma ';' no es necesario (no se requieren terminadores de línea)"
    
    # Barra invertida fuera de cadena
    elif char == '\\':
        return f"Barra invertida '\\' solo válida dentro de cadenas"
    
    # Caracteres con acento
    elif char in 'áéíóúÁÉÍÓÚñÑ':
        base = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u',
                'Á':'A', 'É':'E', 'Í':'I', 'Ó':'O', 'Ú':'U',
                'ñ':'n', 'Ñ':'N'}
        replacement = base.get(char, char)
        return f"Carácter acentuado '{char}' no válido (use '{replacement}' sin acento)"
    
    # Otros caracteres Unicode
    elif ord(char) > 127:
        return f"Carácter Unicode '{char}' no permitido (código: {ord(char)})"
    
    # Caracteres de control
    elif ord(char) < 32 and char not in '\n\t\r':
        return f"Carácter de control no válido (código ASCII: {ord(char)})"
    
    # Backticks y tildes
    elif char in '`~':
        return f"Carácter '{char}' no es válido en este lenguaje"
    
    # Carácter por defecto
    else:
        return f"Carácter ilegal '{char}'"


def t_error(t):
    """Maneja errores léxicos con categorización detallada."""
    line = t.lexer.lineno
    column = find_column(t.lexer.lexdata, t)
    lines = t.lexer.lexdata.splitlines()
    line_text = lines[line - 1] if line - 1 < len(lines) else ""
    
    char = t.value[0]
    message = None
    
    # Caso especial 1: Cadena no cerrada
    if char == '"':
        rest_of_line = line_text[column - 1:]
        # Si solo hay una comilla en lo que resta de línea, probablemente no está cerrada
        if rest_of_line.count('"') == 1:
            message = "Cadena no cerrada (falta comilla de cierre)"
        else:
            message = "Error en cadena de texto (verifique las comillas)"
    
    # Caso especial 2: Comentario de bloque no cerrado
    elif t.value.startswith('/*'):
        rest_of_text = t.lexer.lexdata[t.lexpos:]
        if '*/' not in rest_of_text:
            message = "Comentario de bloque sin cierre (falta */)"
        else:
            message = "Error en comentario de bloque"
    
    # Caso especial 3: Operador '!' incompleto
    elif char == '!' and column < len(line_text):
        next_char = line_text[column] if column < len(line_text) else ''
        if next_char != '=':
            message = "Operador '!' incompleto (use '!=' para desigualdad o 'not' para negación)"
    
    # Categorización por carácter
    if not message:
        message = categorize_char_error(char, line_text, column)
    
    error = {
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
    Imprime los errores de manera formateada con línea, columna, texto y flecha.
    Esto sirve para ver la salida del lexer directamente, descomentando el código de main y en 
    code poner el código directamente. Sirve para debuggear
    """
    for error in errors:
        print(f"Error léxico en línea {error['line']}, columna {error['column']}: {error['message']}")
        print(f"  {error['line_text']}")
        print(f"  {' ' * (error['column'] - 1)}^")

def format_errors(errors: List[Dict[str, Any]]) -> str:
    """Devuelve una cadena formateada con los errores para la interfaz del compilador"""
    if not errors:
        return ""
    lines = []
    for error in errors:
        lines.append(f"Error léxico en línea {error['line']}, columna {error['column']}: {error['message']}")
        lines.append(f"  {error['line_text']}")
        lines.append(f"  {' ' * (error['column'] - 1)}^")
        lines.append("")  # blank line between errors
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