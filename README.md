# snaptics

Version 1.0:
Integración de la interfaz desarrollada en QT Designer e importada en python. Se necesita instalar la librería pyQT.


## Instalación y Uso

### OPCIÓN 1
Para colaborar en este proyecto, configuren el entorno de desarrollo con conda:
```bash
conda create -n snaptics python=3.11 ply pandas numpy scipy matplotlib seaborn jupyterlab
conda activate snaptics
```

Después instalan PyQt6:
```bash
pip install PyQt6
```

### OPCIÓN 2
Con pip 
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Ejecutar
```bash
python main.py
```

## Arquitectura

```
snaptics/
├── main.py                   # Punto de entrada y lógica principal
├── ui/                       # Paquete completo de interfaz gráfica
│   ├── __init__.py           # Configuración del paquete UI
│   ├── ui_base.py            # Definición de widgets base
│   ├── main_window.py        # Ventana principal con lógica
│   ├── terminal_controller.py# Controlador de terminal
│   ├── file_manager.py       # Manejador de archivos
│   ├── theme_manager.py      # Manejador de temas
│   └── compilerGUI.ui        # Archivo de diseño original
└── lexer.py                  # Analizador léxico
```

En la aplicación, abre o escribe código y presiona F9 (o menú Run → Compile) para ejecutar el analizador léxico y ver los tokens en la terminal integrada.

## Atajos de Teclado

### Archivo
- `Ctrl+N` - Nuevo archivo
- `Ctrl+O` - Abrir archivo  
- `Ctrl+S` - Guardar
- `Ctrl+Shift+S` - Guardar como
- `Ctrl+Q` - Salir

### Edición
- `Ctrl+Z` - Deshacer
- `Ctrl+Y` - Rehacer
- `Ctrl+C` - Copiar
- `Ctrl+V` - Pegar

### Terminal
- `Ctrl+J` - Alternar terminal

### Temas
- `F12` - Alternar entre tema claro y oscuro

## Organizaicón GUI

El código está organizado de la siguiente forma: 

- **main.py**: Punto de entrada único que maneja PyQt6, errores e inicia la aplicación
- **ui/ Package**: Contiene toda la interfaz gráfica y lógica relacionada
  - **ui_base.py**: Definición pura de widgets e interfaz
  - **main_window.py**: Ventana principal con toda la lógica de la aplicación
  - **Controladores**: Manejan funcionalidades específicas (terminal, archivos, temas)

## Licencia

Ver archivo [LICENSE](LICENSE)
