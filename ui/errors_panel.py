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
				'id': 'LEX-999',
                'nombre': 'Carácter ilegal',
				'descripcion': 'Carácter general no reconocido por el analizador léxico',
				'ejemplo': '',
                'solucion': 'Reemplazar o eliminar el carácter ilegal'
            }

			# ========= Errores de declaraciones =========
			
			{
				'id': 'SYN-101',
                'nombre': 'Declaración de dataset incompleta',
				'descripcion': 'La declaración del dataset no está compelta',
				'ejemplo': 'dataset ventas =',
                'solucion': 'Completar con import from "file.csv" o select ... from ...'
            },
			{
				'id': 'SYN-102',
                'nombre': 'Declaración de hecho incompleta',
				'descripcion': 'La declaración del hecho esta incompleta',
				'ejemplo': 'fact ventas_altas =',
                'solucion': 'Completar P(condición)'
            },
			{
				'id': 'SYN-103',
                'nombre': 'Declaración de regla incompleta',
				'descripcion': 'La declaración de la regla está incompleta',
				'ejemplo': 'rule mi_regla :-',
                'solucion': 'Agregar la condición después de :-'
            },
			{
				'id': 'SYN-104',
                'nombre': 'Declaración d econsulta incompleta',
				'descripcion': 'La consulta está incompleta',
				'ejemplo': 'query',
                'solucion': 'Agregar el identificador de la consulta'
            },
			{
				'id': 'SYN-105',
                'nombre': 'Falta operador de asignación',
				'descripcion': 'Falta el operador = en la declaración',
				'ejemplo': 'dataset ventas import from "files.csv"',
                'solucion': 'Agregar = antes de la expresión'
            },

			# ========= Errores de expresion =========

			{
				'id': 'SYN-201',
                'nombre': 'Falta operando en expresión',
				'descripcion': 'Falta un operando en la operación',
				'ejemplo': 'x = 5 + ',
                'solucion': 'Agregar el operando faltante: x = 5 + 3'
            },
			{
				'id': 'SYN-202',
                'nombre': 'Expresión invalida',
				'descripcion': 'La expresión no es sintácticamente correcta',
				'ejemplo': 'x = + 5',
                'solucion': 'Verificar y corregir la sintaxis'
            },
			{
				'id': 'SYN-203',
                'nombre': 'Falta operador',
				'descripcion': 'Falta un operador entre operandos',
				'ejemplo': 'x = 5 3',
                'solucion': 'Agregar operador faltante: x = 5 + 3'
            },
			{
				'id': 'SYN-204',
                'nombre': 'Token inesperado en expresión',
				'descripcion': 'Token que no se esperaba en este contexto',
				'ejemplo': 'x = 5 , 3',
                'solucion': 'Verificar la sintaxis de la expresión'
            },

			# ========= Errores de parentesis y delimitadores =========

			{
				'id': 'SYN-301',
                'nombre': 'Falta paréntesis de apertura',
				'descripcion': 'Falta el paréntesis de apertura (',
				'ejemplo': 'fact x = P ventas > 10)',
                'solucion': 'Agregar ( antes del operando )'
            },
			{
				'id': 'SYN-302',
                'nombre': 'Falta paréntesis de cierre',
				'descripcion': 'Falta el paréntesis de cierre )',
				'ejemplo': 'fact x = P (ventas > 10',
                'solucion': 'Agregar ) después del operando ('
            },
			{
				'id': 'SYN-303',
                'nombre': 'Paréntesis sin correspondencia',
				'descripcion': 'Los paréntesis no están balanceados',
				'ejemplo': 'x = ((5 + 3)',
				'solucion': 'Verificar y balancear los paréntesis'
            },
			{
				'id': 'SYN-304',
                'nombre': 'Falta coma en lista',
				'descripcion': 'Falta una coma entre elementos de lista',
				'ejemplo': 'select x y z from datos',
                'solucion': 'agregar comas: select x, y, z from datos'
            },
			{
				'id': 'SYN-305',
                'nombre': 'Coma inesperada',
				'descripcion': 'Coma en posición incorrecta',
				'ejemplo': 'fact x = ,5',
                'solucion': 'Eliminar o corregir la posición de la coma'
            },

			# ========= Errores de clausulas =========
			{
				'id': 'SYN-401',
                'nombre': 'Falta cláusula FROM',
				'descripcion': 'Falta la cláusula from en importación o selección',
				'ejemplo': 'dataset x = import "file.csv"',
                'solucion': 'Agregar from: import from "file.csv"'
            },
			{
				'id': 'SYN-402',
                'nombre': 'Condición WHERE incompleta',
				'descripcion': 'La condición después de where está incompleta',
				'ejemplo': 'select x from datos where',
                'solucion': 'Completar la condición: where x > 5'
            },
			{
				'id': 'SYN-403',
                'nombre': 'Cláusula SELECT inválida',
				'descripcion': 'La sintaxis de select es incorrecta',
				'ejemplo': 'dataset x = select from datos',
                'solucion': 'Especificar columnas: select col1, col2 from datos'
            },
			{
				'id': 'SYN-404',
                'nombre': 'Falta cláusula GIVEN',
				'descripcion': 'Falta given en probabilidad condicional',
				'ejemplo': 'P(A B)',
                'solucion': 'Usar sintaxis correcta: P(A given B)'
            },

			# ========= Errores de identificadores =========
			{
				'id': 'SYN-501',
                'nombre': 'Falta identificador',
				'descripcion': 'Se esperaba un identificador',
				'ejemplo': 'fact = P(x > 5)',
                'solucion': 'Agregar nombre: fact ventas_altas = P(x > 5)'
            },
			{
				'id': 'SYN-502',
                'nombre': 'Identificador inválido',
				'descripcion': 'El identificador no es válido en este contexto',
				'ejemplo': 'dataset 123 = import from "file.csv"',
                'solucion': 'Usar identificador válido que comience con letra'
            },
			{
				'id': 'SYN-503',
                'nombre': 'Identificador duplicado',
				'descripcion': 'El identificador ya fue declarado',
				'ejemplo': 'Dos fact x = en el mismo alcance',
                'solucion': 'Usar nombres únicos para cada declaración'
            },
			
			# ========= Errores de valores y literales =========

			{
				'id': 'SYN-601',
                'nombre': 'Falta valor',
				'descripcion': 'Falta un valor en la expresión',
				'ejemplo': 'x =',
                'solucion': 'Agregar el valor: x = 10'
            },
			{
				'id': 'SYN-602',
                'nombre': 'Número inválido',
				'descripcion': 'El formato del número no es correcto',
				'ejemplo': 'x = 12.34.56',
                'solucion': 'Corregir el formato: x = 12.34'
            },
			{
				'id': 'SYN-603',
                'nombre': 'Cadena inválida',
				'descripcion': 'La cadena de texto tiene formato incorrecto',
				'ejemplo': 'Cadena mal formada',
                'solucion': 'Verificar comillas y escapes'
            },
			{
				'id': 'SYN-604',
                'nombre': 'Falta cadena de texto',
				'descripcion': 'Se esperaba una cadena de texto',
				'ejemplo': 'import from',
                'solucion': 'Agregar la ruta: import from "data.csv"'
            },

			# ========= Errores de operadores =========
			{
				'id': 'SYN-701',
                'nombre': 'Operador inválido',
				'descripcion': 'El operador no es válido en este contexto',
				'ejemplo': 'Uso incorrecto de operador',
                'solucion': 'Verificar la sintaxis del operador'
            },
			{
				'id': 'SYN-702',
                'nombre': 'Falta operador relacional',
				'descripcion': 'Falta un operador de comparación',
				'ejemplo': 'where x 5',
                'solucion': 'Agregar operador: where x > 5'
            },
			{
				'id': 'SYN-703',
                'nombre': 'Operador lógico inválido',
				'descripcion': 'El operador lógico no es correcto',
				'ejemplo': 'Uso incorrecto de and/or/not,
                'solucion': 'Verificar la sintaxis lógica'
            },

			# ========= Errores de probabilidad =========

			{
				'id': 'SYN-801',
                'nombre': 'Expresión de probabilidad inválida',
				'descripcion': 'La sintaxis de P() es incorrecta',
				'ejemplo': 'P()',
                'solucion': 'Agregar condición: P(x > 5)'
            },
			{
				'id': 'SYN-802',
                'nombre': 'Falta condición en probabilidad',
				'descripcion': 'Falta la condición dentro de P()',
				'ejemplo': 'fact x = P()',
                'solucion': 'Especificar condición: P(ventas > 100)'
            },
			{
				'id': 'SYN-803',
                'nombre': 'Sintaxis de probabilidad incorrecta',
				'descripcion': 'Error en la estructura de probabilidad',
				'ejemplo': 'P x > 5',
                'solucion': 'Usar paréntesis: P(x > 5)'
            },

			# ========= Errores de estructura =========
			{
				'id': 'SYN-901',
                'nombre': 'Final inesperado del archivo',
				'descripcion': 'El archivo termina abruptamente',
				'ejemplo': 'Estructura sin cerrar al final',
                'solucion': 'Completar todas las declaraciones'
            },
			{
				'id': 'SYN-902',
                'nombre': 'Declaración incompleta',
				'descripcion': 'La declaración no está completa',
				'ejemplo': 'dataset x = al final del archivo',
                'solucion': 'Completar la declaración'
            },
			{
				'id': 'SYN-903',
                'nombre': 'Sintaxis inválida',
				'descripcion': 'Error sintáctico general',
				'ejemplo': 'Estructura no reconocida',
                'solucion': 'Revisar la sintaxis según la gramática'
            },

			# ========= Error general =========
			{
				'id': 'SYN-999',
                'nombre': 'Error sintáctico',
				'descripcion': 'Error sintáctico no categorizado',
				'ejemplo': 'Cualquier error no específico',
                'solucion': 'Revisar la sintaxis general'
            },
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
