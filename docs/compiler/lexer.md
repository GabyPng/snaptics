# Analizador Léxico — `lexer.py`

> **¿Para quién es esta documentación?**  
> Para cualquier persona que quiera entender cómo funciona el análisis léxico de Snaptics, cómo está implementado, qué librerías usa y cómo replicarlo desde cero.

---

## ¿Qué es un analizador léxico?

El analizador léxico (o *lexer*) es la **primera etapa de un compilador**. Su trabajo es leer el código fuente como una cadena de texto y dividirlo en unidades mínimas con significado llamadas **tokens**.

Por ejemplo, el texto:

```
fact ventas_altas = P(ventas.monto > 500)
```

Se convierte en la secuencia de tokens:

```
FACT  |  ID(ventas_altas)  |  ASIG  |  PROB  |  LPAREN  |  ID(ventas.monto)  |  GREATERTHAN  |  INT(500)  |  RPAREN
```

El parser (siguiente etapa) trabaja con esta secuencia de tokens, no con el texto original.

---

## Librería utilizada: PLY

El lexer de Snaptics está construido con **PLY** (*Python Lex-Yacc*), una implementación pura de Python de las herramientas clásicas `lex` y `yacc` de C.

### Instalación

```bash
pip install ply
```

### ¿Cómo funciona PLY?

PLY lee las funciones y variables del módulo que empiezan con el prefijo `t_` y las interpreta como **reglas de token**. A partir de ellas construye internamente un **autómata de estados finitos (DFA)** que reconoce los patrones.

Las reglas pueden definirse de dos formas:

1. **Variable de cadena** — para tokens simples:
   ```python
   t_LPAREN = r'\('
   ```

2. **Función** — para tokens que necesitan lógica adicional (convertir el valor, registrar errores, etc.):
   ```python
   def t_INT(t):
       r'\d+'
       t.value = int(t.value)   # convierte el texto a entero Python
       return t
   ```

   El docstring de la función **es la expresión regular**. PLY la extrae automáticamente.

### Otras librerías usadas en `lexer.py`

| Librería | Uso |
|---|---|
| `ply.lex` | Motor del lexer (DFA, tokenización) |
| `difflib` | Detectar typos en palabras reservadas (`get_close_matches`) |
| `re` | Expresiones regulares auxiliares para detectar números malformados |
| `typing` | Anotaciones de tipo (`Dict`, `List`, `Any`) |
| `sys` | Pasar el módulo actual a PLY (`sys.modules[__name__]`) |
| `io`, `contextlib` | Importados para suprimir salida de PLY (debug) |

---

## Estructura del módulo

```
lexer.py
 ├── LexicalErrorCode          # Clase con todos los códigos de error (LEX-xxx)
 ├── reserved {}               # Diccionario de palabras reservadas
 ├── tokens []                 # Lista de nombres de tokens (requerida por PLY)
 ├── t_ignore                  # Caracteres que se ignoran (espacios, tabs)
 ├── Reglas de token (t_*)     # Una por cada tipo de token
 │   ├── t_COMMENT             # Comentarios de línea (#)
 │   ├── t_COMENTARIO_BLOQUE   # Comentarios de bloque (/* */)
 │   ├── t_MALFORMED_NUMBER    # Números con múltiples puntos (0.60.0)
 │   ├── t_ID                  # Identificadores y palabras reservadas
 │   ├── t_REAL                # Números reales (3.14, 1.0e-3)
 │   ├── t_INT                 # Números enteros (42)
 │   ├── t_STRING              # Cadenas de texto ("archivo.csv")
 │   ├── t_newline             # Saltos de línea (actualiza lineno)
 │   └── t_error               # Manejador de caracteres no reconocidos
 ├── find_column()             # Calcula la columna de un token
 ├── categorize_char_error()   # Clasifica un carácter ilegal
 ├── detect_malformed_number() # Detecta números mal formados
 ├── make_lexer()              # Construye y devuelve el lexer PLY
 ├── tokenize()                # API principal: texto → tokens + errores
 ├── format_errors()           # Formatea errores para la GUI
 └── print_errors()            # Imprime errores en consola
```

