# -*- coding: utf-8 -*-
"""
snaptics
"""

from PyQt6 import QtCore, QtWidgets, QtGui
import traceback
import lexer # NO MOVER !!
import parser as syntax_parser
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
        # Reemplazar el editor por uno con soporte de números de línea
        self._install_code_editor()
        
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
        
        # Conectar resaltado de ocurrencias en selección
        self.ui.code_txt.selectionChanged.connect(self._highlight_occurrences)

    def _install_code_editor(self):
        """Reemplaza el QPlainTextEdit generado por la UI con nuestro CodeEditor que
        soporta numeración de líneas y otras utilidades."""
        # Import aquí para evitar ciclos si se importa UI antes
        class LineNumberArea(QtWidgets.QWidget):
            def __init__(self, editor):
                super().__init__(editor)
                self.editor = editor

            def sizeHint(self):
                return QtCore.QSize(self.editor.lineNumberAreaWidth(), 0)

            def paintEvent(self, event):
                self.editor.lineNumberAreaPaintEvent(event)

        class CodeEditor(QtWidgets.QPlainTextEdit):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.lineNumberArea = LineNumberArea(self)
                self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
                self.updateRequest.connect(self.updateLineNumberArea)
                self.cursorPositionChanged.connect(self._cursorMoved)
                self._current_extra_line = None
                self.updateLineNumberAreaWidth(0)

            def lineNumberAreaWidth(self):
                digits = len(str(max(1, self.blockCount())))
                space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
                return space

            def updateLineNumberAreaWidth(self, _):
                self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
                self.lineNumberArea.setFixedWidth(self.lineNumberAreaWidth())

            def updateLineNumberArea(self, rect, dy):
                if dy:
                    self.lineNumberArea.scroll(0, dy)
                else:
                    self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

                if rect.contains(self.viewport().rect()):
                    self.updateLineNumberAreaWidth(0)

            def resizeEvent(self, event):
                super().resizeEvent(event)
                cr = self.contentsRect()
                self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

            def lineNumberAreaPaintEvent(self, event):
                painter = QtGui.QPainter(self.lineNumberArea)
                painter.fillRect(event.rect(), QtGui.QColor(240, 240, 240))
                block = self.firstVisibleBlock()
                blockNumber = block.blockNumber()
                top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
                bottom = top + int(self.blockBoundingRect(block).height())
                fm = self.fontMetrics()
                width = self.lineNumberArea.width()
                while block.isValid() and top <= event.rect().bottom():
                    if block.isVisible() and bottom >= event.rect().top():
                        number = str(blockNumber + 1)
                        painter.setPen(QtGui.QColor(80, 80, 80))
                        painter.drawText(0, top, width - 4, fm.height(), QtCore.Qt.AlignmentFlag.AlignRight, number)
                    block = block.next()
                    top = bottom
                    bottom = top + int(self.blockBoundingRect(block).height())
                    blockNumber += 1

            def _cursorMoved(self):
                # Mark line to be included when merging extra selections
                cur = self.textCursor()
                block = cur.block()
                sel = QtWidgets.QTextEdit.ExtraSelection()
                # Determine theme via the main window's theme_manager
                main_win = self.window()
                theme_manager = getattr(main_win, 'theme_manager', None)
                is_dark = False
                if theme_manager and hasattr(theme_manager, 'get_current_theme'):
                    is_dark = (theme_manager.get_current_theme() == 'dark')
                lineColor = QtGui.QColor(220, 235, 255) if not is_dark else QtGui.QColor(50, 50, 70)
                sel.format.setBackground(lineColor)
                sel.cursor = cur
                sel.cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
                self._current_extra_line = sel

            def mergeExtraSelections(self, extras):
                # Combine the provided extras (e.g. occurrences) with current line highlight
                merged = list(extras) if extras else []
                if self._current_extra_line:
                    merged.append(self._current_extra_line)
                return merged

        # Replace the widget instance in-place
        old = self.ui.code_txt
        parent = old.parent()
        if parent is None:
            return
        new_editor = CodeEditor(parent)
        new_editor.setObjectName('code_txt')
        new_editor.setPlainText(old.toPlainText())
        # Copy font, tab stops and other properties
        new_editor.setFont(old.font())
        new_editor.setTabStopDistance(old.tabStopDistance())
        # Find and replace within parent layout
        layout = parent.layout()
        if layout is not None:
            for i in range(layout.count()):
                it = layout.itemAt(i)
                if it is not None and it.widget() is old:
                    layout.insertWidget(i, new_editor)
                    layout.removeWidget(old)
                    old.setParent(None)
                    break
        self.ui.code_txt = new_editor
    
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

        # Señales de compilación
        self.ui.actionCompile.triggered.connect(self._run_lexer)
        # View > Tokens: mostrar/ocultar panel de tokens
        self.ui.actionTokens.triggered.connect(self._toggle_tokens_panel)
        # View > Symbols
        self.ui.actionSymbols.triggered.connect(self._open_symbols_dialog)
        

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
#        Presiona Ctrl + H para ayuda.

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
        """Ejecutar análisis léxico y sintáctico completo (compilación)."""
        try:
            text = self.ui.code_txt.toPlainText()
            if not text.strip():
                self._print_to_terminal("[Compiler] No hay contenido para analizar.")
                if hasattr(self, 'tokens_panel'):
                    self.tokens_panel.clear()
                return

            # ========== ENCABEZADO DE COMPILACIÓN ==========
            lines = []
            lines.append("=" * 70)
            lines.append("INICIANDO COMPILACIÓN")
            lines.append("=" * 70)
            lines.append("")
            
            # ========== FASE 1: ANÁLISIS LÉXICO ==========
            lines.append("FASE 1: ANÁLISIS LÉXICO")
            lines.append("-" * 70)
            
            lex_result = lexer.tokenize(text)
            
            # Guardar tokens para tabla de símbolos
            try:
                self.last_tokens = lex_result.get('tokens', []) if isinstance(lex_result, dict) else []
            except Exception:
                self.last_tokens = []

            # Verificar errores léxicos
            lexical_errors = lex_result['errors']
            has_lexical_errors = len(lexical_errors) > 0
            
            # Mostrar resumen de tokens
            num_tokens = len(lex_result['tokens'])
            num_lines = text.count('\n') + 1
            
            lines.append("")
            lines.append(f"✓ Análisis léxico completado")
            lines.append(f"  Tokens generados: {num_tokens}")
            lines.append(f"  Líneas procesadas: {num_lines}")
            lines.append("")
            
            # Mostrar tabla de tokens
            lines.append("Tokens identificados:")
            lines.append("-" * 70)
            header = f"{'LINE':>4} {'COL':>4} {'TYPE':<20} VALUE"
            lines.append(header)
            lines.append("-" * 70)
            
            for t in lex_result['tokens']:
                val = t['value']
                sval = repr(val)
                if len(sval) > 40:
                    sval = sval[:37] + '...'
                lines.append(f"{t['line']:>4} {t['column']:>4} {t['type']:<20} {sval}")
            
            if not lex_result['tokens']:
                lines.append("(Sin tokens)")
            
            lines.append("")
            
            # Actualizar panel de tokens
            if hasattr(self, 'tokens_panel'):
                self.tokens_panel.set_tokens(lex_result['tokens'])
                if lex_result['tokens']:
                    self.tokens_dock.show()
            
            # ========== FASE 2: ANÁLISIS SINTÁCTICO ==========
            lines.append("")
            lines.append("FASE 2: ANÁLISIS SINTÁCTICO")
            lines.append("-" * 70)
            
            parse_result = syntax_parser.parse(text)
            
            syntactic_errors = parse_result['errors']
            has_syntactic_errors = len(syntactic_errors) > 0
            
            if parse_result['success'] and not has_lexical_errors:
                # Análisis sintáctico exitoso
                lines.append("")
                lines.append(f"Análisis sintáctico completado")
                lines.append(f"  Se generó el Árbol de Sintaxis Abstracta (AST)")
                lines.append("")
                
                # Mostrar estructura del AST
                lines.append("Estructura del AST:")
                lines.append("-" * 70)
                
                # Imprimir lo que tenemos hasta ahora
                self._print_to_terminal("\n".join(lines))
                
                # Capturar output del AST
                import io
                import sys
                
                ast_output = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = ast_output
                syntax_parser.print_ast(parse_result['ast'])
                sys.stdout = old_stdout
                
                self._print_to_terminal_append(ast_output.getvalue())
                
                # Guardar el AST para uso posterior
                self.last_ast = parse_result['ast']
                
                # ========== RESUMEN FINAL ==========
                lines_final = []
                lines_final.append("")
                lines_final.append("=" * 70)
                lines_final.append("COMPILACIÓN EXITOSA")
                lines_final.append("=" * 70)
                lines_final.append("")
                lines_final.append("Resumen:")
                lines_final.append(f"  • Fase léxica:      ✓ {num_tokens} tokens")
                lines_final.append(f"  • Fase sintáctica:  ✓ AST generado")
                lines_final.append(f"  • Líneas analizadas: {num_lines}")
                lines_final.append("")
                lines_final.append("=" * 70)
                
                self._print_to_terminal_append("\n".join(lines_final))
                
                # Mostrar mensaje de éxito
                QtWidgets.QMessageBox.information(
                    self,
                    "Compilación Exitosa",
                    f"La compilación se completó sin errores.\n\n"
                    f"• Análisis léxico: {num_tokens} tokens\n"
                    f"• Análisis sintáctico: AST generado\n\n"
                    f"Consulta la terminal para ver los detalles completos."
                )
            else:
                # Hay errores (léxicos o sintácticos)
                all_errors = []
                
                if has_lexical_errors:
                    lines.append("")
                    lines.append("✗ ERRORES LÉXICOS ENCONTRADOS")
                    lines.append("")
                    # Agregar errores léxicos formateados
                    lexical_error_output = lexer.format_errors(lexical_errors)
                    lines.append(lexical_error_output)
                    all_errors.extend(lexical_errors)
                
                if has_syntactic_errors and not has_lexical_errors:
                    lines.append("")
                    lines.append("✗ ERRORES SINTÁCTICOS ENCONTRADOS")
                    lines.append("")
                    
                    # Formatear errores sintácticos
                    for i, error in enumerate(syntactic_errors, 1):
                        lines.append(f"[Error #{len(all_errors) + i}]")
                        if error.get('line') == 'EOF':
                            lines.append(f"  Posición: Final del archivo")
                        else:
                            lines.append(f"  Línea {error.get('line', '?')}, Columna {error.get('column', '?')}")
                        
                        token_type = error.get('token', '?')
                        token_value = error.get('value', '')
                        if token_value:
                            lines.append(f"  Token problemático: '{token_value}' (tipo: {token_type})")
                        else:
                            lines.append(f"  Token problemático: {token_type}")
                        
                        lines.append(f"  Mensaje: {error.get('message', 'Error desconocido')}")
                        lines.append("")
                        lines.append("-" * 70)
                        lines.append("")
                    
                    all_errors.extend(syntactic_errors)
                elif has_syntactic_errors and has_lexical_errors:
                    lines.append("")
                    lines.append("⚠️  NOTA: Hay errores sintácticos adicionales, pero pueden ser")
                    lines.append("   consecuencia de los errores léxicos. Corrija primero los")
                    lines.append("   errores léxicos y vuelva a compilar.")
                    lines.append("")
                
                # Imprimir todo hasta ahora
                self._print_to_terminal("\n".join(lines))
                
                # ========== RESUMEN FINAL CON ERRORES ==========
                lines_final = []
                lines_final.append("")
                lines_final.append("=" * 70)
                lines_final.append("COMPILACIÓN FALLIDA")
                lines_final.append("=" * 70)
                lines_final.append("")
                lines_final.append("Resumen:")
                lines_final.append(f"  • Fase léxica:      {'✗' if has_lexical_errors else '✓'} {num_tokens} tokens")
                if has_lexical_errors:
                    lines_final.append(f"  • Fase sintáctica:  ⚠️  Omitida (errores léxicos detectados)")
                else:
                    lines_final.append(f"  • Fase sintáctica:  {'✗' if has_syntactic_errors else '✓'} {len(syntactic_errors)} error(es)")
                lines_final.append(f"  • Total errores:    {len(all_errors)}")
                lines_final.append("")
                lines_final.append("=" * 70)
                
                self._print_to_terminal_append("\n".join(lines_final))
                
                # Mostrar mensaje de error
                QtWidgets.QMessageBox.critical(
                    self,
                    "Errores de Compilación",
                    f"Se encontraron {len(all_errors)} error(es) en total.\n\n"
                    f"• Errores léxicos: {len(lexical_errors)}\n"
                    f"• Errores sintácticos: {len(syntactic_errors)}\n\n"
                    f"Consulta la terminal para ver los detalles completos."
                )
                lines_final.append("")
                lines_final.append("Corrija los errores sintácticos antes de continuar.")
                lines_final.append("")
                lines_final.append("=" * 70)
                
                self._print_to_terminal_append("\n".join(lines_final))
                
                # Mostrar diálogo con resumen
               #  self._show_syntax_error_dialog(parse_result['errors'])
                
        except Exception as e:
            error_msg = (
                f"[ERROR CRÍTICO] Falló la compilación:\n\n"
                f"{str(e)}\n\n"
                f"Traceback:\n{traceback.format_exc()}"
            )
            self._print_to_terminal(error_msg)
            QtWidgets.QMessageBox.critical(
                self,
                "Error Crítico",
                f"Ocurrió un error inesperado durante la compilación:\n\n{str(e)}"
            )

    # Método auxiliar para agregar texto sin limpiar
    def _print_to_terminal_append(self, text: str):
        """Agregar texto a la terminal sin limpiar el contenido anterior."""
        self.terminal_controller.show_terminal()
        self.ui.terminal_txt.appendPlainText(text)

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
        <p>Versión 1.3.0</p>

        <h4>Atajos principales:</h4>
        <ul>
            <li><b>F9</b> - Compilar (Análisis Léxico + Sintáctico)</li>
            <li><b>Ctrl+J</b> - Alternar terminal</li>
            <li><b>Ctrl+J</b> - Alternar tabla de Tokens</li>
            <li><b>F12</b> - Alternar tema</li>
        </ul>
        
        """
        
        QtWidgets.QMessageBox.about(self, "Acerca de snaptics", about_text)
    
    def _get_existing_tokens(self):
        tokens = []
        try:
            if hasattr(self, 'tokens_panel') and self.tokens_panel is not None:
                tp = self.tokens_panel
                if hasattr(tp, 'tokens'):
                    tokens = tp.tokens
                elif hasattr(tp, 'get_tokens'):
                    tokens = tp.get_tokens()
                elif hasattr(tp, 'current_tokens'):
                    tokens = tp.current_tokens
        except Exception:
            tokens = []

        if not tokens and hasattr(self, 'last_tokens'):
            tokens = getattr(self, 'last_tokens', []) or []

        return tokens or []

    def _open_symbols_dialog(self):
        """Abrir diálogo con tabla de símbolos usando el arreglo de tokens existente."""
        try:
            tokens = self._get_existing_tokens()

            symbols = {}
            for t in tokens:
                try:
                    if t.get('type') == 'ID':
                        name = t.get('value')
                        if name is None:
                            continue
                        name = str(name)
                        # normalizar (por si el token viene con comillas)
                        if (name.startswith("'") and name.endswith("'")) or (name.startswith('"') and name.endswith('"')):
                            name = name[1:-1]
                        line_no = int(t.get('line', 0)) if t.get('line') is not None else 0
                        if name not in symbols or (line_no and line_no < symbols[name]):
                            symbols[name] = line_no
                except Exception:
                    continue

            # Crear diálogo con tabla
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Symbol Table")
            layout = QtWidgets.QVBoxLayout(dialog)

            table = QtWidgets.QTableWidget(parent=dialog)
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Name", "Line"])
            table.setRowCount(len(symbols))
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            table.horizontalHeader().setStretchLastSection(True)

            # Ordenar por número de línea (asc)
            def _sort_key(item):
                name, ln = item
                ln_val = int(ln) if ln is not None else 0
                
                sort_ln = ln_val if ln_val > 0 else float('inf')
                return (sort_ln, name.lower())

            for i, (name, line_no) in enumerate(sorted(symbols.items(), key=_sort_key)):
                table.setItem(i, 0, QtWidgets.QTableWidgetItem(name))
                table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(line_no)))

            layout.addWidget(table)
            buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close, parent=dialog)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            dialog.resize(420, 300)
            dialog.exec()
        except Exception as e:
            self._print_to_terminal(f"[Symbols] Error al generar tabla de símbolos:\n{e}")
    
    def _highlight_occurrences(self):
        """Resaltar todas las ocurrencias del texto seleccionado."""
        cursor = self.ui.code_txt.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            if selected_text.strip():
                # Buscar todas las ocurrencias en el documento
                document = self.ui.code_txt.document()
                extra_selections = []
                search_cursor = QtGui.QTextCursor(document)
                
                # Usar azul claro semi-transparente para mejor visibilidad en ambos temas
                highlight_color = QtGui.QColor(100, 200, 255, 150)
                
                while not search_cursor.isNull() and not search_cursor.atEnd():
                    search_cursor = document.find(selected_text, search_cursor)
                    if not search_cursor.isNull():
                        selection = QtWidgets.QTextEdit.ExtraSelection()
                        selection.format.setBackground(highlight_color)
                        selection.cursor = search_cursor
                        extra_selections.append(selection)

                # Merge with any editor-provided extras (e.g. current-line highlight)
                if hasattr(self.ui.code_txt, 'mergeExtraSelections'):
                    merged = self.ui.code_txt.mergeExtraSelections(extra_selections)
                    self.ui.code_txt.setExtraSelections(merged)
                else:
                    self.ui.code_txt.setExtraSelections(extra_selections)
            else:
                self.ui.code_txt.setExtraSelections([])
        else:
            self.ui.code_txt.setExtraSelections([])
    # def _run_parser(self):
    #     """Ejecutar el analizador sintáctico sobre el texto del editor."""
    #     try:
    #         text = self.ui.code_txt.toPlainText()
    #         if not text.strip():
    #             self._print_to_terminal("[Parser] No hay contenido para analizar.")
    #             return

    #         self._print_to_terminal("[Parser] Analizando sintaxis...\n")
            
    #         # Primero ejecutar el lexer para verificar errores léxicos
    #         lex_result = lexer.tokenize(text)
            
    #         if lex_result['errors']:
    #             # Si hay errores léxicos, mostrarlos y no continuar
    #             error_output = lexer.format_errors(lex_result['errors'])
    #             self._print_to_terminal(f"[Errores léxicos encontrados]\n{error_output}")
    #             self._print_to_terminal("\n⚠️  Corrija los errores léxicos antes de continuar con el análisis sintáctico.")
    #             return
            
    #         # Si no hay errores léxicos, proceder con el parser
    #         parse_result = syntax_parser.parse(text)
            
    #         if parse_result['success']:
    #             # Análisis exitoso
    #             lines = []
    #             lines.append("=" * 70)
    #             lines.append("ANÁLISIS SINTÁCTICO COMPLETADO CON ÉXITO")
    #             lines.append("=" * 70)
    #             lines.append("")
    #             lines.append("✓ El código es sintácticamente correcto")
    #             lines.append("✓ Se generó el Árbol de Sintaxis Abstracta (AST)")
    #             lines.append("")
    #             lines.append("-" * 70)
    #             lines.append("ESTRUCTURA DEL AST:")
    #             lines.append("-" * 70)
    #             lines.append("")
                
    #             # Convertir AST a texto para mostrar
    #             import io
    #             import sys
                
    #             ast_output = io.StringIO()
    #             old_stdout = sys.stdout
    #             sys.stdout = ast_output
    #             syntax_parser.print_ast(parse_result['ast'])
    #             sys.stdout = old_stdout
                
    #             lines.append(ast_output.getvalue())
    #             lines.append("")
    #             lines.append("=" * 70)
                
    #             output = "\n".join(lines)
    #             self._print_to_terminal(output)
                
    #             # Guardar el AST para uso posterior
    #             self.last_ast = parse_result['ast']
                
    #             # Mostrar mensaje de éxito
    #             QtWidgets.QMessageBox.information(
    #                 self,
    #                 "Análisis Sintáctico Exitoso",
    #                 f"El código es sintácticamente correcto.\n\n"
    #                 f"Se ha generado el Árbol de Sintaxis Abstracta.\n"
    #                 f"Consulta la terminal para ver los detalles."
    #             )
    #         else:
    #             # Hay errores sintácticos
    #             num_errors = len(parse_result['errors'])
                
    #             lines = []
    #             lines.append("=" * 70)
    #             lines.append("ANÁLISIS SINTÁCTICO FALLIDO")
    #             lines.append("=" * 70)
    #             lines.append("")
    #             lines.append(f"Total de errores encontrados: {num_errors}")
    #             lines.append("")
    #             lines.append("-" * 70)
    #             lines.append("")
                
    #             # Formatear errores de forma similar al lexer
    #             for i, error in enumerate(parse_result['errors'], 1):
    #                 lines.append(f"[Error #{i}]")
    #                 if error.get('line') == 'EOF':
    #                     lines.append(f"  Posición: Final del archivo")
    #                 else:
    #                     lines.append(f"  Línea {error.get('line', '?')}, Columna {error.get('column', '?')}")
                    
    #                 token_type = error.get('token', '?')
    #                 token_value = error.get('value', '')
    #                 if token_value:
    #                     lines.append(f"  Token problemático: '{token_value}' (tipo: {token_type})")
    #                 else:
    #                     lines.append(f"  Token problemático: {token_type}")
                    
    #                 lines.append(f"  Mensaje: {error.get('message', 'Error desconocido')}")
    #                 lines.append("")
    #                 lines.append("-" * 70)
    #                 lines.append("")
                
    #             output = "\n".join(lines)
    #             self._print_to_terminal(output)
                
    #             # Mostrar diálogo con resumen
    #             self._show_syntax_error_dialog(parse_result['errors'])
                
    #     except Exception as e:
    #         error_msg = (
    #             f"[ERROR CRÍTICO] Falló el análisis sintáctico:\n\n"
    #             f"{str(e)}\n\n"
    #             f"Traceback:\n{traceback.format_exc()}"
    #         )
    #         self._print_to_terminal(error_msg)
    #         QtWidgets.QMessageBox.critical(
    #             self,
    #             "Error Crítico",
    #             f"Ocurrió un error inesperado durante el análisis:\n\n{str(e)}"
    #         )

    def _show_syntax_error_dialog(self, errors):
        """Muestra un diálogo con los errores sintácticos."""
        num_errors = len(errors)
        
        msg = f"""
        <h3>Errores Sintácticos Detectados</h3>
        <p><b>Total de errores:</b> <b style="color: #d32f2f;">{num_errors}</b></p>
        
        <p><b>Primeros errores:</b></p>
        <table style="font-family: monospace; font-size: 11px;">
        """
        
        for i, err in enumerate(errors[:5], 1):
            line = err.get('line', '?')
            col = err.get('column', '?')
            token = err.get('token', '?')
            
            msg += f"""
            <tr>
                <td style="padding: 4px;"><b>{i}.</b></td>
                <td style="padding: 4px;">Línea {line}, Col {col}</td>
                <td style="padding: 4px; color: #d32f2f;">{token}</td>
            </tr>
            """
        
        if num_errors > 5:
            msg += f"""
            <tr>
                <td colspan="3" style="padding: 4px;">
                    <i>... y {num_errors - 5} error(es) más</i>
                </td>
            </tr>
            """
        
        msg += """
        </table>
        <br>
        <p><i>Consulta la terminal para ver los detalles completos.</i></p>
        """
        
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Errores Sintácticos")
        msg_box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msg_box.setText(msg)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg_box.exec()