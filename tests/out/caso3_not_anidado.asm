; ============================================================
; Programa generado por el codegen de Snaptics -> emu8086
; ============================================================
include Biblioteca.lib

.MODEL SMALL
.STACK 100h
.DATA
    ; ---- Sección DATA generada por codegen ----
    RUTA         DB 'ventas.csv', 0
    ID_ARCHIVO   DW 0
    BUFFER       DB 4096 DUP(' ')
    BYTES_LEIDOS DW 0

    ; -- Facts derivados del dataset (los llena count_<fact>) --
    fact_altas            DW 0    ; P(monto > 500)
    fact_margen_bajo      DW 0    ; P(margen < 10)

    ; -- Resultado de evaluación de cada regla --
    rule_sano             DW 0

    ; -- Temporales del IR --
    t0                   DW 0
    t1                   DW 0
    t2                   DW 0
    t3                   DW 0
    t4                   DW 0
    t5                   DW 0

    ; -- Mensajes de queries (consumidos por show_result) --
    msg_sano             DB 'sano = $'

    ; -- Mensajes de evidencia (consumidos por show_result) --
    msg_evid_baja DB ' (evidencia: baja)', 13, 10, '$'
    msg_evid_mod  DB ' (evidencia: moderada)', 13, 10, '$'
    msg_evid_alta DB ' (evidencia: alta)', 13, 10, '$'
    msg_err_file  DB 'Error abriendo el dataset.', 13, 10, '$'

.CODE
INICIO:
    MOV AX, @DATA
    MOV DS, AX
    MOV ES, AX

    ; ---- Apertura y lectura del CSV ----
    abrirArchivo 2, RUTA          ; modo 2 = lectura/escritura
    MOV ID_ARCHIVO, AX
    JC error_archivo
    leerArchivo 4096, BUFFER, ID_ARCHIVO
    JC error_archivo
    MOV BYTES_LEIDOS, AX

    ; ---- Cálculo de facts derivados (rutinas emitidas por Carim) ----
    CALL count_altas             ; P(monto > 500)
    CALL count_margen_bajo             ; P(margen < 10)

    ; ---- Evaluación de reglas y queries ----
    ; NOT margen_bajo -> t4
    MOV AX, fact_margen_bajo
    CALL fuzzy_not
    MOV t4, AX

    ; AND altas, t4 -> t5
    MOV AX, fact_altas
    MOV BX, t4
    CALL fuzzy_and
    MOV t5, AX

    ; rule sano := t5
    MOV AX, t5
    MOV rule_sano, AX

    ; query sano
    MOV AX, rule_sano
    LEA SI, msg_sano
    CALL show_result

    JMP fin

error_archivo:
    MOV AH, 09h
    LEA DX, msg_err_file
    INT 21h

fin:
    MOV AX, 4C00h
    INT 21h

; ============================================================
; Rutinas externas requeridas (deben incluirse / pegarse)
; ============================================================
; Gibran:
;   fuzzy_and PROC  (AX, BX -> AX = MIN(AX, BX))
;   fuzzy_or  PROC  (AX, BX -> AX = MAX(AX, BX))
;   fuzzy_not PROC  (AX     -> AX = 100 - AX)
;
; Fanny:
;   show_result   PROC  (AX = prob, SI = offset de msg_<query>)
;   print_int     PROC  (AX = entero 0..100)
;   show_led      PROC  (AX = entero 0..100 -> puerto LED)
;   show_traffic  PROC  (AX = entero 0..100 -> puerto semáforo)
;
; Carim (generadas por su módulo, una por cada fact derivado):
;   count_altas PROC  ; P(monto > 500)  (count_<fact>)
;   count_margen_bajo PROC  ; P(margen < 10)  (count_<fact>)

END INICIO
