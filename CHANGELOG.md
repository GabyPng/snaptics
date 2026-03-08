# Changelog

All notable changes to this project will be documented in this file.
This project adheres to the "Keep a Changelog" format and uses Semantic Versioning.

## [v2.0.0] - 2026-03-07
### Agregado
- **Analizador Semántico** completo con patrón Visitor sobre el AST (`semantic/semantic_analyzer.py`).
- **Tabla de símbolos** refactorizada: métodos `get()`, `get_category()`, `exists()`, soporte para `data_type` y `category` en cada símbolo.
- Módulo `semantic/type_checker.py` (SEM-2xx): inferencia de tipos (`infer_type`) y verificaciones activas:
  - SEM-201: operaciones aritméticas con tipos incompatibles.
  - SEM-202: operadores lógicos (`and`/`or`/`not`) con operandos no booleanos.
  - SEM-203: comparaciones relacionales entre tipos incompatibles.
  - SEM-204: columna de dataset sin tipo declarado.
- Módulo `semantic/symbol_checks.py` (SEM-1xx): esqueleto con `check_symbol_declared`, `check_redeclaration`, `check_symbol_category` (pendiente de implementación por Carim).
- Módulo `semantic/DRQ_checks.py` (SEM-3xx/5xx): esqueleto con `check_dataset_source`, `check_dataset_access`, `check_query_symbol` (pendiente de implementación por Gibran).
- **Tipado de columnas en `select`**: nueva sintaxis `col: tipo` (`int`, `real`, `string`, `bool`). Las columnas se registran en la tabla de símbolos con su tipo.
- Nuevas palabras reservadas de tipos: `int`, `real`, `string`, `bool` (`TYPE_INT`, `TYPE_REAL`, `TYPE_STRING`, `TYPE_BOOL`).
- Nuevo token `COLON` (`:`) para separador de tipo en columnas.
- Integración del analizador semántico en el pipeline de compilación (`ui/main_window.py`).
- Soporte para abrir archivos `.snp` directamente desde el sistema operativo.
- Tabla de tokens ordenada por orden de aparición en el código.

### Cambiado
- **Recuperación de errores (panic mode)** rediseñada: usa `tokenfunc` con buffer (`_token_buffer`) para devolver el token de sincronización al stream tras la recuperación natural del stack, eliminando la cascada de errores falsos en declaraciones posteriores.
- El parser registra datasets con `category='dataset'` y `data_type='dataset'` (antes era `None, None`).
- Analizador sintáctico (`parser.py`): categoría y tipo de símbolo asignados correctamente en todas las declaraciones.
- `lista_ids` en `select` reemplazada por `lista_cols_tipadas` que soporta `ID COLON tipo` e `ID` solo (sin tipo, para permitir SEM-204).
- Mensajes de error de `or`/`and` mejorados: ahora indican qué se esperaba como operando.
- Umbral de detección de typos en palabras reservadas ajustado a 0.90 (>3 chars) / 0.80 (≤3 chars) para eliminar falsos positivos (ej. `nota` → `not`).
- `infer_type` normaliza tokens de tipo (`TYPE_INT` → `'int'`, etc.) y maneja valores Python crudos con guard defensivo.

### Corregido
- `from _future_ import` corregido a `from __future__ import` en `type_checker.py`.
- Variable `compatible` renombrada a `compatibles` para consistencia con su uso en `check_relational_operation`.
- `SymbolTable.get_type()` reemplazado por `SymbolTable.get().data_type` (el método no existía).
- Valores `None` en `symbol.data_type` ahora retornan `'unknown'` en vez de `None` en `infer_type`.

### Archivos más relevantes modificados
- `semantic/semantic_analyzer.py` (nuevo — orquestador Visitor)
- `semantic/type_checker.py` (nuevo — SEM-2xx)
- `semantic/symbol_checks.py` (nuevo — esqueleto SEM-1xx)
- `semantic/DRQ_checks.py` (nuevo — esqueleto SEM-3xx/5xx)
- `semantic/semantic_errors.py` (nuevo — códigos SEM-101 a SEM-501)
- `symbol_table.py` (refactorización)
- `lexer.py` (nuevos tokens COLON, TYPE_*, ajuste de cutoff)
- `parser.py` (tipado de columnas, panic mode con buffer, mensajes mejorados)
- `ui/main_window.py` (integración semántico)

---

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
