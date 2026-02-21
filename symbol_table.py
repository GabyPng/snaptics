class Symbol:
    """Representa un símbolo en la tabla de símbolos."""
    def __init__(self, name, category, data_type, line):
        self.name = name
        self.category = category  # Ej: 'dataset', 'fact', 'rule', 'metric'
        self.data_type = data_type # Ej: 'int', 'real', 'logic', 'derived'
        self.line = line

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

    def add(self, name, category, data_type, line):
        """Retorna True si se agregó, False si ya existía"""
        if name not in self.symbols:
            self.symbols[name] = Symbol(name, category, data_type, line)
            return True
        return False

    def get_all(self):
        return list(self.symbols.values())
    
    def clear(self):
        self.symbols = {}