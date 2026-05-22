; ============================================================
; Programa generado por el codegen de Snaptics -> emu8086
; ============================================================
include Biblioteca.lib

.MODEL SMALL
.STACK 100h
.DATA
    ; ---- Sección DATA generada por codegen ----
    RUTA         DB 'alumnos.csv', 0
    ID_ARCHIVO   DW 0
    BUFFER       DB 4096 DUP(' ')
    BYTES_LEIDOS DW 0

    ; -- Facts derivados del dataset (los llena count_<fact>) --
    fact_asistencia_critica DW 0    ; P(asistencia < 60)
    fact_p_reprob_dada_asist DW 0    ; P(promedio < 60 given asistencia < 60)

    ; -- Resultado de evaluación de cada regla --
    rule_alerta           DW 0

    ; -- Temporales del IR --
    t0                   DW 0
    t1                   DW 0
    t2                   DW 0
    t3                   DW 0
    t4                   DW 0
    t5                   DW 0
    t6                   DW 0
    t7                   DW 0
    t8                   DW 0
    t9                   DW 0
    t10                  DW 0
    t11                  DW 0

    ; -- Mensajes de queries (consumidos por show_result) --
    msg_alerta           DB 'alerta = $'

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
    CALL count_asistencia_critica             ; P(asistencia < 60)
    CALL count_p_reprob_dada_asist             ; P(promedio < 60 given asistencia < 60)

    ; ---- Evaluación de reglas y queries ----
    ; AND asistencia_critica, p_reprob_dada_asist -> t11
    MOV AX, fact_asistencia_critica
    MOV BX, fact_p_reprob_dada_asist
    CALL fuzzy_and
    MOV t11, AX

    ; rule alerta := t11
    MOV AX, t11
    MOV rule_alerta, AX

    ; query alerta
    MOV AX, rule_alerta
    LEA SI, msg_alerta
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
;   count_asistencia_critica PROC  ; P(asistencia < 60)  (count_<fact>)   [+ where promedio < 80 sobre alumnos_foco]
;   count_p_reprob_dada_asist PROC  ; P(promedio < 60 given asistencia < 60)  (count_given_<fact>)   [+ where promedio < 80 sobre alumnos_foco]

END INICIO
