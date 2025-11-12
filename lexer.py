import ply.lex as lex

"""
    Como construír nuextro léxico:
        Se tiene que escribír un conjunto de cada nombre de los tokens,
        Por cada toquen escrito en el conjunto, se representa ocn una expresión regular,
        compatible con re module de python.
        Cada de una de estas reglas estan definidas por declaraciones con el prefijo t_ para
        indicar que define un toquen 
        Las palabras reservadas deben escribirse 
        
"""


tokens = (
    'ID',
    'NUMINT',
    'NUMREAL',
    'LPAREN',
    'RPAREN',
    'ADD',
    'SUB',
    'ASIG',
    'LESSTHAN',
    'GREATERTHAN',
    'EQ',
    'NUMBER'
)

t_ignore  = ' \t'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_ADD = r'\+'
t_SUB = r'\-'
t_ASIG = r'\->'
t_LESSTHAN = r'\<'
t_GREATERTHAN = r'\>'
t_EQ = r'\=='

reserved = {
    'if' : 'IF',
    'then' : 'THEN',
    'else' : 'ELSE',
    'while' : 'WHILE'
}


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value,'ID')    # Check for reserved words
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)
    
lexer = lex.lex()

data = '''
3 + 4 * 10
  + -20 *2
'''
lexer.input(data)

while True:
    tok = lexer.token()
    if not tok: 
        break     
    print(tok)