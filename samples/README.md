# samples — programas Snaptics de ejemplo

Programas en Snaptics organizados por propósito. Todo `.snp` del repo
vive en alguna subcarpeta de aquí.

## Estructura

```
samples/
├── demo/         ← lo que se presenta al profesor (el caso "estrella")
├── basic/        ← ejemplos generales del lenguaje (sin nada raro)
├── errors/       ← programas con errores intencionales (para probar léxico/sintáctico/semántico)
└── optimizer/    ← programas con redundancias o construcciones que ejercitan al optimizador
```

## Contenido actual

| Carpeta        | Archivo                       | Qué demuestra |
|----------------|-------------------------------|---|
| `demo/`        | `alumnos_riesgo.snp`          | Probabilidad condicional + filtro WHERE + regla AND |
| `demo/`        | `alumnos.csv`                 | Dataset de prueba (10 alumnos, 6 columnas sin header) |
| `basic/`       | `Ejemplo.snp`                 | Programa general de referencia |
| `basic/`       | `alumnosTEC.snp`              | Variante con datos del TEC |
| `errors/`      | `ErroresEj.snp`               | Errores comunes (léxicos / sintácticos) |
| `errors/`      | `erroresSemanticos.snp`       | Casos que disparan errores semánticos (símbolos no declarados, tipos) |
| `errors/`      | `pruebaTipos.snp`             | Casos específicos del type-checker |
| `optimizer/`   | `optimizacion.snp`            | Programa con redundancias para que el optimizer reduzca cuádruplas |

## Antes de escribir tu propio `.snp`

Lee [`CSV_FORMAT.md`](CSV_FORMAT.md). Documenta el contrato entre el
archivo `.csv` y el `select` del `.snp` (sin header, columnas en orden).
Si no se respeta, los conteos salen mal sin que el ensamblador te avise.

## Cómo correr la demo principal

1. Copia el CSV al vdrive de emu8086 (lo que dice el `import from` del `.snp`):
   ```powershell
   copy samples\demo\alumnos.csv C:\emu8086\vdrive\C\alumnos.csv
   ```

2. Compila:
   ```powershell
   python codegen/build.py samples/demo/alumnos_riesgo.snp
   ```

3. Abre `codegen/build/alumnos_riesgo.asm` en emu8086 y presiona **F5**.

4. Resultado esperado:
   - Consola DOS: `alerta = 62`, `Evidencia: MODERADA`
   - LED display: `00062`
   - Semáforo:    luz amarilla
