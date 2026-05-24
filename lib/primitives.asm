; ============================================================
; Primitivas de parsing para CSV 
; ============================================================
; Usadas por las rutinas count_<fact> que genera Carim a partir
; del code_generator. Tres rutinas fijas, no dependen del
; programa Snaptics: se escriben una vez y se quedan.
;
; Convención de registros:
;   - Entradas/salidas: ver firma de cada rutina.
;   - Cualquier rutina preserva CX, DX, SI, DI con PUSH/POP.
;     EXCEPCIÓN: SI lo modifican intencionalmente para avanzar
;     dentro del buffer; es parte del contrato.
;   - AX y BX son volátiles entre llamadas (los puede pisar).
;
; Restricciones del CSV :
;   - Solo enteros (sin decimales).
;   - Separador: coma  ','
;   - Fin de fila:    0Dh, 0Ah  (CRLF)
;   - Columnas referenciadas por índice (0-based).
; ============================================================


; ============================================================
; parse_int
; ------------------------------------------------------------
; Lee un entero ASCII del buffer.
;
;   Entrada:  SI -> primer dígito del número
;   Salida:   AX  = valor entero (sin signo, hasta 65535)
;             SI  = primer byte DESPUÉS del último dígito
;
;   Preserva: BX, CX, DX
;   Modifica: AX, SI
;
; Lee mientras [SI] esté en '0'..'9'. Si el primer byte no es
; un dígito, devuelve AX = 0 sin mover SI.
; ============================================================
parse_int PROC
    PUSH BX
    PUSH CX
    PUSH DX

    XOR AX, AX                  ; AX = 0  (acumulador)
    MOV BX, 10                  ; multiplicador

pi_loop:
    MOV CL, [SI]
    CMP CL, '0'
    JB  pi_done
    CMP CL, '9'
    JA  pi_done

    MUL BX                      ; DX:AX = AX * 10   (DX se restaura al final)

    SUB CL, '0'
    XOR CH, CH                  ; limpiar parte alta para ADD de 16 bits
    ADD AX, CX

    INC SI
    JMP pi_loop

pi_done:
    POP DX
    POP CX
    POP BX
    RET
parse_int ENDP


; ============================================================
; skip_to_col_N
; ------------------------------------------------------------
; Avanza SI hasta el inicio de la columna N de la fila actual.
;
;   Entrada:  SI -> primer byte de la fila
;             AL  = índice de columna (0 = primera columna)
;   Salida:   SI -> primer byte de la columna N
;
;   Preserva: BX, CX, DX
;   Modifica: AX, SI
;
; Si AL = 0, SI no se mueve. Si se encuentra fin de fila
; (0Dh, 0Ah o null) antes de llegar a la columna N, se detiene
; ahí para no salirse de la fila (defensivo).
; ============================================================
skip_to_col_N PROC
    PUSH CX

    XOR CH, CH
    MOV CL, AL                  ; CL = comas que faltan saltar
    OR  CL, CL
    JZ  stcn_done               ; columna 0 → ya estamos

stcn_scan:
    MOV AH, [SI]
    CMP AH, ','
    JE  stcn_comma
    CMP AH, 0Dh                 ; CR — fin de fila anticipado
    JE  stcn_done
    CMP AH, 0Ah                 ; LF — fin de fila anticipado
    JE  stcn_done
    OR  AH, AH                  ; null — fin de buffer
    JZ  stcn_done
    INC SI
    JMP stcn_scan

stcn_comma:
    INC SI                      ; saltar la coma
    DEC CL
    JNZ stcn_scan               ; aún faltan más comas
    ; cuando llegamos aquí, SI ya está en el inicio de la columna N

stcn_done:
    ; saltar espacios iniciales (ej: "juan,   85" → SI en '8')
stcn_spaces:
    MOV AH, [SI]
    CMP AH, ' '
    JNE stcn_end
    INC SI
    JMP stcn_spaces
stcn_end:
    POP CX
    RET
skip_to_col_N ENDP


; ============================================================
; skip_to_eol
; ------------------------------------------------------------
; Avanza SI hasta justo después del LF (0Ah) de la fila actual.
;
;   Entrada:  SI -> algún byte dentro de la fila
;   Salida:   SI -> primer byte de la fila SIGUIENTE
;             (o primer byte después de LF si era la última fila)
;
;   Preserva: BX, CX, DX
;   Modifica: AX, SI
;
; Si el buffer termina sin LF (CSV mal formado), corre hasta
; encontrar null. Si no hay null tampoco, el comportamiento es
; indefinido — Carim debe verificar bounds antes de llamar.
; ============================================================
skip_to_eol PROC
    PUSH AX

ste_loop:
    MOV AL, [SI]
    OR  AL, AL                  ; null = fin de buffer
    JZ  ste_done
    INC SI
    CMP AL, 0Ah                 ; LF = fin de fila
    JNE ste_loop
    ; al salir: SI está justo después del LF

ste_done:
    POP AX
    RET
skip_to_eol ENDP
