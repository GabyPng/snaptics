# Instalación

Esta guía explica cómo configurar el entorno de desarrollo para Snaptics en Windows.

---

## Requisitos previos

| Requisito | Versión mínima | Notas |
|---|---|---|
| Python | 3.11+ | Se recomienda usar conda |
| emu8086 | cualquier versión estable | Necesario para ejecutar el `.asm` generado |
| Git | 2.x | Para clonar el repositorio |

---

## Opción 1 — Conda (recomendado)

Conda gestiona automáticamente las dependencias de Python y evita conflictos entre entornos.

```bash
conda create -n snaptics python=3.11 ply pandas numpy scipy matplotlib seaborn jupyterlab
conda activate snaptics
pip install PyQt6
```

Para verificar que el entorno quedó correctamente configurado:

```bash
python -c "import ply, pandas, PyQt6; print('OK')"
```

---

## Opción 2 — pip + venv

Si prefieres no usar conda, puedes crear un entorno virtual estándar de Python:

```bash
# Crear el entorno
python -m venv .venv

# Activar en Windows (CMD)
.venv\Scripts\activate

# Activar en Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

> **Nota:** Si PowerShell bloquea la ejecución del script, ejecuta primero:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Instalación de emu8086

emu8086 es el emulador 8086 que ejecuta el código ensamblador generado por Snaptics. Es un requisito únicamente si deseas correr el `.asm` resultante.

1. Descarga emu8086 desde [su sitio oficial](https://emu8086-microprocessor-emulator.en.softonic.com/).
2. Instálalo. La ruta por defecto es `C:\emu8086`.
3. Si lo instalaste en una ruta diferente, configúrala en `config.json` (ver sección siguiente).

---

## Configuración de la ruta de emu8086

La ubicación de emu8086 se resuelve en el siguiente orden de precedencia:

1. **Variable de entorno** `SNAPTICS_EMU8086_HOME`
2. **Campo `emu8086_home`** en `config.json` en la raíz del proyecto
3. **Valor por defecto:** `C:\emu8086`

Para configurarlo a nivel de proyecto (recomendado), edita `config.json`:

```json
{
    "theme": "dark",
    "emu8086_home": "C:\\emu8086"
}
```

> Las barras invertidas en JSON deben duplicarse (`\\`).

---

## Ejecutar la IDE

Una vez configurado el entorno, lanza la IDE con:

```bash
python ide/main.py
```

La ventana principal incluye:
- **Editor de código** con resaltado de sintaxis para `.snp`
- **Panel de tokens** (atajo: `Ctrl+T`)
- **Terminal integrada** (atajo: `Ctrl+J`)
- **Panel de errores** con códigos `LEX-xxx`, `SYN-xxx` y `SEM-xxx`

El atajo principal de compilación es **F9**.

---

## Compilar desde la línea de comandos (CLI)

Si prefieres compilar sin abrir la IDE:

```bash
# Compilar un archivo .snp a ensamblador
python codegen/build.py samples/demo/alumnos_riesgo.snp -o build/alumnos.asm

# Ejecutar el programa de prueba embebido
python codegen/build.py --demo
```

El archivo `.asm` generado puede abrirse directamente en emu8086 y ensamblarse con **F5**.

---

## Estructura del proyecto

```
snaptics/
├── ide/                   # IDE en PyQt6
│   ├── main.py            # Punto de entrada
│   └── ui/                # Widgets, ventana principal, controladores
├── lexer.py               # Análisis léxico (PLY)
├── parser.py              # Análisis sintáctico (PLY), AST y tabla de símbolos
├── symbol_table.py        # Tabla de símbolos
├── semantic/              # Análisis semántico (SEM-1xx/2xx/3xx/4xx/5xx)
├── ir_generator.py        # AST → cuádruplas
├── optimizer/             # Pases de optimización sobre la IR
├── codegen/               # IR → ensamblador 8086
├── samples/               # Programas .snp de ejemplo y CSVs
├── tests/                 # Tests
├── config.json            # Configuración del proyecto
└── requirements.txt       # Dependencias Python
```

---

## Verificación de la instalación

Ejecuta los siguientes comandos para confirmar que todo funciona:

```bash
# 1. Verificar dependencias
python -c "import ply, pandas, numpy, scipy, PyQt6; print('Dependencias OK')"

# 2. Compilar el ejemplo incluido
python codegen/build.py --demo

# 3. Lanzar la IDE
python ide/main.py
```

Si alguno de los pasos falla, revisa que el entorno virtual esté activado y que todas las dependencias estén instaladas.

---

## Solución de problemas comunes

| Problema | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: ply` | Entorno no activado | Ejecuta `conda activate snaptics` o activa el `.venv` |
| `ModuleNotFoundError: PyQt6` | PyQt6 no instalado con pip | Ejecuta `pip install PyQt6` |
| La IDE no abre | Python < 3.11 | Verifica con `python --version` |
| El `.asm` no compila en emu8086 | Ruta de emu8086 incorrecta | Actualiza `emu8086_home` en `config.json` |
| `SEM-303` al compilar | CSV no encontrado | Verifica que el CSV exista en la ruta indicada en `import from` |
