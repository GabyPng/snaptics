# Generación de Código — `codegen`

Este documento cubre las dos últimas fases del compilador de Snaptics:

| Módulo | Responsabilidad |
|---|---|
| `codegen/build.py` | Orquestador. Corre el pipeline completo y une todas las piezas en un único `.asm` |
| `codegen/code_generator.py` | Generador. Traduce la IR optimizada a instrucciones 8086 para emu8086 |

---

## Lugar en el pipeline

```
Fuente .snp
    │
    ▼
  Lexer          → tokens
    │
    ▼
  Parser         → AST + symbol_table
    │
    ▼
  Semantic       → AST anotado, errores semánticos
    │
    ▼
  IR Generator   → lista de Quadruples
    │
    ▼
  Optimizer      → lista de Quadruples optimizados
    │
    ▼
  CodeGenerator  ──────────────────────────────►  esqueleto .asm
  CountGenerator ──────────────────────────────►  rutinas count_<fact>
    │
    ▼
  build._stitch  → programa .asm final, autocontenido
```

El programa `.asm` resultante está pensado para abrirse en **emu8086** y ensamblarse con **F5**.

---

## `build.py` — El orquestador

### Función pública: `compile_snaptics`

```python
def compile_snaptics(
    source: str,
    source_path: str | None = None,
    output_basename: str | None = None
) -> dict
```

Ejecuta el pipeline **completo** desde texto fuente hasta `.asm`. Devuelve un diccionario normalizado:

```python
# Éxito
{'ok': True,  'asm': '<contenido del programa .asm>'}

# Error en alguna etapa
{'ok': False, 'stage': 'lex' | 'parse' | 'semantic' | 'stage_csv'
                             | 'ir' | 'opt' | 'codegen' | 'count_generator',
              'errors': [...]}
```

#### Fases en orden

| # | Llamada | Propósito |
|---|---|---|
| 1 | `lexer.tokenize(source)` | Genera tokens. Aborta si hay errores léxicos. |
| 2 | `syntax_parser.parse(source)` | Genera AST. Aborta en errores `SYN-*`. |
| 3 | `semantic_analyze(pr, source_path)` | Valida tipos, referencias, existencia del CSV. |
| 4 | `stage_csvs_in_ast(pr['ast'], source_path)` | Copia el CSV al vdrive de emu8086 y reescribe la ruta en el AST al formato DOS que verá el ensamblador. |
| 5 | `generate_ir(sem, pr)` | Produce la lista de `Quadruple`. |
| 6 | `optimize_ir(ir)` | Plegado de constantes, propagación, etc. |
| 7 | `generate_code(opt, pr, output_log_path)` | Genera el esqueleto .asm y la sección `.DATA`. |
| 8 | `generate_counts(opt, pr)` | Genera las rutinas `count_<fact>` para cada fact derivado. |
| 9 | `_stitch(cg_asm, counts_asm)` | Une todo en un único bloque de texto `.asm`. |

#### Parámetros

- `source_path` — ruta del `.snp` en disco. Permite al analizador semántico resolver rutas relativas del `import from` (error `SEM-303`).
- `output_basename` — nombre (sin extensión) del archivo `.txt` que el programa ensamblado escribe en el vdrive durante su ejecución. Por defecto: `'queries'`.

---

### Función privada: `_stitch`

```python
def _stitch(codegen_asm: str, counts_asm: str) -> str
```

Inserta las partes adicionales **justo antes de `END INICIO`**, preservando la estructura del programa.

**Orden de inserción:**

```
[ esqueleto del codegen ]
[ rutinas count_<fact>  ]     ← generadas por CountGenerator (Carim)
[ lib/fuzzy_logic.asm   ]     ← fuzzy_and / fuzzy_or / fuzzy_not (Gibran)
[ lib/explain_helpers.asm ]   ← print_log_str / print_log_int / nav_pause
[ lib/output_devices.asm ]    ← show_result / print_int / show_led / show_traffic
[ lib/primitives.asm    ]     ← parse_int / skip_to_col_N / skip_to_eol
END INICIO
```

> **¿Por qué `explain_helpers` antes que `output_devices`?**  
> `output_devices.asm` llama internamente a `print_log_str`, `print_log_int` y `nav_pause`. Si esas rutinas no estuvieran definidas antes, el ensamblador reportaría "undefined symbol".

---

### Función privada: `_strip_data_dupes`

