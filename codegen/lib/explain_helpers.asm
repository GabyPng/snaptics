;========================================
; explain_helpers.asm
; Helpers para paginacion con flechas,
; logging a archivo y emision de explain/why.
;========================================
;
; Variables compartidas (declaradas en .DATA por el codegen):
;   OUTPUT_PATH  DB '<ruta>', 0
;   LOG_HANDLE   DW 0
;   cur_page     DB 0
;   max_page     DB 0
;   nav_prompt   DB '...$'
;   itoa_buf     DB ' ',' ',' ',' ',' ',' ',' ','$'
;
; Constantes
SCAN_ESC    EQU 01h
SCAN_LEFT   EQU 4Bh
SCAN_RIGHT  EQU 4Dh


;----------------------------------------
; open_log_file
; Crea (truncando) el archivo de log en OUTPUT_PATH.
; Salida: LOG_HANDLE = handle, o 0 si fallo.
;----------------------------------------
open_log_file PROC
    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX
    MOV AH, 3Ch
    XOR CX, CX
    LEA DX, OUTPUT_PATH
    INT 21h
    JC ofl_err
    MOV LOG_HANDLE, AX
    JMP ofl_done
ofl_err:
    MOV WORD PTR LOG_HANDLE, 0
ofl_done:
    POP DX
    POP CX
    POP BX
    POP AX
    RET
open_log_file ENDP


;----------------------------------------
; close_log_file
;----------------------------------------
close_log_file PROC
    PUSH AX
    PUSH BX
    MOV BX, LOG_HANDLE
    OR BX, BX
    JZ clf_done
    MOV AH, 3Eh
    INT 21h
    MOV WORD PTR LOG_HANDLE, 0
clf_done:
    POP BX
    POP AX
    RET
close_log_file ENDP


;----------------------------------------
; print_log_str
; Entrada: SI = puntero a cadena terminada en '$'
; Imprime en pantalla (INT 21h/09h) y agrega al log.
;----------------------------------------
print_log_str PROC
    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    MOV DX, SI
    MOV AH, 09h
    INT 21h

    ; Calcular longitud hasta '$'
    MOV DI, SI
    XOR CX, CX
pls_scan:
    MOV AL, [DI]
    CMP AL, '$'
    JE pls_write
    INC DI
    INC CX
    JMP pls_scan
pls_write:
    OR CX, CX
    JZ pls_done
    MOV BX, LOG_HANDLE
    OR BX, BX
    JZ pls_done
    MOV AH, 40h
    MOV DX, SI
    INT 21h
pls_done:
    POP DI
    POP SI
    POP DX
    POP CX
    POP BX
    POP AX
    RET
print_log_str ENDP


;----------------------------------------
; print_log_int
; Entrada: AX = entero 0..65535
; Imprime en pantalla y al log.
;----------------------------------------
print_log_int PROC
    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX
    PUSH SI
    PUSH DI

    LEA DI, itoa_buf
    MOV SI, DI
    MOV BX, 10
    XOR CX, CX
pli_apilar:
    XOR DX, DX
    DIV BX
    PUSH DX
    INC CX
    OR AX, AX
    JNZ pli_apilar

pli_pop:
    POP DX
    ADD DL, '0'
    MOV [DI], DL
    INC DI
    LOOP pli_pop
    MOV BYTE PTR [DI], '$'

    ; Imprimir buffer terminado en '$'
    MOV DX, SI
    MOV AH, 09h
    INT 21h

    ; Calcular longitud para escribir al log
    MOV CX, DI
    SUB CX, SI
    JCXZ pli_done
    MOV BX, LOG_HANDLE
    OR BX, BX
    JZ pli_done
    MOV DX, SI
    MOV AH, 40h
    INT 21h
pli_done:
    POP DI
    POP SI
    POP DX
    POP CX
    POP BX
    POP AX
    RET
print_log_int ENDP


