; ============================================================
; Plantilla: count_<fact>  para facts de probabilidad condicional
;            P(A given B)  =  P(A AND B) / P(B)
; ============================================================
; Esta plantilla se llena desde Python con .format(**params).
; Para cada fact con kind == 'given', Carim hace:
;
;     with open('lib/plantilla_count_given.asm') as f:
;         template = f.read()
;     asm = template.format(
;         name        = 'p_reprob',
;         col_a_idx   = 0,        # índice 0-based de la columna de A
;         value_a     = 60,       # umbral entero de A
;         jump_a_neg  = 'JGE',    # salto si NO se cumple A  (ya negado)
;         col_b_idx   = 1,        # índice 0-based de la columna de B
;         value_b     = 60,       # umbral entero de B
;         jump_b_neg  = 'JGE',    # salto si NO se cumple B  (ya negado)
;         where_block = '',       # snippet del where (o cadena vacía)
;     )
;
; Placeholders esperados (doble llave aquí en comentarios porque
; Python los reduce a llave simple al hacer .format(); en el
; cuerpo de abajo aparecen con llave simple porque ahí SÍ se sustituyen):
;   {{name}}        nombre del fact (también usado en todas las etiquetas)
;   {{col_a_idx}}   índice de la columna A en el CSV (0-based)
;   {{value_a}}     umbral entero de A
;   {{jump_a_neg}}  salto si NO se cumple A (entregado negado por el codegen)
;   {{col_b_idx}}   índice de la columna B en el CSV (0-based)
;   {{value_b}}     umbral entero de B
;   {{jump_b_neg}}  salto si NO se cumple B (entregado negado por el codegen)
;   {{where_block}} snippet del where pre-check (o cadena vacía si no aplica)
;
; Algoritmo (una sola pasada sobre el CSV):
;   BX = contador de filas que cumplen B            (denominador)
;   CX = contador de filas que cumplen A AND B      (numerador)
;   Al final: fact = (CX * 100) / BX
;             Si BX = 0, fact queda en 0 (evitar división por cero).
;
; Convenciones (mismas que count_simple y el snippet del where):
;   - Probabilidades viajan como enteros 0..100 en AX.
;   - Esta rutina lee del buffer global BUFFER (longitud BYTES_LEIDOS).
;   - Usa las primitivas de Fanny: parse_int, skip_to_col_N, skip_to_eol.
;   - Toda etiqueta interna lleva el sufijo _{name} para evitar colisiones
;     cuando hay varios count_* en el mismo .asm final.
;   - Los jump_neg los entrega el codegen ya negados; no convertir aquí.
;     Tabla de referencia rápida:
;       condición  >  ->  jump_neg = JLE
;       condición  <  ->  jump_neg = JGE
;       condición  == ->  jump_neg = JNE
;       condición  != ->  jump_neg = JE
;       condición  >= ->  jump_neg = JL
;       condición  <= ->  jump_neg = JG
; ============================================================


count_{name} PROC
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI

    LEA SI, BUFFER
    XOR BX, BX                          ; BX = filas que cumplen B (denominador)
    XOR CX, CX                          ; CX = filas que cumplen A AND B (numerador)

fila_loop_{name}:
    ; ---- verificar si ya salimos del buffer válido ----
    MOV DX, SI
    SUB DX, OFFSET BUFFER
    CMP DX, BYTES_LEIDOS
    JGE fin_loop_{name}

    ; ---- where pre-check (vacío si el dataset no tiene filtro) ----
{where_block}

    ; ---- leer columna B y evaluar denominador ----
    PUSH SI                             ; guardar inicio de la fila actual
    MOV AL, {col_b_idx}
    CALL skip_to_col_N
    CALL parse_int                      ; AX = valor de la celda B
    POP SI                             ; restaurar inicio de la fila

    CMP AX, {value_b}
    {jump_b_neg} no_b_{name}           ; si NO cumple B, saltar fila completa
    INC BX                             ; cumple B -> +1 denominador

    ; ---- leer columna A y evaluar numerador ----
    PUSH SI                             ; guardar inicio de la fila otra vez
    MOV AL, {col_a_idx}
    CALL skip_to_col_N
    CALL parse_int                      ; AX = valor de la celda A
    POP DX                             ; descartar SI guardado (DX = basura, solo libera stack)

    CMP AX, {value_a}
    {jump_a_neg} no_a_{name}           ; si NO cumple A, no sumar al numerador
    INC CX                             ; cumple A AND B -> +1 numerador

no_a_{name}:
    ; seguimos hacia el final de la fila

no_b_{name}:
    CALL skip_to_eol                    ; avanzar al inicio de la siguiente fila
    JMP fila_loop_{name}

fin_loop_{name}:
    ; ---- guardar conteos crudos para explain/why ----
    MOV fact_{name}_cnt, CX             ; numerador (A AND B)
    MOV fact_{name}_tot, BX             ; denominador (B)

    ; ---- calcular AX = (numerador * 100) / denominador ----
    OR  BX, BX                          ; si denominador == 0, evitar div/0
    JZ  div_cero_{name}

    MOV AX, CX                          ; AX = filas A AND B
    XOR DX, DX                          ; limpiar parte alta antes de MUL
    MOV CX, 100
    MUL CX                              ; DX:AX = numerador * 100
    DIV BX                              ; AX = (numerador * 100) / denominador
    JMP almacenar_{name}

div_cero_{name}:
    XOR AX, AX                          ; denominador = 0 -> fact = 0

almacenar_{name}:
    MOV fact_{name}, AX

    POP SI
    POP DX
    POP CX
    POP BX
    RET
count_{name} ENDP
