  # Script de Explicación — Fases IR, Optimizador y Generador de Código
  ### Compilador Snaptics

  ---

  ## INTRODUCCIÓN

  Hola, voy a explicar las últimas cuatro fases del compilador Snaptics:
  la generación de representación intermedia, el optimizador, el generador
  de código objeto y el stitcher que une todo al final.

  Para entender estas fases hay que tener claro el pipeline completo.
  El compilador tiene seis etapas en total:

  1. El **Lexer** convierte el texto fuente en tokens.
  2. El **Parser** valida la gramática y construye el árbol de sintaxis abstracta, el AST.
  3. El **Analizador Semántico** verifica que los identificadores existan, que los tipos sean correctos y que las operaciones tengan sentido.
  4. El **Generador de IR** — que es donde empieza esta explicación — transforma el AST en instrucciones de bajo nivel.
  5. El **Optimizador** reduce esas instrucciones eliminando lo que no hace falta.
  6. El **Generador de Código** traduce las instrucciones optimizadas a ensamblador 8086.

  Y por encima de todo eso está **build.py**, que orquesta el proceso completo
  y produce el archivo `.asm` final listo para abrirse en emu8086.

  ---

  ## PARTE 1 — ir_generator.py: Generación de Representación Intermedia

  ### ¿Qué es la representación intermedia?

  Después del análisis semántico tenemos un árbol: el AST.
  Ese árbol es cómodo para analizar, pero es difícil de ejecutar directamente.
  La representación intermedia, o IR, es una lista plana de instrucciones
  simples llamadas **cuádruplas**.

  Una cuádrupla tiene exactamente cuatro campos:

      operador | argumento 1 | argumento 2 | resultado

  Por ejemplo, sumar dos valores se escribe así:

      ADD | t0 | t1 | t2

  Lo que significa: "suma t0 con t1 y guarda el resultado en t2".

  Esta forma es casi como ensamblador, pero todavía es independiente
  del procesador. Eso nos permite optimizarla antes de comprometernos
  con instrucciones reales de 8086.

  ---

  ### La clase Quadruple

  La clase `Quadruple` es simplemente un contenedor con esos cuatro campos:
  `op`, `arg1`, `arg2` y `result`. Usa `__slots__` para ocupar poca memoria,
  y su método `__repr__` imprime la cuádrupla en el formato de tabla que vemos
  en pantalla.

  ---

  ### La clase IRGenerator

  El generador hereda de `ASTVisitor`. Eso significa que para cada tipo de
  nodo del AST existe un método llamado `visit_` seguido del nombre del nodo.
  Cuando el generador "visita" un nodo, ejecuta el método correspondiente.

  Tiene tres herramientas internas:

  - `new_temp()` genera nombres de temporales únicos: t0, t1, t2 y así sucesivamente.
  - `new_label()` genera etiquetas únicas: L0, L1, L2.
  - `emit()` crea la cuádrupla y la agrega a la lista.

  El punto de entrada es `generate(ast)`, que reinicia los contadores,
  visita el nodo raíz del árbol y devuelve la lista de cuádruplas.

  ---

  ### ¿Cómo se traduce cada construcción del lenguaje?

  **Importación de dataset:**
  La instrucción `dataset alumnos = import from "archivo.csv"` genera
  una sola cuádrupla: `LOAD_DATASET archivo.csv → alumnos`.

  **Preprocesamiento:**
  Un `select columnas from fuente where condición` genera primero un `SELECT`
  con la fuente y las columnas, luego si hay `where` evalúa la condición
  y emite un `WHERE`, y finalmente un `ASSIGN` que guarda el resultado
  en el nombre del dataset destino.

  **Declaración de hecho:**
  `fact asistencia_critica = P(alumnos.asistencia < 60)` genera una cadena:
  primero el acceso al miembro con `MEMBER_ACCESS`, luego la comparación
  con `LT`, luego el cálculo de probabilidad con `PROB`,
  y finalmente un `ASSIGN` al identificador del hecho.

  **Probabilidad condicional:**
  `P(A given B)` genera `PROB_GIVEN` con dos argumentos: el temporal
  de la condición A y el temporal de la condición B.

  **Reglas:**
  `rule alerta :- condición` evalúa la condición y emite `RULE_DEF`
  con el nombre de la regla.

  **Consultas:**
  `query alerta` emite `QUERY`. Con `explain` emite `QUERY_EXPLAIN`.
  Con `why` emite `QUERY_WHY`.

  **Operaciones aritméticas y lógicas:**
  Se mapean directamente: `+` es `ADD`, `-` es `SUB`, `and` es `AND`,
  `not` es `NOT`, y así con todos los operadores.

  ---

  ### Función generate_ir

  La función pública `generate_ir` recibe el resultado del analizador semántico
  y el resultado del parser, verifica que no haya errores previos,
  instancia el generador con la tabla de símbolos, llama a `generate(ast)`
  y devuelve un diccionario con la lista de cuádruplas, el éxito booleano
  y una representación formateada como tabla.

  ---

  ## PARTE 2 — optimizer/ir_optimizer.py: El Optimizador

  ### ¿Para qué sirve optimizar?

  El generador de IR produce cuádruplas correctas, pero no necesariamente
  eficientes. Por ejemplo, puede generar instrucciones del tipo
  `t0 = 3 + 4` en vez de simplemente usar `7`, o puede haber temporales
  que se asignan pero nunca se vuelven a leer.

  El optimizador elimina ese desperdicio antes de generar el código objeto.
  Cuantas menos cuádruplas haya, más corto y rápido será el ensamblador final.

  ---

  ### Los siete pases

  El optimizador aplica siete transformaciones en orden:

  **Pase 1 — Constant Folding (plegado de constantes):**
  Si una operación tiene dos argumentos literales, la calcula en tiempo de
  compilación. Por ejemplo `3 + 4` se convierte directamente en `7`,
  y esa cuádrupla desaparece.

  **Pase 2 — Constant Propagation (propagación de constantes):**
  Si un temporal fue asignado con un valor constante, sustituye todas las
  apariciones de ese temporal por el valor. Así el siguiente pase de plegado
  puede operar sobre más literales.

  **Pase 3 — Algebraic Simplification (simplificación algebraica):**
  Aplica identidades matemáticas: `X + 0` es `X`, `X * 1` es `X`,
  `X * 0` es `0`, `X / 1` es `X`, `X ^ 1` es `X`, `X ^ 0` es `1`.
  Cada una de esas simplificaciones elimina una cuádrupla.

  **Pase 4 — Logic Simplification (simplificación lógica):**
  Aplica identidades booleanas: `verdadero AND X` es `X`,
  `falso OR X` es `X`, `NOT (NOT X)` es `X`, y similares.

  **Pase 5 — Probability Rules (reglas de probabilidad):**
  Aplica casos triviales de probabilidad: `P(true)` es `1`,
  `P(false)` es `0`, `P(A AND NOT A)` es `0`.

  **Pase 6 — Peephole:**
  Analiza pares o tríos de cuádruplas consecutivas y elimina patrones
  ineficientes como dobles negaciones o asignaciones redundantes.

  **Pase 7 — Dead Temp Elimination (eliminación de temporales muertos):**
  Barre toda la lista y elimina las cuádruplas cuyo resultado nunca es leído
  por ninguna instrucción posterior. Es el paso de limpieza final.

  ---

  ### Estrategia fixed-point

  Los pases no se ejecutan una sola vez. Se ejecutan en un bucle hasta que
  ningún pase produzca cambios. A esto se le llama **punto fijo**.

  La razón es que los pases se habilitan entre sí: el plegado produce
  constantes que la propagación puede sustituir; la propagación produce
  nuevos literales que el plegado puede volver a plegar; la simplificación
  algebraica produce temporales sin uso que la eliminación de muertos borra.

  En la práctica, el compilador converge en dos o cuatro iteraciones.
  Para evitar ciclos infinitos por algún error en un pase, hay un límite
  de cincuenta iteraciones.

  ---

  ### El método report

  Al terminar, el optimizador puede imprimir un reporte con el número de
  cuádruplas antes y después, el porcentaje de reducción, cuántas
  iteraciones tomó llegar al punto fijo, y cuántas veces aplicó cambios
  cada pase.

  ---

  ## PARTE 3 — optimizer/optimizer.py: Integración con el Pipeline

  Este archivo es una capa muy delgada. Su única responsabilidad es
  seguir el mismo contrato que el resto del pipeline.

  La función `optimize_ir` recibe el diccionario que devolvió `generate_ir`,
  verifica que el campo `success` sea verdadero, instancia el `IROptimizer`
  y le pasa las cuádruplas.

  Al terminar devuelve un nuevo diccionario con las cuádruplas optimizadas,
  la IR formateada, la IR original como referencia, el reporte de estadísticas
  y el número de cuádruplas eliminadas.

  Este patrón — función pública que recibe el dict del paso anterior
  y devuelve un dict normalizado — es el mismo en todas las fases del
  compilador. Eso hace que el pipeline sea fácil de encadenar y de depurar.

  ---

  ## PARTE 4 — codegen/code_generator.py: Generador de Código Objeto

  ### ¿Qué hace?

  Este módulo es la última fase de transformación. Toma la lista de cuádruplas
  optimizadas y produce un programa ensamblador en la sintaxis de emu8086.

  Hay una convención acordada con el equipo:
  - Toda probabilidad viaja en el registro **AX** como un entero de cero a cien.
  - Las rutinas auxiliares preservan CX, DX, SI y DI con push y pop.
  - AX y BX son volátiles.

  ---

  ### Alcance de la versión 1

  Hay ciertas operaciones que el generador soporta y otras que no.

  Lo que **sí** soporta:
  - Facts con valor constante, porque el optimizador ya los plegó a un número.
  - Facts derivados de un dataset: `P(columna OP valor)`.
  - Facts con probabilidad condicional: `P(A given B)`.
  - Reglas con AND, OR y NOT, incluso anidadas.
  - Comparaciones crisp dentro de reglas, como `fact > 0.30`.
  - Los tres tipos de query: básico, explain y why.
  - Paginación con flechas y exportación del log a un archivo .txt.
  - Importar un CSV y filtrar con WHERE.

  Lo que **no** soporta y reporta como error GEN-001:
  - Las métricas estadísticas: mean, variance, stddev, correlation.
  - El auto_discover.
  - Aritmética dentro de expresiones probabilísticas.

  ---

  ### Dos fases internas: análisis y emisión

  El generador trabaja en dos fases.

  **Fase 1: `_analyze()`**
  Lee toda la lista de cuádruplas y clasifica los símbolos sin emitir
  ningún código todavía.

  - Marca todos los temporales para reservarles un slot `DW` en `.DATA`.
  - Los `LOAD_DATASET` llenan el diccionario de datasets con sus rutas.
  - Los `MEMBER_ACCESS` mapean temporales a nombres de columna y de dataset.
  - Los `ASSIGN` a facts los clasifica en literales o derivados, y para los
    derivados busca hacia atrás en la IR para encontrar el `PROB` o `PROB_GIVEN`
    y la comparación que lo originó.
  - Los `RULE_DEF` registran el nombre de la regla y reconstruyen su árbol
    estructural caminando hacia atrás por la IR. Ese árbol se usa después
    para generar las pantallas de explain y why.
  - Los `QUERY`, `QUERY_EXPLAIN` y `QUERY_WHY` se guardan en una lista
    con su nivel de detalle.

  **Fase 2: emisión**
  Primero se llama a `_emit_code()`, que genera la sección `.CODE`,
  y luego a `_emit_data()`, que genera la sección `.DATA`.

  El orden importa: el código registra los mensajes auxiliares de explain
  y why en una lista interna, y esos mensajes tienen que aparecer después
  en la sección `.DATA`. Si se hiciera al revés, los mensajes no existirían
  todavía cuando se necesitan.

  ---

  ### Sección .DATA

  Contiene en orden:
  - La ruta del CSV, el handle del archivo, el buffer de lectura y el contador
    de bytes, solo si hay facts derivados de dataset.
  - Los facts con valor constante como palabras `DW`.
  - Los facts derivados como palabras `DW 0` con comentario descriptivo,
    más dos contadores auxiliares `_cnt` y `_tot` que Carim llena.
  - Los resultados de las reglas como palabras `DW`.
  - Los temporales del IR como palabras `DW`.
  - Los mensajes de query en formato `DB 'nombre = $'`.
  - Los mensajes de evidencia baja, moderada y alta.
  - El prompt de navegación, la ruta del log y los mensajes auxiliares
    de explain y why.

  ---

  ### Sección .CODE

  Primero abre el archivo de log.

  Luego, si hay facts derivados, abre el CSV, lo lee en el buffer
  y hace `CALL count_<nombre>` para cada fact derivado.
  Esas rutinas son las que Carim genera con su módulo.

  Después itera sobre las cuádruplas en orden y emite el código
  para cada una:

  - `AND` y `OR` cargan los operandos en AX y BX y llaman a `fuzzy_and`
    o `fuzzy_or` de Gibran.
  - `NOT` carga el operando en AX y llama a `fuzzy_not`.
  - `RULE_DEF` mueve el temporal del resultado al slot `rule_<nombre>`.
  - Las comparaciones dentro de reglas emiten código crisp: si se cumple
    AX vale 100, si no vale 0.
  - `QUERY` llama a la pantalla correspondiente.

  ---

  ### Las tres pantallas de query

  **Básico:** carga el valor del fact o regla en AX, carga el puntero
  al mensaje y llama a `show_result`.

  **Explain:** imprime un encabezado con el valor, luego la lectura de
  cada hecho involucrado con sus conteos reales, la fórmula de la regla
  en texto, la evaluación de cada comparación mostrando si se cumple
  o no, una nota sobre el operador raíz si es AND u OR, y una conclusión.

  **Why:** imprime el origen del dataset con su filtro si lo tiene,
  luego cada hecho numerado con su lectura y la evaluación de su umbral,
  luego el razonamiento explicando cómo se combinan los hechos, y si
  hay exactamente dos hechos muestra el factor decisivo: el de mayor
  cobertura si la regla es OR, el de menor cobertura si es AND.

  ---

  ## PARTE 5 — codegen/build.py: El Stitcher

  ### ¿Qué hace build.py?

  `build.py` es el punto de entrada del compilador cuando se usa desde
  la línea de comandos. Ejecuta el pipeline completo y une todas las
  piezas en un único archivo `.asm` autocontenido.

  ---

  ### Pipeline completo en compile_snaptics

  La función `compile_snaptics` recibe el texto fuente y hace lo siguiente
  en orden:

  1. **Léxico:** si hay errores, para y los reporta.
  2. **Sintaxis:** si hay errores de tipo `syntax_error`, para y los reporta.
  3. **Semántica:** si hay errores, para y los reporta.
  4. **Stage CSV:** copia cada archivo CSV referenciado al vdrive de emu8086
    y reescribe las rutas en el AST al formato DOS que el ensamblador verá.
    Esto permite que el `.snp` use rutas reales de Windows.
  5. **Generación de IR.**
  6. **Optimización.**
  7. **Generación de código:** produce el esqueleto del `.asm`.
  8. **Generación de counts:** Carim produce las rutinas `count_<fact>`.
  9. **Stitch:** fusiona todo.

  ---

  ### El stitcher `_stitch`

  Esta función recibe el `.asm` del codegen y el `.asm` de los counts,
  localiza la última aparición del centinela `END INICIO` en el primero
  y antes de ese punto inserta:

  - Las rutinas `count_<fact>` de Carim.
  - Las cuatro librerías en orden:
    `fuzzy_logic.asm`, `explain_helpers.asm`, `output_devices.asm`
    y `primitives.asm`.

  El orden de las librerías es importante: `explain_helpers` va antes
  que `output_devices` porque `show_result` llama a `print_log_str`
  y `nav_pause`, que están definidas en `explain_helpers`.

  Antes de pegar cada librería, `_strip_data_dupes` quita las líneas que
  declaran variables que el codegen ya emitió en `.DATA`. Si no se hiciera
  eso, el ensamblador reportaría símbolo duplicado o leería el string
  desde el segmento de código en lugar del segmento de datos,
  lo que en DOS hace que INT 21h imprima basura.

  ---

  ### Uso desde la línea de comandos

  Hay dos modos:

      python codegen/build.py mi_programa.snp -o salida.asm

  Compila el archivo `.snp` y escribe el `.asm` en la ruta indicada.
  Si no se indica salida, se crea en la carpeta `codegen/build/`.

      python codegen/build.py --demo

  Usa un programa de prueba embebido que importa un CSV de alumnos,
  filtra por promedio menor a 80, declara dos facts y una regla,
  y hace un query con explain.

  ---

  ## CIERRE

  Para resumir: el pipeline de las fases que cubrimos hace lo siguiente.

  El **generador de IR** toma el árbol del programa y lo aplana en
  instrucciones simples de cuatro campos.

  El **optimizador** limpia esas instrucciones en hasta siete pasadas,
  repitiendo el proceso hasta que no queda nada por simplificar.

  El **generador de código** lee las instrucciones optimizadas, clasifica
  los símbolos, y produce una sección `.DATA` con todas las variables
  y una sección `.CODE` con la lógica del programa en ensamblador 8086.

  Y **build.py** junta el código generado con las rutinas de conteo
  de Carim y las librerías de Gibran y Fanny para producir el archivo
  `.asm` final, listo para ensamblar en emu8086 con F5.
