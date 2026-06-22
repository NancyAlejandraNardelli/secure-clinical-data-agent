# Ejemplo: Cruce Demográfico Simultáneo (Zona y Edad)

**Input del Usuario (Prompt):**
"Distribución por zona de procedencia y grupo etario de los pacientes diagnosticados con Diabetes"

**Ejecución Interna del Agente (Tool Call):**
```json
{
  "name": "get_demographic_stats",
  "arguments": {
    "group_by": "zone_and_age",
    "diagnostico_filter": "Diabetes"
  }
}
```

**Respuesta Esperada del Agente (Formato):**
A continuación se presenta la distribución cruzada de pacientes diagnosticados con Diabetes, agrupados por zona de procedencia y grupo etario:

| Zona de Procedencia | Pediátrico (0-14) | Jóvenes (15-24) | Adultos (25-64) | Geriatría (65+) | Total |
|---------------------|-------------------|-----------------|-----------------|-----------------|-------|
| Centro              | 0                 | 5               | 120             | 45              | 170   |
| Norte               | 1                 | 2               | 85              | 30              | 118   |
| Sur                 | 0                 | 0               | 50              | 20              | 70    |

*Nota: La mayor prevalencia de casos se concentra en la población Adulta de la zona Centro. Los datos han sido filtrados mediante búsqueda rápida encriptada.*