Algunos archivos `.lib` traen declaraciones `DB` de variables que el codegen ya emite en su propia sección `.DATA`. Si se incluyeran dos veces, el ensamblador arrojaría "duplicate symbol".

`_strip_data_dupes` recorre cada línea del archivo de librería y comenta las líneas que empiezan con cualquiera de los símbolos en `_DATA_DUPES`:

```python
_DATA_DUPES = ('msg_evid_baja', 'msg_evid_mod', 'msg_evid_alta')
```

Las líneas eliminadas se reemplazan por un comentario explicativo:
```asm
; (declaración movida a .DATA por build.py: msg_evid_baja)
```

---

### Función privada: `_read_text`

Lee un archivo `.asm` probando tres encodings en orden: `utf-8`, `cp1252`, `latin-1`. Si ninguno funciona, usa `utf-8` con `errors='replace'` para no detener el build por bytes corruptos en archivos editados en diferentes sistemas.

---

### CLI (`main`)

```bash
python build.py archivo.snp -o salida.asm
python build.py --demo
```

- Sin `-o`: la salida se escribe en `codegen/build/<basename>.asm`.
- `--demo`: usa un programa de prueba embebido sin necesitar archivo `.snp`.
- Imprime `[OK] -> ruta` + número de líneas generadas, o `[FAIL] etapa 'X'` con el detalle del error.

---

## `code_generator.py` — El generador

### Propósito

Traduce la lista de `Quadruple` (IR optimizada) a un programa 8086 ensambable en emu8086. Produce **dos cosas**:

1. El texto del programa `.asm` (sección `.DATA` + sección `.CODE` + esqueleto `INICIO/fin/error_archivo`).
2. Metadatos para el `count_generator`: qué facts existen, qué columna leen, qué condición evalúan y si su dataset tiene filtro `WHERE`.

---

### Clase `CodeGenerator`

#### Constructor

```python
CodeGenerator(
    symbol_table = None,
    dataset_path: str | None = None,
    output_log_path: str | None = None
)
```

| Parámetro | Descripción |
|---|---|
| `symbol_table` | Tabla de símbolos del parser. Permite saber si un nombre es `fact`, `rule`, `dataset`, etc. |
| `dataset_path` | Ruta DOS del CSV. Default: `C:\emu8086\vdrive\C\dataset.txt` |
| `output_log_path` | Ruta DOS del `.txt` de log. Default: `C:\emu8086\vdrive\C\output\queries.txt` |

#### Método principal: `generate`

```python
def generate(self, quadruples: list[Quadruple]) -> str
```

Ejecuta los dos pasos en orden y devuelve el `.asm` completo:

```
1. _reset()       → limpia estado interno
2. _analyze()     → Pase 1: clasifica toda la IR en estructuras internas
3. _emit_code()   → Pase 2a: genera la sección .CODE (registra mensajes auxiliares)
4. _emit_data()   → Pase 2b: genera la sección .DATA (incluye mensajes auxiliares ya registrados)
5. _assemble()    → une .DATA + .CODE en el texto final
```

> **Orden importa:** `.CODE` se emite antes que `.DATA` porque los emisores de `explain`/`why` registran mensajes DB en `self._aux_msgs` al construir las instrucciones. Esos mensajes se vuelcan a `.DATA` al final.

---

### Pase 1: `_analyze`

Recorre cada `Quadruple` de la IR y clasifica su contenido en las estructuras internas:

| Estructura | Tipo | Contenido |
|---|---|---|
| `facts_literal` | `dict[str, int]` | Facts con valor constante (resueltos por el optimizer). El valor está escalado 0..100. |
| `facts_derived` | `dict[str, dict]` | Facts que se calculan leyendo el CSV en runtime. |
| `rules` | `list[str]` | Nombres de reglas en orden de aparición. |
| `queries` | `list[tuple]` | Pares `(nombre, nivel)` donde nivel ∈ `{basic, explain, why}`. |
| `rule_structures` | `dict[str, dict]` | Árbol AST reconstruido de cada regla (para explain/why). |
| `datasets_with_filter` | `dict[str, dict]` | Datasets con cláusula `WHERE`. Contiene la condición del filtro. |
| `column_aliases` | `dict[str, str]` | `tN → nombre_columna`. Resuelve `MEMBER_ACCESS`. |
| `column_datasets` | `dict[str, str]` | `tN → nombre_dataset`. Sabe a qué dataset pertenece cada columna. |
| `absorbed_cmp_temps` | `set[str]` | Temporales de comparación que son condición de un `PROB` o `PROB_GIVEN`. No se emiten como instrucciones ASM separadas. |
| `temps` | `set[str]` | Todos los temporales `tN` referenciados; reservan slots `DW` en `.DATA`. |

