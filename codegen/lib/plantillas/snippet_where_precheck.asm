; ============================================================
; Snippet: where pre-check
; ============================================================
; Bloque que se inyecta como {{where_block}} en plantilla_count_simple.asm
; y plantilla_count_given.asm cuando el dataset tiene cláusula WHERE.
;
; Carim lo usa así:
;
;     with open('lib/snippet_where_precheck.asm') as f:
;         where_template = f.read()
;     where_block = where_template.format(
;         name            = 'asistencia_critica',
;         filter_col_idx  = 1,        # índice 0-based de la columna del where
;         filter_value    = 80,       # umbral entero del filtro
;         filter_jump_neg = 'JGE',    # salto si NO se cumple el filtro (negado)
;     )
;     # luego where_block se pasa a la plantilla del fact:
;     asm = fact_template.format(..., where_block=where_block)
;
; Si el dataset NO tiene filtro, Carim pasa where_block='' y este
; snippet no se incluye en absoluto.
;
; Placeholders (doble llave en comentarios; llave simple en el cuerpo):
;   {{name}}            nombre del fact — para apuntar a fila_loop_{{name}}
;                       y no_b_{{name}} / no_match_{{name}} del fact padre
;   {{filter_col_idx}}  índice de la columna del where (0-based)
;   {{filter_value}}    umbral entero del filtro
;   {{filter_jump_neg}} salto si NO se cumple el filtro (ya negado por codegen)
;
; Notas de integración:
;   - Este snippet va ANTES de las lecturas del fact en el fila_loop.
;   - Cuando el filtro no se cumple, salta directamente a fila_loop_{name}
;     PASANDO por el skip_to_eol que está al final del loop, para que SI
;     avance a la siguiente fila sin contar nada.
;   - SI apunta al inicio de la fila actual cuando este bloque se ejecuta.
;   - El snippet preserva SI (hace PUSH/POP alrededor de la lectura).
;   - No altera BX ni CX (contadores del fact).
; ============================================================
    ; ---- where pre-check: filtrar filas que no cumplen el dataset WHERE ----
    PUSH SI                             ; guardar inicio de la fila
    MOV AL, {filter_col_idx}
    CALL skip_to_col_N
    CALL parse_int                      ; AX = valor de la columna del filtro
    POP SI                             ; restaurar inicio de la fila

    CMP AX, {filter_value}
    {filter_jump_neg} skip_where_{name} ; no cumple el filtro -> saltar la fila
    JMP check_done_{name}               ; cumple el filtro -> continuar con el fact

skip_where_{name}:
    CALL skip_to_eol                    ; avanzar a la siguiente fila
    JMP fila_loop_{name}               ; volver al inicio del loop

check_done_{name}:
    ; la fila pasó el filtro, continúa la lógica normal del fact
