# Tipos de datos

Snaptics implementa un sistema de tipado estático con inferencia. Cada expresión tiene un tipo que el compilador determina en la fase semántica (módulo `semantic/type_checker.py`).

---

## Tipos primitivos

| Tipo | Token interno | Descripción | Ejemplo de literal |
|---|---|---|---|
| `int` | `TYPE_INT` | Entero de 16 bits (compatible con 8086) | `42`, `0`, `-5` |
| `real` | `TYPE_REAL` | Número de punto flotante | `3.14`, `0.5`, `1.0` |
| `string` | `TYPE_STRING` | Cadena de texto entre comillas dobles | `"Norte"`, `"ventas.csv"` |
| `bool` | `TYPE_BOOL` | Valor booleano | `true`, `false` |

---

## Tipado de columnas en `select`

Al declarar un dataset con `select`, cada columna puede anotarse con su tipo usando la sintaxis `columna: tipo`:

```snaptics
dataset alumnos_foco = select alumno: int, asistencia: int, calificacion: int,
                              grupo: int, tareas: int, promedio: int
                       from alumnos_raw
                       where promedio < 80
```

- Las columnas tipadas quedan registradas en la tabla de símbolos con su tipo exacto.
- Si una columna se declara sin tipo (`select nombre from ...`), el semántico emite **SEM-204** al usarla en expresiones que requieren un tipo concreto.

---

## Tipos de los constructos del lenguaje

### Hechos (`fact`)
Siempre producen tipo `real`. Todo `fact` es el resultado de una expresión `P(...)`, que devuelve un valor en `[0.0, 1.0]`.

```snaptics
fact ventas_altas = P(ventas.monto > 500)
-- ventas_altas tiene tipo real
```

### Reglas (`rule`)
Siempre producen tipo `bool`. Una regla evalúa una expresión lógica que es verdadera o falsa.

```snaptics
rule baja_rentabilidad :- ventas_altas < 0.5 and margen_bajo > 0.3
-- baja_rentabilidad tiene tipo bool
```

### Expresiones `P(...)`
El resultado de `P(expr)` es siempre `real`, independientemente del tipo de la expresión interior.

### Acceso a miembros (`dataset.columna`)
El tipo se resuelve desde la tabla de símbolos usando el tipo declarado en el `select`. Si la columna no tiene tipo declarado, se usa `real` como valor de retorno por defecto.

---

## Inferencia de tipos

El módulo `semantic/type_checker.py` infiere el tipo de cada nodo del AST mediante la función `infer_type()`. Las reglas de inferencia son:

| Nodo AST | Tipo inferido |
|---|---|
| `Probabilidad` (`P(...)`) | `real` |
| `Media`, `Varianza`, `DesviacionEstandar`, `Correlacion` | `real` |
| `AccesoMiembro` (`dataset.col`) | tipo de la columna en la tabla de símbolos, o `real` si no está declarado |
| `LiteralEntero` | `int` |
| `LiteralReal` | `real` |
| `LiteralCadena` | `string` |
| `LiteralBooleano` | `bool` |
| `OperacionAritmetica` | `real` si algún operando es `real`, `int` si ambos son `int` |
| `OperacionRelacional` | `bool` |
| `OperacionLogica` | `bool` |
| Identificador de `fact` | `real` |
| Identificador de `rule` | `bool` |

---

## Verificaciones de tipo (errores SEM-2xx)

El analizador semántico realiza las siguientes comprobaciones activas:

### SEM-201 — Operación aritmética con tipos incompatibles
Se emite cuando se intenta aplicar `+`, `-`, `*`, `/` o `^` entre tipos que no son numéricos (`int` o `real`).

```snaptics
-- Incorrecto: string en operación aritmética
fact error = P(ventas.region + 10)  -- SEM-201
```

### SEM-202 — Operandos no booleanos en operación lógica
Se emite cuando `and`, `or` o `not` reciben operandos de tipo no booleano.

```snaptics
-- Incorrecto: int en expresión lógica
rule error :- 42 and margen_bajo    -- SEM-202
```

### SEM-203 — Comparación entre tipos incompatibles
Se emite cuando los operandos de `==`, `!=`, `<`, `>`, `<=`, `>=` tienen tipos incompatibles entre sí.

```snaptics
-- Incorrecto: real comparado con string
rule error :- asistencia_critica > "alto"  -- SEM-203
```

### SEM-204 — Columna sin tipo declarado
Se emite cuando se usa una columna de dataset en una expresión que requiere un tipo concreto, pero la columna fue declarada sin anotación de tipo.

```snaptics
dataset datos = select nombre from raw_data   -- nombre sin tipo
fact error = P(datos.nombre > 50)             -- SEM-204
```

**Solución:** anotar el tipo en el `select`:

```snaptics
dataset datos = select nombre: string from raw_data
```

---

## Tabla de compatibilidad de tipos

| Operación | `int` | `real` | `string` | `bool` |
|---|---|---|---|---|
| Aritmética (`+`, `-`, `*`, `/`, `^`) | ✅ | ✅ | ❌ | ❌ |
| Relacional (`<`, `>`, `<=`, `>=`) | ✅ | ✅ | ❌ | ❌ |
| Igualdad (`==`, `!=`) | ✅ | ✅ | ✅ | ✅ |
| Lógica (`and`, `or`, `not`) | ❌ | ❌ | ❌ | ✅ |
| Dentro de `P(...)` | ✅ | ✅ | ✅* | ❌ |

> \* Las cadenas solo se usan válida­mente en comparaciones de igualdad dentro de `P(...)`.

---

## Conversión implícita

Snaptics **no realiza conversiones implícitas** entre tipos. Si se necesita operar entre `int` y `real`, el `int` se promueve automáticamente a `real` durante la generación de IR, pero el type checker ya lo trata como compatible.

No existe conversión automática entre tipos numéricos y `string` o `bool`.
