; ============================================================
; test_csv_read.asm
; ============================================================
; Prueba end-to-end de lectura de CSV desde disco:
;   1. Abre el archivo con abrirArchivo (Biblioteca.lib)
;   2. Lee hasta 512 bytes en BUFFER
;   3. Itera fila por fila e imprime en pantalla:
;         Fila N  col0=<valor>  col1=<valor>
;
; CSV esperado en C:\dataset.txt (emu8086 virtual drive):
;   asistencia,promedio
;   75,82
;   55,61
;   90,45
;   48,78
;   67,55
;
; Para correr:
;   1. Copia dataset.txt al vdrive: C:\emu8086\vdrive\C\dataset.txt
;   2. Asegurate que Biblioteca.lib esta en C:\emu8086\inc\
;   3. Abre este .asm en emu8086 -> F5 (Compile and Run)
;   4. La salida aparece en la ventana de emulacion
; ============================================================

include Biblioteca.lib

.MODEL SMALL
.STACK 200h

.DATA
    RUTA         DB 'C:\dataset.txt', 0
    ID_ARCHIVO   DW 0
    BUFFER       DB 512 DUP(' ')
    BYTES_LEIDOS DW 0

    ; Resultado de cada fila (para inspeccion en memoria)
    col0_val     DW 0
    col1_val     DW 0

    ; Mensajes de pantalla
    msg_ok       DB 'Archivo abierto OK', 0Dh, 0Ah, '$'
    msg_err      DB 'ERROR: no se pudo abrir el archivo', 0Dh, 0Ah, '$'
    msg_fila     DB 'Fila ', '$'
    msg_col0     DB '  col0=', '$'
    msg_col1     DB '  col1=', '$'
    msg_nl       DB 0Dh, 0Ah, '$'
    fila_num     DB 0            ; contador de filas (1-based para mostrar)

.CODE
INICIO:
    MOV AX, @DATA
    MOV DS, AX
    MOV ES, AX

    ; ---- abrir archivo ----
    abrirArchivo 2, RUTA
    JC  error_apertura
    MOV ID_ARCHIVO, AX

    MOV AH, 09h
    LEA DX, msg_ok
    INT 21h

    ; ---- leer hasta 512 bytes ----
    leerArchivo 512, BUFFER, ID_ARCHIVO
    JC  error_apertura
    MOV BYTES_LEIDOS, AX

    cerrarArchivo ID_ARCHIVO

    ; ---- saltar la primera fila (cabecera) ----
    LEA SI, BUFFER
    CALL skip_to_eol             ; SI ahora apunta al inicio de la fila 1

    ; ---- iterar filas ----
loop_filas:
    ; verificar bounds: si SI >= BUFFER + BYTES_LEIDOS, terminamos
    MOV DX, SI
    SUB DX, OFFSET BUFFER
    CMP DX, BYTES_LEIDOS
    JGE fin

    ; verificar que hay algo que leer (no solo CR/LF/null)
    MOV AL, [SI]
    OR  AL, AL
    JZ  fin
    CMP AL, 0Dh
    JE  fin

    ; incrementar contador de fila
    INC fila_num

    ; guardar inicio de fila
    MOV BX, SI                   ; BX = inicio de la fila actual

    ; ---- leer columna 0 ----
    MOV SI, BX
    MOV AL, 0
    CALL skip_to_col_N
    CALL parse_int
    MOV col0_val, AX

    ; ---- leer columna 1 ----
    MOV SI, BX
    MOV AL, 1
    CALL skip_to_col_N
    CALL parse_int
    MOV col1_val, AX

    ; ---- imprimir "Fila N" ----
    MOV AH, 09h
    LEA DX, msg_fila
    INT 21h

    MOV AX, 0
    MOV AL, fila_num
    CALL print_int

    ; ---- imprimir "  col0=<valor>" ----
    MOV AH, 09h
    LEA DX, msg_col0
    INT 21h

    MOV AX, col0_val
    CALL print_int

    ; ---- imprimir "  col1=<valor>" ----
    MOV AH, 09h
    LEA DX, msg_col1
    INT 21h

    MOV AX, col1_val
    CALL print_int

    ; ---- salto de linea ----
    MOV AH, 09h
    LEA DX, msg_nl
    INT 21h

    ; ---- avanzar a la siguiente fila ----
    MOV SI, BX
    CALL skip_to_eol
    JMP loop_filas

error_apertura:
    MOV AH, 09h
    LEA DX, msg_err
    INT 21h

fin:
    MOV AX, 4C00h
    INT 21h

; ============================================================
include primitives.asm
; ============================================================
; print_int: imprime AX como decimal en pantalla
; ============================================================
print_int PROC
    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX

    MOV BX, 10
    XOR CX, CX          ; contador de digitos en stack

pi_div:
    XOR DX, DX
    DIV BX              ; AX = cociente, DX = digito
    PUSH DX
    INC CX
    OR  AX, AX
    JNZ pi_div

pi_print:
    POP DX
    ADD DL, '0'
    MOV AH, 02h
    INT 21h
    LOOP pi_print

    POP DX
    POP CX
    POP BX
    POP AX
    RET
print_int ENDP

END INICIO
