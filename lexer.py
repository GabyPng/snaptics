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
    'BOOL',
    'STRING'
    
] + list(reserved.values())

t_ignore  = ' \t'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_ADD = r'\+'
t_SUB = r'-'
t_MUL = r'\*'
t_DIV = r'/'
t_ASIG = r'='
t_EQ = r'=='
t_NEQ = r'\!='
t_LEQ = r'\<='
t_GEQ = r'\>='
t_LESSTHAN = r'\<'
t_GREATERTHAN = r'\>'
# Operador de implicación/condición estilo Prolog
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

def t_BOOL(t):
    r'(true|false)'
    t.value = True if t.value == 'true' else False
    return t

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

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

def t_COMMENT(t):
    r'\#.*'
    pass
    # No return value. Token discarded

def t_COMENTARIO_BLOQUE(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n') 
    pass 


def make_lexer():
    """Construye y devuelve una instancia de lexer PLY para este módulo."""
    # PLY espera un objeto de módulo (no solo globals()).
    return lex.lex(module=sys.modules[__name__])


def tokenize(text: str) -> Dict[str, Any]:
    """Tokeniza el texto y devuelve los tokens y mensajes.

    Retorno:
    - {
        'tokens': List[{ 'type', 'value', 'line', 'column', 'lexpos' }],
        'output': str  # mensajes (incluye errores impresos por t_error)
      }
      
    Tipo de token, Valor del token, ,NUMERO DE LÍNEA, COLUMNA
    print(tok.type, tok.value, tok.lineno, tok.lexpos)
    
    """
    lexer = make_lexer()
    lexer.input(text)

    buf = io.StringIO()
    tokens: List[Dict[str, Any]] = []
    # Patrones para recuperar el lexema exacto a partir de lexpos
    real_re = re.compile(r'\d+\.\d+([eE][-+]?\d+)?')
    int_re = re.compile(r'\d+')
    str_re = re.compile(r'\"([^\\\"]|\\.)*\"')
    bool_re = re.compile(r'(true|false)')

    with contextlib.redirect_stdout(buf):
        while True:
            tok = lexer.token()
            if not tok:
                break
            col = find_column(text, tok)
            # Calcular longitud exacta del lexema
            length = None
            slice_from = text[tok.lexpos:] # Slicing con el metodo lexpos hasta donde termine el token
            if tok.type == 'REAL':
                m = real_re.match(slice_from)
                if m:
                    length = len(m.group(0))
            elif tok.type == 'INT':
                m = int_re.match(slice_from)
                if m:
                    length = len(m.group(0))
            elif tok.type == 'STRING':
                m = str_re.match(slice_from)
                if m:
                    length = len(m.group(0))
            elif tok.type == 'BOOL':
                m = bool_re.match(slice_from)
                if m:
                    length = len(m.group(0))
            # Fallback: usar la representación actual del valor
            if length is None:
                try:
                    length = len(str(tok.value))
                except Exception:
                    length = 1

            lexeme = slice_from[:length]
            tokens.append({
                'type': tok.type,
                'value': tok.value,
                'line': tok.lineno,
                'column': col,
                'lexpos': tok.lexpos, # índice absoluto del inicio del token en el texto
                'length': length, # longitud exacta del lexema en el texto.
                'lexeme': lexeme, #el texto original del lexema 
            })

    return {'tokens': tokens, 'output': buf.getvalue()}


if __name__ == '__main__':
    pass
# Tienes que ejecutar la clase main.py
"""
    sample = (
        'import dataset ventas from "ventas.csv"\n'
        'fact ventas_altas = P(ventas> 500) = 0.72\n'
        'rule baja_rentabilidad :- ventas_altas < 0.5 and margen_bajo > 0.3\n'
        'query rentabilidad_general\n'
    )
    result = tokenize(sample)
    for t in result['tokens']:
        print(t['type'], t['value'], t['line'], t['column'])
    if result['output']:
        print('\nMensajes del lexer:')
        print(result['output'])
"""