# -*- coding: utf-8 -*-
"""
Manejador de archivos para snaptics
"""

from PyQt6 import QtWidgets


class FileManager:
    """Manejador de operaciones de archivo"""
    
    def __init__(self, ui, main_window):
        self.ui = ui
        self.main_window = main_window
        self.current_file_path = None
        self.is_modified = False
    
    def new_file(self):
        """Crear nuevo archivo"""
        if self._check_unsaved_changes():
            return
        
        self.ui.code_txt.clear()
        self.current_file_path = None
        self.is_modified = False
        self._update_window_title("Nuevo archivo")
    
    def open_file(self):
        """Abrir archivo existente"""
        if self._check_unsaved_changes():
            return
        
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.main_window, "Abrir archivo", "", 
            "Archivos Python (*.py);;Archivos de texto (*.txt);;Todos los archivos (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.ui.code_txt.setPlainText(content)
                    self.current_file_path = file_path
                    self.is_modified = False
                    self._update_window_title(file_path)
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self.main_window, "Error", 
                    f"No se pudo abrir el archivo:\n{str(e)}"
                )
    
    def save_file(self):
        """Guardar archivo actual"""
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
        else:
            self.save_file_as()
    
    def save_file_as(self):
        """Guardar archivo con nuevo nombre"""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.main_window, "Guardar archivo como", "", 
            "Archivos Python (*.py);;Archivos de texto (*.txt);;Todos los archivos (*)"
        )
        
        if file_path:
            self._save_to_file(file_path)
            self.current_file_path = file_path
            self._update_window_title(file_path)
    
    def _save_to_file(self, file_path):
        """Guardar contenido en el archivo especificado"""
        try:
            content = self.ui.code_txt.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
                self.is_modified = False
                QtWidgets.QMessageBox.information(
                    self.main_window, "Guardado", "Archivo guardado correctamente"
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.main_window, "Error", 
                f"No se pudo guardar el archivo:\n{str(e)}"
            )
    
    def _check_unsaved_changes(self):
        """Verificar si hay cambios sin guardar"""
        if self.is_modified:
            reply = QtWidgets.QMessageBox.question(
                self.main_window, "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Desea guardarlos?",
                QtWidgets.QMessageBox.StandardButton.Yes | 
                QtWidgets.QMessageBox.StandardButton.No | 
                QtWidgets.QMessageBox.StandardButton.Cancel
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.save_file()
                return False
            elif reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                return True
        
        return False
    
    def _update_window_title(self, filename):
        """Actualizar el título de la ventana"""
        if filename == "Nuevo archivo":
            title = "snaptics - Nuevo archivo"
        else:
            import os
            title = f"snaptics - {os.path.basename(filename)}"
        
        if self.is_modified:
            title += " *"
        
        self.main_window.setWindowTitle(title)
    
    def mark_modified(self):
        """Marcar el archivo como modificado"""
        if not self.is_modified:
            self.is_modified = True
            current_title = self.main_window.windowTitle()
            if not current_title.endswith(" *"):
                self.main_window.setWindowTitle(current_title + " *")
    
    def get_current_file(self):
        """Obtener la ruta del archivo actual"""
        return self.current_file_path
    
    def is_file_modified(self):
        """Verificar si el archivo ha sido modificado"""
        return self.is_modified