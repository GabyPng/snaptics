# Funciones y operadores

Snaptics proporciona funciones integradas para análisis probabilístico y estadístico, así como operadores aritméticos, relacionales y lógicos.

---

## Función de probabilidad — `P(...)`

### Probabilidad marginal

```snaptics
P(expresion)
```

Devuelve la proporción de filas del dataset donde `expresion` es verdadera.

```snaptics
fact ventas_altas    = P(ventas.monto > 500)
fact asistencia_baja = P(alumnos.asistencia < 60)
```

### Probabilidad condicional

```snaptics
P(expresion_A given expresion_B)
```

Calcula P(A | B): proporción de filas donde A es verdadera dado que B también lo es.

```snaptics
fact p_reprob = P(alumnos.promedio < 60 given alumnos.asistencia < 60)
```

**Tipo de retorno:** `real` en `[0.0, 1.0]`.

---

## Funciones estadísticas

Operan sobre columnas de datasets y devuelven siempre `real`.

| Función | Sintaxis | Descripción |
|---|---|---|
| `mean` | `mean(dataset.col)` | Media aritmética |
| `var` | `var(dataset.col)` | Varianza |
| `std` | `std(dataset.col)` | Desviación estándar |
| `correlation` | `correlation(dataset.a, dataset.b)` | Correlación de Pearson entre dos columnas (`[-1.0, 1.0]`) |
| `distribution` | `distribution(dataset.col)` | Distribución de frecuencias |

```snaptics
fact promedio_ventas  = mean(ventas.monto)
fact dispersion       = std(ventas.monto)
fact relacion         = correlation(ventas.publicidad, ventas.monto)
```

---

## Descubrimiento automático — `auto_discover`

```snaptics
auto_discover dataset(nombre) where correlation > umbral
```

Detecta automáticamente correlaciones fuertes entre columnas y las registra como hechos.

```snaptics
auto_discover dataset(ventas) where correlation > 0.7
```

---

## Operadores aritméticos

| Operador | Descripción | Tipos válidos |
|---|---|---|
| `+` | Suma | `int`, `real` |
| `-` | Resta | `int`, `real` |
| `*` | Multiplicación | `int`, `real` |
| `/` | División | `int`, `real` |
| `^` | Potencia | `int`, `real` |

---

## Operadores relacionales

| Operador | Descripción |
|---|---|
| `==` | Igual |
| `!=` | Diferente |
| `<` | Menor que |
| `>` | Mayor que |
| `<=` | Menor o igual |
| `>=` | Mayor o igual |

---

## Operadores lógicos

| Operador | Descripción | Uso en reglas |
|---|---|---|
| `and` | Ambas condiciones verdaderas | `fact_a > 0.5 and fact_b` |
| `or` | Al menos una verdadera | `riesgo_a or riesgo_b` |
| `not` | Negación | `not margen_bajo` |

Los hechos son de tipo `real`, por lo que se comparan con umbrales antes de aplicar lógica:

```snaptics
rule alerta :- asistencia_critica > 0.6 and not p_reprob < 0.3
```

---

## Modificadores de `query`

| Modificador | Salida |
|---|---|
| *(ninguno)* | Resultado booleano y nivel de confianza |
| `explain` | Resultado + cadena de razonamiento completa |
| `why` | Resultado + lista de hechos que contribuyeron |

```snaptics
query alerta
query alerta explain
query alerta why
```

---

## Precedencia de operadores

De menor a mayor prioridad:

1. `or`
2. `and`
3. `not`
4. `==`, `!=`, `<`, `>`, `<=`, `>=`
5. `+`, `-`
6. `*`, `/`
7. Unario `-`
8. `^`
