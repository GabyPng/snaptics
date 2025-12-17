# -*- coding: utf-8 -*-
"""
Panel de errores: muestra una tabla con los errores posibles.
"""
from PyQt6 import QtWidgets, QtCore


class ErrorsPanel(QtWidgets.QDialog):
	"""Diálogo que muestra una tabla con los errores definidos."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Errors")
		self.resize(760, 360)

		layout = QtWidgets.QVBoxLayout(self)

		self.table = QtWidgets.QTableWidget(parent=self)
		self.table.setColumnCount(5)
		self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Descripción", "Ejemplo", "Solución"])
		self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
		self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.horizontalHeader().setStretchLastSection(True)
		self.table.verticalHeader().setVisible(False)

		layout.addWidget(self.table)

		buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close, parent=self)
		buttons.rejected.connect(self.reject)
		buttons.accepted.connect(self.accept)
		layout.addWidget(buttons)

		# Cargar errores por defecto
		self._load_default_errors()

	def _load_default_errors(self):
		errors = [
			# ========= Errores lexicos =========
            {
				'id': 'LEX-101',
				'nombre': 'Signo de puntuacion inicial',
				'descripcion': 'Uso signos de interrogacion o exclamacion de apertura',
				'ejemplo': '¿pregunta? o ¡valor!',
				'solucion': 'Eliminar los signos de apertura'
			},
			{
				'id': 'LEX-102',
				'nombre': 'Símbolo arroba',
				'descripcion': 'El símbolo @ solo es válido dentro de cadenas',
				'ejemplo': 'promedi@_bajo',
				'solucion': 'Reemplazar o eliminar el símbolo @'
            },
			{
				'id': 'LEX-103',
				'nombre': 'Símbolo de moneda',
				'descripcion': 'El símbolo $ es inválido',
				'ejemplo': 'promedio$',
				'solucion': 'Reemplazar o eliminar el símbolo $'
            },
			{
				'id': 'LEX-104',
				'nombre': 'Símbolo porcentaje',
				'descripcion': 'El símbolo % es inválido',
				'ejemplo': 'promedio%',
				'solucion': 'Eliminar o utilizar división /'    
            },
			
            # ========= Errores de delimitadores =========

			{
				'id': 'LEX-201',
                'nombre': 'Corchetes',
				'descripcion': 'Los delimitadores [] son inválidos',
				'ejemplo': 'array[0]',
                'solucion': 'Usar delimitadores ()'
            },
			{
				'id': 'LEX-202',
                'nombre': 'Llaves',
				'descripcion': 'Los delimitadores {} son inválidos',
				'ejemplo': '{x, y, z}',
                'solucion': 'Usar delimitadores ()'
            },
			
            # ========= Errores de operadores =========
			
			{
				'id': 'LEX-301',
                'nombre': 'Operador pipe',
				'descripcion': 'El operador | es inválido',
				'ejemplo': 'this | that',
                'solucion': 'Eliminar operador inválido'
            },
			{
				'id': 'LEX-302',
                'nombre': 'Operador doble pipe',
				'descripcion': 'El operador || es inválido',
				'ejemplo': 'this || that',
                'solucion': 'Eliminar operador inválido'
            },
            {
				'id': 'LEX-303',
                'nombre': 'Operador ampersand',
				'descripcion': 'El operador & es inválido',
				'ejemplo': 'this & that',
                'solucion': 'Eliminar operador inválido'
            },
			{
				'id': 'LEX-304',
                'nombre': 'Operador doble ampersand',
				'descripcion': 'El operador && es inválido',
				'ejemplo': 'this && that',
                'solucion': 'Eliminar operador inválido'
            },
			{
				'id': 'LEX-305',
                'nombre': 'Operador negación',
				'descripcion': 'El operador ! por si solo es inválido',
				'ejemplo': '!this',
                'solucion': 'Completar operador !=, reemplazar con NOT, o eliminar operador inválido'
            },
			
            # ========= Errores de sintaxis =========

			{
				'id': 'LEX-401',
                'nombre': 'Símbolo semicolon',
				'descripcion': 'El símbolo ; es innecesario para fin de línea',
				'ejemplo': 'fact x = 10;',
                'solucion': 'Eliminar símbolo innecesario'
            },
			{
				'id': 'LEX-402',
                'nombre': 'Símbolo barra invertida',
				'descripcion': 'El símbolo \\ solo es válido dentro de cadenas',
				'ejemplo': 'path \\ to \\ file',
				'solucion': 'Reemplazar o eliminar el símbolo \\'
            },
			
            # ========= Errores de caracteres =========
            
            {
				'id': 'LEX-501',
                'nombre': 'Símbolo acentuado',
				'descripcion': 'Los símbolos acentuados son inválidos',
				'ejemplo': 'análisis',
                'solucion': 'Reemplazar o eliminar símbolos acentuados'
            },
			{
				'id': 'LEX-502',
                'nombre': 'Unicode inválido',
				'descripcion': 'Caracteres unicode fuera del rango ASCII',
				'ejemplo': '小红书',
                'solucion': 'Eliminar caracteres unicode inválidos'
            },
			{
				'id': 'LEX-503',
                'nombre': 'Cáracter inválido',
				'descripcion': 'Caracteres como backtick o tilde son inválidos',
				'ejemplo': 'variable` o value~',
                'solucion': 'Eliminar caracteres inválidos'
            },
			
            # ========= Errores de cadenas y comentarios =========
			{
				'id': 'LEX-601',
                'nombre': 'Cadena de texto sin cerrar',
				'descripcion': 'Falta de comillas de cierre',
				'ejemplo': '"texto sin cerrar...',
                'solucion': 'Agregar comillas de cierre'
            },
			{
				'id': 'LEX-602',
                'nombre': 'Error en cadena de texto',
				'descripcion': 'Error general en el formato de la cadena de texto',
				'ejemplo': '"error"en texto"',
                'solucion': 'Verficiar y corregir el formato de la cadena'
            },
			{
				'id': 'LEX-603',
                'nombre': 'Comentario sin cerrar',
				'descripcion': 'Falta de cierre en un comentario',
				'ejemplo': '/* comentario sin cerrar...',
                'solucion': 'Agregar cierre */ al comentario'
            },
			{
				'id': 'LEX-604',
                'nombre': 'Error en comentario',
				'descripcion': 'Error general en el formato del comentario',
				'ejemplo': '/* comentario */ erroneo */',
                'solucion': 'Verficiar y corregir el formato del comentario'
            },
			
            # ========= Errores de palabras reservadas =========
			
            {
				'id': 'LEX-701',
                'nombre': 'Palabra reservada erronea',
				'descripcion': 'Error tipográfico en palabra reservada',
				'ejemplo': 'fakt',
                'solucion': 'Corregir la palabra reservada (fact)'
            },
			
            # ========= Error general =========
            {
				'id': 'LEX-801',
                'nombre': 'Carácter ilegal',
				'descripcion': 'Carácter general no reconocido por el analizador léxico',
				'ejemplo': '',
                'solucion': 'Reemplazar o eliminar el carácter ilegal'
            }
		]

		self.set_errors(errors)

	def set_errors(self, errors):
		"""Poblar la tabla con una lista de errores (lista de dicts)."""
		self.table.setRowCount(len(errors))
		for r, e in enumerate(errors):
			self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(e.get('id', ''))))
			self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(e.get('nombre', ''))))
			self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(e.get('descripcion', ''))))
			self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(e.get('ejemplo', ''))))
			self.table.setItem(r, 4, QtWidgets.QTableWidgetItem(str(e.get('solucion', ''))))

		# Ajustar tamaños de columna para legibilidad
		self.table.resizeColumnsToContents()
