# -*- coding: utf-8 -*-
"""
Manejador de temas
"""

import json
import os


class ThemeManager:
    """Manejador de temas de la interfaz"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        self.current_theme = self.load_theme()
        self.apply_current_theme()
    
    def apply_current_theme(self):
        """Aplicar el tema actual"""
        if self.current_theme == "dark":
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
    
    def load_theme(self):
        """Cargar el tema desde el archivo de configuración"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('theme', 'light')
        except Exception:
            pass
        return 'light'
    
    def save_theme(self):
        """Guardar el tema actual en el archivo de configuración"""
        try:
            config = {'theme': self.current_theme}
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass
    
    def apply_dark_theme(self):
        """Aplicar tema oscuro"""
        dark_style = """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QPlainTextEdit {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #555555;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 11pt;
            line-height: 1.2;
            selection-background-color: #4a90e2;
            selection-color: #ffffff;
        }
        QTabWidget::pane {
            background-color: #2b2b2b;
            border: 1px solid #555555;
            top: -1px;
        }
        QTabWidget::tab-bar {
            alignment: left;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
            border: 1px solid #555555;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background-color: #2b2b2b;
            color: #ffffff;
            border-bottom: 1px solid #2b2b2b;
        }
        QTabBar::tab:!selected {
            background-color: #3c3c3c;
            color: #cccccc;
        }
        QTabBar::tab:hover {
            background-color: #4c4c4c;
            color: #ffffff;
        }
        QMenuBar {
            background-color: #2b2b2b;
            color: #ffffff;
            border-bottom: 1px solid #555555;
        }
        QMenuBar::item {
            padding: 4px 8px;
            background-color: transparent;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #3c3c3c;
            color: #ffffff;
        }
        QMenu {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QMenu::item {
            padding: 6px 20px;
            color: #ffffff;
        }
        QMenu::item:selected {
            background-color: #3c3c3c;
            color: #ffffff;
        }
        QSplitter::handle {
            background-color: #555555;
        }
        QSplitter::handle:hover {
            background-color: #666666;
        }
        """
        
        self.main_window.setStyleSheet(dark_style)
        self.current_theme = "dark"
        self.save_theme()
    
    def apply_light_theme(self):
        """Aplicar tema claro"""
        light_style = """
        QMainWindow {
            background-color: #ffffff;
            color: #000000;
        }
        QWidget {
            background-color: #ffffff;
            color: #000000;
        }
        QPlainTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 11pt;
            line-height: 1.2;
            selection-background-color: #4a90e2;
            selection-color: #ffffff;
        }
        QTabWidget::pane {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            top: -1px;
        }
        QTabWidget::tab-bar {
            alignment: left;
        }
        QTabBar::tab {
            background-color: #f0f0f0;
            color: #000000;
            padding: 8px 16px;
            margin-right: 2px;
            border: 1px solid #cccccc;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #000000;
            border-bottom: 1px solid #ffffff;
        }
        QTabBar::tab:!selected {
            background-color: #f0f0f0;
            color: #666666;
        }
        QTabBar::tab:hover {
            background-color: #e0e0e0;
            color: #000000;
        }
        QMenuBar {
            background-color: #ffffff;
            color: #000000;
            border-bottom: 1px solid #cccccc;
        }
        QMenuBar::item {
            padding: 4px 8px;
            background-color: transparent;
            color: #000000;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
            color: #000000;
        }
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
        }
        QMenu::item {
            padding: 6px 20px;
            color: #000000;
        }
        QMenu::item:selected {
            background-color: #e0e0e0;
            color: #000000;
        }
        QSplitter::handle {
            background-color: #cccccc;
        }
        QSplitter::handle:hover {
            background-color: #aaaaaa;
        }
        """
        
        self.main_window.setStyleSheet(light_style)
        self.current_theme = "light"
        self.save_theme()
    
    def get_current_theme(self):
        """Obtener el tema actual"""
        return self.current_theme
    
    def toggle_theme(self):
        """Alternar entre tema claro y oscuro"""
        if self.current_theme == "light":
            self.apply_dark_theme()
        else:
            self.apply_light_theme()