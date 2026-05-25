"""
csv_stager.py
=============
Asegura que los CSVs referenciados por `import from` estén dentro de la
carpeta `vdrive\` de emu8086, copiándolos si hace falta. **No reescribe
el path en el AST**: el `.asm` final usa la ruta tal como aparece en el
`.snp`. El usuario es responsable de escribir un path que emu8086 pueda
abrir en runtime (lo más común: una ruta absoluta dentro del vdrive).

Motivación: emu8086 lee archivos vía `INT 21h/3Dh`. Para CSVs que ya
viven dentro del vdrive, no se hace nada — el `.asm` los abre directo.
Para CSVs externos a vdrive, este módulo los copia a
`<vdrive>\C\snaptics_data\<basename>` por conveniencia, pero igual el
.asm conserva la ruta original del .snp (si necesitas que apunte al
archivo copiado, escribe esa ruta directamente en el `import from`).

Pasos del módulo:
  1. Resuelve la ruta del CSV tal cual la escribió el usuario.
  2. Si vive fuera del vdrive, la copia a `<vdrive>\C\snaptics_data\<basename>`.
  3. (eliminado intencionalmente) la ruta del AST NO se modifica.

Configuración (precedencia, mayor a menor):
  1. Variable de entorno `SNAPTICS_EMU8086_HOME`.
  2. Campo `"emu8086_home"` en `<raíz_proyecto>/config.json`.
  3. Default `C:\emu8086`.

Llamado desde: `codegen/build.py` (entre semántico e IR).
"""

from __future__ import annotations
import json
import os
import shutil
from typing import Iterator

# Default para Windows típico de la cátedra. Se sobreescribe vía env var
# o vía config.json del proyecto.
DEFAULT_EMU8086_HOME = r"C:\emu8086"
# Subcarpeta dentro de vdrive\C\ donde dejamos los CSVs externos.
STAGE_SUBDIR = "snaptics_data"

# Raíz del proyecto: codegen/ es subdirectorio directo, así que subimos uno.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_FILE = os.path.join(_PROJECT_ROOT, 'config.json')


def _read_config_emu8086() -> str | None:
    """Lee `emu8086_home` de `config.json` en la raíz del proyecto.

    Retorna None si el archivo no existe, no es JSON válido, el campo
    no está presente o está vacío. Errores se ignoran silenciosamente:
    si algo está mal con el config, caemos al siguiente nivel de
    precedencia (env var o default).
    """
    try:
        with open(_CONFIG_FILE, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    value = data.get('emu8086_home')
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def get_emu8086_home() -> str:
    """Raíz de instalación de emu8086. Precedencia: env > config.json > default."""
    return (
        os.environ.get('SNAPTICS_EMU8086_HOME')
        or _read_config_emu8086()
        or DEFAULT_EMU8086_HOME
    )


def _vdrive_root() -> str:
    return os.path.join(get_emu8086_home(), 'vdrive')


def resolve_real_path(source_file: str, source_path: str | None) -> str:
    """Resuelve la ruta del CSV escrita en el .snp al filesystem real.

    Rutas absolutas se usan tal cual; relativas se resuelven contra el
    directorio del .snp (o cwd si no se conoce el .snp).
    """
    if os.path.isabs(source_file):
        return os.path.normpath(source_file)
    base_dir = os.path.dirname(os.path.abspath(source_path)) if source_path else os.getcwd()
    return os.path.normpath(os.path.join(base_dir, source_file))


def _is_inside(path: str, root: str) -> bool:
    """¿`path` cae bajo `root`?"""
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return False
    return not (rel.startswith('..') or os.path.isabs(rel))


def stage_csv(real_path: str) -> str | None:
    """Asegura que `real_path` sea visible para emu8086 (copiándolo al
    vdrive si vive fuera). No devuelve ningún path: el AST mantiene la
    ruta original del `.snp`.

    Returns:
        Mensaje de error si algo falló (vdrive inexistente, permisos, etc.).
        None en caso normal (incluido el caso de que el archivo ya estaba
        dentro del vdrive).
    """
    real_path = os.path.normpath(os.path.abspath(real_path))
    vdrive = _vdrive_root()

    # Caso 1: ya vive dentro del vdrive → nada que hacer.
    if _is_inside(real_path, vdrive):
        return None

    # Caso 2: hay que copiarlo a <vdrive>\C\snaptics_data\ para que
    # emu8086 pueda abrirlo. El usuario se encargará de poner la ruta
    # correcta en el `.snp`.
    if not os.path.isdir(vdrive):
        return (
            f"No encuentro la carpeta vdrive de emu8086 en '{vdrive}'. "
            f"Define la variable de entorno SNAPTICS_EMU8086_HOME apuntando "
            f"al directorio donde está instalado emu8086."
        )

    dest_dir = os.path.join(vdrive, 'C', STAGE_SUBDIR)
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as e:
        return f"No pude crear '{dest_dir}': {e}"

    basename = os.path.basename(real_path)
    dest = os.path.join(dest_dir, basename)
    try:
        shutil.copyfile(real_path, dest)
    except OSError as e:
        return f"No pude copiar '{real_path}' a '{dest}': {e}"

    return None


def _walk_ast(node) -> Iterator:
    """Generador que recorre el AST en profundidad."""
    from parser import ASTNode
    if not isinstance(node, ASTNode):
        return
    yield node
    for v in node.properties.values():
        if isinstance(v, ASTNode):
            yield from _walk_ast(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, ASTNode):
                    yield from _walk_ast(item)


def stage_csvs_in_ast(ast, source_path: str | None) -> list[str]:
    """Recorre el AST y copia los CSVs al vdrive si viven fuera. No modifica
    el AST: la ruta original del `.snp` se conserva tal cual y aparece sin
    cambios en el `.asm` generado.

    Args:
        ast:         nodo raíz (tipo 'Programa').
        source_path: ruta del .snp en disco para resolver rutas relativas.

    Returns:
        Lista de mensajes de error (vacía si todo OK). Los CSVs cuya ruta
        real no existe se ignoran silenciosamente: SEM-303 ya los reportó
        antes en el pipeline.
    """
    errors: list[str] = []
    for node in _walk_ast(ast):
        if node.type != 'Importacion':
            continue
        original = node.properties.get('source_file')
        if not original:
            continue

        real = resolve_real_path(original, source_path)
        if not os.path.isfile(real):
            # SEM-303 ya lo reportó; no añadimos ruido aquí.
            continue

        err = stage_csv(real)
        if err:
            errors.append(err)

    return errors
