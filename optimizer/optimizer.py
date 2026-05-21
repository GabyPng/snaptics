"""
Integración del IR Optimizer con el pipeline del compilador.
============================================================
Mismo patrón que `semantic.semantic_analyzer.analyze()` e
`ir_generator.generate_ir()`: una función pública que recibe
el resultado del paso previo y devuelve un dict normalizado.

Uso desde el pipeline:

    parse_result    = parser.parse(code)
    semantic_result = semantic_analyzer.analyze(parse_result)
    ir_result       = ir_generator.generate_ir(semantic_result, parse_result)
    opt_result      = optimizer.optimize_ir(ir_result)

    if opt_result['success']:
        runtime.execute(opt_result['quadruples'])
"""

from __future__ import annotations
from ir_generator import Quadruple, format_quadruples
from optimizer.ir_optimizer import IROptimizer


def optimize_ir(ir_result: dict, debug: bool = False) -> dict:
    """
    Optimiza la lista de cuádruplas producida por IRGenerator.

    Args:
        ir_result: dict retornado por ir_generator.generate_ir()
            - 'quadruples': list[Quadruple]
            - 'success':    bool
            - 'formatted':  str
        debug: si True, imprime el progreso pase a pase.

    Returns:
        dict:
            - 'quadruples':       list[Quadruple] optimizadas
            - 'success':          bool
            - 'formatted':        str — IR optimizada formateada
            - 'original':         list[Quadruple] sin optimizar (referencia)
            - 'report':           str — resumen estadístico del optimizador
            - 'stats':            dict — aplicaciones por pase
            - 'reduction':        int — cuádruplas eliminadas
    """
    if not ir_result.get('success'):
        return {
            'quadruples': [],
            'success': False,
            'formatted': 'No se puede optimizar: la generación de IR falló.',
            'original': [],
            'report': '',
            'stats': {},
            'reduction': 0,
        }

    original: list[Quadruple] = list(ir_result.get('quadruples', []))

    optimizer = IROptimizer(debug=debug)
    optimized = optimizer.optimize(original)

    return {
        'quadruples': optimized,
        'success':    True,
        'formatted':  format_quadruples(optimized),
        'original':   original,
        'report':     optimizer.report(),
        'stats':      dict(optimizer.stats),
        'reduction':  optimizer.initial_size - optimizer.final_size,
    }