---

## Palabras reservadas

PLY no tiene un mecanismo nativo de palabras reservadas. El patrón estándar es definirlas en un **diccionario** y resolverlas dentro de la regla `t_ID`: si el lexema coincide con una clave del diccionario, se sustituye el tipo del token.

```python
# Diccionario: lexema (texto) → nombre del token
reserved = {
    # Datos
    'dataset':      'DATASET',
    'import':       'IMPORT',
    'from':         'FROM',
    'select':       'SELECT',
    'where':        'WHERE',
    'group':        'GROUP',
    'filter':       'FILTER',
    'auto_discover':'AUTO_DISCOVER',
    # Lógica
    'fact':         'FACT',
    'rule':         'RULE',
    'query':        'QUERY',
    'evidence':     'EVIDENCE',
    'confidence':   'CONFIDENCE',
    # Probabilidad y estadística
    'P':            'PROB',
    'distribution': 'DISTRIBUTION',
    'mean':         'MEAN',
    'var':          'VAR',
    'std':          'STD',
    'correlation':  'CORRELATION',
    # Explicabilidad
    'explain':      'EXPLAIN',
    'why':          'WHY',
    # Lógica booleana
    'and':          'AND',
    'or':           'OR',
    'not':          'NOT',
    'if':           'IF',
    'then':         'THEN',
    'else':         'ELSE',
    'given':        'GIVEN',
    # Booleanos
    'true':         'TRUE',
    'false':        'FALSE',
    # Tipos de dato
    'int':          'TYPE_INT',
    'real':         'TYPE_REAL',
    'string':       'TYPE_STRING',
    'bool':         'TYPE_BOOL',
}
```

La lista `tokens` que PLY exige se construye combinando los tokens no-reservados con los valores del diccionario:

```python
tokens = [
    'ID',
    'LPAREN', 'RPAREN',
    'ADD', 'SUB', 'MUL', 'DIV', 'POW',
    'EQ', 'NEQ', 'LESSTHAN', 'GREATERTHAN', 'LEQ', 'GEQ',
    'ASIG', 'COND', 'RANGE', 'COMMA', 'DOT', 'COLON',
    'INT', 'REAL', 'STRING',
] + list(reserved.values())
```

---

## Tokens simples (reglas como cadenas)

Para tokens cuyo único propósito es reconocer un patrón fijo sin transformar el valor, se usa una variable:

```python
t_LPAREN      = r'\('
t_RPAREN      = r'\)'
t_ADD         = r'\+'
t_SUB         = r'-'
t_MUL         = r'\*'
t_DIV         = r'/'
t_POW         = r'\^'
t_EQ          = r'=='
t_NEQ         = r'!='
t_LEQ         = r'<='
t_GEQ         = r'>='
t_LESSTHAN    = r'<'
t_GREATERTHAN = r'>'
t_ASIG        = r'='
t_COND        = r':-'    # operador de implicación en reglas
t_RANGE       = r'\.\.'  # rango (..)
t_COMMA       = r','
t_DOT         = r'\.'
t_COLON       = r':'
t_ignore      = ' \t'   # espacios y tabs se descartan silenciosamente
```

> **Regla de prioridad de PLY:** cuando dos reglas pueden coincidir con el mismo texto, PLY da prioridad a la **más larga**. Por eso `t_EQ` (`==`) debe definirse antes de `t_ASIG` (`=`), y `t_RANGE` (`..`) antes de `t_DOT` (`.`). PLY ordena las cadenas por longitud descendente automáticamente.

---

## Tokens con lógica (reglas como funciones)

### Identificadores y palabras reservadas — `t_ID`

Esta es la regla más importante del lexer. Reconoce cualquier identificador y luego verifica si es una palabra reservada. Si no lo es, comprueba si parece un typo de alguna palabra reservada.

