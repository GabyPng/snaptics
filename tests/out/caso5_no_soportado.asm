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

    msg_evid_baja DB 13, 10, 'Evidencia: BAJA$'
    msg_evid_mod  DB 13, 10, 'Evidencia: MODERADA$'
    msg_evid_alta DB 13, 10, 'Evidencia: ALTA$'
    msg_err_file  DB 'Error abriendo el dataset.', 13, 10, '$'

.CODE
INICIO:
    MOV AX, @DATA
    MOV DS, AX
    MOV ES, AX

    ; ---- Evaluación de reglas y queries ----
    ; query promedio
    MOV AX, fact_promedio
    LEA SI, msg_promedio
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
;   (no hay facts derivados de dataset en este programa)

END INICIO