#### Operaciones ignoradas en análisis (`_NOOP_OPS`)

- `SELECT` — solo declara columnas (metadatos para el semantic/IR, sin efecto en runtime).
- `MEMBER_ACCESS` — resuelve `dataset.columna` a un temporal; el codegen lo absorbe mapeando ese temporal al nombre real de la columna.

#### Operaciones fuera de alcance v1 (`_UNSUPPORTED_OPS`)

Generan error `GEN-001` y se registran pero no detienen la compilación:
`MEAN`, `VARIANCE`, `STDDEV`, `CORRELATION`, `AUTO_DISCOVER`, `ADD`, `SUB`, `MUL`, `DIV`, `POW`, `UNARY_MINUS`, `UNARY_PLUS`.

---

### Clasificación de facts derivados

Cuando `_analyze` encuentra `ASSIGN fact_X = tN`, llama a `_classify_assign`, que intenta dos patrones de búsqueda hacia atrás en la IR:

#### Fact simple — `_trace_fact_condition`

Busca el patrón:
```
<CMP_OP>  col_temp  valor   t_cmp
PROB      t_cmp     _       tN
```
Si lo encuentra, registra `{col, op, value, ir_op, jump, jump_neg, dataset, kind: 'simple'}`.

#### Fact condicional — `_trace_fact_given`

Busca el patrón:
```
<CMP_A>     col_a  val_a  t_a
<CMP_B>     col_b  val_b  t_b
PROB_GIVEN  t_a    t_b    tN
```
Donde `arg1 = A` (numerador) y `arg2 = B` (denominador).
Registra `{col_a, op_a, value_a, jump_a_neg, col_b, op_b, value_b, jump_b_neg, dataset, kind: 'given'}`.

---

### Reconstrucción del árbol de regla — `_build_rule_tree`

Para cada `RULE_DEF`, recorre la IR hacia atrás desde el temporal asignado y reconstruye el árbol estructural de la regla:

```python
# Nodos posibles
{'kind': 'logic',    'op': 'AND'|'OR'|'NOT',  'left': ..., 'right': ...}
{'kind': 'cmp',      'op': 'GT'|'LT'|...,     'sym': '>',  'left': ..., 'right': ...}
{'kind': 'fact_ref', 'name': 'nombre_del_fact'}
{'kind': 'literal',  'value': 0.3}
{'kind': 'unknown',  'value': ...}
```

Este árbol se usa para:
- Serializar la expresión en texto legible (`_serialize_rule_expr`)
- Recolectar las referencias a facts (`_collect_fact_refs`)
- Recolectar las comparaciones crisp (`_collect_cmps`)

---

### Pase 2a: `_emit_code`

Genera la sección `.CODE` del programa. Estructura emitida:

```asm
; 1) Abrir archivo de log
CALL open_log_file

; 2) Apertura y lectura del CSV (solo si hay facts derivados)
abrirArchivo 2, RUTA
MOV ID_ARCHIVO, AX
JC error_archivo
leerArchivo 4096, BUFFER, ID_ARCHIVO
JC error_archivo
MOV BYTES_LEIDOS, AX

; 3) Cálculo de facts (una CALL por cada fact derivado)
CALL count_asistencia_critica
CALL count_p_reprob_dada_asistencia_baja
...

; 4) Evaluación de reglas y queries (traducción quad por quad)
; AND, OR, NOT → CALL fuzzy_and / fuzzy_or / fuzzy_not
; RULE_DEF    → MOV rule_X, AX
; QUERY       → switch_to_page + show_result / pantalla explain / pantalla why
; comparaciones crisp → booleano 0/100

; 5) Navegación y cierre
MOV BYTE PTR max_page, N
CALL final_nav_loop
CALL close_log_file
```

#### Traducción de cuádruplas (`_emit_quad`)

