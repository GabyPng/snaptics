# Programas Snaptics

Programas de ejemplo para mostrar el compilador end-to-end, con su
dataset asociado. El `.asm` resultante de compilarlos se escribe en
`../build/`.

## Archivos

| Archivo                | Qué es                                                  |
|------------------------|---------------------------------------------------------|
| `alumnos_riesgo.snp`   | Programa Snaptics: análisis de riesgo de reprobación    |
| `alumnos.csv`          | Dataset de 10 alumnos, 6 columnas, sin encabezado       |

## Cómo correr la demo

1. Copia `alumnos.csv` a la ruta que aparece en el `import from` del
   `.snp`. Por defecto:
   ```
   C:\emu8086\vdrive\C\alumnos.csv
   ```

2. Compila y arma el `.asm`:
   ```powershell
   python build.py programs/alumnos_riesgo.snp
   ```
   El archivo se guarda en `build/alumnos_riesgo.asm`.

3. Abre ese `.asm` en emu8086 y presiona **F5**.

4. Salida esperada con el CSV provisto:
   - Consola DOS: `alerta = 62`, `Evidencia: MODERADA`
   - LED display: `00062`
   - Semáforo:    luz amarilla

## Sobre el CSV

`alumnos.csv` no tiene fila de encabezado. Las columnas, en orden, son:

| Idx | Columna       |
|-----|---------------|
| 0   | alumno        |
| 1   | asistencia    |
| 2   | calificacion  |
| 3   | grupo         |
| 4   | tareas        |
| 5   | promedio      |

El SELECT del programa Snaptics declara estos mismos seis nombres en
ese mismo orden, así Carim sabe a qué índice corresponde cada uno
sin tener que adivinar.
