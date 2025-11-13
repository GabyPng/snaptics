# Changelog

All notable changes to this project will be documented in this file.
This project adheres to the "Keep a Changelog" format and uses Semantic Versioning.

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