| Operación IR | Emisión ASM |
|---|---|
| `AND` | `MOV AX,arg1; MOV BX,arg2; CALL fuzzy_and; MOV result,AX` |
| `OR` | Igual con `fuzzy_or` |
| `NOT` | `MOV AX,arg1; CALL fuzzy_not; MOV result,AX` |
| `RULE_DEF` | `MOV AX,arg1; MOV rule_X,AX` |
| `QUERY` | Cambia de página de video + cuerpo básico |
| `QUERY_EXPLAIN` | Cambia de página + cuerpo explain |
| `QUERY_WHY` | Cambia de página + cuerpo why |
| `ASSIGN tN` | `MOV AX,arg1; MOV tN,AX` (solo si el destino es temporal real) |
| `<CMP_OP>` no absorbido | Booleano crisp: `CMP; J→true(100)/false(0)` |
| `<CMP_OP>` absorbido | `None` (lo maneja `count_<fact>`) |
| `PROB`, `PROB_GIVEN`, `LOAD_DATASET`, `FILTER` | `None` (absorbidos en `_analyze`) |

---

### Paginación en emu8086

emu8086 tiene **4 páginas de video** (0..3), accesibles con `INT 10h`. El codegen asigna una página a cada pantalla emitida:

```python
page = self._screen_counter % 4   # wrap: 0,1,2,3,0,1,...
self._screen_counter += 1
```

Con más de 4 pantallas, se reutilizan páginas (las anteriores se sobreescriben en la pantalla), pero el archivo `.txt` de log captura todo el output sin límite.

Tras todas las pantallas, `final_nav_loop` habilita navegación interactiva con flechas `←/→` entre páginas.

---

### Pase 2b: `_emit_data`

Genera la sección `.DATA`. Variables emitidas en orden:

| Variable | Tipo | Descripción |
|---|---|---|
| `RUTA` | `DB` | Ruta DOS del CSV (null-terminated) |
| `ID_ARCHIVO` | `DW` | Handle del archivo abierto |
| `BUFFER` | `DB 4096 DUP(0)` | Buffer de lectura del CSV |
| `BYTES_LEIDOS` | `DW` | Bytes leídos en la última operación |
| `fact_X` | `DW 0` | Valor 0..100 de cada fact derivado |
| `fact_X_cnt` | `DW 0` | Filas que cumplen la condición (para explain/why) |
| `fact_X_tot` | `DW 0` | Total de filas evaluadas |
| `fact_X` (literal) | `DW N` | Valor constante (ya resuelto por optimizer) |
| `rule_X` | `DW 0` | Resultado de evaluación de cada regla |
| `tN` | `DW 0` | Temporales del IR |
| `msg_X` | `DB 'X = $'` | Mensaje de cada query |
| `msg_evid_*` | `DB ...` | Textos de nivel de evidencia (BAJA/MODERADA/ALTA) |
| `msg_continuar` | `DB ...` | Prompt "Presiona una tecla..." |
| `msg_err_file` | `DB ...` | Mensaje de error al abrir el dataset |
| `OUTPUT_PATH` | `DB ...` | Ruta del `.txt` de log (null-terminated) |
| `cur_page / max_page` | `DB 0` | Control de paginación |
| `nav_prompt` | `DB ...` | Texto del prompt de navegación por flechas |
| `itoa_buf` | `DB ...` | Buffer temporal para convertir entero a texto |
| `msg_true / msg_false` | `DB ...` | Textos ` SE CUMPLE` / ` NO SE CUMPLE` |
| Mensajes auxiliares | `DB ...` | Cadenas generadas por explain/why (labels `em0`, `em1`, ...) |

> **`BUFFER` se inicializa con `DUP(0)`, no con espacios.** `skip_to_eol` usa `0` como guardia de fin de buffer. Con espacios, el loop no terminaría si el CSV no cierra con `LF`.

---

### Salidas de explain y why

#### Pantalla `basic`

```
<target> = <val>%
Evidencia: ALTA | MODERADA | BAJA
>> Presiona una tecla para continuar...
```

Emitida por `_emit_basic_body`. Llama a `show_result` que maneja todo internamente.

---

#### Pantalla `explain` — `_emit_explain_body`

```
=========================================================
  EXPLAIN: alerta_general = 75%
=========================================================
 HECHOS:
   asistencia_critica = 60%
     6 de 10 alumnos de alumnos_foco cumplen asistencia_porcentaje < 60.
   tareas_insuficientes = 80%
     8 de 10 alumnos de alumnos_foco cumplen calificacion_tareas < 70.
 REGLA:
   alerta_general := (asistencia_critica > 30 or tareas_insuficientes > 40)
 EVALUACION:
   asistencia_critica = 60% (umbral > 30%) -> SE CUMPLE
   tareas_insuficientes = 80% (umbral > 40%) -> SE CUMPLE
   OR: basta que una condicion se cumpla para que la regla se active.
 CONCLUSION: alerta_general = 75%
=========================================================
```

