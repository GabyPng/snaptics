# -*- coding: utf-8 -*-
"""
snaptics - Editor de código con terminal integrada
Ventana principal modular
"""

from PyQt6 import QtCore, QtWidgets
from .ui_base import Ui_snaptics
from .terminal_controller import TerminalController
from .file_manager import FileManager
from .theme_manager import ThemeManager


class SnapticsMainWindow(QtWidgets.QMainWindow):
    """Ventana principal de snaptics con arquitectura modular"""
    
    def __init__(self):
        super().__init__()
        
        # Configurar interfaz base
        self.ui = Ui_snaptics()
        self.ui.setupUi(self)
        
        # Inicializar controladores modulares
        self._init_controllers()
        
        # Conectar señales
        self._connect_signals()
        
        # Configurar estado inicial
        self._setup_initial_state()
    
    def _init_controllers(self):
        """Inicializar todos los controladores modulares"""
        self.terminal_controller = TerminalController(self.ui)
        self.file_manager = FileManager(self.ui, self)
        self.theme_manager = ThemeManager(self)
        
        # Conectar detección de cambios en el texto
        self.ui.code_txt.textChanged.connect(self.file_manager.mark_modified)
    
    def _connect_signals(self):
        """Conectar todas las señales de la interfaz"""
        # Señales de archivo
        self.ui.actionNuevo.triggered.connect(self.file_manager.new_file)
        self.ui.actionOpen.triggered.connect(self.file_manager.open_file)
        self.ui.actionSave.triggered.connect(self.file_manager.save_file)
        self.ui.actionSave_As.triggered.connect(self.file_manager.save_file_as)
        self.ui.actionExit.triggered.connect(self.close)
        
        # Señales de edición
        self.ui.actionundo.triggered.connect(self.ui.code_txt.undo)
        self.ui.actionredo.triggered.connect(self.ui.code_txt.redo)
        self.ui.actioncopy.triggered.connect(self.ui.code_txt.copy)
        self.ui.actionpaste.triggered.connect(self.ui.code_txt.paste)
        
        # Señales de terminal
        self.ui.actionNew_Terminal.triggered.connect(self.terminal_controller.show_terminal)
        self.ui.actionHide_Terminal.triggered.connect(self.terminal_controller.hide_terminal)
        
        # Señales de tema
        self.ui.actionDark.triggered.connect(self.theme_manager.apply_dark_theme)
        self.ui.actionLight.triggered.connect(self.theme_manager.apply_light_theme)
        
        # Señal de ayuda
        self.ui.actionAbout.triggered.connect(self._show_about)
    
    def _setup_initial_state(self):
        """Configurar el estado inicial de la aplicación"""
        # Aplicar tema claro por defecto
        self.theme_manager.apply_light_theme()
        
        # Configurar contenido inicial
        self._set_welcome_content()
        
        # Marcar como no modificado
        self.file_manager.is_modified = False
    
    def _set_welcome_content(self):
        """Establecer contenido de bienvenida"""
        welcome_text = """# Bienvenido a snaptics
        Presiona Ctrl + H para ayuda.

"""
        self.ui.code_txt.setPlainText(welcome_text)
    
    def keyPressEvent(self, event):
        """Manejar eventos de teclado globales"""
        # Shortcut para alternar terminal (Ctrl+`)
        if (event.key() == QtCore.Qt.Key.Key_QuoteLeft and 
            event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier):
            self.terminal_controller.toggle_terminal()
            return
        
        # Shortcut para alternar tema (F12)
        if event.key() == QtCore.Qt.Key.Key_F12:
            self.theme_manager.toggle_theme()
            return
        
        super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Manejar redimensionamiento de ventana"""
        super().resizeEvent(event)
        # Los layouts se encargan automáticamente del redimensionamiento
    
    def closeEvent(self, event):
        """Manejar cierre de aplicación"""
        if self.file_manager._check_unsaved_changes():
            event.ignore()
        else:
            event.accept()
    
    def _show_about(self):
        """Mostrar información sobre la aplicación"""
        about_text = """<h3>snaptics</h3>
        <p><b>Compilador del equipo #2</b></p>
        <p>Versión 1.0</p>

        <h4>Atajos principales:</h4>
        <ul>
            <li><b>Ctrl+`</b> - Alternar terminal</li>
            <li><b>F12</b> - Alternar tema</li>
            <li><b>Ctrl+Shift+H</b> - Ocultar terminal</li>
            <li><b>Ctrl+Shift+T</b> - Mostrar terminal</li>
        </ul>
        
        """
        
        QtWidgets.QMessageBox.about(self, "Acerca de snaptics", about_text)