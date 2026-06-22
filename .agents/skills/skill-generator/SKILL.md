---
name: skill-generator
description: Use this skill to save a successful clinical query or analytical workflow as a new reusable Antigravity skill, persisting it to .agents/skills/ for future use.
---

# Skill: Generador y Persistencia de Skills de Consulta (skill-generator)

Este skill permite al agente aprender y persistir nuevas habilidades automáticamente. Cuando se formula una consulta T-SQL compleja que funciona correctamente, o cuando el médico solicita guardar un reporte/consulta recurrente, el agente genera un nuevo skill en el espacio de trabajo.

## Instrucciones para Guardar un Skill

1. **Identificar la Solicitud o el Caso Exitoso:**
   * Cuando el usuario diga: *"Guarda esta consulta"*, *"Crea una plantilla para esta búsqueda"* o *"Guarda esto como un skill llamado [nombre]"*.
   * O cuando tú determines que una consulta compleja (que involucra cruces de diagnósticos, exclusiones o grupos etarios) ha retornado resultados válidos y es muy valiosa para el futuro.

2. **Diseñar el Metadato (Frontmatter YAML):**
   * **name:** Un identificador en minúsculas y separado por guiones (ej. `diabeticos-sin-insulina`).
   * **description:** Una descripción clara en español que contenga las palabras clave de búsqueda (ej. "Recupera pacientes con diagnóstico de diabetes mellitus tipo 2 que no tengan prescripciones de insulina"). Esto servirá como el trigger semántico en futuras sesiones.

3. **Escribir el Archivo SKILL.md:**
   * Crea el directorio `.agents/skills/<name>/` si no existe.
   * Escribe el archivo `.agents/skills/<name>/SKILL.md`.
   * El archivo debe contener:
     * El bloque YAML Frontmatter.
     * Un título descriptivo.
     * La consulta T-SQL exacta que funcionó, comentada con los nombres de las columnas reales (`v_historiaClinica`, `t_Cie10`, etc.).
     * Un ejemplo de uso o plantilla de prompt para volver a llamarlo.

### Ejemplo de Archivo SKILL.md Generado

```markdown
---
name: diabeticos-adultos-procedencia
description: Obtiene la distribución geográfica de pacientes diabéticos de más de 45 años.
---

# Consulta de Diabéticos Adultos por Procedencia

Este skill contiene la consulta optimizada para obtener pacientes diabéticos mayores de 45 años agrupados por su procedencia geográfica.

## Consulta T-SQL Ejecutada

`​``sql
SELECT 
    proc_Descripcion AS Procedencia,
    COUNT(DISTINCT hc_paciente) AS TotalPacientes
FROM 
    v_historiaClinica
WHERE 
    (valor LIKE '%diabetes%' OR estructura LIKE '%diabetes%')
    AND DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) > 45
GROUP BY 
    proc_Descripcion
ORDER BY 
    TotalPacientes DESC;
`​``

## Uso
Pide al agente: "Ejecutar la consulta de diabéticos adultos por procedencia".
```

4. **Confirmar al Usuario:**
   * Informa al usuario que el skill ha sido creado en `.agents/skills/<name>/SKILL.md` y que podrá usarlo directamente en futuras preguntas estadísticas.