**Flujo del emisor:**
1. Encabezado con separadores y valor actual (runtime) de `target`.
2. Bloque `HECHOS:` — recorre `_collect_fact_refs(tree)` y emite `_emit_fact_lectura` por cada fact.
3. Bloque `REGLA:` — serializa el árbol con `_serialize_rule_expr`.
4. Bloque `EVALUACION:` — recorre `_collect_cmps(tree)` y emite `_emit_cmp_eval` por cada comparación.
5. Línea explicativa del operador raíz (OR/AND).
6. Conclusión con valor runtime de `target`.

---

#### Pantalla `why` — `_emit_why_body`

```
=========================================================
  WHY: alerta_general = 75%
=========================================================
 Origen: alumnos_foco (alumnos con promedio_parcial < 80)
 HECHO 1: asistencia_critica
   asistencia_critica = 60%
     6 de 10 alumnos de alumnos_foco cumplen asistencia_porcentaje < 60.
   Umbral exigido: > 30%. SE CUMPLE
 HECHO 2: tareas_insuficientes
   tareas_insuficientes = 80%
     8 de 10 alumnos de alumnos_foco cumplen calificacion_tareas < 70.
   Umbral exigido: > 40%. SE CUMPLE
 ---------------------------------------------------------
 RAZONAMIENTO:
   La regla combina los hechos con OR.
   Basta una condicion verdadera para activar la regla.
 FACTOR DECISIVO:
   La condicion con mayor cobertura es la que mas peso aporta:
   -> tareas_insuficientes: 8 de 10 alumnos cumplen.
 ---------------------------------------------------------
 CONCLUSION: alerta_general = 75%
=========================================================
```

**Flujo del emisor:**
1. Encabezado.
2. **Origen** (`_build_origen_text`): toma el dataset del primer fact con metadata y construye `"Origen: dataset (entidad con col op val)"`. Incluye la condición `WHERE` si el dataset tiene filtro registrado en `datasets_with_filter`.
3. **HECHOS** numerados: para cada fact, `_emit_fact_lectura` + `_emit_cmp_decision` (solo SE CUMPLE/NO SE CUMPLE sin repetir el valor y el umbral).
4. **RAZONAMIENTO**: texto estático según el operador raíz (`OR` / `AND` / expresión libre).
5. **FACTOR DECISIVO** (`_emit_factor_decisivo`): solo cuando hay exactamente 2 facts referenciados. Comparación en runtime: OR→gana el de mayor valor (`JG`), AND→gana el de menor valor (`JL`). Imprime los conteos crudos `_cnt` y `_tot` del fact ganador.
6. Conclusión.

---

### Helper: `_emit_fact_lectura`

Emite la "lectura natural" de un fact intercalando llamadas `print_log_int` con cadenas estáticas DB:

**Forma simple** (`kind == 'simple'`):
```
<fact> = <pct>%
  <cnt> de <tot> <entidad> de <dataset> cumplen <col> <op> <val>.
```
Ejemplo: `asistencia_critica = 60%  /  6 de 10 alumnos de alumnos_foco cumplen asistencia_porcentaje < 60.`

**Forma condicional** (`kind == 'given'`):
```
<fact> = <pct>%
  de los <tot> <entidad> de <dataset> con <col_b> <op_b> <val_b>,
  <cnt> tambien cumplen <col_a> <op_a> <val_a>.
```
Ejemplo: `p_reprob_dada_asistencia_baja = 100%  /  de los 8 alumnos de alumnos_foco con asistencia_porcentaje < 60, 8 tambien cumplen promedio_parcial < 60.`

El sustantivo de entidad (`alumnos`, `ventas`, ...) se deriva con `_entity_noun`:
```python
'alumnos_foco' → 'alumnos'
'ventas_norte' → 'ventas'
'datos'        → 'datos'
''             → 'registros'
```

---

### Helper: `_emit_cmp_eval`

Imprime `<fact> = <val>% (umbral <sym> <th>%) -> SE CUMPLE / NO SE CUMPLE` con decisión en **runtime**:

