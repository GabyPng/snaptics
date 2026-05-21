"""
Orquestador del IR Optimizer — snaptics
=======================================
Ejecuta los pases de optimización en orden definido y los repite
hasta alcanzar un punto fijo (no se producen más cambios) o
hasta el límite de iteraciones.

Orden de los pases:
    1. constant_folding         pliega operaciones con literales
    2. constant_propagation     inlinea valores de ASSIGN constantes
    3. algebraic_simplification X+0, X*1, X*0, X/1, X^1, X^0
    4. logic_simplification     identidades AND/OR/NOT booleanas
    5. probability_rules        P(true), P(false), P(A AND NOT A)
    6. peephole                 NOT NOT X y patrones inter-cuádruplas
    7. dead_temp_elimination    barrido final de temporales huérfanos

Estrategia fixed-point:
    while changed and iter < MAX:
        for pase in PASSES:
            quads, c = pase(quads)
            changed |= c

Justificación: cada pase puede habilitar a los demás.
    - folding habilita propagation
    - propagation habilita folding/algebraic/logic
    - algebraic/logic habilitan dead_temp_elimination
    - peephole habilita dead_temp_elimination

Complejidad global: O(k * P * n), donde
    n = número de cuádruplas
    P = número de pases (constante)
    k = iteraciones hasta el punto fijo (típicamente 2-4 en
        programas reales). El cap MAX_ITERATIONS evita patología.
"""

from __future__ import annotations
from ir_generator import Quadruple
from optimizer.passes import (
    constant_folding,
    algebraic_simplification,
    logic_simplification,
    probability_rules,
    constant_propagation,
    peephole,
    dead_temp_elimination,
)


class IROptimizer:
    """Optimizador de código intermedio con fixed-point loop."""

    # (nombre_visible, función_pase)
    PASSES = [
        ('constant_folding',         constant_folding.run),
        ('constant_propagation',     constant_propagation.run),
        ('algebraic_simplification', algebraic_simplification.run),
        ('logic_simplification',     logic_simplification.run),
        ('probability_rules',        probability_rules.run),
        ('peephole',                 peephole.run),
        ('dead_temp_elimination',    dead_temp_elimination.run),
    ]

    # Tope de iteraciones para evitar ciclos infinitos por bugs
    # en algún pase (no debería ocurrir; los pases son monotónicos).
    MAX_ITERATIONS = 50

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.iterations = 0
        # Cuántas veces ejecutó cambios cada pase.
        self.stats: dict[str, int] = {name: 0 for name, _ in self.PASSES}
        # Tamaño antes y después de optimizar.
        self.initial_size = 0
        self.final_size = 0

    def optimize(self, quads: list[Quadruple]) -> list[Quadruple]:
        """
        Punto de entrada principal.

        Args:
            quads: lista original generada por IRGenerator.

        Returns:
            Nueva lista optimizada. La original no se modifica.
        """
        current = list(quads)
        self.initial_size = len(current)
        self.iterations = 0

        for it in range(self.MAX_ITERATIONS):
            changed_any = False
            for name, fn in self.PASSES:
                new_quads, changed = fn(current)
                if changed:
                    changed_any = True
                    self.stats[name] += 1
                    current = new_quads
                    if self.debug:
                        print(f"[iter {it}] {name} -> {len(current)} cuádruplas")
            self.iterations = it + 1
            if not changed_any:
                break

        self.final_size = len(current)
        return current

    # ---------- introspección ----------

    def report(self) -> str:
        """Resumen legible del trabajo realizado."""
        lines = [
            "Reporte de optimización",
            "-----------------------",
            f"Cuádruplas iniciales : {self.initial_size}",
            f"Cuádruplas finales   : {self.final_size}",
            f"Reducción            : {self.initial_size - self.final_size}"
            f" ({self._percent_reduction():.1f}%)",
            f"Iteraciones          : {self.iterations}",
            "",
            "Aplicaciones por pase:",
        ]
        for name, _ in self.PASSES:
            lines.append(f"  {name:<28} {self.stats[name]}")
        return '\n'.join(lines)

    def _percent_reduction(self) -> float:
        if self.initial_size == 0:
            return 0.0
        return (self.initial_size - self.final_size) * 100.0 / self.initial_size