```python
def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    # ¿Es una palabra reservada exacta?
    if t.value in reserved:
        t.type = reserved[t.value]   # cambia el tipo, ej. 'fact' → FACT
    else:
        # ¿Parece un typo de palabra reservada? (usa difflib)
        reserved_words = list(reserved.keys())
        cutoff = 0.90 if len(t.value) > 3 else 0.80
        suggestions = difflib.get_close_matches(t.value.lower(), reserved_words, n=1, cutoff=cutoff)
        if suggestions:
            # Registra LEX-701 pero NO descarta el token
            error = {
                'code': 'LEX-701',
                'message': f"Posible error de escritura: '{t.value}'. ¿Quisiste decir '{suggestions[0]}'?"
                # ... más campos
            }
            t.lexer.errors.append(error)
    return t
```

**Dos umbrales de similitud** para evitar falsos positivos:
- Palabras de **más de 3 caracteres** → `cutoff = 0.90` (muy similar para ser sugerida)
- Palabras de **3 o menos caracteres** → `cutoff = 0.80` (evita que `nota` sugiera `not`)

### Números reales — `t_REAL`

```python
def t_REAL(t):
    r'\d+\.\d+([eE][-+]?\d+)?'
    t.value = float(t.value)   # convierte el lexema a float de Python
    return t
```

Reconoce: `3.14`, `0.5`, `1.0e-3`, `2.5E+10`.  
**Debe definirse antes de `t_INT`** en el código fuente, porque PLY da prioridad a las funciones según el orden de aparición.

### Números enteros — `t_INT`

```python
def t_INT(t):
    r'\d+'
    t.value = int(t.value)   # convierte el lexema a int de Python
    return t
```

### Cadenas de texto — `t_STRING`

```python
def t_STRING(t):
    r'\"([^\\"]|\\.)*\"'
    t.value = t.value[1:-1]   # elimina las comillas delimitadoras
    return t
```

Reconoce cadenas entre comillas dobles con soporte de secuencias de escape (`\"`, `\\`). El valor del token ya no incluye las comillas.

### Números malformados — `t_MALFORMED_NUMBER`

```python
def t_MALFORMED_NUMBER(t):
    r'\d+(\.\d+){2,}'
    # Registra LEX-652 y descarta el token (retorna None)
    ...
    return None
```

Detecta errores como `0.60.0` o `3.14.159` (múltiples puntos decimales). **Debe ir antes de `t_REAL` y `t_INT`** para tener prioridad sobre ellos.

### Comentarios

```python
# Comentario de línea: desde # hasta fin de línea
def t_COMMENT(t):
    r'\#.*'
    pass   # se descarta, no se retorna el token

# Comentario de bloque: /* ... */ (puede ser multilínea)
def t_COMENTARIO_BLOQUE(t):
    r'/\*([^*]|\*+[^*/])*\*/'
    t.lexer.lineno += t.value.count('\n')   # mantiene el conteo de líneas correcto
    pass
```

### Saltos de línea — `t_newline`

```python
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)   # actualiza el número de línea
    # no retorna token: los saltos no son parte de la gramática
```

---

## Función auxiliar: `find_column`

PLY rastrea la posición en bytes (`lexpos`) pero no la columna. Esta función la calcula:

```python
def find_column(input: str, token) -> int:
    # Busca el último salto de línea antes de la posición del token
    line_start = input.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1
```

Se usa en todos los mensajes de error y en los metadatos de `tokenize()`.

---

## Manejo de errores

### La función `t_error`

PLY llama automáticamente a `t_error` cuando ninguna regla reconoce el carácter actual. El lexer de Snaptics implementa un flujo de detección en cascada:

