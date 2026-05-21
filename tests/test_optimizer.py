"""
Suite de pruebas del IR Optimizer.

Ejecuta:
    python -m tests.test_optimizer
o:
    python tests/test_optimizer.py

Cada caso construye manualmente una lista de cuádruplas (sin pasar
por el parser) y verifica que el optimizador produzca la salida
esperada. Esto aísla el optimizador del resto del compilador.
"""

from __future__ import annotations
import os
import sys

# Asegura que la raíz del proyecto esté en sys.path al ejecutar
# este archivo directamente.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Forzar UTF-8 en stdout para que los caracteres de cuadro de
# format_quadruples no rompan en consolas cp1252 (Windows).
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

from ir_generator import Quadruple, format_quadruples
from optimizer import IROptimizer


# ---------- utilidades de aserción ----------

def _as_tuple(q: Quadruple) -> tuple:
    return (q.op, q.arg1, q.arg2, q.result)


def _assert_equal(actual: list[Quadruple], expected: list[tuple], name: str):
    actual_tuples = [_as_tuple(q) for q in actual]
    if actual_tuples != expected:
        print(f"[FALLA] {name}")
        print("  Esperado:")
        for t in expected:
            print(f"    {t}")
        print("  Obtenido:")
        for t in actual_tuples:
            print(f"    {t}")
        raise AssertionError(name)
    print(f"[OK]    {name}")


def _run(quads: list[Quadruple]) -> list[Quadruple]:
    return IROptimizer().optimize(quads)


# ---------- casos ----------

def test_constant_folding_arithmetic():
    quads = [Quadruple('ADD', 5, 3, 't1')]
    _assert_equal(
        _run(quads),
        [],  # t1 nunca se usa -> eliminado por dead_temp_elimination
        "constant_folding + dead_temp (ADD 5 3)",
    )


def test_constant_folding_kept_when_used():
    quads = [
        Quadruple('ADD', 5, 3, 't1'),
        Quadruple('ASSIGN', 't1', None, 'x'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 8, None, 'x')],
        "folding + propagation + dead_temp (objetivo del enunciado)",
    )


def test_constant_folding_relational():
    quads = [
        Quadruple('GT', 5, 3, 't1'),
        Quadruple('ASSIGN', 't1', None, 'r'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', True, None, 'r')],
        "folding relacional (5 > 3)",
    )


def test_algebraic_mul_one():
    quads = [
        Quadruple('MUL', 'x', 1, 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 'x', None, 'y')],
        "X * 1 -> X",
    )


def test_algebraic_mul_zero():
    quads = [
        Quadruple('MUL', 'x', 0, 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 0, None, 'y')],
        "X * 0 -> 0",
    )


def test_algebraic_pow():
    quads = [
        Quadruple('POW', 'x', 0, 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 1, None, 'y')],
        "X ^ 0 -> 1",
    )


def test_logic_and_true():
    quads = [
        Quadruple('AND', 'x', True, 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 'x', None, 'y')],
        "X AND true -> X",
    )


def test_logic_and_false():
    quads = [
        Quadruple('AND', 'x', False, 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', False, None, 'y')],
        "X AND false -> false",
    )


def test_logic_or_true():
    quads = [
        Quadruple('OR', 'x', True, 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', True, None, 'y')],
        "X OR true -> true",
    )


def test_logic_idempotence():
    quads = [
        Quadruple('AND', 'x', 'x', 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 'x', None, 'y')],
        "X AND X -> X",
    )


def test_not_not():
    quads = [
        Quadruple('NOT', 'x', None, 't1'),
        Quadruple('NOT', 't1', None, 't2'),
        Quadruple('ASSIGN', 't2', None, 'y'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 'x', None, 'y')],
        "NOT NOT X -> X",
    )


def test_prob_of_true():
    quads = [
        Quadruple('PROB', True, None, 't1'),
        Quadruple('ASSIGN', 't1', None, 'f'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 1.0, None, 'f')],
        "P(true) -> 1.0",
    )


def test_prob_of_false():
    quads = [
        Quadruple('PROB', False, None, 't1'),
        Quadruple('ASSIGN', 't1', None, 'f'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 0.0, None, 'f')],
        "P(false) -> 0.0",
    )


def test_prob_contradiction():
    # t1 = NOT a
    # t2 = a AND t1   -> a AND NOT a
    # t3 = PROB(t2)
    # f  = t3
    quads = [
        Quadruple('NOT', 'a', None, 't1'),
        Quadruple('AND', 'a', 't1', 't2'),
        Quadruple('PROB', 't2', None, 't3'),
        Quadruple('ASSIGN', 't3', None, 'f'),
    ]
    _assert_equal(
        _run(quads),
        [('ASSIGN', 0.0, None, 'f')],
        "P(A AND NOT A) -> 0.0",
    )


def test_constant_propagation_chain():
    # x = 5; y = x + 3; z = y * 2
    quads = [
        Quadruple('ASSIGN', 5, None, 'x'),
        Quadruple('ADD', 'x', 3, 't1'),
        Quadruple('ASSIGN', 't1', None, 'y'),
        Quadruple('MUL', 'y', 2, 't2'),
        Quadruple('ASSIGN', 't2', None, 'z'),
    ]
    # x sobrevive (no es temporal); y también. La aritmética se pliega.
    _assert_equal(
        _run(quads),
        [
            ('ASSIGN', 5,  None, 'x'),
            ('ASSIGN', 8,  None, 'y'),
            ('ASSIGN', 16, None, 'z'),
        ],
        "cadena de propagación + folding",
    )


def test_side_effects_preserved():
    # LOAD_DATASET, SELECT, QUERY no son puras: no se eliminan.
    quads = [
        Quadruple('LOAD_DATASET', 'ventas.csv', None, 'ventas_raw'),
        Quadruple('QUERY', 'q', None, None),
    ]
    _assert_equal(
        _run(quads),
        [
            ('LOAD_DATASET', 'ventas.csv', None, 'ventas_raw'),
            ('QUERY', 'q', None, None),
        ],
        "cuádruplas con efectos colaterales se conservan",
    )


# ---------- demo del enunciado ----------

def demo_enunciado():
    """Reproduce textualmente el ejemplo objetivo del enunciado."""
    quads = [
        Quadruple('ADD', 5, 3, 't1'),
        Quadruple('MUL', 't1', 1, 't2'),
        Quadruple('ASSIGN', 't2', None, 'x'),
    ]
    print("\n" + "=" * 60)
    print(" DEMO: ejemplo objetivo del enunciado")
    print("=" * 60)
    print("\nIR de entrada:")
    print(format_quadruples(quads))

    opt = IROptimizer(debug=False)
    out = opt.optimize(quads)

    print("\nIR optimizada:")
    print(format_quadruples(out))
    print("\n" + opt.report())


# ---------- runner ----------

def main():
    tests = [v for k, v in globals().items() if k.startswith('test_')]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError:
            pass
    print(f"\n{passed}/{len(tests)} pruebas pasadas")

    demo_enunciado()

    if passed != len(tests):
        sys.exit(1)


if __name__ == '__main__':
    main()
