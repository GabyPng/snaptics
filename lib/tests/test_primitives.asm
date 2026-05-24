; ============================================================
; Test standalone de las primitivas de Fanny
; ============================================================
; Ejercita parse_int, skip_to_col_N y skip_to_eol sobre un
; buffer CSV hardcodeado. Si todo funciona, los resultados
; quedan en variables específicas que Fanny puede inspeccionar
; en el panel de memoria de emu8086.
;
; Uso:
;   1. Abre este archivo en emu8086
;   2. F5 (assembly + run)
;   3. Al terminar, revisa estos valores en el panel de memoria:
;       res_parse1    debe ser 123 (0x007B)
;       res_skipcol   debe ser '4'  (0x34)  ← primer byte de la col 1
;       res_parse2    debe ser 45  (0x002D)
;       res_skipeol   debe ser '8'  (0x38)  ← primer byte de la fila 2
;
;   Si los cuatro coinciden, las tres primitivas funcionan.
;   Si alguno difiere, ese te dice cuál rompió.
; ============================================================

.MODEL SMALL
.STACK 100h
.DATA
    ; CSV de prueba: dos filas, tres columnas
    ;   fila 1:  123, 45, 67
    ;   fila 2:  89, 10, 11
    BUFFER       DB '123,45,67', 0Dh, 0Ah
                 DB '89,10,11',  0Dh, 0Ah, 0    ; null terminator de cortesía

    ; Slots para resultados de cada prueba
    res_parse1   DW 0
    res_skipcol  DB 0
    res_parse2   DW 0
    res_skipeol  DB 0

.CODE
INICIO:
    MOV AX, @DATA
    MOV DS, AX

    ; ---- prueba 1: parse_int sobre "123" ----
    LEA SI, BUFFER
    CALL parse_int
    MOV res_parse1, AX           ; esperado: 123

    ; ---- prueba 2: skip_to_col_N N=1 sobre la fila 1 ----
    LEA SI, BUFFER
    MOV AL, 1                    ; columna 1
    CALL skip_to_col_N
    MOV AL, [SI]                 ; byte donde quedó SI
    MOV res_skipcol, AL          ; esperado: '4' (0x34)

    ; ---- prueba 3: parse_int desde donde quedó SI ----
    CALL parse_int
    MOV res_parse2, AX           ; esperado: 45

    ; ---- prueba 4: skip_to_eol desde mitad de fila 1 ----
    LEA SI, BUFFER
    ADD SI, 5                    ; cualquier byte dentro de fila 1
    CALL skip_to_eol
    MOV AL, [SI]
    MOV res_skipeol, AL          ; esperado: '8' (0x38), primer byte de fila 2

    ; salir
    MOV AX, 4C00h
    INT 21h

; ------------------------------------------------------------
; Aquí abajo van las primitivas. Para correr el test, pega el
; contenido completo de primitives.asm en este punto
; ------------------------------------------------------------
include primitives.asm

END INICIO
