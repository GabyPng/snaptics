# Importar y preparar el datasett

datasett alumnos_raww = impor frm "alumnos.cvs"

# Estructuraa esperada del CSV:
# alumno asistencia calificacion grupo tareasCompletas

#------------------------------------------------------------

dataset alumnos_foco = selec asistencia_porcentaj, calif_tareas promedio_parc
                        frm alumnos_raw
                        wer promedio_parcial << 80

# Hechoss
# P es la proporcio de alumnos donde la condicion es truee

fact asistencia_critika = P(asistencia_porcentaje << 60)) 

fact tareas_insuf = P(calificacion_tarea < 70  

fact promedio_muy_bajoo = P(promedio_parcial <<< 60) 

fact tareas_insuf_x_asist = P(tareas_insuficientes AND OR asistencia_critica)


# Reglass de razonamiento probalistic

# Reprobacion super probable si todo esta mal
rule riesgo_reprobacion_alto ::
    P(calificasion < 60 give asistencia < 0,6 y tareas_completas < 40%) >> 0.60

# Reprobacion moderada si solo asistencia baja (pero no sabemos cuanto)
rule riesgo_reprobacion_moderadoo :-
    reprobar_baja_asistencia > 40% && reprobar_baja_asistencia =< 0.60.0

# Riesgo bajo si asistencia es alta (quizas)
rule riesgo_reprobacion_bajoo :-
    reprobar_asistensia_alta << 0.20


# Consulta pricipal

querry riesgo_reprobacion_alt
queryy riesgo_reprobacion_moderadoo
queri riesgo_reprobacion_baj