```
carácter actual
 │
 ├─ ¿Es un dígito?
 │   └─ detect_malformed_number() → si hay patrón → LEX-652, skip todo el número
 │
 ├─ ¿Es '"'?
 │   ├─ una sola comilla en la línea → LEX-601 (cadena sin cerrar)
 │   └─ otro caso                   → LEX-602 (error en cadena)
 │
 ├─ ¿Empieza con '/*'?
 │   ├─ no hay '*/' después → LEX-603 (bloque sin cerrar)
 │   └─ otro caso          → LEX-604
 │
 ├─ ¿Es '!' sin '=' a continuación?
 │   └─ LEX-305 (operador incompleto, sugerir '!=' o 'not')
 │
 └─ categorize_char_error(char) → clasifica por carácter específico
     ├─ '¿','¡'          → LEX-101
     ├─ '@'              → LEX-102
     ├─ '$'              → LEX-103
     ├─ '%'              → LEX-104
     ├─ '[',']'          → LEX-201 (usar paréntesis)
     ├─ '{','}'          → LEX-202 (usar paréntesis)
     ├─ '|'              → LEX-301 (usar 'or')
     ├─ '&'              → LEX-303 (usar 'and')
     ├─ ';'              → LEX-401 (no se necesita)
     ├─ '\'              → LEX-402
     ├─ á,é,í,ó,ú,ñ...  → LEX-501 (sugiere versión sin acento)
     ├─ ord(char) > 127  → LEX-502 (Unicode no permitido)
     ├─ '`','~'          → LEX-503
     └─ cualquier otro   → LEX-999

Después de registrar el error → t.lexer.skip(1) → continúa sin detenerse
```

> **Recuperación de errores:** el lexer **nunca se detiene** ante un error. Avanza un carácter con `skip(1)` y sigue tokenizando. Esto permite reportar todos los errores de un archivo en una sola pasada.

### Tabla de códigos de error

| Código | Causa | Ejemplo | Sugerencia emitida |
|---|---|---|---|
| LEX-101 | Puntuación española | `¿`, `¡` | — |
| LEX-102 | Símbolo `@` | `user@` | Solo en cadenas |
| LEX-103 | Símbolo `$` | `precio$` | Usar nombre o cadena |
| LEX-104 | Símbolo `%` | `margen%` | No es operador válido |
| LEX-201 | Corchetes `[]` | `lista[0]` | Usar paréntesis |
| LEX-202 | Llaves `{}` | `{x: 1}` | Usar paréntesis |
| LEX-301 | Pipe `\|` | `a \| b` | Usar `or` |
| LEX-303 | Ampersand `&` | `a & b` | Usar `and` |
| LEX-305 | `!` sin `=` | `!valor` | Usar `!=` o `not` |
| LEX-401 | Punto y coma `;` | `query x;` | No se requiere |
| LEX-402 | Barra invertida `\` | `ruta\n` | Solo en cadenas |
| LEX-501 | Carácter acentuado | `análisis` | Versión sin acento |
| LEX-502 | Unicode | `α`, `€` | No permitido |
| LEX-503 | Backtick o tilde | `` ` ``, `~` | No válido |
| LEX-601 | Cadena sin cerrar | `"sin cierre` | Añadir `"` |
| LEX-602 | Error en cadena | comillas mal anidadas | Revisar comillas |
| LEX-603 | Bloque sin cerrar | `/* sin cierre` | Añadir `*/` |
| LEX-604 | Error en bloque | — | — |
| LEX-651 | Número malformado | (desbordamiento) | — |
| LEX-652 | Múltiples decimales | `0.60.0` | Solo un punto |
| LEX-701 | Typo en reservada | `factt` | `fact` |
| LEX-999 | Carácter ilegal | cualquier otro | — |

### Estructura de un objeto de error

Todo error registrado en `lexer.errors` sigue este esquema:

```python
{
    'type':      'lexical',        # siempre 'lexical'
    'code':      'LEX-101',        # código del error
    'category':  'Puntuación española',  # descripción corta
    'line':      3,                # línea donde ocurre (base 1)
    'column':    8,                # columna donde ocurre (base 1)
    'line_text': 'query alerta¿',  # texto completo de la línea
    'message':   "Signo '¿' no permitido",  # descripción con contexto
}
```

