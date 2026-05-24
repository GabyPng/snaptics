; ============================================================
; test_fuzzy_logic.asm  —  Pruebas para fuzzy_and / or / not
; ============================================================
; Abre este archivo en emu8086 y corre con F5.
; Al terminar, revisa el panel de variables/memoria buscando
; los slots res_* y compara contra los valores esperados:
;
;   Prueba                          Variable          Esperado
;   ─────────────────────────────────────────────────────────
;   AND(70, 40)  → min = 40        res_and1          40
;   AND(30, 30)  → min = 30        res_and2          30
;   AND(100,  0) → min =  0        res_and3           0
;   AND(  0,100) → min =  0        res_and4           0
;   OR( 70, 40)  → max = 70        res_or1           70
;   OR( 30, 30)  → max = 30        res_or2           30
;   OR(100,  0)  → max = 100       res_or3          100
;   OR(  0,100)  → max = 100       res_or4          100
;   NOT(70)      → 100-70 = 30     res_not1          30
;   NOT( 0)      → 100- 0 = 100    res_not2         100
;   NOT(100)     → 100-100 = 0     res_not3           0
;   Cadena AND+OR+NOT del caso2 y caso3 del pipeline:
;     altas=70, margen_bajo=40
;     AND(70,40)=40  -> res_chain_and      40
;     NOT(margen_bajo=40) = 60
;     AND(altas=70, NOT(40)) = AND(70,60) = 60 -> res_chain_not_and  60
; ============================================================

.MODEL SMALL
.STACK 100h
.DATA
    ; ---- slots de resultados ----
    res_and1         DW 0    ; AND(70, 40)  esperado: 40
    res_and2         DW 0    ; AND(30, 30)  esperado: 30
    res_and3         DW 0    ; AND(100, 0)  esperado: 0
    res_and4         DW 0    ; AND(0, 100)  esperado: 0

    res_or1          DW 0    ; OR(70, 40)   esperado: 70
    res_or2          DW 0    ; OR(30, 30)   esperado: 30
    res_or3          DW 0    ; OR(100, 0)   esperado: 100
    res_or4          DW 0    ; OR(0, 100)   esperado: 100

    res_not1         DW 0    ; NOT(70)      esperado: 30
    res_not2         DW 0    ; NOT(0)       esperado: 100
    res_not3         DW 0    ; NOT(100)     esperado: 0

    ; Cadena que imita el caso2 del pipeline: AND(altas, margen_bajo)
    res_chain_and    DW 0    ; AND(70, 40)  esperado: 40
    ; Cadena que imita el caso3: AND(altas, NOT(margen_bajo))
    res_chain_not_and DW 0   ; AND(70, 60)  esperado: 60

.CODE
INICIO:
    MOV AX, @DATA
    MOV DS, AX
    MOV ES, AX

    ; =========================================================
    ; Bloque fuzzy_and
    ; =========================================================

    ; AND(70, 40) → 40
    MOV AX, 70
    MOV BX, 40
    CALL fuzzy_and
    MOV res_and1, AX

    ; AND(30, 30) → 30  (empate: devuelve el mismo valor)
    MOV AX, 30
    MOV BX, 30
    CALL fuzzy_and
    MOV res_and2, AX

    ; AND(100, 0) → 0   (certeza vs imposibilidad)
    MOV AX, 100
    MOV BX, 0
    CALL fuzzy_and
    MOV res_and3, AX

    ; AND(0, 100) → 0   (orden invertido, mismo resultado)
    MOV AX, 0
    MOV BX, 100
    CALL fuzzy_and
    MOV res_and4, AX

    ; =========================================================
    ; Bloque fuzzy_or
    ; =========================================================

    ; OR(70, 40) → 70
    MOV AX, 70
    MOV BX, 40
    CALL fuzzy_or
    MOV res_or1, AX

    ; OR(30, 30) → 30   (empate)
    MOV AX, 30
    MOV BX, 30
    CALL fuzzy_or
    MOV res_or2, AX

    ; OR(100, 0) → 100
    MOV AX, 100
    MOV BX, 0
    CALL fuzzy_or
    MOV res_or3, AX

    ; OR(0, 100) → 100  (orden invertido)
    MOV AX, 0
    MOV BX, 100
    CALL fuzzy_or
    MOV res_or4, AX

    ; =========================================================
    ; Bloque fuzzy_not
    ; =========================================================

    ; NOT(70) → 30
    MOV AX, 70
    CALL fuzzy_not
    MOV res_not1, AX

    ; NOT(0) → 100
    MOV AX, 0
    CALL fuzzy_not
    MOV res_not2, AX

    ; NOT(100) → 0
    MOV AX, 100
    CALL fuzzy_not
    MOV res_not3, AX

    ; =========================================================
    ; Cadena caso2: rule problema :- altas AND margen_bajo
    ;   altas = 70, margen_bajo = 40  →  AND = 40
    ; =========================================================
    MOV AX, 70           ; fact_altas
    MOV BX, 40           ; fact_margen_bajo
    CALL fuzzy_and
    MOV res_chain_and, AX

    ; =========================================================
    ; Cadena caso3: rule sano :- altas AND NOT(margen_bajo)
    ;   altas = 70, margen_bajo = 40
    ;   NOT(40) = 60  →  AND(70, 60) = 60
    ; =========================================================
    MOV AX, 40           ; fact_margen_bajo
    CALL fuzzy_not       ; AX = 60  (complemento)
    MOV BX, AX           ; BX = NOT(margen_bajo) = 60
    MOV AX, 70           ; fact_altas
    CALL fuzzy_and
    MOV res_chain_not_and, AX

    ; ---- fin ----
    MOV AX, 4C00h
    INT 21h

; ============================================================
; Rutinas — incluidas directamente para test standalone
; ============================================================
include fuzzy_logic.asm

END INICIO
