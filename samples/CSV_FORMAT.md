# Contrato CSV — Snaptics

Documento que explica cómo el runtime de Snaptics lee los archivos CSV y
qué reglas debe cumplir el `.snp` para que los datos se interpreten bien.

## TL;DR — las dos reglas

1. **El CSV NO debe tener fila de encabezado**. Solo filas de datos.
2. **El SELECT del `.snp` debe declarar TODAS las columnas del CSV en el
   mismo ORDEN en que aparecen en el archivo.**

Si rompes cualquiera de las dos, el programa va a ensamblar y correr, pero
los conteos serán incorrectos porque el runtime estará leyendo celdas
equivocadas.

## Cómo lee el runtime

El runtime no proyecta columnas (no copia ni reorganiza el CSV). Lee
directo del buffer crudo byte por byte usando tres primitivas:

| Primitiva       | Qué hace                                             |
|-----------------|------------------------------------------------------|
| `skip_to_col_N` | Recibe `AL` con el índice de columna y avanza `SI` saltando comas hasta esa columna |
| `parse_int`     | Lee dígitos ASCII desde `SI` y los acumula como entero en `AX` |
| `skip_to_eol`   | Avanza `SI` hasta justo después del próximo LF (`0Ah`) |

Cuando una rutina `count_<fact>` quiere leer la columna `asistencia`, lo
hace así:

```asm
MOV AL, 1           ; ← índice numérico de la columna
CALL skip_to_col_N
CALL parse_int      ; ← AX queda con el valor entero de esa celda
```

El número `1` no es mágico: lo decide `count_generator.py` en
compile-time a partir del SELECT.

## Cómo el SELECT define los índices

`count_generator._build_column_map` recorre las cuádruplas SELECT del
programa, parsea su `arg2` (la lista de columnas con sus tipos), y asigna
un índice basado en la posición:

```python
for idx, name in enumerate(cols):
    col_map[name] = idx
```

O sea: el primer nombre en el SELECT es índice 0, el segundo índice 1, y
así. Ese índice se emite directamente como `MOV AL, <idx>` en el `.asm`.

## Ejemplo concreto

Tu `samples/demo/alumnos.csv`:

```
1,85,90,22400,1,82
2,45,60,22400,0,55
3,70,75,22400,1,65
...
```

Sin header. Seis columnas. El `samples/demo/alumnos_riesgo.snp`:

```snaptics
dataset alumnos_foco = select alumno: int, asistencia: int, calificacion: int,
                              grupo: int, tareas: int, promedio: int
                       from alumnos_raw
                       where promedio < 80
```

El compilador resuelve este mapeo:

| Nombre         | Posición en SELECT | Índice en CSV |
|----------------|--------------------|---------------|
| `alumno`       | 1° (idx 0)         | 0             |
| `asistencia`   | 2° (idx 1)         | 1             |
| `calificacion` | 3° (idx 2)         | 2             |
| `grupo`        | 4° (idx 3)         | 3             |
| `tareas`       | 5° (idx 4)         | 4             |
| `promedio`     | 6° (idx 5)         | 5             |

Y cuando ve `P(alumnos_foco.asistencia < 60)`, sabe que tiene que leer
la columna 1 del CSV. Emite `MOV AL, 1` en la rutina correspondiente.

## Qué pasa si rompes las reglas

**Si el CSV tiene fila de encabezado:**

```
asistencia, promedio    ← header
85, 82
45, 55
```

La primera iteración del loop intenta parsear `"asistencia"` con
`parse_int`. Como no son dígitos, devuelve `0`. Una comparación tipo
`0 < 60` siempre es verdadera, así que la fila del header contará como
"match" en todos los facts. Tus porcentajes salen mal.

**Si el SELECT no lista todas las columnas:**

```snaptics
select asistencia: int, promedio: int from alumnos_raw
```

Sobre un CSV de 6 columnas, esto mapea `asistencia: 0, promedio: 1`. Pero
las celdas reales en posiciones 0 y 1 son `alumno` y `asistencia`. El
runtime parsea valores equivocados y los conteos quedan mal sin error
visible.

**Si el SELECT reordena las columnas:**

```snaptics
select promedio: int, asistencia: int from alumnos_raw   ← invertido
```

Sobre un CSV `alumno, asistencia, calificacion, grupo, tareas, promedio`,
esto mapea `promedio: 0, asistencia: 1`. Pero la columna 0 del CSV es
`alumno`, no `promedio`. Conteos incorrectos otra vez.

## Por qué es así (limitación de v1)

En un compilador SQL "de verdad", el SELECT haría una **proyección real**:
el runtime leería el CSV crudo, copiaría a otro buffer solo las columnas
pedidas y en el orden pedido, y todas las operaciones siguientes operarían
sobre el buffer proyectado.

Implementar esto en 8086 requiere:

- Otro buffer en `.DATA` para el dataset proyectado
- Una rutina de copia/transformación con su propio loop
- Otro nivel de indirección en las `count_<fact>`

Es factible pero **no entra en el alcance de v1**. La decisión de diseño
fue mantener el código objeto simple y delegar el orden de columnas al
contrato `.snp` ↔ `.csv`.

## Lo que cambiaría en v2

Una versión 2 implementaría:

1. **Proyección real en runtime**: cualquier orden en el SELECT, cualquier
   subconjunto de columnas del CSV.
2. **Header opcional en el CSV**: el runtime salta la primera fila si
   detecta que tiene texto no numérico, o lo dice una directiva del `.snp`.
3. **Validación en compile-time**: el compilador podría leer un esquema
   del CSV (header o un archivo `.schema`) y verificar que los nombres
   del SELECT existen.

Por ahora, dos reglas claras y bien documentadas son suficientes para que
la demo funcione y los datos no mientan.
