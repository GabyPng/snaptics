class SemanticErrorCode:
    # SEM-100: errores de símbolos
    SYMBOL_NOT_DECLARED  = ("SEM-101", "Símbolo no declarado")
    SYMBOL_REDECLARED    = ("SEM-102", "Redeclaración de símbolo")
    INVALID_SYMBOL_USE   = ("SEM-103", "Uso incorrecto de símbolo")

    # SEM-200: errores de tipos
    TYPE_MISMATCH        = ("SEM-201", "Tipos incompatibles")
    INVALID_LOGICAL_TYPE = ("SEM-202", "Operador lógico con tipo inválido")
    INVALID_COMPARISON   = ("SEM-203", "Comparación inválida")
    MISSING_COLUMN_TYPE  = ("SEM-204", "Tipo de columna no declarado")

    # SEM-300: errores de datasets
    DATASET_SOURCE_NOT_FOUND = ("SEM-301", "Dataset fuente inexistente")
    DATASET_NOT_DECLARED     = ("SEM-302", "Dataset no declarado")
    CSV_FILE_NOT_FOUND       = ("SEM-303", "Archivo CSV no encontrado")

    # SEM-400: errores de reglas
    INVALID_RULE = ("SEM-401", "Regla inválida")

    # SEM-500: errores de consultas
    QUERY_SYMBOL_NOT_FOUND = ("SEM-501", "Consulta a símbolo inexistente")


class SemanticError:
    """Representa un error semántico con código SEM-XXX."""

    def __init__(self, code: str, description: str, line: int, detail: str = ""):
        self.code = code
        self.description = description
        self.line = line
        self.detail = detail

    def __repr__(self):
        loc = f"Línea {self.line}" if isinstance(self.line, int) else str(self.line)
        base = f"[{self.code}] {self.description} — {loc}"
        return f"{base}: {self.detail}" if self.detail else base

    def to_dict(self) -> dict:
        return {
            "type": "semantic_error",
            "code": self.code,
            "category": self.description,
            "line": self.line,
            "message": self.detail or self.description,
        }
