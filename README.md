# snaptics

Lenguaje declarativo orientado al razonamiento lógico-probabilístico. Toma
datos tabulares, declara *hechos* y *reglas* con probabilidades asociadas y
deriva *consultas* explicables. El pipeline compila a ensamblador 8086
que corre en emu8086.

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

## Instalación

### Opción 1 — conda (recomendado)

```bash
conda create -n snaptics python=3.11 ply pandas numpy scipy matplotlib seaborn jupyterlab
conda activate snaptics
pip install PyQt6
```

### Opción 2 — pip + venv

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
```

### Requisito adicional (solo para generar y correr `.asm`)

[emu8086](https://emu8086-microprocessor-emulator.en.softonic.com/) instalado.
Por defecto se asume `C:\emu8086`. Si está en otra ruta, ver la sección
*Configuración*.

## Ejecutar la IDE

```bash
python ide/main.py
```

Atajo principal: **F9** para compilar el `.snp` abierto. Los resultados de
cada fase (tokens, AST, IR, IR optimizada) aparecen en las pestañas
laterales y la terminal integrada.

## Compilar a ensamblador (CLI)

```bash
python codegen/build.py samples/demo/alumnos_riesgo.snp -o build/alumnos.asm
```

El `.asm` generado se abre directamente en emu8086 y se ensambla con F5.

```bash
python codegen/build.py --demo    # corre un programa de prueba embebido
```

## Pipeline de compilación

```
.snp ──► lexer ──► parser ──► semántico ──► CSV staging ──► IR ──► optimizer ──► codegen ──► .asm
```

| Etapa            | Módulo                              | Qué hace                                                       |
|------------------|-------------------------------------|----------------------------------------------------------------|
| Léxico           | `lexer.py`                          | Tokens y errores `LEX-xxx`                                     |
| Sintáctico       | `parser.py`                         | AST + tabla de símbolos, errores `SYN-xxx`                     |
| Semántico        | `semantic/`                         | Tipos, redeclaraciones, datasets/columnas, errores `SEM-xxx`   |
| CSV staging      | `codegen/csv_stager.py`             | Copia CSVs al `vdrive\` de emu8086 (ver más abajo)             |
| IR               | `ir_generator.py`                   | Cuádruplas                                                     |
| Optimización     | `optimizer/`                        | Constant folding/propagation, simplificación lógica, etc.      |
| Generación       | `codegen/code_generator.py`, `count_generator.py` | `.asm` 8086 final |

## Importación de CSVs y configuración de emu8086

emu8086 sandboxea el acceso a archivos contra su carpeta `vdrive\`, así que
el `.asm` solo puede leer archivos que vivan dentro de ese árbol. Para que
el `.snp` pueda apuntar a cualquier ubicación del disco, el build hace
*staging* automático: copia cada CSV referenciado por `import from "..."`
a `<emu8086>\vdrive\C\snaptics_data\` y reescribe el path en el `.asm` a la
forma DOS equivalente.

### Configuración de la ruta de emu8086

La ubicación de emu8086 se determina (en orden de precedencia):

1. Variable de entorno `SNAPTICS_EMU8086_HOME`.
2. Campo `"emu8086_home"` en `config.json` de la raíz del proyecto.
3. Default `C:\emu8086`.

Para configurarlo a nivel proyecto (recomendado), edita
[`config.json`](config.json):

```json
{
    "theme": "dark",
    "emu8086_home": "C:\\emu8086"
}
```

> Nota: en JSON las barras invertidas se duplican (`\\`).

### Verificación en tiempo de compilación

El semántico reporta `SEM-303` si el archivo CSV referenciado en
`import from` no existe en el filesystem real. Las rutas relativas se
resuelven contra el directorio del `.snp`.

### Formato del CSV

Sin fila de encabezado y con las columnas en el mismo orden que el
`select`. Ver [`samples/CSV_FORMAT.md`](samples/CSV_FORMAT.md) para el
contrato completo.

## Estructura del proyecto

```
snaptics/
├── ide/                   # IDE en PyQt6
│   ├── main.py            # Entry point
│   └── ui/                # Widgets, ventana principal, controladores
├── lexer.py               # Análisis léxico (PLY)
├── parser.py              # Análisis sintáctico (PLY), AST y tabla de símbolos
├── symbol_table.py        # Tabla de símbolos
├── semantic/              # Análisis semántico (SEM-1xx/2xx/3xx/4xx/5xx)
├── ir_generator.py        # AST → cuádruplas
├── optimizer/             # Pases de optimización sobre la IR
├── codegen/               # IR → ensamblador 8086
│   ├── build.py           # CLI para compilar a .asm
│   ├── code_generator.py  # Esqueleto principal del .asm
│   ├── count_generator.py # Rutinas count_<fact> que leen el CSV
│   ├── csv_stager.py      # Copia CSVs al vdrive y reescribe rutas
│   └── lib/               # Librerías .asm (fuzzy_logic, output_devices, primitives)
├── samples/               # Programas .snp de ejemplo y CSVs
├── tests/                 # Tests
├── config.json            # Configuración del proyecto (tema, emu8086_home)
└── requirements.txt
```

## Atajos de teclado de la IDE

### Archivo
- `Ctrl+N` — Nuevo archivo
- `Ctrl+O` — Abrir archivo
- `Ctrl+S` — Guardar
- `Ctrl+Shift+S` — Guardar como
- `Ctrl+Q` — Salir

### Edición
- `Ctrl+Z` — Deshacer
- `Ctrl+Y` — Rehacer
- `Ctrl+C` — Copiar
- `Ctrl+V` — Pegar

### Compilación y vistas
- `F9` — Compilar (léxico + sintáctico + semántico + IR + optimización)
- `Ctrl+T` — Pestaña de tokens
- `Ctrl+J` — Alternar terminal integrada
- `Ctrl+H` — Acerca de

### Temas
- `F12` — Alternar entre tema claro y oscuro

## Organización de la GUI

- **`ide/main.py`**: punto de entrada que arranca PyQt6 y la ventana principal.
- **`ide/ui/`**: paquete con toda la interfaz gráfica:
  - `ui_base.py` — definición pura de widgets.
  - `main_window.py` — ventana principal con la lógica del IDE.
  - Controladores específicos: `terminal_controller.py`, `file_manager.py`,
    `theme_manager.py`, `tokens_panel.py`, `errors_panel.py`.

## Licencia

Ver archivo [LICENSE](LICENSE).
