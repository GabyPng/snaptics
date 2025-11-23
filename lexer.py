import ply.lex as lex
from typing import List, Dict, Any
import contextlib
import io
import sys
import re

"""
    Como construír nuextro léxico:
        Se tiene que escribír un conjunto de cada nombre de los tokens,
        Por cada toquen escrito en el conjunto, se representa ocn una expresión regular,
        compatible con re module de python.
        Cada de una de estas reglas estan definidas por declaraciones con el prefijo t_ para
        indicar que define un toquen 
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
    'infer': 'INFER',
    'explain': 'EXPLAIN',
    'evidence': 'EVIDENCE',
    'confidence': 'CONFIDENCE',

    # Probabilidad y estadística
    'P': 'PROB',
    'probability': 'PROBABILITY',
    'distribution': 'DISTRIBUTION',
    'mean': 'MEAN',
    'var': 'VAR',
    'std': 'STD',
    'correlation': 'CORRELATION',

    # Conectores y lógica
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    'if': 'IF',
    'then': 'THEN',
    'else': 'ELSE',
    'given': 'GIVEN',

    # Explicabilidad
    'why': 'WHY',
    'because': 'BECAUSE',

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
    
    'EQ',
    'NEQ',
    'LESSTHAN',
    'GREATERTHAN',
    'LEQ',
    'GEQ',
    
    'ASIG', # =
    'COND', # :=
    'RANGE', # ..
    
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

def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
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

lex_errors = []

def t_error(t):
    line = t.lexer.lineno
    column = find_column(t.lexer.lexdata, t)
    lines = t.lexer.lexdata.splitlines()
    line_text = lines[line - 1] if line - 1 < len(lines) else ""
    
    match t.value:
        case value if value.startswith('"') and not value.endswith('"'):
            message = "Cadena no cerrada"
        case _:
            message = f"Carácter ilegal '{t.value[0]}'"
    
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
        code poner el códgo directamente. Sirve para debuggear
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
    pass