---

## API pública

### `make_lexer() → lex.Lexer`

Construye y devuelve una instancia de lexer PLY. Se usa internamente por `tokenize()` y también directamente en los tests.

```python
from lexer import make_lexer

lexer = make_lexer()
lexer.errors = []
lexer.input("fact x = P(datos.valor > 10)")
for tok in lexer:
    print(tok)
```

### `tokenize(text: str) → dict`

**Función principal.** Acepta el código fuente completo y devuelve:

```python
{
    'tokens': [...],   # lista de tokens reconocidos
    'errors': [...],   # lista de errores léxicos
    'output': "",      # reservado (actualmente vacío)
}
```

Cada token en la lista tiene:

| Campo | Tipo | Descripción |
|---|---|---|
| `type` | `str` | Nombre del tipo (`'FACT'`, `'ID'`, `'INT'`, …) |
| `value` | `Any` | Valor semántico (`int`, `float`, `str`, o el lexema) |
| `line` | `int` | Número de línea (base 1) |
| `column` | `int` | Número de columna (base 1) |
| `lexpos` | `int` | Posición en bytes desde el inicio del texto |
| `lexeme` | `str` | Texto exacto tomado del fuente |
| `length` | `int` | Longitud del lexema en caracteres |

**Ejemplo completo:**

```python
from lexer import tokenize, print_errors

codigo = '''
dataset alumnos = import from "alumnos.csv"
fact riesgo = P(alumnos.promedio < 60)
rule alerta :- riesgo
query alerta
'''

resultado = tokenize(codigo)

# Mostrar tokens
for tok in resultado['tokens']:
    print(f"{tok['type']:<15} {repr(tok['value']):<20} línea {tok['line']} col {tok['column']}")

# Mostrar errores (si hay)
if resultado['errors']:
    print_errors(resultado['errors'])
```

Salida:

```
DATASET         'dataset'            línea 2 col 1
ID              'alumnos'            línea 2 col 9
ASIG            '='                  línea 2 col 17
IMPORT          'import'             línea 2 col 19
FROM            'from'               línea 2 col 26
STRING          'alumnos.csv'        línea 2 col 31
FACT            'fact'               línea 3 col 1
ID              'riesgo'             línea 3 col 6
...
```

### `format_errors(errors: list) → str`

Devuelve todos los errores como una cadena de texto formateada, lista para mostrarse en la GUI o en la terminal.

### `print_errors(errors: list)`

Equivalente a `format_errors` pero imprime directamente en `stdout`.

**Formato de salida:**

```
[LEX-501] Carácter acentuado no válido
  Línea 2, Columna 8: Carácter 'á' no válido (use 'a' sin acento)
  fact análisis = P(datos.valor > 0)
         ^
```

---

## Ejemplo con errores reales

Dado el siguiente código con errores intencionales:

```
fact análisis@ = P(ventas.monto > 500)
rule resultado :- análisis & otro | tercero
query resultado;
dataset d = import from "sin_cierre
```

El lexer produce (sin detenerse):

```
[LEX-501] Carácter acentuado no válido
  Línea 1, Columna 6: Carácter 'á' no válido (use 'a' sin acento)
  fact análisis@ = P(ventas.monto > 500)
       ^

[LEX-102] Símbolo '@' no válido
  Línea 1, Columna 14: Símbolo '@' no válido (solo permitido dentro de cadenas)
  fact análisis@ = P(ventas.monto > 500)
               ^

[LEX-303] Operador '&' no válido
  Línea 2, Columna 28: Operador '&' no válido (use 'and')
  rule resultado :- análisis & otro | tercero
                             ^

[LEX-301] Operador '|' no válido
  Línea 2, Columna 35: Operador '|' no válido (use 'or')
  rule resultado :- análisis & otro | tercero
                                    ^

[LEX-401] Punto y coma innecesario
  Línea 3, Columna 17: ';' no es necesario en Snaptics
  query resultado;
                 ^

[LEX-601] Cadena sin cerrar
  Línea 4, Columna 22: Cadena no cerrada (falta comilla de cierre)
  dataset d = import from "sin_cierre
                           ^
```

