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


reserved = {
    # Tipos de datos para hechos y reglas
    'fact' : 'FACT',
    'rule' : 'RULE',
    
    # Tipos de datos probabilísticos y estadísticos. Para representar distribuciones y variables aleatorias 
    'randvar' : 'RANDVAR',
    'dist' : 'DIST',
    'event' : 'EVENT',
    'probability' : 'PROBABILITY',
    'sample' : 'SAMPLE',
    'posterior' : 'POSTERIOR',
    
    # Tipos derivados. Para soportar estructuras complejas o aprendizaje bayesiano
    'dataset' : 'DATASET',
    'query' : 'QUERY',
    'model' : 'MODEL',
    'parameter' : 'PARAMETER',
    
    'given' : 'GIVEN',
    'evidence' : 'EVIDENCE',
    'confidence' : 'CONFIDENCE',
    
    'prob' : 'PROB',
    'Infer' : 'INFER',
    'define' : 'DEFINE',
    'return' : 'RETURN',
    
    'and' : 'AND',
    'or' : 'OR',
    'not' : 'NOT',
    'true' : 'TRUE',
    'false' : 'FALSE',
    
    # Importarl los datos
    'import' : 'IMPORT',
    'from' : 'FROM',
    
    # Para Análisis, investigación.
    'analyze' : 'ANALIZE',
    'discover' : 'DISCOVER',
    'where' : 'WHERE',
    
    'if' : 'IF',
    'then' : 'THEN',
    'else' : 'ELSE',
    'for' : 'FOR',
    'each' : 'EACH',
    'as' : 'AS',
    
    'load' : 'LOAD',
    'measure' : 'MEASURE',
    'pattern' : 'PATTERN',
    'observe' : 'OBSERVE',
    
    'calculate' : 'CALCULATE',
    'reason' : 'REASON',
    'with' : 'WITH',
    'show' : 'SHOW'
}

tokens = [
    'ID',
    'INT',
    'REAL',
    'STRING',
    'BOOL',
    'ATOM', # Para hechos probabilisticos hecho(planta_verde)
    
    'RECORD',
    'LIST',
    'SET',
    'DICT',
    # FACT hecho(llueve, 0.3)
    # RULE prob(llueve(X)) :- humedad(X) > 0.8.
    
    'LPAREN',
    'RPAREN',
    
    'ADD',
    'SUB',
    'MUL',
    'DIV',
    
    #'AND',
    #'OR',
    #'NOT',
    #'IMPLIES',
    'EQ',
    'NEQ',
    'LESSTHAN',
    'GREATERTHAN',
    'LEQ',
    'GEQ',
    
    'ASIG',
    'COND'
] + list(reserved.values())

t_ignore  = ' \t'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_ADD = r'\+'
t_SUB = r'\-'
t_ASIG = r'\->'
t_LESSTHAN = r'\<'
t_GREATERTHAN = r'\>'
t_EQ = r'\=='


def t_ID(t):
    r'[a-z][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value,'ID')    # Check for reserved words
    # Look up symbol table information and return a tuple
    t.value = (t.value, symbol_lookup(t.value))
    return t

def t_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_REAL(t):
    r'\f+'
    t.value = float(t.value)
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

def t_COMMENT(t):
    r'\#.*'
    pass
    # No return value. Token discarded


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