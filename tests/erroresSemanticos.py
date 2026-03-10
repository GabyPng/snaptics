# Importar y preparar el dataset

dataset alumnos_raw = import from "alumnos.csv"
dataset alumnos_raw = import from "alumnos.csv"

dataset ventas_raw = import from "ventas.csv"

# Estructura esperada del CSV:
# alumno, asistencia, calificacion, grupo, tareas_completas

#------------------------------------------------------------

dataset alumnos_foco = select asistencia_porcentaje, calificacion_tareas:int, promedio_parcial:int
                        from alumnos_raw
                        where promedio_parcial < 80

dataset ventas_altas = select producto:string, unidades_vendidas:int
                        from noExisteDataset
                        where unidades_vendidas > 50

# Hechos
# P es la proporción de alumnos en el dataset donde la condición es TRUE.
fact asistencia_critica = P(asistencia_porcentaje < 60) 

fact tareas_insuficientes = P(alumnos_foco.calificacion_tareas < 70) 

fact promedio_muy_bajo = P(alumnos_foco.promedio_parcial < 60) 

fact p_reprobacion_dada_asistencia_baja =
    P(
        promedio_parcial < 60 given
        datasetnNuevo.asistencia_porcentaje < 60
    )

fact p_reprobacion_dada_tareas_bajas =
    P(
        alumnos_foco.columnaNpExiste < 60 given
        alumnos_foco.calificacion_tareas + "texto" < 70
    )


# Reglas de razonamiento probabilístico

# Regla en caso de que el alumno baje su rendimiento
rule riesgo_reprobacion_alto :-
    error > 0.30
    or alumnos_foco > 0.40

# Repetido
rule riesgo_reprobacion_alto :-
    p_reprobacion_dada_asistencia_media > 0.60
    and p_reprobacion_dada_tareas_bajas > "error"

# Reprobación moderada si solo asistencia baja
rule riesgo_reprobacion_moderado :-
    p_reprobacion_dada_asistencia_baja	 > 0.40
    and p_reprobacion_dada_asistencia_baja <= 0.60

# Riesgo bajo si asistencia es alta
rule riesgo_reprobacion_bajo :-
    p_reprobacion_dada_asistencia_baja or alumnos_foco

promedio = mean(ventas_altas.column)

# Consulta principal

query riesgo_reprobacion_alto
query riesgo_reprobacion_moderado
query error