"""
Paquete Optimizer — snaptics
============================
Fase de optimización sobre código intermedio (cuádruplas).
Se ejecuta DESPUÉS del IRGenerator y ANTES del runtime.

Exporta:
  IROptimizer     — orquestador con fixed-point optimization
  optimize_ir()   — función de integración con el pipeline
"""

from optimizer.ir_optimizer import IROptimizer
from optimizer.optimizer import optimize_ir

__all__ = ['IROptimizer', 'optimize_ir']
