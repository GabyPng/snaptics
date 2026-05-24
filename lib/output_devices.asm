;========================================
; Librería de dispositivos de salida
; output_devices.asm
;========================================

;---- Puertos ----
LED_PORT     EQU 199      ; Puerto del LED display
TRAFFIC_PORT EQU 4        ; Puerto del semáforo

;---- Mensajes ----
msg_evid_baja DB 13,10,'Evidencia: BAJA$'
msg_evid_mod  DB 13,10,'Evidencia: MODERADA$'
msg_evid_alta DB 13,10,'Evidencia: ALTA$'

;--------------------------------------------------
; print_int
; Entrada : AX = número a imprimir (0-100)

print_int PROC NEAR

    ; Guardar registros
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    MOV BX, 10             ; Divisor decimal
    XOR CX, CX             ; Contador de dígitos

pi_apilar:
    XOR DX, DX             ; Limpiar DX antes de DIV
    DIV BX                 ; AX = cociente, DX = residuo
    PUSH DX                ; Guardar dígito
    INC CX                 ; Incrementar contador
    OR AX, AX              ; ¿AX es 0?
    JNZ pi_apilar          ; Si no, continuar

pi_imprimir:
    POP DX                 ; Recuperar dígito
    ADD DL, '0'            ; Convertir a ASCII
    MOV AH, 02h            ; INT 21h -> imprimir carácter
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
; Entrada : AX = número a mostrar

show_led PROC NEAR

    PUSH AX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    ; Enviar número al LED display
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

    ; Determinar color según probabilidad
    CMP AX, 33
    JB  st_rojo

    CMP AX, 66
    JB  st_amarillo

    ; AX >= 66 -> verde
st_verde:
    MOV AX, 0004h
    JMP st_out

st_amarillo:
    MOV AX, 0002h
    JMP st_out

st_rojo:
    MOV AX, 0001h

st_out:
    ; Enviar valor al semáforo
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

    ;---- Imprimir nombre de la query ----
    MOV DX, SI
    MOV AH, 09h
    INT 21h                ; Imprime hasta encontrar '$'

    ;---- Imprimir probabilidad ----
    MOV AX, BX
    CALL print_int

    ;---- Mostrar en LED display ----
    MOV AX, BX
    CALL show_led

    ;---- Mostrar semáforo ----
    MOV AX, BX
    CALL show_traffic

    ;---- Mostrar nivel de evidencia ----
    CMP BX, 33
    JB  sr_baja

    CMP BX, 66
    JB  sr_mod

    ; Evidencia alta
sr_alta:
    MOV DX, OFFSET msg_evid_alta
    JMP sr_print

    ; Evidencia moderada
sr_mod:
    MOV DX, OFFSET msg_evid_mod
    JMP sr_print

    ; Evidencia baja
sr_baja:
    MOV DX, OFFSET msg_evid_baja

sr_print:
    MOV AH, 09h
    INT 21h

    ; Restaurar registros
    POP DI
    POP SI
    POP DX
    POP CX
    POP BX
    POP AX

    RET
show_result ENDP
