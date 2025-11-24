# Changelog

All notable changes to this project will be documented in this file.
This project adheres to the "Keep a Changelog" format and uses Semantic Versioning.

## [v1.3.0] - 2025-11-23
### Agregado
- Nuevos tokens: `COMMA` (`,`) y `DOT` (`.`) para permitir comas y puntos en expresiones.
- Soporte para puntos en identificadores (IDs con `.`), modificando la regex de `t_ID`.
- Función `categorize_char_error()` para categorizar errores léxicos con mensajes más descriptivos.
- Mejoras en `t_error()` con casos especiales para cadenas no cerradas, comentarios de bloque incompletos y operadores incompletos.
- Manejo de errores léxicos avanzado: reporta línea, columna, texto de la línea y flecha apuntando al error (`lexer.py`).
- Detección específica de cadenas no cerradas con mensaje "Cadena no cerrada" usando `match-case` en `t_error()`.
- Funciones `format_errors()` y `print_errors()` para formatear errores en GUI y consola.
- Integración de errores en la interfaz gráfica: muestra errores en la terminal integrada y oculta el panel de tokens si hay errores.
- Resaltado de ocurrencias: al seleccionar texto en el editor, se iluminan todas las ocurrencias con fondo amarillo.
- Números de línea: ahora el editor muestra números de línea en el margen izquierdo (CodeEditor con LineNumberArea).

### Cambiado
- Regex de `t_ID` actualizada para requerir contenido válido después de puntos: `r'[A-Za-z_][A-Za-z_0-9]*(\.[A-Za-z_][A-Za-z_0-9]*)*'`, evitando IDs que terminen con punto.
- Mensajes de error más específicos y en español.
- `ui/main_window.py`: `_run_lexer()` ahora verifica errores y muestra solo errores o tokens según corresponda.

### Archivos más relevantes modificados
- `lexer.py` (nuevos tokens, regex de ID, categorización de errores)
- `ui/main_window.py` (integración de errores, resaltado de ocurrencias)


## [v1.1.0] - 2025-11-12
### Agregado
- Panel de Tokens (dockable) con tabla ordenable y filtrable (`ui/tokens_panel.py`). Atajo: `Ctrl+T`.
- API pública de tokenización en `lexer.py`: función `tokenize(text)` y `make_lexer()` que devuelven tokens con metadatos detallados (línea, columna, `lexpos`, `length`, `lexeme`).
- Archivo de ejemplo `Ejemplo.snp` añadido como muestra de sintaxis.
- `requirements.txt` agregado/actualizado incluyendo dependencias necesarias (p.ej. `ply`).

### Cambiado
- Refactor general de `lexer.py`: mejoras en reglas (ACEPTA IDs que empiezan por mayúsculas/underscore), nuevos patrones para `REAL`, `INT`, `STRING` y `BOOL`, y extracción precisa del lexema usando expresiones regulares a partir de `lexpos`.
- Integración del analizador léxico con la interfaz: `ui/main_window.py` ahora ejecuta `lexer.tokenize` desde la acción Compile (Run→Compile / F9) y muestra el resultado en la terminal integrada.
- Se añadió un dock de Tokens en la ventana principal y se implementó navegación desde la tabla hacia el editor (doble-clic / Enter), usando `lexpos` + `length` para seleccionar el rango exacto.
- Atajos y menús: la terminal ahora se alterna con `Ctrl+J` (toggle). Se asignó `Ctrl+T` para abrir/cerrar el panel Tokens. Se eliminó la acción redundante "Hide Terminal" del menú.
- `ui/__init__.py` exporta `TokensPanel`; `ui/ui_base.py` y `ui/main_window.py` actualizados para reflejar atajos y nuevas acciones.
- `README.md` reorganizado (separación clara de instalación y ejecución, instrucciones pip/venv y conda).

### Corregido
- Correcciones en la construcción del lexer (uso del objeto de módulo para PLY) para evitar errores en tiempo de ejecución.
- Correcciones en la tokenización para capturar correctamente lexemas completos (p. ej. `P` → `PROB`, operador `:-`) y en la longitud del lexema para selección exacta en la UI.

### Eliminado
- Eliminada la ejecución de ejemplo embebida en `lexer.py` (no se ejecuta en import).
- Eliminada la acción de menú `Hide Terminal` y sus atajos duplicados.

### Documentación
- `README.md` actualizado con instrucciones de instalación (conda y pip/venv), comando de ejecución (`python main.py`) y atajos actualizados (`Ctrl+J` para terminal, `Ctrl+T` para Tokens).

### Archivos más relevantes modificados
- `lexer.py` (refactor, API `tokenize`, metadatos de tokens)
- `ui/tokens_panel.py` (nuevo)
- `ui/main_window.py` (integración lexer, dock tokens, navegación, terminal toggle)
- `ui/ui_base.py` (atajos: `Ctrl+T`, `Ctrl+J`; eliminación de Hide Terminal)
- `ui/__init__.py` (export TokensPanel)
- `README.md` (documentación actualizada)
- `requirements.txt` (dependencias)
- `Ejemplo.snp` (archivo de ejemplo)

## [v1.0.0] - 2025-01-01
### Agregado
- Publicación inicial del proyecto (ver `README.md` para más detalles).
