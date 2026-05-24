# -*- coding: utf-8 -*-
"""
Manejador de terminal
"""

from PyQt6 import QtCore


class TerminalController:
    """Controlador para manejo de la terminal integrada"""
    
    def __init__(self, ui):
        self.ui = ui
        self.terminal_visible = True
        self.splitter_sizes = None
        self.terminal_height = 200
        
        # Configurar el splitter inicial
        self._setup_splitter()
    
    def _setup_splitter(self):
        """Configurar el splitter con políticas de redimensionamiento"""
        self.ui.splitter.setStretchFactor(0, 1)  # tabBar puede expandirse
        self.ui.splitter.setStretchFactor(1, 0)  # terminal tiene tamaño fijo
        
        # Establecer tamaños iniciales después de que la ventana se muestre
        QtCore.QTimer.singleShot(100, self._set_initial_sizes)
    
    def _set_initial_sizes(self):
        """Establecer tamaños iniciales del splitter"""
        total_height = self.ui.splitter.height()
        if total_height > 0:
            # 70% para el editor, 30% para el terminal
            editor_height = int(total_height * 0.7)
            terminal_height = total_height - editor_height
            self.ui.splitter.setSizes([editor_height, terminal_height])
            self.splitter_sizes = [editor_height, terminal_height]
    
    def show_terminal(self):
        """Mostrar la terminal sin afectar el splitter"""
        if not self.terminal_visible:
            self.terminal_visible = True
            self.ui.terminal_txt.setVisible(True)
            
            # Restaurar los tamaños del splitter
            if self.splitter_sizes and len(self.splitter_sizes) >= 2:
                self.ui.splitter.setSizes(self.splitter_sizes)
            else:
                # Valores por defecto
                total_height = self.ui.splitter.height()
                editor_height = total_height - self.terminal_height
                self.ui.splitter.setSizes([editor_height, self.terminal_height])
                
            # Actualizar geometría del editor
            self._update_geometry()
    
    def hide_terminal(self):
        """Ocultar la terminal guardando el estado del splitter"""
        if self.terminal_visible:
            # Guardar los tamaños actuales
            current_sizes = self.ui.splitter.sizes()
            if len(current_sizes) >= 2 and current_sizes[1] > 0:
                self.splitter_sizes = current_sizes.copy()
                self.terminal_height = current_sizes[1]
            
            self.terminal_visible = False
            self.ui.terminal_txt.setVisible(False)
            
            # Hacer que el tabBar ocupe todo el espacio disponible
            if current_sizes:
                total_height = sum(current_sizes)
                self.ui.splitter.setSizes([total_height, 0])
                
            # Forzar actualización de la geometría
            self._update_geometry()
    
    def toggle_terminal(self):
        """Alternar la visibilidad de la terminal"""
        if self.terminal_visible:
            self.hide_terminal()
        else:
            self.show_terminal()
    
    def _update_geometry(self):
        """Actualizar la geometría del editor"""
        QtCore.QTimer.singleShot(10, self._do_update)
    
    def _do_update(self):
        """Realizar la actualización de geometría"""
        if hasattr(self.ui, 'tabBar'):
            self.ui.tabBar.updateGeometry()
        if hasattr(self.ui, 'tab_layout'):
            self.ui.tab_layout.update()
    
    def is_terminal_visible(self):
        """Verificar si la terminal está visible"""
        return self.terminal_visible