---

## Cómo replicar el lexer en otro proyecto

Si quisieras construir un lexer similar para otro lenguaje usando PLY, los pasos son:

1. **Instalar PLY:** `pip install ply`
2. **Definir `tokens`:** lista con todos los nombres de token que usará el parser.
3. **Definir `reserved`:** diccionario `{lexema: TOKEN}` para palabras reservadas.
4. **Escribir reglas `t_*`:** una variable o función por cada tipo de token.
   - Las funciones se procesan antes que las variables.
   - Las funciones se procesan en **orden de aparición** en el archivo.
   - Las variables de cadena se ordenan por **longitud descendente** automáticamente.
5. **Definir `t_error`:** para caracteres no reconocidos. Siempre llamar `t.lexer.skip(1)` al final.
6. **Definir `t_newline`:** para rastrear el número de línea (`t.lexer.lineno += len(t.value)`).
7. **Construir el lexer:** `lexer = lex.lex(module=sys.modules[__name__])`.
8. **Usar el lexer:** `lexer.input(texto)` y luego iterar con `lexer.token()`.

---

## Posición del lexer en el pipeline de compilación

El lexer es la **primera** de siete etapas. Su salida (lista de tokens) es la entrada del parser.

```
Código fuente (.snp)
        │
        ▼
┌───────────────┐
│    LEXER      │  ← lexer.py
│               │  Texto → tokens + errores LEX-xxx
└───────┬───────┘
        │ List[Token]
        ▼
┌───────────────┐
│    PARSER     │  ← parser.py
│               │  Tokens → AST + tabla de símbolos + errores SYN-xxx
└───────┬───────┘
        │ AST
        ▼
┌───────────────┐
│   SEMÁNTICO   │  ← semantic/
│               │  Validación de tipos y símbolos + errores SEM-xxx
└───────┬───────┘
        │ AST anotado
        ▼
┌───────────────┐
│  CSV STAGING  │  ← codegen/csv_stager.py
│               │  Copia CSVs al vdrive de emu8086
└───────┬───────┘
        │
        ▼
┌───────────────┐
│      IR       │  ← ir_generator.py
│               │  AST → cuádruplas intermedias
└───────┬───────┘
        │ IR
        ▼
┌───────────────┐
│  OPTIMIZADOR  │  ← optimizer/
│               │  Constant folding, propagación, simplificación
└───────┬───────┘
        │ IR optimizada
        ▼
┌───────────────┐
│    CODEGEN    │  ← codegen/
│               │  IR → ensamblador 8086 (.asm)
└───────────────┘
```

Si el lexer encuentra errores, **el pipeline completo se detiene**: el parser no recibe tokens y las etapas posteriores no se ejecutan. Esto garantiza que los mensajes de error sean claros y no se propaguen en cascada.

---

## Referencia rápida — todas las expresiones regulares

Tabla con todas las reglas de token en orden de prioridad (de mayor a menor, tal como PLY las aplica):

