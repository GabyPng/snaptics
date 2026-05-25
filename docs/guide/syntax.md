# Sintaxis de Snaptics

Esta referencia cubre todas las construcciones sintácticas válidas del lenguaje. Cada sección incluye la gramática formal (BNF), ejemplos y notas de comportamiento.

---

## Estructura general de un programa

Un programa Snaptics es una secuencia de sentencias. No existe un punto de entrada explícito; las sentencias se evalúan en orden de aparición.

```bnf
programa ::= sentencia+
sentencia ::= importacion
            | preprocesamiento
            | declaracion_hecho
            | declaracion_regla
            | consulta
```

Ejemplo completo mínimo:

```snaptics
dataset datos = import from "archivo.csv"
fact probabilidad = P(datos.valor > 10)
rule conclusion :- probabilidad
query conclusion
```

---

## Comentarios

Los comentarios de línea comienzan con `--`:

```snaptics
-- Este es un comentario de una línea
fact ventas_altas = P(ventas.monto > 500)  -- comentario al final de una sentencia
```

---

## Importación de datos

### Gramática

```bnf
importacion ::= DATASET ID = IMPORT FROM STRING
```

### Ejemplo

```snaptics
dataset ventas_raw = import from "ventas.csv"
dataset alumnos    = import from "datos/alumnos.csv"
```

- El nombre del archivo es una cadena entre comillas dobles.
- Las rutas relativas se resuelven contra el directorio del archivo `.snp`.
- El semántico valida la existencia del CSV en tiempo de compilación (`SEM-303`).

---

## Preprocesamiento de datasets

### Gramática

```bnf
preprocesamiento ::= DATASET ID = SELECT lista_cols FROM ID
                   | DATASET ID = SELECT lista_cols FROM ID WHERE expresion

lista_cols ::= col_tipada (COMMA col_tipada)*
col_tipada ::= ID COLON tipo
             | ID

tipo ::= int | real | string | bool
```

### Ejemplo

```snaptics
dataset alumnos_foco = select alumno: int, asistencia: int, promedio: int
                       from alumnos_raw
                       where promedio < 80
```

- La cláusula `where` es opcional.
- Cada columna puede tener un tipo anotado (`col: tipo`). Si se omite el tipo, el semántico puede emitir `SEM-204`.
- El dataset resultante solo contiene las filas que satisfacen la condición `where`.

---

## Declaración de hechos

### Gramática

```bnf
declaracion_hecho ::= FACT ID = P(expresion)
                    | FACT ID = P(expresion GIVEN expresion)
```

### Ejemplo

```snaptics
fact asistencia_critica = P(alumnos_foco.asistencia < 60)
fact p_reprob           = P(alumnos_foco.promedio < 60 given alumnos_foco.asistencia < 60)
```

- `P(expr)` calcula la probabilidad marginal: proporción de filas donde `expr` es verdadera.
- `P(A given B)` calcula la probabilidad condicional P(A | B).
- El resultado siempre es un valor `real` en `[0.0, 1.0]`.

---

## Declaración de reglas

### Gramática

```bnf
declaracion_regla ::= RULE ID :- expresion
```

### Ejemplo

```snaptics
rule alerta          :- asistencia_critica and p_reprob
rule alta_rentab     :- ventas_altas > 0.7 and not margen_bajo
rule riesgo_moderado :- asistencia_critica or p_reprob
```

- El cuerpo de la regla es una expresión lógica que combina hechos y comparaciones.
- El resultado es un booleano (`true` / `false`).
- Los hechos pueden compararse con umbrales numéricos directamente (p. ej. `ventas_altas > 0.7`).

---

## Consultas

### Gramática

```bnf
consulta ::= QUERY ID
           | QUERY ID EXPLAIN
           | QUERY ID WHY
```

### Ejemplo

```snaptics
query alerta
query alerta explain
query alerta why
```

| Variante | Salida |
|---|---|
| `query ID` | Resultado booleano y nivel de confianza |
| `query ID explain` | Resultado + cadena de razonamiento completa |
| `query ID why` | Resultado + lista de hechos que contribuyeron |

---

## Expresiones

### Operadores relacionales

| Operador | Significado |
|---|---|
| `==` | Igual |
| `!=` | Diferente |
| `<` | Menor que |
| `>` | Mayor que |
| `<=` | Menor o igual |
| `>=` | Mayor o igual |

### Operadores aritméticos

| Operador | Significado |
|---|---|
| `+` | Suma |
| `-` | Resta |
| `*` | Multiplicación |
| `/` | División |
| `^` | Potencia |

### Operadores lógicos

| Operador | Significado |
|---|---|
| `and` | Conjunción (ambas condiciones) |
| `or` | Disyunción (al menos una) |
| `not` | Negación |

### Acceso a columnas de dataset

```snaptics
dataset.columna
```

Por ejemplo: `alumnos_foco.promedio`, `ventas.monto`.

---

## Precedencia de operadores

De **menor** a **mayor** prioridad:

| Nivel | Operadores |
|---|---|
| 1 (menor) | `or` |
| 2 | `and` |
| 3 | `not` |
| 4 | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| 5 | `+`, `-` |
| 6 | `*`, `/` |
| 7 | Unario `-` |
| 8 (mayor) | `^` |

---

## Palabras reservadas

Las siguientes palabras están reservadas y no pueden usarse como identificadores:

### Datos y análisis
`dataset`, `import`, `select`, `from`, `where`, `group`, `filter`, `auto_discover`

### Lógica y conocimiento
`fact`, `rule`, `query`, `evidence`, `confidence`

### Estadística
`P`, `mean`, `var`, `std`, `correlation`, `distribution`

### Condicionales
`if`, `then`, `else`, `when`, `given`

### Explicabilidad
`explain`, `why`

### Booleanos
`true`, `false`

### Tipos
`int`, `real`, `string`, `bool`

---

## Identificadores

Los identificadores siguen la regla:

```regex
[A-Za-z_][A-Za-z_0-9]*
```

También se soportan identificadores compuestos con punto para acceso a miembros:

```regex
[A-Za-z_][A-Za-z_0-9]*(\.[A-Za-z_][A-Za-z_0-9]*)*
```

---

## Literales

| Tipo | Ejemplos |
|---|---|
| Entero | `42`, `0`, `100` |
| Real | `3.14`, `0.5`, `1.0` |
| Cadena | `"ventas.csv"`, `"datos/alumnos.csv"` |
| Booleano | `true`, `false` |
