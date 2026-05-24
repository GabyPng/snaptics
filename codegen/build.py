"""
build.py
========
Toma un programa Snaptics y produce un .asm final, autocontenido,
listo para abrir en emu8086 y ensamblar con F5.

Junta:
  - El esqueleto del code_generator (Laura)
  - Las rutinas count_<fact> generadas por count_generator (Carim)
  - lib/fuzzy_logic.asm     (Gibran: fuzzy_and / or / not)
  - lib/output_devices.asm  (Fanny:  print_int / show_led / show_traffic / show_result)
  - lib/primitives.asm      (Laura:  parse_int / skip_to_col_N / skip_to_eol)

Uso:
    python build.py archivo.snp -o salida.asm
    python build.py --demo               # corre la demo embebida abajo
"""

from __future__ import annotations
import os
import sys
import argparse

# Bootstrap: build.py vive en codegen/, importa cosas de la raíz del proyecto
# (lexer, parser, semantic, ir_generator, optimizer) y también de su mismo
# directorio (code_generator, count_generator). Añadimos ambos al sys.path.
_HERE = os.path.dirname(os.path.abspath(__file__))            # codegen/
_PROJECT_ROOT = os.path.dirname(_HERE)                        # snaptics/
for _p in (_PROJECT_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lexer
import parser as syntax_parser
from semantic.semantic_analyzer import analyze as semantic_analyze
from ir_generator import generate_ir
from optimizer import optimize_ir
from code_generator import generate_code
from count_generator import generate_counts

# Las libs de producción viven al lado de este script.
_LIB_FILES = (
    os.path.join(_HERE, 'lib', 'fuzzy_logic.asm'),
    os.path.join(_HERE, 'lib', 'output_devices.asm'),
    os.path.join(_HERE, 'lib', 'primitives.asm'),
)


# ==================== pipeline ====================

def compile_snaptics(source: str, source_path: str | None = None) -> dict:
    """Corre el pipeline completo, devuelve dict con asm y errores.

    Args:
        source:      texto del programa .snp.
        source_path: ruta del archivo .snp en disco (opcional).
                     Se usa para resolver rutas relativas en `import from`
                     al verificar la existencia del CSV (SEM-303).
    """
    lex = lexer.tokenize(source)
    if lex.get('errors'):
        return {'ok': False, 'stage': 'lex', 'errors': lex['errors']}

    pr = syntax_parser.parse(source)
    syn_errors = [e for e in pr.get('errors', [])
                  if e.get('type') == 'syntax_error'
                  or str(e.get('code', '')).startswith('SYN-')]
    if syn_errors:
        return {'ok': False, 'stage': 'parse', 'errors': syn_errors}

    sem = semantic_analyze(pr, source_path=source_path)
    if sem.get('errors'):
        return {'ok': False, 'stage': 'semantic', 'errors': sem['errors']}

    ir = generate_ir(sem, pr)
    if not ir.get('success'):
        return {'ok': False, 'stage': 'ir', 'errors': ['IR generation failed']}

    opt = optimize_ir(ir)
    if not opt.get('success'):
        return {'ok': False, 'stage': 'opt', 'errors': ['optimizer failed']}

    cg = generate_code(opt, pr)
    if not cg.get('success'):
        return {'ok': False, 'stage': 'codegen', 'errors': cg['errors']}

    counts = generate_counts(opt, pr)
    if not counts.get('success'):
        return {'ok': False, 'stage': 'count_generator', 'errors': counts['errors']}

    asm = _stitch(cg['asm'], counts['asm'])
    return {'ok': True, 'asm': asm}


# ==================== stitcher ====================

def _stitch(codegen_asm: str, counts_asm: str) -> str:
    """Inserta las rutinas count_<fact> y las libs ANTES de END INICIO."""
    sentinel = 'END INICIO'
    idx = codegen_asm.rfind(sentinel)
    if idx < 0:
        raise RuntimeError("No se encontró 'END INICIO' en el .asm del codegen")

    head = codegen_asm[:idx]
    tail = codegen_asm[idx:]

    lib_chunks = []
    for full in _LIB_FILES:
        content = _read_text(full)
        # Algunas declaraciones DB deben vivir en .DATA (las emite el codegen),
        # no en .CODE donde se incluye este archivo. Si el archivo las trae,
        # las filtramos para evitar conflicto de segmentos y/o de símbolo.
        content = _strip_data_dupes(content)
        rel = os.path.relpath(full, _HERE)
        lib_chunks.append(f"\n; ====== inicio de {rel} ======\n{content}"
                          f"\n; ====== fin de {rel} ======\n")

    pieces = [head]
    pieces.append("\n; ============================================================\n")
    pieces.append("; Rutinas count_<fact> generadas por count_generator (Carim)\n")
    pieces.append("; ============================================================\n")
    pieces.append(counts_asm)
    pieces.append("\n\n")
    pieces.extend(lib_chunks)
    pieces.append("\n")
    pieces.append(tail)
    return ''.join(pieces)


# ==================== CLI ====================

def _read_source(path: str) -> str:
    with open(path, encoding='utf-8') as f:
        return f.read()


_DATA_DUPES = ('msg_evid_baja', 'msg_evid_mod', 'msg_evid_alta')


def _strip_data_dupes(content: str) -> str:
    """Quita líneas que declaran variables que el codegen ya emite en .DATA.
    Útil para evitar conflictos de segmento (cadenas en CODE que se leen
    con DS:DX) y errores de "duplicate symbol".
    """
    out = []
    for line in content.splitlines(keepends=True):
        stripped = line.lstrip()
        if any(stripped.startswith(name + ' ') or stripped.startswith(name + '\t')
               for name in _DATA_DUPES):
            out.append('; (declaración movida a .DATA por build.py: ' +
                       stripped.split(None, 1)[0] + ')\n')
            continue
        out.append(line)
    return ''.join(out)


def _read_text(path: str) -> str:
    """Lee un archivo intentando varios encodings. Útil para archivos asm
    del equipo que pueden venir en utf-8 o cp1252 según cómo los hayan guardado."""
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # Último recurso: ignorar bytes malos para no detener el build
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="Stitcher final Snaptics -> emu8086.")
    ap.add_argument('source', nargs='?', help='archivo .snp (programa Snaptics)')
    ap.add_argument('-o', '--output', default=None,
                    help='archivo .asm de salida. Default: build/<basename>.asm')
    ap.add_argument('--demo', action='store_true',
                    help='usar un programa de prueba embebido')
    args = ap.parse_args()

    if args.demo:
        # El CSV vive en el vdrive de emu8086, ahí lo busca en runtime.
        # El SELECT lista las 6 columnas del CSV crudo (sin header) en
        # orden, así Carim mapea cada nombre al índice correcto.
        source = (
            r'dataset alumnos_raw = import from "C:\emu8086\vdrive\C\alumnos.csv"' + '\n'
            'dataset alumnos_foco = select alumno: int, asistencia: int, calificacion: int, '
            'grupo: int, tareas: int, promedio: int '
            'from alumnos_raw where promedio < 80\n'
            'fact asistencia_critica = P(alumnos_foco.asistencia < 60)\n'
            'fact p_reprob = P(alumnos_foco.promedio < 60 given alumnos_foco.asistencia < 60)\n'
            'rule alerta :- asistencia_critica and p_reprob\n'
            'query alerta\n'
        )
        default_name = 'demo'
    elif args.source:
        source = _read_source(args.source)
        default_name = os.path.splitext(os.path.basename(args.source))[0]
    else:
        ap.error("hay que pasar un archivo .snp o usar --demo")
        return  # unreachable, calla al linter

    if args.output is None:
        build_dir = os.path.join(_HERE, 'build')
        os.makedirs(build_dir, exist_ok=True)
        args.output = os.path.join(build_dir, default_name + '.asm')

    snp_path = os.path.abspath(args.source) if args.source else None
    result = compile_snaptics(source, source_path=snp_path)
    if not result['ok']:
        print(f"[FAIL] etapa '{result['stage']}':")
        for e in result['errors']:
            print(f"  {e}")
        sys.exit(1)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(result['asm'])

    print(f"[OK] -> {args.output}")
    print(f"      {len(result['asm'].splitlines())} líneas")


if __name__ == '__main__':
    main()
