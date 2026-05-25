; ============================================================
; Programa generado por el codegen de Snaptics -> emu8086
; ============================================================
; --- ERRORES DE GENERACIÓN ---
; [GEN-001] (cuádrupla #1) Operación 'MEAN' fuera del alcance v1.
; -----------------------------

include Biblioteca.lib

.MODEL SMALL
.STACK 100h
.DATA
    ; ---- Sección DATA generada por codegen ----
    ; -- Temporales del IR --
    t0                   DW 0

    ; -- Mensajes de queries (consumidos por show_result) --
    msg_promedio         DB 'promedio = $'

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

    ; ---- Evaluación de reglas y queries ----
    ; --- pantalla 0 (pagina 0) query promedio [basic] ---
    MOV AL, 0
    CALL switch_to_page

    ; query promedio (basico)
    MOV AX, fact_promedio
    LEA SI, msg_promedio
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
;   (no hay facts derivados de dataset en este programa)

END INICIO
