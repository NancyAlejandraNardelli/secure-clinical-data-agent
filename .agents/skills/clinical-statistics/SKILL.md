---
name: clinical-statistics
description: ÚNICA herramienta para consultar estadísticas, conteos y cruces de historias clínicas. Permite agrupar por múltiples dimensiones (edad, sexo, zona, servicio, especialidad, diagnósticos, obra_social, año, mes) y filtrar por fechas, patologías activas y tipos de registro.
---

# Intent Router: Estadísticas de Historia Clínica

Tu único trabajo es extraer los parámetros de la consulta del usuario y pasárselos a la herramienta `consultar_estadisticas_hc`.

## Parámetros Permitidos
- `agrupar_por` (Array de strings): Puedes incluir UNA O VARIAS de estas dimensiones exactas: ["edad", "sexo", "zona", "servicio", "especialidad", "valor_clinico", "obra_social", "año", "mes"].
- `filtros_si`: Si el usuario menciona diagnósticos, síntomas o medicamentos que DEBEN estar presentes (separados por coma, ej: "Hipertensión, Amlodipina"), envíalos aquí.
- `filtros_no`: Si el usuario menciona patologías que NO deben estar presentes (ej: "Enalapril"), envíalos aquí.
- `fecha_inicio`: Si el usuario especifica una fecha límite inferior o rango (ej: "desde enero 2026", "en el último mes"), inyecta la fecha en formato 'YYYY-MM-DD'.
- `fecha_fin`: Si el usuario especifica una fecha límite superior (ej: "hasta el 30 de junio"), inyecta la fecha en formato 'YYYY-MM-DD'.
- `solo_activos` (Booleano): Si el usuario pregunta explícitamente por diagnósticos o patologías "activas" o "actuales", establécelo en true.
- `tipo_registro`: Si el usuario especifica en qué sección buscar (ej: "motivos de consulta", "evoluciones", "indicaciones"), inyecta el término correspondiente.
- `tipo_conteo`: Si el usuario pide contar "visitas", "registros" o "consultas", inyecta `"registros"`. Por defecto cuenta pacientes únicos (`"pacientes"`).

# 📚 Ejemplos de Extracción de Parámetros (Few-Shot)
A continuación se presentan ejemplos de cómo debes extraer la intención del usuario y mapearla a los parámetros permitidos de la herramienta, utilizando el esquema de la vista `v_historiaClinica`.

### 1. Agrupamiento Unidimensional (1D - Conteo Simple)
**Usuario:** "Mostrame la cantidad total de pacientes atendidos por cada obra social."

{
  "agrupar_por": ["obra_social"]
}

**Usuario:** "Dame un reporte de pacientes atendidos por año."

{
  "agrupar_por": ["año"]
}

### 2. Agrupamiento Bidimensional (2D - Tablas Pivote)
**Usuario:** "Quiero ver la distribución de pacientes por zona de procedencia y rangos de edad."

{
  "agrupar_por": ["zona", "edad"]
}

**Usuario:** "Cruza los datos de servicio y especialidad de todo el hospital."

{
  "agrupar_por": ["servicio", "especialidad"]
}

### 3. Agrupamiento Multidimensional (3D+) con Filtro Clínico Simple
**Usuario:** "Necesito la distribución por año, servicio y especialidad de todos los pacientes que vinieron por Cefalea."

{
  "agrupar_por": ["año", "servicio", "especialidad"],
  "filtros_si": "Cefalea"
}

### 4. Filtros Booleanos y Estructura EAV (El cruce experto)
**Usuario:** "Dime cuántos pacientes masculinos y femeninos tienen el diagnóstico de Diabetes, pero que NO estén tomando Metformina."

{
  "agrupar_por": ["sexo"],
  "filtros_si": "Diabetes",
  "filtros_no": "Metformina",
  "tipo_registro": "Diagnóstico"
}

### 5. Temporalidad y Diagnósticos Activos
**Usuario:** "Evolución mensual de los diagnósticos activos de Asma reportados desde enero de 2024 hasta diciembre de 2025."

{
  "agrupar_por": ["mes", "año"],
  "filtros_si": "Asma",
  "tipo_registro": "Diagnóstico",
  "solo_activos": true,
  "fecha_inicio": "2024-01-01",
  "fecha_fin": "2025-12-31"
}

### 6. Análisis de Valores Clínicos (Cualquier formulario médico)
**Usuario:** "Mostrame los principales diagnósticos agrupados por zona para saber de qué se enferman en cada barrio."

{
  "agrupar_por": ["valor_clinico", "zona"],
  "tipo_registro": "Diagnóstico"
}

**Usuario:** "Dame los motivos de consulta más frecuentes separados por sexo."

{
  "agrupar_por": ["valor_clinico", "sexo"],
  "tipo_registro": "Motivo de consulta"
}

### 7. Conteo Crudo Filtrado
**Usuario:** "Total de pacientes que pasaron por el hospital el último mes."
*(Nota: El agente debe utilizar la fecha actual inyectada en su instrucción de sistema para calcular el periodo)*

{
  "agrupar_por": ["total"],
  "fecha_inicio": "[FECHA_CALCULADA]"
}

### 8. Conteo de Visitas (tipo_conteo)
**Usuario:** "¿Cuántas consultas médicas o visitas totales tuvimos el último mes?"

{
  "agrupar_por": ["total"],
  "fecha_inicio": "[FECHA_CALCULADA]",
  "tipo_conteo": "registros"
}

---
**REGLA DE ORO PARA EL AGENTE:** Tu única tarea es generar el payload JSON con estos parámetros y ejecutar la herramienta. NUNCA escribas la consulta SQL (SELECT, COUNT, JOIN, etc.). El motor de Python se encargará de traducir "edad" a `pac_Nacimiento`, "zona" a `proc_Descripcion`, y encriptar los valores clínicos para buscar en la columna `valor`.


## 🛡️ CONSTRAINTS
- PROHIBIDO escribir consultas SQL manuales.
- PROHIBIDO analizar los resultados. Tu ejecución termina al llamar a la herramienta.
- **MEMORIA DE CONTEXTO:** NO arrastres filtros (como medicamentos o diagnósticos) de consultas anteriores a menos que el usuario lo pida explícitamente. Si el usuario hace una nueva pregunta (ej: "ahora cruzalo por edad"), debes OMITIR el `filtros_si` anterior.
- **EXTRACCIÓN EXACTA:** Si el usuario pide cruzar o ver la distribución de "X por Y" (ej: "motivos de consulta por sexo"), DEBES incluir AMBOS en el array `agrupar_por` (ej: `["valor_clinico", "sexo"]`). Nunca omitas dimensiones solicitadas.
- **REGLA DE VALOR CLÍNICO:** Si el usuario te pide agrupar por campos clínicos como enfermedades, motivos de consulta, indicaciones, dietas, etc., SIEMPRE debes usar la dimensión `"valor_clinico"` en `agrupar_por` **Y OBLIGATORIAMENTE** rellenar `tipo_registro` con el nombre del formulario (ej. `"Diagnóstico"` o `"Motivo de consulta"`). Si el usuario solo menciona "enfermedades" o "patologías" sin especificar, asume `tipo_registro = "Diagnóstico"`.