```asm
LEA SI, em12                  ; "<fact> = "
CALL print_log_str
MOV AX, fact_asistencia_critica
CALL print_log_int
LEA SI, em13                  ; "% (umbral > 30%) ->"
CALL print_log_str
MOV AX, fact_asistencia_critica
CMP AX, 30
JG  xt_0
LEA SI, msg_false
CALL print_log_str
JMP xd_0
xt_0:
LEA SI, msg_true
CALL print_log_str
xd_0:
```

---

### Convención de registros (acuerdo de equipo)

| Registro | Uso |
|---|---|
| `AX` | Probabilidad en tránsito (entero 0..100). Volátil. |
| `BX` | Segundo operando para fuzzy. Volátil. |
| `CX`, `DX`, `SI`, `DI` | Preservados por todas las rutinas auxiliares con push/pop. |

Las probabilidades viajan siempre como enteros 0..100. Los literales 0.0..1.0 del fuente Snaptics se escalan con `_scale(value)` que aplica `int(round(v * 100))`.

---

### Tabla de mapeo IR → salto ASM (`_CMP_OP_INFO`)

| Op IR | Salto "si verdadero" | Salto "si falso" | Símbolo Snaptics |
|---|---|---|---|
| `GT` | `JG` | `JLE` | `>` |
| `LT` | `JL` | `JGE` | `<` |
| `EQ` | `JE` | `JNE` | `==` |
| `NEQ` | `JNE` | `JE` | `!=` |
| `LEQ` | `JLE` | `JG` | `<=` |
| `GEQ` | `JGE` | `JL` | `>=` |

El "salto si falso" (`jump_neg`) es lo que usan las plantillas `count_<fact>` de Carim: si la condición **no** se cumple, se salta la fila sin contarla.

---

### Errores de generación

| Código | Condición |
|---|---|
| `GEN-001` | Operación de IR fuera del alcance v1 (`MEAN`, `AUTO_DISCOVER`, etc.) |
| `GEN-002` | Operación de IR completamente desconocida |
| `GEN-101` | No se pudo trazar la condición de un fact (ni `PROB` ni `PROB_GIVEN` encontrados) |

Los errores no abortan la generación: el `.asm` se emite igual (posiblemente parcial) con los errores como comentarios al inicio del archivo.

---

### Función pública: `generate_code`

```python
def generate_code(
    opt_result: dict,
    parse_result: dict | None = None,
    dataset_path: str | None = None,
    output_log_path: str | None = None
) -> dict
```

Punto de entrada del módulo. Crea un `CodeGenerator`, llama a `generate()` y devuelve:

```python
{
    'asm':           str,          # programa .asm completo
    'success':       bool,         # True si no hubo errores GEN-*
    'errors':        list[str],    # mensajes formateados de CodeGenError
    'derived_facts': dict,         # metadatos planos para uso legacy
    'metadata':      dict,         # metadatos completos para CountGenerator
}
```

El campo `metadata` tiene la forma:
```python
{
    'datasets': {
        'alumnos_foco': {
            'filter': {'col': 'promedio_parcial', 'op': '<', 'value': 80, 'jump': 'JL'}
        }
    },
    'facts': {
        'asistencia_critica': {
            'kind': 'simple', 'dataset': 'alumnos_foco',
            'col': 'asistencia_porcentaje', 'op': '<', 'value': 60, 'jump_neg': 'JGE'
        },
        'p_reprob_dada_asistencia_baja': {
            'kind': 'given', 'dataset': 'alumnos_foco',
            'col_a': 'promedio_parcial',   'op_a': '<', 'value_a': 60, 'jump_a_neg': 'JGE',
            'col_b': 'asistencia_porcentaje', 'op_b': '<', 'value_b': 60, 'jump_b_neg': 'JGE',
        }
    }
}
```

`CountGenerator` usa `metadata` para saber qué plantilla instanciar (`simple` vs `given`) y si inyectar un `where pre-check` en el loop de conteo.

---

## Resumen de responsabilidades

```
build.py
  └── compile_snaptics()   ← API pública que usa la IDE y los tests
        ├── Llama a cada fase en orden y aborta en el primer error
        ├── Coordina stage_csvs_in_ast (copiar CSV al vdrive)
        └── _stitch() ← ensambla el .asm final

code_generator.py
  └── CodeGenerator.generate()
        ├── _analyze()     ← Pase 1: clasifica la IR sin emitir nada
        ├── _emit_code()   ← Pase 2: traduce quad por quad, emite .CODE
        ├── _emit_data()   ← Pase 2: declara variables, emite .DATA
        └── _assemble()    ← concatena todo en el string final
```
