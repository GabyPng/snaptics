# -*- coding: utf-8 -*-
"""
Panel de tokens con tabla ordenable/filtrable
"""

from PyQt6 import QtCore, QtWidgets


class TokenTableModel(QtCore.QAbstractTableModel):
    """Modelo de tabla para tokens.
    Espera una lista de dicts con llaves: type, value, line, column, lexpos.
    """

    HEADERS = ["LINE", "COL", "TYPE", "VALUE"]

    def __init__(self, tokens=None, parent=None):
        super().__init__(parent)
        self._tokens = tokens or []

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._tokens)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return self.HEADERS[section]
            else:
                return section + 1
        return None

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        tok = self._tokens[index.row()]
        col = index.column()

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return tok.get('line', '')
            elif col == 1:
                return tok.get('column', '')
            elif col == 2:
                return tok.get('type', '')
            elif col == 3:
                val = tok.get('value', '')
                s = repr(val)
                return s

        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 1):
                return int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            return int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        return QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled

    def set_tokens(self, tokens):
        self.beginResetModel()
        self._tokens = tokens or []
        self.endResetModel()


class TokenFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy para filtrar por cualquier columna (case-insensitive)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self._filter = ''

    def setFilterString(self, text: str):
        self._filter = text or ''
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        if not self._filter:
            return True
        model = self.sourceModel()
        cols = model.columnCount()
        for c in range(cols):
            idx = model.index(source_row, c, source_parent)
            val = model.data(idx, QtCore.Qt.ItemDataRole.DisplayRole)
            if val is None:
                continue
            if self._filter in str(val).lower():
                return True
        return False


class TokensPanel(QtWidgets.QWidget):
    """Widget con filtro y tabla de tokens."""
    tokenActivated = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = TokenTableModel()
        self._proxy = TokenFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Filtro
        filter_layout = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Filter:")
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Escribe para filtrar por cualquier columna…")
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(lbl)
        filter_layout.addWidget(self.filter_edit)

        # Tabla
        self.table = QtWidgets.QTableView(self)
        self.table.setModel(self._proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultSectionSize(120)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        self.table.activated.connect(self._on_table_activated)

        layout.addLayout(filter_layout)
        layout.addWidget(self.table)

    def _on_filter_changed(self, text: str):
        self._proxy.setFilterString(text.lower() if text else '')

    def set_tokens(self, tokens):
        self._model.set_tokens(tokens)
        # Ajustes de columnas
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.table.resizeColumnToContents(2)
        # La última columna se estira automáticamente

    def clear(self):
        self.set_tokens([])

    def _emit_token_for_index(self, proxy_index: QtCore.QModelIndex):
        if not proxy_index.isValid():
            return
        src_index = self._proxy.mapToSource(proxy_index)
        row = src_index.row()
        if row < 0 or row >= self._model.rowCount():
            return
        token = self._model._tokens[row]
        self.tokenActivated.emit(token)

    def _on_table_double_clicked(self, proxy_index: QtCore.QModelIndex):
        self._emit_token_for_index(proxy_index)

    def _on_table_activated(self, proxy_index: QtCore.QModelIndex):
        """Se emite al presionar Enter/Return o double-click según estilo; aquí lo usamos para Enter."""
        self._emit_token_for_index(proxy_index)
