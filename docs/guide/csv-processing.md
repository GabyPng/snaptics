# Procesamiento de CSV

Snaptics trabaja con archivos CSV como fuente de datos. Esta guía cubre el formato esperado, el mecanismo de *staging* hacia emu8086 y las validaciones que realiza el compilador.

---

## Formato del CSV

Los archivos CSV que Snaptics consume deben cumplir el siguiente contrato:

- **Sin fila de encabezado.** Las columnas se identifican por posición, en el mismo orden que el `select`.
- **Separador:** coma (`,`).
- **Codificación:** UTF-8.
- **Sin comillas** alrededor de los valores, a menos que el campo contenga una coma.
- Los valores numéricos no llevan símbolo de moneda ni separador de miles.

### Ejemplo

Para un `select` con columnas `alumno: int, asistencia: int, promedio: int`:

```
1,85,72
2,45,58
3,92,90
4,30,41
```

Ver [`samples/CSV_FORMAT.md`](../../samples/CSV_FORMAT.md) para la especificación completa.

---

## Importar un CSV

```snaptics
dataset nombre = import from "ruta/al/archivo.csv"
```

- La ruta es relativa al directorio del archivo `.snp` que contiene la sentencia.
- El compilador verifica la existencia del CSV en tiempo de compilación y emite **SEM-303** si no lo encuentra.

```snaptics
dataset alumnos_raw = import from "alumnos.csv"
dataset ventas_raw  = import from "../datos/ventas.csv"
```

---

## Filtrar con `select … from … where`

Una vez importado el CSV crudo, se aplica `select` para seleccionar columnas y opcionalmente filtrar filas:

```snaptics
dataset alumnos_foco = select alumno: int, asistencia: int, promedio: int
                       from alumnos_raw
                       where promedio < 80
```

- Solo las columnas listadas en `select` estarán disponibles para `fact` y expresiones posteriores.
- La cláusula `where` es opcional; sin ella se incluyen todas las filas.
- Las columnas deben declararse **en el mismo orden** que aparecen en el CSV.

---

## Mecanismo de staging hacia emu8086

emu8086 sandboxea el acceso a archivos contra su carpeta `vdrive\`. Para que el `.asm` generado pueda leer los CSVs, el compilador realiza **staging automático**:

1. Detecta cada `import from "..."` en el programa.
2. Copia el CSV referenciado a `<emu8086>\vdrive\C\snaptics_data\`.
3. Reescribe la ruta en el `.asm` generado a la forma DOS equivalente.

Este proceso lo ejecuta el módulo `codegen/csv_stager.py` y es transparente para el programador.

### Ruta resultante en el `.asm`

```asm
; Ruta original en .snp: "alumnos.csv"
; Ruta reescrita en .asm:
mov dx, offset filename_alumnos
; filename_alumnos db 'C:\snaptics_data\alumnos.csv', 0
```

---

## Configuración de la ruta de emu8086

El *stager* necesita conocer dónde está instalado emu8086 para copiar los CSVs. Se configura en orden de precedencia:

1. Variable de entorno `SNAPTICS_EMU8086_HOME`
2. Campo `"emu8086_home"` en `config.json`
3. Valor por defecto: `C:\emu8086`

```json
{
    "emu8086_home": "C:\\emu8086"
}
```

---

## Errores relacionados con CSV

| Código | Descripción | Solución |
|---|---|---|
| **SEM-303** | El archivo CSV indicado en `import from` no existe en el sistema de archivos | Verifica la ruta y que el archivo exista |
| **SEM-204** | Columna usada sin tipo declarado en el `select` | Añade la anotación de tipo (`col: int`) |

### Ejemplo de SEM-303

```snaptics
-- Si "ventas.csv" no existe en el directorio del .snp:
dataset ventas = import from "ventas.csv"
-- Error: SEM-303 — archivo 'ventas.csv' no encontrado
```

---

## Múltiples datasets

Un programa puede importar y usar múltiples CSVs. Cada dataset es independiente:

```snaptics
dataset alumnos = import from "alumnos.csv"
dataset grupos  = import from "grupos.csv"

dataset alumnos_riesgo = select alumno: int, asistencia: int, promedio: int
                         from alumnos where promedio < 70

fact riesgo_reprobacion = P(alumnos_riesgo.promedio < 60)
fact grupos_pequenos    = P(grupos.tamano < 10)

rule alerta_general :- riesgo_reprobacion and grupos_pequenos
query alerta_general
```

---

## Buenas prácticas

- **Nombra los datasets descriptivamente:** `ventas_raw` para el CSV importado, `ventas_foco` para el dataset filtrado.
- **Siempre declara tipos en `select`:** evita `SEM-204` y permite al compilador verificar operaciones.
- **Coloca los CSVs junto al `.snp`** o en una subcarpeta `data/` para que las rutas relativas sean predecibles.
- **No modifiques manualmente el CSV** en `vdrive\`; el *stager* lo sobreescribe en cada compilación.
