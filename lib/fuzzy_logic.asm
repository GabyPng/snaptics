; ============================================================
; fuzzy_logic.asm  —  Rutinas de lógica difusa para Snaptics
; ============================================================
; Tres rutinas que implementan AND / OR / NOT sobre probabilidades
; representadas como enteros 0..100 (no como 0..1 float).
;
; Convención de registros (misma que todo el proyecto):
;   - Probabilidades viajan en AX  (y BX para operaciones binarias).
;   - Se preservan CX, DX, SI, DI con PUSH/POP.
;   - AX y BX son volátiles: el llamador no debe asumir que sobreviven
;     si no guardó primero.
;
; Por qué MIN para AND y MAX para OR:
;   La lógica de Zadeh define:
;       T-norma  (AND) = min(a, b)   — el grado más restrictivo
;       S-norma  (OR)  = max(a, b)   — el grado más permisivo
;       NOT(a)         = 100 - a     — complemento en escala entera
;   Es la misma semántica que usa el codegen en _emit_binary_logic.
; ============================================================


; ============================================================
; fuzzy_and
; ------------------------------------------------------------
; Devuelve el MÍNIMO de dos probabilidades (T-norma de Zadeh).
;
;   Entrada : AX = prob_a  (0..100)
;             BX = prob_b  (0..100)
;   Salida  : AX = min(AX, BX)
;
;   Preserva: CX, DX, SI, DI
;   Modifica: AX, BX
; ============================================================
fuzzy_and PROC
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    CMP AX, BX
    JLE fand_done       ; AX ya es el menor, no hay nada que hacer
    MOV AX, BX          ; BX es menor -> copiarlo a AX

fand_done:
    POP DI
    POP SI
    POP DX
    POP CX
    RET
fuzzy_and ENDP


; ============================================================
; fuzzy_or
; ------------------------------------------------------------
; Devuelve el MÁXIMO de dos probabilidades (S-norma de Zadeh).
;
;   Entrada : AX = prob_a  (0..100)
;             BX = prob_b  (0..100)
;   Salida  : AX = max(AX, BX)
;
;   Preserva: CX, DX, SI, DI
;   Modifica: AX, BX
; ============================================================
fuzzy_or PROC
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    CMP AX, BX
    JGE for_done        ; AX ya es el mayor, no hay nada que hacer
    MOV AX, BX          ; BX es mayor -> copiarlo a AX

for_done:
    POP DI
    POP SI
    POP DX
    POP CX
    RET
fuzzy_or ENDP


; ============================================================
; fuzzy_not
; ------------------------------------------------------------
; Complemento difuso: NOT(a) = 100 - a
;
;   Entrada : AX = prob_a  (0..100)
;   Salida  : AX = 100 - AX
;
;   Preserva: BX, CX, DX, SI, DI
;   Modifica: AX
; ============================================================
fuzzy_not PROC
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    MOV BX, 100
    SUB BX, AX
    MOV AX, BX          ; AX = 100 - AX original

    POP DI
    POP SI
    POP DX
    POP CX
    POP BX
    RET
fuzzy_not ENDP
