# codegen — back-end del compilador

Generación de código objeto 8086 a partir de la IR optimizada que producen
las fases anteriores. Este directorio contiene **todo lo necesario para
producir un `.asm` ensamblable en emu8086** a partir de un programa Snaptics.

## Estructura

```
codegen/
├── code_generator.py        ← recorre la IR y emite el esqueleto del .asm
├── count_generator.py       ← genera las rutinas count_<fact> a partir de
│                              los metadatos (rellena plantillas con .format)
├── build.py                 ← stitcher: corre el pipeline completo
│                              y junta todas las piezas en un .asm final
├── lib/
│   ├── Biblioteca.lib       ← macros preexistentes del equipo (abrirArchivo, leerArchivo)
│   ├── fuzzy_logic.asm      ← Gibran: fuzzy_and / fuzzy_or / fuzzy_not
│   ├── output_devices.asm   ← Fanny:  print_int / show_led / show_traffic / show_result
│   ├── primitives.asm       ← Laura:  parse_int / skip_to_col_N / skip_to_eol
│   ├── plantillas/          ← .asm con placeholders ({name}, {col_idx}, ...)
│   │   ├── plantilla_count_simple.asm
│   │   ├── plantilla_count_given.asm
│   │   └── snippet_where_precheck.asm
│   └── tests/               ← pruebas aisladas de las libs (correr a mano en emu8086)
│       ├── test_fuzzy_logic.asm
│       └── test_primitives.asm
└── build/                   ← .asm finales generados por build.py
```

## Pipeline

```
samples/demo/x.snp
   │
   ├─ lexer       (raíz)
   ├─ parser      (raíz)
   ├─ semantic    (raíz/semantic/)
   ├─ ir          (raíz/ir_generator.py)
   ├─ optimizer   (raíz/optimizer/)
   ▼
   code_generator.py       → esqueleto del .asm + metadatos (datasets, facts, kinds)
   count_generator.py      → rutinas count_<fact> rellenando plantillas
   build.py                → stitcher: agrega libs y produce el .asm final
   ▼
codegen/build/x.asm  →  abrir en emu8086, F5
```

## Contrato con el CSV

El runtime lee CSVs crudos byte por byte, sin proyectar columnas. El
`.snp` debe respetar dos reglas para que los datos se interpreten bien:

1. El CSV NO tiene fila de encabezado.
2. El SELECT del `.snp` declara las columnas del CSV en el mismo orden.

Detalles, ejemplos y consecuencias de violar el contrato:
[`../samples/CSV_FORMAT.md`](../samples/CSV_FORMAT.md).

## Cómo se usa

```powershell
# desde la raíz del proyecto
python codegen/build.py samples/demo/alumnos_riesgo.snp
# -> escribe codegen/build/alumnos_riesgo.asm
```

## Cómo se prueba

```powershell
python tests/codegen/test_codegen.py
python tests/codegen/test_count_generator.py
```

Los outputs de los tests se escriben a `tests/codegen/out/` (al lado del test).
