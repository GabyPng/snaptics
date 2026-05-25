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
    BUFFER       DB 4096 DUP(0)
    BYTES_LEIDOS DW 0

    ; -- Facts derivados del dataset (los llena count_<fact>) --
    fact_altas            DW 0    ; P(monto > 500)
    fact_altas_cnt DW 0    ; matches
    fact_altas_tot DW 0    ; total considerado

    ; -- Resultado de evaluación de cada regla --
    rule_alerta           DW 0

    ; -- Temporales del IR --
    t0                   DW 0
    t1                   DW 0
    t2                   DW 0
    t3                   DW 0
    t4                   DW 0

    ; -- Mensajes de queries (consumidos por show_result) --
    msg_alerta           DB 'alerta = $'

    msg_evid_baja DB 13, 10, 'Evidencia: BAJA', 13, 10, '$'
    msg_evid_mod  DB 13, 10, 'Evidencia: MODERADA', 13, 10, '$'
    msg_evid_alta DB 13, 10, 'Evidencia: ALTA', 13, 10, '$'
    msg_continuar DB 13, 10, '>> Presiona una tecla para continuar...', 13, 10, 13, 10, '$'
    msg_err_file  DB 'Error abriendo el dataset.', 13, 10, '$'

    ; -- Logging a archivo y paginacion por flechas --
    OUTPUT_PATH  DB 'C:\emu8086\vdrive\C\output\queries.txt', 0
    LOG_HANDLE   DW 0
    cur_page     DB 0
    max_page     DB 0
    nav_prompt   DB 13, 10, '>> Flechas: <- anterior, -> siguiente, ESC para salir', 13, 10, '$'
    itoa_buf     DB '       ', '$', 0  ; espacio para hasta 6 digitos + '$'
    msg_true     DB ' SE CUMPLE', 13, 10, '$'
    msg_false    DB ' NO SE CUMPLE', 13, 10, '$'


.CODE
INICIO:
    MOV AX, @DATA
    MOV DS, AX
    MOV ES, AX

    ; ---- Abrir archivo de log (queries -> .txt) ----
    CALL open_log_file

    ; ---- Apertura y lectura del CSV ----
    abrirArchivo 2, RUTA          ; modo 2 = lectura/escritura
    MOV ID_ARCHIVO, AX
    JC error_archivo
    leerArchivo 4096, BUFFER, ID_ARCHIVO
    JC error_archivo
    MOV BYTES_LEIDOS, AX

    ; ---- Cálculo de facts derivados (rutinas emitidas por Carim) ----
    CALL count_altas             ; P(monto > 500)

    ; ---- Evaluación de reglas y queries ----
    ; GT altas, 0.3 -> t2  (cmp crisp en regla)
    MOV AX, fact_altas
    CMP AX, 30
    JG cmp_t_0
    MOV AX, 0
    JMP cmp_d_0
cmp_t_0:
    MOV AX, 100
cmp_d_0:
    MOV t2, AX

    ; GT altas, 0.5 -> t3  (cmp crisp en regla)
    MOV AX, fact_altas
    CMP AX, 50
    JG cmp_t_1
    MOV AX, 0
    JMP cmp_d_1
cmp_t_1:
    MOV AX, 100
cmp_d_1:
    MOV t3, AX

    ; OR t2, t3 -> t4
    MOV AX, t2
    MOV BX, t3
    CALL fuzzy_or
    MOV t4, AX

    ; rule alerta := t4
    MOV AX, t4
    MOV rule_alerta, AX

    ; --- pantalla 0 (pagina 0) query alerta [basic] ---
    MOV AL, 0
    CALL switch_to_page

    ; query alerta (basico)
    MOV AX, rule_alerta
    LEA SI, msg_alerta
    CALL show_result

    ; ---- Navegacion libre por flechas tras los queries ----
    MOV BYTE PTR max_page, 0
    CALL final_nav_loop
    CALL close_log_file

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

END INICIO
