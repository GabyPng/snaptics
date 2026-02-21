#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snaptics
"""

def main():
    """Función principal de la aplicación"""
    import sys
    
    try:
        from PyQt6 import QtWidgets
        from ui import SnapticsMainWindow
        
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("snaptics")
        app.setApplicationVersion("2.0")
        
        window = SnapticsMainWindow()
        window.show()
        
        return app.exec()
        
    except ImportError as e:
        print("Error de importación:")
        print(f"   {e}")
        if 'PyQt6' in str(e):
            print("\nSolución:")
            print("   pip install PyQt6")
        return 1
        
    except Exception as e:
        print(f"Error al inicializar snaptics: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())