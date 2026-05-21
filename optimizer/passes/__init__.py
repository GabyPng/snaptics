"""
Pases individuales del IR Optimizer.

Cada pase expone una función pública:
    run(quads: list[Quadruple]) -> tuple[list[Quadruple], bool]

donde el booleano indica si el pase realizó cambios.
"""

from optimizer.passes import (
    constant_folding,
    algebraic_simplification,
    logic_simplification,
    probability_rules,
    constant_propagation,
    peephole,
    dead_temp_elimination,
)

__all__ = [
    'constant_folding',
    'algebraic_simplification',
    'logic_simplification',
    'probability_rules',
    'constant_propagation',
    'peephole',
    'dead_temp_elimination',
]
