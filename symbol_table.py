class Symbol:
    """Representa un símbolo en la tabla de símbolos."""
    def __init__(self, name, category, data_type, line, dataset=None):
        self.name = name
        self.category = category  # Ej: 'dataset', 'fact', 'rule', 'metric', 'column'
        self.data_type = data_type # Ej: 'int', 'real', 'logic', 'derived'
        self.line = line
        # columnas pertenecen a un dataset especificado
        self.dataset = dataset

    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "type": self.data_type,
            "line": self.line
        }

class SymbolTable:
    """Maneja la colección de símbolos identificados durante el análisis."""
    def __init__(self):
        self.symbols = {}

    def add(self, name, category, data_type, line, dataset=None):
        """Retorna True si se agregó, False si ya existía

        Args:
            dataset: nombre del dataset al que pertenece este símbolo
                     (solo aplica para columnas)
        """
        if name not in self.symbols:
            self.symbols[name] = Symbol(name, category, data_type, line, dataset)
            return True
        return False

    def exists(self, name: str) -> bool:
        """Retorna True si el símbolo está declarado."""
        return name in self.symbols

    def get(self, name: str):
        """Retorna el Symbol o None si no existe."""
        return self.symbols.get(name)

    def get_category(self, name: str):
        """Retorna la categoría del símbolo ('dataset', 'fact', 'rule', 'metric') o None."""
        symbol = self.symbols.get(name)
        return symbol.category if symbol else None

    def get_all(self):
        return list(self.symbols.values())

    def clear(self):
        self.symbols = {}