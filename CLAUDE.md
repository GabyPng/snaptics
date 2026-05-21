# ¿Qué es Snaptics?

Snaptics es un lenguaje de programación declarativo orientado al razonamiento lógico-probabilístico. Su propósito es analizar datos, detectar patrones e inferir conclusiones usando probabilidad, lógica y estadística.

A diferencia de otros lenguajes que solo procesan datos numéricos, Snaptics busca interpretar información y generar conocimiento explicable mediante hechos, reglas e inferencias.

---

# Objetivo

Transformar datos procesados en conocimiento estructurado mediante:

* Hechos probabilísticos
* Reglas lógicas
* Inferencias cuantificadas
* Explicaciones interpretables

El sistema trabaja sobre datos previamente limpiados y analizados para descubrir relaciones y grados de certeza.

---

# Flujo General de Trabajo

## 1. Importación de datos

```snaptics
dataset ventas_raw = import from "ventas.csv"
```

## 2. Preprocesamiento

```snaptics
dataset mis_datos =
    select region, monto, margen
    from ventas_raw
    where monto > 0
```

## 3. Declaración de hechos

```snaptics
fact ventas_altas = P(ventas > 500)
fact margen_bajo = P(margen < 10%)
```

## 4. Descubrimiento automático

```snaptics
auto_discover dataset(ventas) where correlation > 0.7
```

Salida:

```snaptics
fact corr_ventas_region = P(ventas or region == "Norte") = 0.85
```

## 5. Reglas

```snaptics
rule baja_rentabilidad :-
    ventas_altas < 0.5 and margen_bajo > 0.3
```

## 6. Consultas

```snaptics
query rentabilidad_general
```

Salida:

```text
La probabilidad de baja rentabilidad es 0.46
(nivel de evidencia: moderado)
```

---

# Filosofía

Snaptics combina:

* Lógica
* Estadística
* Probabilidad
* Explicabilidad

Su objetivo es permitir razonamiento sobre incertidumbre utilizando inferencias comprensibles y reproducibles.

---

# Analizador Léxico

El lexer transforma el código fuente en tokens.

## Tokens principales

### Identificadores

```regex
[A-Za-z_][A-Za-z_0-9]*
```

### Operadores

| Tipo         | Ejemplos        |
| ------------ | --------------- |
| Aritméticos  | + - * / ^       |
| Relacionales | == != < > <= >= |
| Lógicos      | and, or, not    |
| Asignación   | =               |
| Reglas       | :-              |

### Tipos de datos

* INT
* REAL
* STRING
* BOOLEAN

### Delimitadores

* `( )`
* `,`
* `.`

---

# Palabras Reservadas

## Datos y análisis

* dataset
* import
* select
* from
* where
* group
* filter
* auto_discover

## Lógica y conocimiento

* fact
* rule
* query
* evidence
* confidence

## Estadística

* P
* mean
* var
* std
* correlation
* distribution

## Condicionales

* if
* then
* else
* when
* given

## Explicabilidad

* explain
* why

## Booleanos

* true
* false

---

# Lógica Difusa

| Operador | Significado       |
| -------- | ----------------- |
| and      | Ambas condiciones |
| or       | Al menos una      |
| not      | Negación          |

Ejemplo:

```snaptics
rule alta_rentabilidad :-
    ventas_altas > 0.7 and not margen_bajo
```

---

# Sistema de Errores Léxicos

El compilador identifica errores y genera códigos específicos.

## Ejemplos

| Código  | Error                        |
| ------- | ---------------------------- |
| LEX-101 | Símbolos ¿ ¡ inválidos       |
| LEX-102 | Uso inválido de @            |
| LEX-201 | Uso de []                    |
| LEX-202 | Uso de {}                    |
| LEX-304 | Uso de &&                    |
| LEX-601 | Cadena sin cerrar            |
| LEX-701 | Palabra reservada incorrecta |

Snaptics también sugiere correcciones automáticas para errores tipográficos.

---

# Sistema de Errores Sintácticos

| Código  | Descripción           |
| ------- | --------------------- |
| SYN-101 | Dataset incompleto    |
| SYN-102 | Hecho incompleto      |
| SYN-103 | Regla incompleta      |
| SYN-302 | Falta paréntesis      |
| SYN-401 | Falta FROM            |
| SYN-402 | WHERE incompleto      |
| SYN-801 | Probabilidad inválida |

Los mensajes son amigables y orientados a facilitar la depuración.

---

# Analizador Sintáctico

El parser utiliza gramática LALR(1) para validar estructuras del lenguaje y construir el AST.

## Estructura general

```bnf
programa ::= sentencia
           | programa sentencia
```

## Tipos de sentencia

* Importación
* Preprocesamiento
* Declaración de hechos
* Reglas
* Consultas
* Manejo de errores

---

# Gramática Principal

## Importación

```bnf
DATASET ID = IMPORT FROM STRING
```

## Hechos

```bnf
FACT ID = P(expresion)
```

## Reglas

```bnf
RULE ID :- expresion
```

## Consultas

```bnf
QUERY ID
QUERY ID EXPLAIN
QUERY ID WHY
```

## Probabilidad condicional

```bnf
P(A GIVEN B)
```

---

# Expresiones Soportadas

## Relacionales

* ==
* !=
* <
* >
* <=
* > =

## Aritméticas

* *
* *
* *
* /
* ^

## Lógicas

* and
* or
* not

---

# AST (Árbol de Sintaxis Abstracta)

Cada estructura reconocida genera un nodo ASTNode con:

* Tipo
* Línea
* Propiedades

El árbol puede exportarse como JSON para depuración y visualización.

---

# Arquitectura del Compilador

## Flujo de compilación

1. Lexer → genera tokens
2. Parser → valida gramática
3. AST → representa estructura
4. Sistema de errores → clasifica fallos

---

# PLY

El compilador está implementado usando PLY (Python Lex-Yacc).

## Componentes principales

* `lexer.py`
* `parser.py`
* `ASTNode`
* Sistema de errores

---

# Funciones Principales

## tokenize(text)

Devuelve:

* Tokens
* Errores léxicos

## parse(text)

Devuelve:

* AST
* Errores sintácticos
* Estado de compilación

---

# Precedencia de Operadores

De menor a mayor prioridad:

1. OR
2. AND
3. NOT
4. Comparaciones
5. * -
6. * /
7. Unarios
8. Potencia

---

# Instalación

## Con Conda

```bash
conda create -n snaptics python=3.x
```

## Con pip y venv

```bash
python -m venv venv
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

### Atajos

* F9 → Compilar
* Ctrl+O → Abrir
* Ctrl+S → Guardar

---

