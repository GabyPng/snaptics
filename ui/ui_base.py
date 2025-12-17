# -*- coding: utf-8 -*-
"""
Interfaz gráfica base generada desde compilerGUI.ui
Este archivo contiene solo la definición de la interfaz de usuario
"""

from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_snaptics(object):
    """Clase de interfaz base para snaptics"""
    
    def setupUi(self, snaptics):
        """Configurar la interfaz de usuario"""
        snaptics.setObjectName("snaptics")
        snaptics.resize(1024, 600)
        
        # Configurar paleta de colores
        self._setup_palette(snaptics)
        
        # Crear widget central
        self._setup_central_widget(snaptics)
        
        # Crear splitter y componentes principales
        self._setup_splitter()
        self._setup_editor()
        self._setup_terminal()
        
        # Configurar menús y acciones
        self._setup_menus(snaptics)
        self._setup_actions(snaptics)
        self._connect_menu_actions()
        
        # Aplicar traducciones
        self.retranslateUi(snaptics)
        self.tabBar.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(snaptics)
    
    def _setup_palette(self, snaptics):
        """Configurar la paleta de colores"""
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(156, 194, 255))
        brush.setStyle(QtCore.Qt.BrushStyle.SolidPattern)
        palette.setBrush(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Light, brush)
        palette.setBrush(QtGui.QPalette.ColorGroup.Inactive, QtGui.QPalette.ColorRole.Light, brush)
        palette.setBrush(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Light, brush)
        snaptics.setPalette(palette)
        snaptics.setDocumentMode(False)
    
    def _setup_central_widget(self, snaptics):
        """Configurar el widget central con layout"""
        self.centralwidget = QtWidgets.QWidget(parent=snaptics)
        self.centralwidget.setObjectName("centralwidget")
        
        # Layout principal
        self.main_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(0)
        
        snaptics.setCentralWidget(self.centralwidget)
    
    def _setup_splitter(self):
        """Configurar el splitter principal"""
        self.splitter = QtWidgets.QSplitter(parent=self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.splitter.setObjectName("splitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(3)
        
        self.main_layout.addWidget(self.splitter)
    
    def _setup_editor(self):
        """Configurar el área del editor con tabs"""
        # Tab widget principal
        self.tabBar = QtWidgets.QTabWidget(parent=self.splitter)
        self.tabBar.setObjectName("tabBar")
        # No se añaden aquí los estilos fijos para que los temas se integren correctamente
        
        # Tab principal con editor
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        
        # Layout para el tab
        self.tab_layout = QtWidgets.QVBoxLayout(self.tab)
        self.tab_layout.setContentsMargins(5, 5, 5, 5)
        self.tab_layout.setSpacing(0)
        
        # Editor de texto
        self.code_txt = QtWidgets.QPlainTextEdit(parent=self.tab)
        self.code_txt.setObjectName("code_txt")
        # Aquí tampoco :P
        
        self.tab_layout.addWidget(self.code_txt)
        self.tabBar.addTab(self.tab, "")
    
    def _setup_terminal(self):
        """Configurar el área de terminal"""
        self.terminal_txt = QtWidgets.QPlainTextEdit(parent=self.splitter)
        self.terminal_txt.setEnabled(True)
        self.terminal_txt.setObjectName("terminal_txt")
    
    def _setup_menus(self, snaptics):
        """Configurar la barra de menús"""
        self.menuBar = QtWidgets.QMenuBar(parent=snaptics)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 1024, 21))
        self.menuBar.setObjectName("menuBar")
        
        # Menús principales
        self.menuArchivo = QtWidgets.QMenu(parent=self.menuBar)
        self.menuArchivo.setObjectName("menuArchivo")
        
        self.menuEdit = QtWidgets.QMenu(parent=self.menuBar)
        self.menuEdit.setObjectName("menuEdit")
        
        self.menuView = QtWidgets.QMenu(parent=self.menuBar)
        self.menuView.setObjectName("menuView")
        
        self.menuRun = QtWidgets.QMenu(parent=self.menuBar)
        self.menuRun.setObjectName("menuRun")
        
        self.menuTheme = QtWidgets.QMenu(parent=self.menuBar)
        self.menuTheme.setObjectName("menuTheme")
        
        self.menuTerminal = QtWidgets.QMenu(parent=self.menuBar)
        self.menuTerminal.setObjectName("menuTerminal")
        
        self.menuHelp = QtWidgets.QMenu(parent=self.menuBar)
        self.menuHelp.setObjectName("menuHelp")
        
        snaptics.setMenuBar(self.menuBar)
    
    def _setup_actions(self, snaptics):
        """Crear todas las acciones del menú"""
        # Acciones de archivo
        self.actionNuevo = QtGui.QAction(parent=snaptics)
        self.actionNuevo.setObjectName("actionNuevo")
        
        self.actionOpen = QtGui.QAction(parent=snaptics)
        self.actionOpen.setObjectName("actionOpen")
        
        self.actionSave = QtGui.QAction(parent=snaptics)
        self.actionSave.setObjectName("actionSave")
        
        self.actionSave_As = QtGui.QAction(parent=snaptics)
        self.actionSave_As.setObjectName("actionSave_As")
        
        self.actionExit = QtGui.QAction(parent=snaptics)
        self.actionExit.setObjectName("actionExit")
        
        # Acciones de edición
        self.actionundo = QtGui.QAction(parent=snaptics)
        self.actionundo.setObjectName("actionundo")
        
        self.actionredo = QtGui.QAction(parent=snaptics)
        self.actionredo.setObjectName("actionredo")
        
        self.actioncopy = QtGui.QAction(parent=snaptics)
        self.actioncopy.setObjectName("actioncopy")
        
        self.actionpaste = QtGui.QAction(parent=snaptics)
        self.actionpaste.setObjectName("actionpaste")
        
        # Acciones de vista
        self.actionTokens = QtGui.QAction(parent=snaptics)
        self.actionTokens.setObjectName("actionTokens")
        
        self.actionSymbols = QtGui.QAction(parent=snaptics)
        self.actionSymbols.setObjectName("actionSymbols")
        
        # Acciones de ejecución
        self.actionCompile = QtGui.QAction(parent=snaptics)
        self.actionCompile.setObjectName("actionCompile")
        
        self.actionRun = QtGui.QAction(parent=snaptics)
        self.actionRun.setObjectName("actionRun")
        
        # Acciones de tema
        self.actionDark = QtGui.QAction(parent=snaptics)
        self.actionDark.setObjectName("actionDark")
        
        self.actionLight = QtGui.QAction(parent=snaptics)
        self.actionLight.setObjectName("actionLight")
        
        # Acciones de terminal
        self.actionNew_Terminal = QtGui.QAction(parent=snaptics)
        self.actionNew_Terminal.setObjectName("actionNew_Terminal")
        
        # Acción de ayuda
        self.actionAbout = QtGui.QAction(parent=snaptics)
        self.actionAbout.setObjectName("actionAbout")
        # Acción para mostrar errores
        self.actionErrors = QtGui.QAction(parent=snaptics)
        self.actionErrors.setObjectName("actionErrors")
    
    def _connect_menu_actions(self):
        """Conectar acciones a los menús"""
        # Menú Archivo
        self.menuArchivo.addAction(self.actionNuevo)
        self.menuArchivo.addAction(self.actionOpen)
        self.menuArchivo.addAction(self.actionSave)
        self.menuArchivo.addAction(self.actionSave_As)
        self.menuArchivo.addAction(self.actionExit)
        
        # Menú Edición
        self.menuEdit.addAction(self.actionundo)
        self.menuEdit.addAction(self.actionredo)
        self.menuEdit.addAction(self.actioncopy)
        self.menuEdit.addAction(self.actionpaste)
        
        # Menú Vista
        self.menuView.addAction(self.actionTokens)
        self.menuView.addAction(self.actionSymbols)
        
        # Menú Ejecutar
        self.menuRun.addAction(self.actionCompile)
        self.menuRun.addAction(self.actionRun)
        
        # Menú Tema
        self.menuTheme.addAction(self.actionDark)
        self.menuTheme.addAction(self.actionLight)
        
        # Menú Terminal
        self.menuTerminal.addAction(self.actionNew_Terminal)
        
        # Menú Ayuda
        self.menuHelp.addAction(self.actionErrors)
        self.menuHelp.addAction(self.actionAbout)
        
        # Agregar menús a la barra
        self.menuBar.addAction(self.menuArchivo.menuAction())
        self.menuBar.addAction(self.menuEdit.menuAction())
        self.menuBar.addAction(self.menuView.menuAction())
        self.menuBar.addAction(self.menuRun.menuAction())
        self.menuBar.addAction(self.menuTheme.menuAction())
        self.menuBar.addAction(self.menuTerminal.menuAction())
        self.menuBar.addAction(self.menuHelp.menuAction())
    
    def retranslateUi(self, snaptics):
        """Configurar textos y traducciones"""
        _translate = QtCore.QCoreApplication.translate
        
        # Ventana principal
        snaptics.setWindowTitle(_translate("snaptics", "snaptics"))
        
        # Tabs
        self.tabBar.setTabText(self.tabBar.indexOf(self.tab), _translate("snaptics", "Tab 1"))
        
        # Menús
        self.menuArchivo.setTitle(_translate("snaptics", "File"))
        self.menuEdit.setTitle(_translate("snaptics", "Edit"))
        self.menuView.setTitle(_translate("snaptics", "View"))
        self.menuRun.setTitle(_translate("snaptics", "Run"))
        self.menuTheme.setTitle(_translate("snaptics", "Theme"))
        self.menuHelp.setTitle(_translate("snaptics", "Help"))
        self.menuTerminal.setTitle(_translate("snaptics", "Terminal"))
        
        # Acciones de archivo
        self.actionNuevo.setText(_translate("snaptics", "New"))
        self.actionNuevo.setShortcut(_translate("snaptics", "Ctrl+N"))
        self.actionOpen.setText(_translate("snaptics", "Open"))
        self.actionOpen.setShortcut(_translate("snaptics", "Ctrl+O"))
        self.actionSave.setText(_translate("snaptics", "Save"))
        self.actionSave.setShortcut(_translate("snaptics", "Ctrl+S"))
        self.actionSave_As.setText(_translate("snaptics", "Save As"))
        self.actionSave_As.setShortcut(_translate("snaptics", "Ctrl+Shift+S"))
        self.actionExit.setText(_translate("snaptics", "Exit"))
        self.actionExit.setShortcut(_translate("snaptics", "Ctrl+Q"))
        
        # Acciones de edición
        self.actionundo.setText(_translate("snaptics", "Undo"))
        self.actionundo.setShortcut(_translate("snaptics", "Ctrl+Z"))
        self.actionredo.setText(_translate("snaptics", "Redo"))
        self.actionredo.setShortcut(_translate("snaptics", "Ctrl+Y"))
        self.actioncopy.setText(_translate("snaptics", "Copy"))
        self.actioncopy.setShortcut(_translate("snaptics", "Ctrl+C"))
        self.actionpaste.setText(_translate("snaptics", "Paste"))
        self.actionpaste.setShortcut(_translate("snaptics", "Ctrl+V"))
        
        # Acciones de vista
        self.actionTokens.setText(_translate("snaptics", "Tokens"))
        self.actionTokens.setShortcut(_translate("snaptics", "Ctrl+T"))
        self.actionSymbols.setText(_translate("snaptics", "Symbols"))
        
        # Acciones de ejecución
        self.actionCompile.setText(_translate("snaptics", "Compile"))
        self.actionCompile.setShortcut(_translate("snaptics", "F9"))
        self.actionRun.setText(_translate("snaptics", "Run"))
        self.actionRun.setShortcut(_translate("snaptics", "F5"))
        
        # Acciones de tema
        self.actionDark.setText(_translate("snaptics", "Dark"))
        self.actionLight.setText(_translate("snaptics", "Light"))
        
        # Acciones de ayuda
        self.actionAbout.setText(_translate("snaptics", "About"))
        self.actionAbout.setShortcut(_translate("snaptics", "Ctrl+H"))
        self.actionErrors.setText(_translate("snaptics", "Errors"))
        
        # Acciones de terminal
        self.actionNew_Terminal.setText(_translate("snaptics", "Terminal"))
        self.actionNew_Terminal.setShortcut(_translate("snaptics", "Ctrl+J"))
    


