;========================================
; Librer�a de dispositivos de salida
; output_devices.asm
;========================================

;---- Puertos ----
LED_PORT     EQU 199      ; Puerto del LED display
TRAFFIC_PORT EQU 4        ; Puerto del sem�foro

;---- Mensajes ----
msg_evid_baja DB 13,10,'Evidencia: BAJA$'
msg_evid_mod  DB 13,10,'Evidencia: MODERADA$'
msg_evid_alta DB 13,10,'Evidencia: ALTA$'

;--------------------------------------------------
; print_int
; Entrada : AX = n�mero a imprimir (0-100)

print_int PROC NEAR

    ; Guardar registros
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    MOV BX, 10             ; Divisor decimal
    XOR CX, CX             ; Contador de d�gitos

pi_apilar:
    XOR DX, DX             ; Limpiar DX antes de DIV
    DIV BX                 ; AX = cociente, DX = residuo
    PUSH DX                ; Guardar d�gito
    INC CX                 ; Incrementar contador
    OR AX, AX              ; �AX es 0?
    JNZ pi_apilar          ; Si no, continuar

pi_imprimir:
    POP DX                 ; Recuperar d�gito
    ADD DL, '0'            ; Convertir a ASCII
    MOV AH, 02h            ; INT 21h -> imprimir car�cter
    INT 21h
    LOOP pi_imprimir

    ; Restaurar registros
    POP DI
    POP SI
    POP DX
    POP CX
    POP BX

    RET
print_int ENDP


;-------------------------------------
; show_led
; Entrada : AX = n�mero a mostrar

show_led PROC NEAR

    PUSH AX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    ; Enviar n�mero al LED display
    OUT LED_PORT, AX

    ; Restaurar registros
    POP DI
    POP SI
    POP DX
    POP CX
    POP AX

    RET
show_led ENDP


;---------------------------------------------------------
; show_traffic
; Entrada : AX = probabilidad (0-100)

show_traffic PROC NEAR

    PUSH AX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    ; Determinar color segun probabilidad, interpretada como NIVEL DE ALERTA:
    ;   0..32   verde   (sin alerta)
    ;   33..65  amarillo (alerta moderada)
    ;   66..100 rojo    (alerta alta)
    CMP AX, 33
    JB  st_verde

    CMP AX, 66
    JB  st_amarillo

    ; AX >= 66 -> rojo (cae por fallthrough al primer label de abajo)
st_rojo:
    MOV AX, 0001h
    JMP st_out

st_amarillo:
    MOV AX, 0002h
    JMP st_out

st_verde:
    MOV AX, 0004h

st_out:
    ; Enviar valor al semaforo
    OUT TRAFFIC_PORT, AX

    ; Restaurar registros
    POP DI
    POP SI
    POP DX
    POP CX
    POP AX

    RET
show_traffic ENDP


;------------------------------------------------------
; show_result
; Entrada :
;   AX = probabilidad (0-100)
;   SI = nombre de la query terminado en '$'

show_result PROC NEAR

    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    MOV BX, AX             ; Guardar probabilidad

    ;---- Imprimir nombre de la query (a pantalla + log) ----
    CALL print_log_str     ; SI ya apunta a msg_<query>

    ;---- Imprimir probabilidad ----
    MOV AX, BX
    CALL print_log_int

    ;---- Mostrar en LED display ----
    MOV AX, BX
    CALL show_led

    ;---- Mostrar sem�foro ----
    MOV AX, BX
    CALL show_traffic

    ;---- Mostrar nivel de evidencia ----
    CMP BX, 33
    JB  sr_baja

    CMP BX, 66
    JB  sr_mod

    ; Evidencia alta
sr_alta:
    LEA SI, msg_evid_alta
    JMP sr_print

    ; Evidencia moderada
sr_mod:
    LEA SI, msg_evid_mod
    JMP sr_print

    ; Evidencia baja
sr_baja:
    LEA SI, msg_evid_baja

sr_print:
    CALL print_log_str

    ;---- Pausa con navegacion por flechas ----
    CALL nav_pause

    ; Restaurar registros
    POP DI
    POP SI
    POP DX
    POP CX
    POP BX
    POP AX

    RET
show_result ENDP
