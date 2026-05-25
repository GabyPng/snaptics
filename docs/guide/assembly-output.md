# Salida en ensamblador

El compilador de Snaptics genera código ensamblador 8086 (`.asm`) compatible con emu8086. Esta guía explica la estructura del archivo generado, cómo ejecutarlo y cómo interpretar su salida.

---

## Visión general del pipeline de generación

```
IR (cuádruplas) ──► optimizer ──► code_generator.py ──► count_generator.py ──► .asm
```

| Módulo | Responsabilidad |
|---|---|
| `codegen/code_generator.py` | Genera el esqueleto principal del `.asm` (segmentos de datos, pila, código) |
| `codegen/count_generator.py` | Genera las rutinas `count_<fact>` que leen el CSV fila a fila y evalúan condiciones |
| `codegen/csv_stager.py` | Copia los CSVs al `vdrive\` de emu8086 y reescribe sus rutas en el `.asm` |
| `codegen/lib/` | Librerías `.asm` estáticas: `fuzzy_logic.asm`, `output_devices.asm`, `primitives.asm` |

---

## Compilar a ensamblador

### Desde la IDE

Presiona **F9** para ejecutar el pipeline completo. El `.asm` se genera automáticamente en el directorio de salida configurado.

### Desde la línea de comandos

```bash
python codegen/build.py samples/demo/alumnos_riesgo.snp -o build/alumnos.asm
```

```bash
# Ejecutar el programa de prueba embebido
python codegen/build.py --demo
```

---

## Estructura del archivo `.asm` generado

Un archivo `.asm` típico generado por Snaptics tiene la siguiente estructura:

```asm
; ============================================================
; Generado por Snaptics Compiler
; Fuente: alumnos_riesgo.snp
; ============================================================

.MODEL SMALL
.STACK 100h

.DATA
    ; --- Rutas de archivos CSV ---
    filename_alumnos db 'C:\snaptics_data\alumnos.csv', 0

    ; --- Buffers de lectura ---
    buffer           db 128 dup(?)
    newline          db 0Dh, 0Ah, '$'

    ; --- Contadores para probabilidades ---
    count_total      dw 0
    count_asistencia dw 0
    count_promedio   dw 0

    ; --- Resultados ---
    result_fact1     dw 0
    result_fact2     dw 0

.CODE
MAIN PROC
    ; Inicializar segmentos
    mov ax, @data
    mov ds, ax

    ; --- Leer CSV y evaluar condiciones ---
    call COUNT_ASISTENCIA_CRITICA
    call COUNT_P_REPROB

    ; --- Evaluar regla ---
    call EVAL_ALERTA

    ; --- Mostrar resultado ---
    call PRINT_RESULT

    ; Terminar programa
    mov ax, 4C00h
    int 21h
MAIN ENDP
```

---

## Rutinas `count_<fact>`

Para cada `fact` declarado en el programa, el generador crea una rutina que:

1. Abre el CSV correspondiente.
2. Lee el archivo línea a línea usando interrupciones DOS (`int 21h`).
3. Parsea cada fila y evalúa la condición del `fact`.
4. Acumula un contador de filas que cumplen la condición y el total de filas.
5. Calcula la proporción (aproximada en aritmética entera de 16 bits).

```asm
COUNT_ASISTENCIA_CRITICA PROC
    ; Abrir archivo
    mov ah, 3Dh
    mov al, 0
    lea dx, filename_alumnos
    int 21h

    ; ... leer y parsear filas ...

    ; Guardar resultado
    mov [count_asistencia], cx
    ret
COUNT_ASISTENCIA_CRITICA ENDP
```

---

## Librerías estáticas (`codegen/lib/`)

El código generado incluye o hace referencia a librerías `.asm` precompiladas:

| Librería | Propósito |
|---|---|
| `primitives.asm` | Operaciones básicas: lectura de archivo, parseo de enteros, salida a pantalla |
| `fuzzy_logic.asm` | Implementación de operadores `and`, `or`, `not` sobre valores probabilísticos escalados |
| `output_devices.asm` | Formateo y escritura de resultados en la terminal de emu8086 |

---

## Ejecutar el `.asm` en emu8086

1. Abre emu8086.
2. Ve a **File → Open** y selecciona el `.asm` generado.
3. Presiona **F5** (Assemble & Run).
4. El resultado aparece en la ventana de salida de emu8086.

### Requisito previo: staging del CSV

Antes de ejecutar, asegúrate de que el CSV ya fue copiado al `vdrive\` por el compilador. Si compilaste con `build.py` o con F9 en la IDE, el staging se hace automáticamente.

Si lo ejecutas manualmente, copia el CSV a:

```
C:\emu8086\vdrive\C\snaptics_data\
```

---

## Formato de la salida en pantalla

El programa imprime en la terminal de emu8086:

```
RESULTADO: alerta
Probabilidad: 0.73
Nivel de evidencia: MODERADO
```

Los niveles de evidencia son:

| Rango de probabilidad | Nivel |
|---|---|
| `>= 0.80` | ALTO |
| `>= 0.50` | MODERADO |
| `< 0.50` | BAJO |

---

## Limitaciones del objetivo 8086

La generación de código para 8086 tiene restricciones inherentes a la arquitectura:

| Limitación | Impacto |
|---|---|
| Aritmética entera de 16 bits | Las probabilidades se escalan a valores enteros (0–1000 para representar 0.000–1.000) |
| Sin punto flotante nativo | No se usa la FPU; se usa aritmética entera escalada |
| Memoria segmentada | Los buffers de lectura están limitados a 128 bytes por línea |
| Sin multitarea | Los CSVs se leen secuencialmente, un `fact` a la vez |

---

## Depuración del ensamblador generado

Para depurar el `.asm` en emu8086:

1. Usa **View → Registers** para inspeccionar el estado de los registros.
2. Coloca *breakpoints* con **F2** en las instrucciones clave.
3. Avanza instrucción a instrucción con **F8** (Step Into).
4. Inspecciona la memoria en **View → Memory**.

Para depurar a nivel Snaptics, compila con F9 en la IDE y revisa las pestañas de **IR** e **IR Optimizada** antes de analizar el `.asm`.
