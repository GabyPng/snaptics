# Introducción a Snaptics

Snaptics es un **lenguaje de programación declarativo** orientado al razonamiento lógico-probabilístico. Su propósito es analizar datos tabulares, declarar *hechos* y *reglas* con probabilidades asociadas y derivar *consultas* explicables.

A diferencia de los lenguajes convencionales que solo procesan datos numéricos, Snaptics interpreta información y genera **conocimiento estructurado** a través de hechos, reglas e inferencias cuantificadas.

---

## Filosofía del lenguaje

Snaptics combina cuatro disciplinas en una sintaxis coherente:

| Pilar | Rol |
|---|---|
| **Lógica** | Define reglas y relaciones entre hechos |
| **Estadística** | Calcula métricas como media, varianza y correlación |
| **Probabilidad** | Cuantifica la incertidumbre mediante expresiones `P(...)` |
| **Explicabilidad** | Produce conclusiones legibles por humanos |

El objetivo es permitir **razonamiento sobre incertidumbre** usando inferencias comprensibles y reproducibles.

---

## Primer ejemplo

El siguiente programa carga un CSV de alumnos, calcula dos hechos probabilísticos, define una regla de alerta y consulta el resultado:

```snaptics
dataset alumnos_raw  = import from "alumnos.csv"
dataset alumnos_foco = select alumno: int, asistencia: int, calificacion: int,
                              grupo: int, tareas: int, promedio: int
                       from alumnos_raw where promedio < 80

fact asistencia_critica = P(alumnos_foco.asistencia < 60)
fact p_reprob = P(alumnos_foco.promedio < 60 given alumnos_foco.asistencia < 60)
rule alerta :- asistencia_critica and p_reprob
query alerta
```

**¿Qué ocurre paso a paso?**

1. `import from` lee `alumnos.csv` y lo almacena como dataset crudo.
2. `select … from … where` filtra y tipa las columnas de interés.
3. Los `fact` calculan probabilidades sobre el dataset filtrado.
4. `rule alerta` se activa cuando ambos hechos se cumplen simultáneamente (AND lógico).
5. `query alerta` evalúa la regla e imprime el resultado con su nivel de confianza.

---

## Flujo general de trabajo

```
dataset  →  select / filter  →  fact  →  rule  →  query
```

1. **Importar datos** — cargar uno o más archivos CSV como datasets crudos.
2. **Preprocesar** — aplicar `select`, `from` y `where` para dar forma al dataset de trabajo.
3. **Declarar hechos** — calcular valores probabilísticos sobre columnas del dataset.
4. **Escribir reglas** — combinar hechos con operadores lógicos (`and`, `or`, `not`).
5. **Ejecutar consultas** — evaluar reglas/hechos y recibir una salida explicable.

---

## Pipeline de compilación

Los archivos fuente de Snaptics (`.snp`) pasan por un pipeline de múltiples etapas que genera código ensamblador 8086 ejecutable en emu8086:

```
.snp ──► lexer ──► parser ──► semántico ──► CSV staging ──► IR ──► optimizer ──► codegen ──► .asm
```

| Etapa | Módulo | Responsabilidad |
|---|---|---|
| Léxico | `lexer.py` | Tokeniza el fuente, reporta errores `LEX-xxx` |
| Sintáctico | `parser.py` | Construye el AST y la tabla de símbolos, reporta errores `SYN-xxx` |
| Semántico | `semantic/` | Verifica tipos, resuelve símbolos, reporta errores `SEM-xxx` |
| CSV staging | `codegen/csv_stager.py` | Copia los CSVs al `vdrive\` de emu8086 |
| IR | `ir_generator.py` | Convierte el AST a cuádruplas |
| Optimización | `optimizer/` | Constant folding, propagación, simplificación lógica |
| Generación de código | `codegen/` | Emite el `.asm` final para 8086 |

---

## Conceptos clave

### Dataset
Tabla de datos con nombre, importada desde un CSV y opcionalmente filtrada con `select … from … where`.

### Hecho (*fact*)
Enunciado probabilístico evaluado sobre la columna de un dataset. Siempre produce un valor `real` en el rango `[0.0, 1.0]`.

```snaptics
fact ventas_altas = P(ventas.monto > 500)
```

### Regla (*rule*)
Combinación lógica de hechos que evalúa a un booleano (`true` / `false`).

```snaptics
rule baja_rentabilidad :- ventas_altas < 0.5 and margen_bajo > 0.3
```

### Consulta (*query*)
Directiva que evalúa una regla o hecho e imprime una conclusión en lenguaje natural:

```snaptics
query baja_rentabilidad
query baja_rentabilidad explain   -- incluye la cadena de razonamiento
query baja_rentabilidad why       -- explica qué hechos contribuyeron
```

---

## ¿A dónde ir después?

| Tema | Guía |
|---|---|
| Configurar el entorno | [Instalación](installation.md) |
| Referencia de sintaxis | [Sintaxis](syntax.md) |
| Tipos de datos y sistema de tipado | [Tipos](types.md) |
| Funciones y operadores integrados | [Funciones](functions.md) |
| Trabajo con archivos CSV | [Procesamiento de CSV](csv-processing.md) |
| Entender la salida en ensamblador | [Salida en ensamblador](assembly-output.md) |
