; ============================================================
; Plantilla: count_<fact>  para facts de probabilidad simple
;            P(col OP valor)
; ============================================================
; Esta plantilla se llena desde Python con .format(**params).
; Para cada fact con kind == 'simple', Carim hace:
;
;     with open('lib/plantilla_count_simple.asm') as f:
;         template = f.read()
;     asm = template.format(
;         name='asistencia_critica',
;         col_idx=0,
;         value=60,
;         jump_neg='JGE',
;         where_block='',           # o el snippet si el dataset tiene where
;     )
;
; Placeholders esperados (escritos en este comentario con doble llave
; porque Python las reduce a llave simple al hacer .format(); en el
; cuerpo de abajo aparecen con llave simple porque ahí SÍ se sustituyen):
;   {{name}}        nombre del fact (también usado en etiquetas)
;   {{col_idx}}     índice numérico de la columna en el CSV (0-based)
;   {{value}}       umbral entero contra el que se compara
;   {{jump_neg}}    salto a "no_match" si NO se cumple la condición
;                   (el codegen lo entrega ya negado en meta['jump_neg'])
;   {{where_block}} snippet del where pre-check (o cadena vacía si no aplica)
;
; Convenciones (mismas que count_given y el snippet del where):
;   - Probabilidades viajan como enteros 0..100 en AX.
;   - Esta rutina lee del buffer global BUFFER (longitud BYTES_LEIDOS).
;   - Usa las primitivas de Fanny: parse_int, skip_to_col_N, skip_to_eol.
;   - Toda etiqueta interna lleva el sufijo _<name> para evitar colisiones
;     cuando hay varios count_* en el mismo .asm final.
; ============================================================


count_{name} PROC
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI

    LEA SI, BUFFER
    XOR BX, BX                          ; BX = filas que cumplen la condición
    XOR CX, CX                          ; CX = total de filas contadas

fila_loop_{name}:
    ; ---- verificar si ya salimos del buffer válido ----
    MOV DX, SI
    SUB DX, OFFSET BUFFER
    CMP DX, BYTES_LEIDOS
    JGE fin_loop_{name}

    ; ---- where pre-check (vacío si el dataset no tiene filtro) ----
{where_block}

    ; ---- leer la columna del fact y comparar ----
    PUSH SI                             ; guardar inicio de la fila
    MOV AL, {col_idx}
    CALL skip_to_col_N
    CALL parse_int                      ; AX = valor de la celda
    POP DX                              ; descartar el SI guardado

    CMP AX, {value}
    {jump_neg} no_match_{name}          ; si NO se cumple, saltar sin contar
    INC BX                              ; cumple -> +1 match
no_match_{name}:
    INC CX                              ; siempre +1 total

    CALL skip_to_eol                    ; avanzar a la siguiente fila
    JMP fila_loop_{name}

fin_loop_{name}:
    ; ---- calcular AX = (matches * 100) / total ----
    OR  CX, CX                          ; si total == 0, evitar div/0
    JZ  div_cero_{name}

    MOV AX, BX
    MOV DX, 0
    MOV BX, 100
    MUL BX                              ; DX:AX = matches * 100
    DIV CX                              ; AX = (matches * 100) / total
    JMP almacenar_{name}

div_cero_{name}:
    XOR AX, AX                          ; total = 0 -> fact = 0

almacenar_{name}:
    MOV fact_{name}, AX

    POP SI
    POP DX
    POP CX
    POP BX
    RET
count_{name} ENDP