| Prioridad | Nombre | Expresión regular | Tipo de regla | Notas |
|---|---|---|---|---|
| 1 | `t_COMMENT` | `\#.*` | función | descarta el token |
| 2 | `t_COMENTARIO_BLOQUE` | `/\*([^*]|\*+[^*/])*\*/` | función | actualiza `lineno` |
| 3 | `t_MALFORMED_NUMBER` | `\d+(\.\d+){2,}` | función | LEX-652, descarta |
| 4 | `t_ID` | `[A-Za-z_][A-Za-z_0-9]*` | función | resuelve reservadas |
| 5 | `t_REAL` | `\d+\.\d+([eE][-+]?\d+)?` | función | convierte a `float` |
| 6 | `t_INT` | `\d+` | función | convierte a `int` |
| 7 | `t_STRING` | `\"([^\\"]|\\.)*\"` | función | elimina comillas |
| 8 | `t_newline` | `\n+` | función | actualiza `lineno` |
| 9 | `t_EQ` | `==` | variable (len=2) | antes de `t_ASIG` |
| 9 | `t_NEQ` | `!=` | variable (len=2) | antes de `t_LESSTHAN` |
| 9 | `t_LEQ` | `<=` | variable (len=2) | antes de `t_LESSTHAN` |
| 9 | `t_GEQ` | `>=` | variable (len=2) | antes de `t_GREATERTHAN` |
| 9 | `t_COND` | `:-` | variable (len=2) | implicación de regla |
| 9 | `t_RANGE` | `\.\.` | variable (len=2) | antes de `t_DOT` |
| 10 | `t_LPAREN` | `\(` | variable (len=1) | — |
| 10 | `t_RPAREN` | `\)` | variable (len=1) | — |
| 10 | `t_ADD` | `\+` | variable (len=1) | — |
| 10 | `t_SUB` | `-` | variable (len=1) | — |
| 10 | `t_MUL` | `\*` | variable (len=1) | — |
| 10 | `t_DIV` | `/` | variable (len=1) | — |
| 10 | `t_POW` | `\^` | variable (len=1) | — |
| 10 | `t_LESSTHAN` | `<` | variable (len=1) | — |
| 10 | `t_GREATERTHAN` | `>` | variable (len=1) | — |
| 10 | `t_ASIG` | `=` | variable (len=1) | — |
| 10 | `t_COMMA` | `,` | variable (len=1) | — |
| 10 | `t_DOT` | `\.` | variable (len=1) | — |
| 10 | `t_COLON` | `:` | variable (len=1) | — |
| — | `t_ignore` | `' \t'` | especial | no genera token |
| — | `t_error` | — | especial | PLY llama si nada coincide |

---

## Decisiones de diseño

Esta sección explica el *por qué* detrás de las decisiones de implementación menos obvias.

### ¿Por qué no usar expresiones regulares directamente con `re`?

Usando `re` puro habría que escribir el bucle de tokenización manualmente, manejar la posición en el texto, y gestionar la prioridad de patrones de forma explícita. PLY hace todo eso automáticamente y además genera tablas de parsing eficientes, lo que simplifica el mantenimiento y escala mejor cuando se añaden nuevos tokens.

### ¿Por qué `t_MALFORMED_NUMBER` es una función y no una variable?

Las variables de cadena en PLY se ordenan por longitud de la regex, no por su semántica. Para garantizar que `\d+(\.\d+){2,}` se evalúe **antes** que `\d+\.\d+` y `\d+`, es necesario definirla como función (las funciones tienen mayor prioridad que las variables en PLY).

### ¿Por qué dos mecanismos para detectar números malformados?

`t_MALFORMED_NUMBER` captura el patrón cuando el DFA aún está buscando un token válido (inicio de un lexema). `detect_malformed_number` dentro de `t_error` cubre el caso en que el número comienza con dígitos pero el DFA ya quedó en un estado intermedio y delegó el control al manejador de errores. Ambos son necesarios para cubrir todos los casos sin depender del orden exacto del estado interno del DFA.

### ¿Por qué dos umbrales en la detección de typos (`t_ID`)?

Un `cutoff` único de `0.90` haría que palabras cortas como `nota` o `par` nunca sugirieran nada útil (muy estricto). Un `cutoff` único de `0.80` causaría falsos positivos: `nota` sugeriría `not`, `dan` sugeriría `and`. La solución es usar `0.90` para palabras largas (más carácteres para comparar → más confiable) y `0.80` para palabras cortas.

### ¿Por qué el lexer no se detiene ante el primer error?

Detener la compilación en el primer error léxico obliga al programador a corregir un error, volver a compilar, ver el siguiente, etc. El modo de recuperación con `skip(1)` permite mostrar **todos los errores en una sola pasada**, lo cual es mucho más eficiente para el flujo de trabajo de desarrollo.

