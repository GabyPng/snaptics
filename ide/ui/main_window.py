# -*- coding: utf-8 -*-
"""
snaptics
"""

from PyQt6 import QtCore, QtWidgets, QtGui
import os
import traceback
import lexer # NO MOVER !!
import parser as syntax_parser
from parser import ASTNode
from semantic.semantic_analyzer import analyze as semantic_analyze
from ir_generator import generate_ir
from optimizer import optimize_ir
from .ui_base import Ui_snaptics
from .tokens_panel import TokensPanel
from .terminal_controller import TerminalController
from .file_manager import FileManager
from .theme_manager import ThemeManager
from .errors_panel import ErrorsPanel



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
        soporta numeración de líneas y otras utilidades. También crea un sistema de pestañas."""
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
        
        # Crear el editor de código
        new_editor = CodeEditor(parent)
        new_editor.setObjectName('code_txt')
        new_editor.setPlainText(old.toPlainText())
        # Copy font, tab stops and other properties
        new_editor.setFont(old.font())
        new_editor.setTabStopDistance(old.tabStopDistance())
        
        # Crear el visor del AST como árbol jerárquico
        self.ast_viewer = QtWidgets.QTreeWidget(parent)
        self.ast_viewer.setObjectName('ast_viewer')
        self.ast_viewer.setColumnCount(3)
        self.ast_viewer.setHeaderLabels(["Nodo", "Valor", "Línea"])
        self.ast_viewer.setAlternatingRowColors(True)
        self.ast_viewer.setExpandsOnDoubleClick(True)
        self.ast_viewer.header().setStretchLastSection(False)
        self.ast_viewer.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.ast_viewer.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.ast_viewer.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        # Crear el visor de IR (cuádruplas) como tabla
        self.ir_viewer = self._build_ir_table(parent, 'ir_viewer')

        # Crear el visor de IR Optimizada (cuádruplas tras IROptimizer)
        self.ir_opt_viewer = self._build_ir_table(parent, 'ir_opt_viewer')
        # Etiqueta de estadísticas que se mostrará encima de la tabla optimizada
        self.ir_opt_stats_label = QtWidgets.QLabel("Sin datos. Compile para ver la IR optimizada.", parent)
        self.ir_opt_stats_label.setObjectName('ir_opt_stats_label')
        self.ir_opt_stats_label.setStyleSheet("padding: 4px; font-weight: bold;")
        
        # Configurar color de selección y hover similar al del editor de código
        self.ast_viewer.setStyleSheet("""
            QTreeWidget::item:selected {
                background-color: rgb(220, 235, 255);
                color: black;
            }
            QTreeWidget::item:selected:!active {
                background-color: rgb(220, 235, 255);
                color: black;
            }
            QTreeWidget::item:hover {
                background-color: rgb(220, 235, 255);
                color: black;
            }
        """)
        
        # Find and replace within parent layout
        layout = parent.layout()
        if layout is not None:
            for i in range(layout.count()):
                it = layout.itemAt(i)
                if it is not None and it.widget() is old:
                    layout.insertWidget(i, new_editor)
                    layout.insertWidget(i + 1, self.ast_viewer)
                    layout.removeWidget(old)
                    old.setParent(None)
                    # Ocultar el AST viewer inicialmente
                    self.ast_viewer.hide()
                    break
        
        # Usar el tabBar existente de la UI para las pestañas
        if hasattr(self.ui, 'tabBar'):
            # Limpiar el tab existente y recrearlo con las dos vistas
            self.ui.tabBar.clear()
            # Crear contenedor para Code
            code_widget = QtWidgets.QWidget()
            code_layout = QtWidgets.QVBoxLayout(code_widget)
            code_layout.setContentsMargins(5, 5, 5, 5)
            code_layout.addWidget(new_editor)
            self.ui.tabBar.addTab(code_widget, "Code")
            
            # Crear contenedor para AST
            ast_widget = QtWidgets.QWidget()
            ast_layout = QtWidgets.QVBoxLayout(ast_widget)
            ast_layout.setContentsMargins(5, 5, 5, 5)
            ast_layout.addWidget(self.ast_viewer)
            self.ui.tabBar.addTab(ast_widget, "AST")

            # Crear contenedor para IR
            ir_widget = QtWidgets.QWidget()
            ir_layout = QtWidgets.QVBoxLayout(ir_widget)
            ir_layout.setContentsMargins(5, 5, 5, 5)
            ir_layout.addWidget(self.ir_viewer)
            self.ui.tabBar.addTab(ir_widget, "IR")

            # Crear contenedor para IR Optimizada
            ir_opt_widget = QtWidgets.QWidget()
            ir_opt_layout = QtWidgets.QVBoxLayout(ir_opt_widget)
            ir_opt_layout.setContentsMargins(5, 5, 5, 5)
            ir_opt_layout.addWidget(self.ir_opt_stats_label)
            ir_opt_layout.addWidget(self.ir_opt_viewer)
            self.ui.tabBar.addTab(ir_opt_widget, "IR Optimizada")

            # Mostrar los viewers ya que están en tabs
            self.ast_viewer.show()
            self.ir_viewer.show()
            self.ir_opt_viewer.show()
        
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
        # View > IR
        self.ui.actionIR.triggered.connect(self._open_ir_dialog)
        

        # Señal de ayuda
        self.ui.actionAbout.triggered.connect(self._show_about)
        
        # Help -> Errors
        try:
            self.ui.actionErrors.triggered.connect(self._show_errors_panel)
        except Exception:
            pass

    def _show_errors_panel(self):
        """Abrir el diálogo con la tabla de errores."""
        try:
            dlg = ErrorsPanel(self)
            dlg.exec()
        except Exception as e:
            self._print_to_terminal(f"[Errors] No se pudo abrir el panel de errores: {e}")
    
    def _setup_initial_state(self):
        """Configurar el estado inicial de la aplicación"""
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

            # Ejecutar análisis léxico
            lex_result = lexer.tokenize(text)
            
            # Guardar tokens para tabla de símbolos
            try:
                self.last_tokens = lex_result.get('tokens', []) if isinstance(lex_result, dict) else []
            except Exception:
                self.last_tokens = []

            # Actualizar panel de tokens
            if hasattr(self, 'tokens_panel'):
                self.tokens_panel.set_tokens(lex_result['tokens'])
                if lex_result['tokens']:
                    self.tokens_dock.show()

            # Verificar errores léxicos
            lexical_errors = lex_result['errors']
            has_lexical_errors = len(lexical_errors) > 0
            
            # Ejecutar análisis sintáctico
            parse_result = syntax_parser.parse(text)
            syntactic_errors = [
                err for err in parse_result.get('errors', [])
                if err.get('type') == 'syntax_error' or err.get('code', '').startswith('SYN-')
            ]
            has_syntactic_errors = len(syntactic_errors) > 0
            
            # Mostrar solo los errores
            if has_lexical_errors or has_syntactic_errors:
                lines = []
                
                if has_lexical_errors:
                    lines.append("✗ ERRORES LÉXICOS ENCONTRADOS")
                    lines.append("")
                    lexical_error_output = lexer.format_errors(lexical_errors)
                    lines.append(lexical_error_output)
                
                if has_syntactic_errors:
                    if has_lexical_errors:
                        lines.append("")
                    lines.append("✗ ERRORES SINTÁCTICOS ENCONTRADOS")
                    lines.append("")
                    syntactic_error_output = syntax_parser.format_syntax_errors(syntactic_errors, text)
                    lines.append(syntactic_error_output)
                
                self._print_to_terminal("\n".join(lines))

                self.last_ast = None
                
                # Mostrar mensaje de error
                total_errors = len(lexical_errors) + len(syntactic_errors)
                QtWidgets.QMessageBox.critical(
                    self,
                    "Errores de Compilación",
                    f"Se encontraron {total_errors} error(es) en total.\n\n"
                    f"• Errores léxicos: {len(lexical_errors)}\n"
                    f"• Errores sintácticos: {len(syntactic_errors)}\n\n"
                    f"Consulta la terminal para ver los detalles completos."
                )
            else:
                # Análisis semántico
                current_snp_path = self.file_manager.get_current_file()
                semantic_result = semantic_analyze(parse_result, source_path=current_snp_path)
                semantic_errors = semantic_result.get('errors', [])
                has_semantic_errors = len(semantic_errors) > 0

                if has_semantic_errors:
                    lines = ["✗ ERRORES SEMÁNTICOS ENCONTRADOS", ""]
                    for err in semantic_errors:
                        lines.append(str(err))
                    self._print_to_terminal("\n".join(lines))

                    self.last_ast = None
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Errores Semánticos",
                        f"Se encontraron {len(semantic_errors)} error(es) semántico(s).\n\n"
                        f"Consulta la terminal para ver los detalles completos."
                    )
                else:
                    # Guardar el AST para uso posterior
                    self.last_ast = parse_result['ast']
                    self.last_symbol_table = parse_result.get('symbol_table')

                    # Mostrar el AST en la pestaña correspondiente
                    self._display_ast(parse_result['ast'])

                    # Generar Representación Intermedia (cuádruplas)
                    ir_result = generate_ir(semantic_result, parse_result)
                    self.last_ir_result = ir_result

                    opt_result = None
                    if ir_result['success']:
                        self._display_ir(ir_result['quadruples'])

                        # Fase de optimización sobre la IR
                        opt_result = optimize_ir(ir_result)
                        self.last_opt_result = opt_result
                        self._display_ir_optimized(opt_result)

                    # Generación de codigo objeto (.asm para emu8086).
                    # Se ejecuta solo si la optimizacion fue exitosa.
                    asm_summary = ""
                    if opt_result and opt_result.get('success'):
                        asm_summary = self._generate_asm(text, current_snp_path)

                    # Mostrar mensaje en terminal con reporte del optimizador
                    terminal_lines = ["Compilación exitosa"]
                    if opt_result and opt_result.get('success'):
                        terminal_lines.append("")
                        terminal_lines.append(opt_result.get('report', ''))
                    if asm_summary:
                        terminal_lines.append("")
                        terminal_lines.append(asm_summary)
                    self._print_to_terminal("\n".join(terminal_lines))

                    # Cambiar automáticamente a la pestaña de IR Optimizada
                    if hasattr(self.ui, 'tabBar'):
                        self.ui.tabBar.setCurrentIndex(3)  # Índice 3 = IR Optimizada

                    # Mostrar mensaje de éxito
                    num_tokens = len(lex_result['tokens'])
                    num_quads = len(ir_result.get('quadruples', []))
                    opt_summary = ""
                    if opt_result and opt_result.get('success'):
                        before = len(opt_result.get('original', []))
                        after = len(opt_result.get('quadruples', []))
                        reduction = opt_result.get('reduction', before - after)
                        pct = (reduction * 100.0 / before) if before else 0.0
                        opt_summary = (
                            f"• IR optimizada: {before} → {after} "
                            f"(reducción {reduction}, {pct:.1f}%)\n"
                        )
                    QtWidgets.QMessageBox.information(
                        self,
                        "Compilación Exitosa",
                        f"La compilación se completó sin errores.\n\n"
                        f"• Tokens generados: {num_tokens}\n"
                        f"• AST generado correctamente\n"
                        f"• Cuádruplas generadas: {num_quads}\n"
                        f"{opt_summary}"
                        f"{('• ' + asm_summary) if asm_summary else ''}"
                    )
                
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

    def _generate_asm(self, source: str, source_path: str | None) -> str:
        """Genera el .asm objetivo emu8086 y lo escribe en codegen/build/.
        Devuelve una linea-resumen para mostrar en el dialogo y la terminal.
        Cualquier fallo se loggea pero no aborta la compilacion del IDE.
        """
        try:
            from codegen.build import compile_snaptics, _HERE as _CODEGEN_HERE
            if source_path:
                basename = os.path.splitext(os.path.basename(source_path))[0]
            else:
                basename = 'untitled'
            result = compile_snaptics(source, source_path=source_path,
                                      output_basename=basename)
            if not result.get('ok'):
                stage = result.get('stage', '?')
                errs = result.get('errors', [])
                detail = "\n".join(f"  {e}" for e in errs)
                return (
                    f"Codegen ({stage}) reporto {len(errs)} error(es):\n"
                    f"{detail}"
                )

            build_dir = os.path.join(_CODEGEN_HERE, 'build')
            os.makedirs(build_dir, exist_ok=True)
            out_path = os.path.join(build_dir, basename + '.asm')
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(result['asm'])

            return f"ASM generado: {out_path}"
        except Exception as e:
            return f"Codegen fallo: {e}\n{traceback.format_exc()}"

    def _display_ast(self, ast):
        """Mostrar el AST formateado en un árbol jerárquico."""
        if not hasattr(self, 'ast_viewer'):
            return
        
        try:
            # Limpiar el árbol
            self.ast_viewer.clear()
            
            # Crear el nodo raíz y construir el árbol
            if ast:
                self._build_ast_tree(ast, self.ast_viewer.invisibleRootItem())
                # Expandir el primer nivel para mostrar la estructura principal
                self.ast_viewer.expandToDepth(1)
            
        except Exception as e:
            # Si falla, mostrar error en el árbol
            error_item = QtWidgets.QTreeWidgetItem([f"Error: {str(e)}", "", ""])
            self.ast_viewer.addTopLevelItem(error_item)
    
    def _build_ir_table(self, parent, object_name: str):
        """Construye una QTableWidget configurada para mostrar cuádruplas."""
        table = QtWidgets.QTableWidget(parent)
        table.setObjectName(object_name)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["#", "Operador", "Arg1", "Arg2", "Resultado"])
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        return table

    def _populate_ir_table(self, table, quadruples):
        """Llena una tabla de cuádruplas con la lista provista."""
        if table is None:
            return
        try:
            table.setRowCount(0)
            table.setRowCount(len(quadruples))
            for i, q in enumerate(quadruples):
                a1 = str(q.arg1) if q.arg1 is not None else ''
                a2 = str(q.arg2) if q.arg2 is not None else ''
                res = str(q.result) if q.result is not None else ''
                table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i)))
                table.setItem(i, 1, QtWidgets.QTableWidgetItem(q.op))
                table.setItem(i, 2, QtWidgets.QTableWidgetItem(a1))
                table.setItem(i, 3, QtWidgets.QTableWidgetItem(a2))
                table.setItem(i, 4, QtWidgets.QTableWidgetItem(res))
        except Exception as e:
            table.setRowCount(1)
            table.setItem(0, 0, QtWidgets.QTableWidgetItem(f"Error: {e}"))

    def _display_ir(self, quadruples):
        """Mostrar las cuádruplas (sin optimizar) en la pestaña IR."""
        self._populate_ir_table(getattr(self, 'ir_viewer', None), quadruples)

    def _display_ir_optimized(self, opt_result: dict):
        """Mostrar la IR optimizada y sus estadísticas en la pestaña IR Optimizada."""
        viewer = getattr(self, 'ir_opt_viewer', None)
        label = getattr(self, 'ir_opt_stats_label', None)
        if viewer is None:
            return

        quads = opt_result.get('quadruples', [])
        self._populate_ir_table(viewer, quads)

        if label is None:
            return
        if not opt_result.get('success'):
            label.setText("La optimización no se ejecutó.")
            return

        original = opt_result.get('original', [])
        stats = opt_result.get('stats', {}) or {}
        before, after = len(original), len(quads)
        reduction = opt_result.get('reduction', before - after)
        pct = (reduction * 100.0 / before) if before else 0.0
        applied = sum(1 for c in stats.values() if c > 0)
        label.setText(
            f"Cuádruplas: {before} -> {after}   "
            f"|   Reducción: {reduction} ({pct:.1f}%)   "
            f"|   Pases con cambios: {applied}/{len(stats)}"
        )

    def _build_ast_tree(self, node, parent_item):
        """Construir recursivamente el árbol del AST."""
        if node is None:
            return
        
        if isinstance(node, ASTNode):
            # Obtener el tipo y la línea
            node_type = node.type
            line = str(node.properties.get('line', '')) if node.properties.get('line') else ""
            
            # Crear item para este nodo
            node_item = QtWidgets.QTreeWidgetItem(parent_item, [node_type, "", line])
            node_item.setExpanded(False)
            
            # Agregar propiedades simples como hijos
            for key, val in node.properties.items():
                if key == 'line':
                    continue
                    
                if isinstance(val, ASTNode):
                    # Propiedad que es un nodo: crear un hijo con el nombre de la propiedad
                    prop_item = QtWidgets.QTreeWidgetItem(node_item, [f"{key}", "", ""])
                    self._build_ast_tree(val, prop_item)
                    
                elif isinstance(val, list):
                    if not val:
                        continue
                    # Lista: crear un nodo contenedor
                    list_item = QtWidgets.QTreeWidgetItem(node_item, [f"{key} ({len(val)} items)", "", ""])
                    for idx, item in enumerate(val):
                        if isinstance(item, ASTNode):
                            self._build_ast_tree(item, list_item)
                        else:
                            # Item simple en la lista
                            QtWidgets.QTreeWidgetItem(list_item, [f"[{idx}]", str(item), ""])
                else:
                    # Propiedad simple: mostrar como hijo directo
                    QtWidgets.QTreeWidgetItem(node_item, [key, str(val), ""])
        
        elif isinstance(node, dict):
            # Manejar diccionarios
            node_type = node.get('type', 'Unknown')
            line = str(node.get('line', '')) if node.get('line') else ""
            
            node_item = QtWidgets.QTreeWidgetItem(parent_item, [node_type, "", line])
            node_item.setExpanded(False)
            
            for key, val in node.items():
                if key in ['type', 'line']:
                    continue
                    
                if isinstance(val, dict):
                    prop_item = QtWidgets.QTreeWidgetItem(node_item, [f"{key}", "", ""])
                    self._build_ast_tree(val, prop_item)
                    
                elif isinstance(val, list):
                    if not val:
                        continue
                    list_item = QtWidgets.QTreeWidgetItem(node_item, [f"{key} ({len(val)} items)", "", ""])
                    for item in val:
                        self._build_ast_tree(item, list_item)
                else:
                    QtWidgets.QTreeWidgetItem(node_item, [key, str(val), ""])
    
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
        # Usar la tabla de símbolos generada por el parser si existe
        symbols_list = []
        if hasattr(self, 'last_symbol_table') and self.last_symbol_table:
            symbols_list = self.last_symbol_table.get_all()
        
        if not symbols_list:
            QtWidgets.QMessageBox.information(self, "Tabla de Símbolos", "No hay símbolos disponibles. Compile el código primero.")
            return

        try:
            # Crear diálogo con tabla
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Symbol Table")
            layout = QtWidgets.QVBoxLayout(dialog)

            table = QtWidgets.QTableWidget(parent=dialog)
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Name", "Category", "Type", "Line"])
            table.setRowCount(len(symbols_list))
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            table.horizontalHeader().setStretchLastSection(True)

            # Ordenar por número de línea (asc)
            def _sort_key(item):
                ln_val = item.line
                sort_ln = ln_val if ln_val > 0 else float('inf')
                return (sort_ln, item.name.lower())

            for i, sym in enumerate(sorted(symbols_list, key=_sort_key)):
                table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(sym.name)))
                table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(sym.category)))
                table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(sym.data_type)))
                table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(sym.line)))

            layout.addWidget(table)
            buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close, parent=dialog)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            dialog.resize(550, 350)
            dialog.exec()
        except Exception as e:
            self._print_to_terminal(f"[Symbols] Error al generar tabla de símbolos:\n{e}")

    def _open_ir_dialog(self):
        """Abrir diálogo con las cuádruplas de la Representación Intermedia."""
        ir_result = getattr(self, 'last_ir_result', None)
        if not ir_result or not ir_result.get('quadruples'):
            QtWidgets.QMessageBox.information(
                self, "IR Cuádruplas",
                "No hay cuádruplas disponibles. Compile el código primero."
            )
            return

        try:
            quads = ir_result['quadruples']

            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Representación Intermedia (Cuádruplas)")
            layout = QtWidgets.QVBoxLayout(dialog)

            table = QtWidgets.QTableWidget(parent=dialog)
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["#", "Operador", "Arg1", "Arg2", "Resultado"])
            table.setRowCount(len(quads))
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            table.setAlternatingRowColors(True)
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setSectionResizeMode(
                0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
            )

            for i, q in enumerate(quads):
                a1 = str(q.arg1) if q.arg1 is not None else ''
                a2 = str(q.arg2) if q.arg2 is not None else ''
                res = str(q.result) if q.result is not None else ''
                table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i)))
                table.setItem(i, 1, QtWidgets.QTableWidgetItem(q.op))
                table.setItem(i, 2, QtWidgets.QTableWidgetItem(a1))
                table.setItem(i, 3, QtWidgets.QTableWidgetItem(a2))
                table.setItem(i, 4, QtWidgets.QTableWidgetItem(res))

            layout.addWidget(table)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Close, parent=dialog
            )
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            dialog.resize(700, 400)
            dialog.exec()
        except Exception as e:
            self._print_to_terminal(f"[IR] Error al generar tabla de cuádruplas:\n{e}")

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