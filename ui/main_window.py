# -*- coding: utf-8 -*-
"""
snaptics
"""

from PyQt6 import QtCore, QtWidgets, QtGui
import traceback
import lexer # NO MOVER !!
from .ui_base import Ui_snaptics
from .tokens_panel import TokensPanel
from .terminal_controller import TerminalController
from .file_manager import FileManager
from .theme_manager import ThemeManager


class SnapticsMainWindow(QtWidgets.QMainWindow):
    """Ventana principal de snaptics"""
    
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
        # Configurar panel de tokens
        self._setup_tokens_panel()
    
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
        # Ctrl+J (acción Show Terminal) alterna la terminal
        self.ui.actionNew_Terminal.triggered.connect(self.terminal_controller.toggle_terminal)
    # V 1.1: Se eliminó la acción "Hide Terminal" del menú; solo queda Ctrl+J (toggle)
        
        # Señales de tema
        self.ui.actionDark.triggered.connect(self.theme_manager.apply_dark_theme)
        self.ui.actionLight.triggered.connect(self.theme_manager.apply_light_theme)

        # Señales de compilación/analizador léxico
        self.ui.actionCompile.triggered.connect(self._run_lexer)
        # View > Tokens: mostrar/ocultar panel de tokens
        self.ui.actionTokens.triggered.connect(self._toggle_tokens_panel)

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
        # (Se elimina Ctrl+` para alternar terminal; el atajo oficial es Ctrl+J)
        
        # Shortcut para alternar tema (F12)
        if event.key() == QtCore.Qt.Key.Key_F12:
            self.theme_manager.toggle_theme()
            return
        
        super().keyPressEvent(event)

    def _setup_tokens_panel(self):
        """Crear y preparar el dock con la tabla de tokens."""
        self.tokens_panel = TokensPanel(self)
        self.tokens_panel.tokenActivated.connect(self._goto_token)
        self.tokens_dock = QtWidgets.QDockWidget("Tokens", self)
        self.tokens_dock.setObjectName("tokensDock")
        self.tokens_dock.setWidget(self.tokens_panel)
        self.tokens_dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
            | QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
            | QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.tokens_dock)
        self.tokens_dock.hide()

    def _run_lexer(self):
        """Ejecutar el analizador léxico sobre el texto del editor y mostrar resultados."""
        try:
            text = self.ui.code_txt.toPlainText()
            if not text.strip():
                self._print_to_terminal("[Lexer] No hay contenido para analizar.")
                # Limpiar la tabla si no hay contenido
                if hasattr(self, 'tokens_panel'):
                    self.tokens_panel.clear()
                return

            self._print_to_terminal("[Lexer] Analizando tokens...\n")
            result = lexer.tokenize(text)

            if result['errors']:
                # Mostrar errores y no mostrar tokens
                error_output = lexer.format_errors(result['errors'])
                self._print_to_terminal(f"[Errores encontrados]\n{error_output}")
                # Limpiar y ocultar panel de tokens
                if hasattr(self, 'tokens_panel'):
                    self.tokens_panel.clear()
                    self.tokens_dock.hide()
            else:
                # Formatear salida de tokens
                lines = []
                header = f"{'LINE':>4} {'COL':>4} {'TYPE':<20} VALUE"
                lines.append(header)
                lines.append('-' * len(header))
                for t in result['tokens']:
                    # Representar valores largos de forma compacta
                    val = t['value']
                    sval = repr(val)
                    if len(sval) > 60:
                        sval = sval[:57] + '...'
                    lines.append(f"{t['line']:>4} {t['column']:>4} {t['type']:<20} {sval}")

                output = "\n".join(lines)
                if not result['tokens']:
                    output += "\n(Sin tokens)"
                if result.get('output'):
                    output += "\n\n[Mensajes del lexer]\n" + result['output']

                self._print_to_terminal(output)

                # Actualizar panel de tokens
                if hasattr(self, 'tokens_panel'):
                    self.tokens_panel.set_tokens(result['tokens'])
                    if result['tokens']:
                        self.tokens_dock.show()
        except Exception as e:
            self._print_to_terminal("[Error] Falló el análisis léxico:\n" + str(e) + "\n" + traceback.format_exc())

    def _print_to_terminal(self, text: str):
        """Escribir texto en la terminal integrada, limpiando previamente."""
        self.terminal_controller.show_terminal()
        self.ui.terminal_txt.clear()
        self.ui.terminal_txt.appendPlainText(text)

    def _toggle_tokens_panel(self):
        """Mostrar/ocultar el dock de tokens desde el menú View > Tokens."""
        if self.tokens_dock.isVisible():
            self.tokens_dock.hide()
        else:
            self.tokens_dock.show()

    def _goto_token(self, token: dict):
        """Mover el cursor del editor al rango exacto del token usando lexpos/length."""
        try:
            pos = int(token.get('lexpos', 0))
            length = int(token.get('length', 1))
            cursor = self.ui.code_txt.textCursor()
            cursor.setPosition(pos)
            cursor.setPosition(pos + max(0, length), QtGui.QTextCursor.MoveMode.KeepAnchor)
            self.ui.code_txt.setTextCursor(cursor)
            self.ui.code_txt.centerOnScroll()
        except Exception:
            # No bloquear por errores; navegación es best-effort
            pass
    
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
            <li><b>Ctrl+J</b> - Alternar terminal</li>
            <li><b>F12</b> - Alternar tema</li>
        </ul>
        
        """
        
        QtWidgets.QMessageBox.about(self, "Acerca de snaptics", about_text)