### ¿Por qué se usa `sys.modules[__name__]` en `make_lexer`?

PLY necesita inspeccionar el módulo donde están definidas las reglas `t_*`. Pasar `module=sys.modules[__name__]` le dice a PLY que busque en el módulo actual (`lexer.py`) sin importar desde qué archivo se llame `make_lexer()`. Esto permite construir el lexer desde la IDE, el CLI o los tests sin cambiar el código.

---

## Casos borde y comportamiento esperado

Situaciones ambiguas o poco intuitivas y cómo las maneja el lexer:

| Situación | Entrada | Resultado |
|---|---|---|
| `P` mayúscula es reservada | `P(x > 0)` | Token `PROB`, no `ID` |
| `p` minúscula no es reservada | `p(x > 0)` | Token `ID('p')` |
| Identificador con punto | `ventas.monto` | Un solo `ID('ventas.monto')` gracias a la regex de `t_ID` |
| `auto_discover` con guion bajo | `auto_discover` | Token `AUTO_DISCOVER` (clave en `reserved`) |
| Número entero seguido de punto | `42.` | `INT(42)` + `DOT` (el punto no forma parte del entero) |
| Real con notación científica | `1.5e-3` | `REAL(0.0015)` |
| Múltiples puntos decimales | `0.60.0` | Error `LEX-652`, token descartado |
| Cadena vacía | `""` | `STRING('')` sin error |
| Comentario de bloque multilínea | `/* línea1\nlínea2 */` | Descartado; `lineno` incrementado en 1 |
| Typo con palabra corta | `dan` | `ID('dan')` + posible `LEX-701` si similaridad ≥ 0.80 con `and` |
| `:-` partido en dos líneas | `:\` `(newline)` `-` | `COLON` + error `LEX-402` (barra fuera de cadena) |
| Carácter acentuado en cadena | `"café"` | `STRING('café')` sin error (dentro de comillas es válido) |
| `!` seguido de `=` | `!=` | Token `NEQ` (la variable `t_NEQ` coincide completa) |
| `!` sin `=` | `!x` | Error `LEX-305`, luego `ID('x')` |

---

## Limitaciones conocidas

Aspectos que el lexer actual **no maneja** o maneja parcialmente, y que podrían abordarse en versiones futuras:

| Limitación | Descripción | Posible solución |
|---|---|---|
| **Comentarios `--`** | El lenguaje usa `--` para comentarios de línea (ver guía de sintaxis), pero el lexer solo tiene regla para `#`. Los `--` se interpretan como `SUB SUB`. | Añadir `t_COMMENT_LINE = r'--.*'` antes de `t_SUB`. |
| **Identificadores con punto** | `ventas.monto` se tokeniza como un único `ID`. Esto funciona para acceso a columnas, pero impide que `a.b.c` se interprete como dos accesos encadenados. | Separar en `ID DOT ID` en el parser con una regla de producción específica. |
| **Strings multilínea** | No se soportan cadenas que abarquen más de una línea. `"primera\nsegunda"` producirá `LEX-601`. | Añadir soporte de cadenas con comillas triples (`"""`) o manejar `\n` dentro del patrón de `t_STRING`. |
| **Números negativos** | `-42` se tokeniza como `SUB INT(42)`, no como `INT(-42)`. La negación se resuelve en el parser. | Es el comportamiento correcto para un lexer; documentar en la guía del parser. |
| **Recuperación en bloques** | `t_error` avanza de a un carácter. Para errores dentro de bloques grandes (ej. bloque `/* */` muy largo) esto puede ser lento. | Usar `t.lexer.skip(n)` con `n` calculado para saltar todo el bloque de una vez. |
| **Sugerencias solo para reservadas** | `difflib` solo compara contra palabras reservadas. Un typo en un identificador de usuario (`ventaz` por `ventas`) no genera sugerencia. | Extender la comparación contra la tabla de símbolos construida durante el parsing. |