;----------------------------------------
; switch_to_page
; Entrada: AL = numero de pagina (0..3)
; Activa la pagina y reposiciona el cursor en (0,0).
; Actualiza cur_page y, si es nueva pagina, limpia.
;----------------------------------------
switch_to_page PROC
    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX

    MOV cur_page, AL

    ; Activar la pagina (AH=05h, AL=pagina)
    PUSH AX
    MOV AH, 05h
    INT 10h
    POP AX

    ; Limpiar la pagina activa (AH=06h scroll, AL=0 -> clear)
    PUSH AX
    MOV AH, 06h
    MOV AL, 0                ; 0 lineas = limpiar toda la ventana
    MOV BH, 07h              ; atributo color por defecto
    MOV CH, 0
    MOV CL, 0
    MOV DH, 24
    MOV DL, 79
    INT 10h
    POP AX

    ; Reposicionar cursor en (0,0) de la pagina activa
    MOV BH, AL
    MOV AH, 02h
    XOR DX, DX
    INT 10h

    POP DX
    POP CX
    POP BX
    POP AX
    RET
switch_to_page ENDP


;----------------------------------------
; nav_pause
; Pausa entre screens: imprime el nav_prompt y espera flecha.
;   LEFT  -> retrocede pagina (si cur_page > 0), redibuja, espera de nuevo
;   RIGHT -> regresa al caller (avanza al siguiente screen)
;   ESC   -> termina el programa
;----------------------------------------
nav_pause PROC
    PUSH AX
    PUSH BX
    PUSH DX

    LEA DX, nav_prompt
    MOV AH, 09h
    INT 21h

np_wait:
    MOV AH, 00h
    INT 16h
    CMP AH, SCAN_ESC
    JE np_exit
    CMP AH, SCAN_RIGHT
    JE np_done
    CMP AH, SCAN_LEFT
    JE np_left
    JMP np_wait

np_left:
    MOV AL, cur_page
    OR AL, AL
    JZ np_wait               ; ya estamos en pagina 0; ignorar
    DEC AL
    PUSH AX
    MOV AH, 05h
    INT 10h
    POP AX
    MOV cur_page, AL
    JMP np_wait

np_done:
    POP DX
    POP BX
    POP AX
    RET

np_exit:
    CALL close_log_file
    MOV AX, 4C00h
    INT 21h
nav_pause ENDP


;----------------------------------------
; final_nav_loop
; Despues del ultimo screen: el usuario puede navegar libremente
; entre las paginas 0..max_page con flechas. ESC termina.
;----------------------------------------
final_nav_loop PROC
    PUSH AX
    PUSH BX
    PUSH DX

    LEA DX, nav_prompt
    MOV AH, 09h
    INT 21h

fnl_wait:
    MOV AH, 00h
    INT 16h
    CMP AH, SCAN_ESC
    JE fnl_exit
    CMP AH, SCAN_RIGHT
    JE fnl_right
    CMP AH, SCAN_LEFT
    JE fnl_left
    JMP fnl_wait

fnl_left:
    MOV AL, cur_page
    OR AL, AL
    JZ fnl_wrap_to_max
    DEC AL
    JMP fnl_apply
fnl_wrap_to_max:
    MOV AL, max_page
fnl_apply:
    MOV cur_page, AL
    PUSH AX
    MOV AH, 05h
    INT 10h
    POP AX
    JMP fnl_wait

fnl_right:
    MOV AL, cur_page
    MOV BL, max_page
    CMP AL, BL
    JB fnl_inc
    XOR AL, AL               ; al final, regresa a pagina 0
    JMP fnl_apply2
fnl_inc:
    INC AL
fnl_apply2:
    MOV cur_page, AL
    PUSH AX
    MOV AH, 05h
    INT 10h
    POP AX
    JMP fnl_wait

fnl_exit:
    POP DX
    POP BX
    POP AX
    RET
final_nav_loop ENDP
