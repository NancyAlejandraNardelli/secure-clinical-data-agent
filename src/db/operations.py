# import re
# import json
# import pandas as pd
# from src.db.connection import get_db_connection

# def fn_crypt(cadena: str) -> str:
#     """Implementación en Python de la función SQL Server dbo.fnCrypt"""
#     if cadena is None:
#         return None
#     crypt = ""
#     for char in cadena:
#         int_ascii = ord(char)
#         if int_ascii < 128:
#             crypt += chr(int_ascii + 128)
#         elif int_ascii > 128:
#             crypt += chr(int_ascii - 128)
#         else:
#             crypt += char
#     return crypt

# def build_matching_patients_subquery(filtros_si: str = None, filtros_no: str = None) -> tuple[str, list]:
#     """Construye una subconsulta optimizada usando UNION, INTERSECT y EXCEPT.
    
#     Esto evita múltiples EXISTS correlacionados sobre la vista v_historiaClinica,
#     permitiendo a SQL Server ejecutar búsquedas en paralelo y resolver la cohorte en segundos.
#     """
#     subqueries = []
#     params = []
    
#     if filtros_si:
#         terms_si = list(dict.fromkeys([t.strip() for t in filtros_si.split(",") if t.strip()]))
#         for term in terms_si:
#             encrypted = fn_crypt(term)
#             subqueries.append(f"""(
#                 SELECT hc_paciente FROM v_historiaClinica WHERE valor LIKE ?
#                 UNION
#                 SELECT hc_paciente FROM v_historiaClinica WHERE estructura LIKE ? OR grupo LIKE ?
#             )""")
#             params.extend([f"%{encrypted}%", f"%{term}%", f"%{term}%"])
            
#     if subqueries:
#         pos_sql = "\n            INTERSECT\n            ".join(subqueries)
#     else:
#         pos_sql = "SELECT DISTINCT hc_paciente FROM v_historiaClinica"
        
#     neg_subqueries = []
#     if filtros_no:
#         terms_no = list(dict.fromkeys([t.strip() for t in filtros_no.split(",") if t.strip()]))
#         for term in terms_no:
#             encrypted = fn_crypt(term)
#             neg_subqueries.append(f"""(
#                 SELECT hc_paciente FROM v_historiaClinica WHERE valor LIKE ?
#                 UNION
#                 SELECT hc_paciente FROM v_historiaClinica WHERE estructura LIKE ? OR grupo LIKE ?
#             )""")
#             params.extend([f"%{encrypted}%", f"%{term}%", f"%{term}%"])
            
#     if neg_subqueries:
#         neg_sql = "\n            UNION\n            ".join(neg_subqueries)
#         final_sql = f"""(
#             {pos_sql}
#             EXCEPT
#             {neg_sql}
#         )"""
#     else:
#         final_sql = pos_sql
        
#     return final_sql, params

# def consultar_estadisticas_hc(
#     agrupar_por: list[str] | str,
#     filtros_si: str = None,
#     filtros_no: str = None,
#     fecha_inicio: str = None,
#     fecha_fin: str = None,
#     solo_activos: bool = False,
#     tipo_registro: str = None
# ) -> dict | str:
#     """Consulta estadísticas de pacientes en la vista v_historiaClinica de forma flexible y segura."""
#     # 1. Definición estricta de dimensiones permitidas y sus expresiones SQL
#     DIMENSIONS = {
#         "edad": {
#             "select": """CASE 
#                 WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END < 15 THEN 'Pediátrico (0-14)'
#                 WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 15 AND 24 THEN 'Jóvenes (15-24)'
#                 WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 25 AND 64 THEN 'Adultos (25-64)'
#                 ELSE 'Adultos Mayores / Geriatría (65+)'
#             END AS Rango_Etario""",
#             "group": """CASE 
#                 WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END < 15 THEN 'Pediátrico (0-14)'
#                 WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 15 AND 24 THEN 'Jóvenes (15-24)'
#                 WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 25 AND 64 THEN 'Adultos (25-64)'
#                 ELSE 'Adultos Mayores / Geriatría (65+)'
#             END""",
#             "alias": "Rango_Etario"
#         },
#         "sexo": {
#             "select": "COALESCE(NULLIF(UPPER(pac_Sexo), ''), 'Sin Dato') AS Sexo",
#             "group": "COALESCE(NULLIF(UPPER(pac_Sexo), ''), 'Sin Dato')",
#             "alias": "Sexo"
#         },
#         "zona": {
#             "select": "COALESCE(NULLIF(proc_Descripcion, ''), 'Sin Dato') AS Zona",
#             "group": "COALESCE(NULLIF(proc_Descripcion, ''), 'Sin Dato')",
#             "alias": "Zona"
#         },
#         "servicio": {
#             "select": "COALESCE(NULLIF(Servicio_Descripcion, ''), 'Sin Dato') AS Servicio",
#             "group": "COALESCE(NULLIF(Servicio_Descripcion, ''), 'Sin Dato')",
#             "alias": "Servicio"
#         },
#         "especialidad": {
#             "select": "COALESCE(NULLIF(Especialidad_Descripcion, ''), 'Sin Dato') AS Especialidad",
#             "group": "COALESCE(NULLIF(Especialidad_Descripcion, ''), 'Sin Dato')",
#             "alias": "Especialidad"
#         },
#         "diagnostico": {
#             "select": "COALESCE(NULLIF(estructura, ''), 'Sin Dato') AS Diagnostico",
#             "group": "COALESCE(NULLIF(estructura, ''), 'Sin Dato')",
#             "alias": "Diagnostico"
#         },
#         "obra_social": {
#             "select": "COALESCE(NULLIF(CAST(pac_Os AS VARCHAR(50)), ''), 'Sin Obra Social') AS Obra_Social",
#             "group": "COALESCE(NULLIF(CAST(pac_Os AS VARCHAR(50)), ''), 'Sin Obra Social')",
#             "alias": "Obra_Social"
#         },
#         "año": {
#             "select": "YEAR(hc_fecha) AS Año",
#             "group": "YEAR(hc_fecha)",
#             "alias": "Año"
#         },
#         "mes": {
#             "select": "MONTH(hc_fecha) AS Mes",
#             "group": "MONTH(hc_fecha)",
#             "alias": "Mes"
#         }
#     }

#     # Mapeo de sinónimos comunes a las claves de DIMENSIONS
#     SYNONYMS = {
#         "age": "edad",
#         "rango_etario": "edad",
#         "grupo_etario": "edad",
#         "gender": "sexo",
#         "genero": "sexo",
#         "sex": "sexo",
#         "zone": "zona",
#         "procedencia": "zona",
#         "service": "servicio",
#         "specialty": "especialidad",
#         "diagnosticos": "diagnostico",
#         "estructura": "diagnostico",
#         "obra social": "obra_social",
#         "os": "obra_social",
#         "año": "año",
#         "mes": "mes",
#         "anio": "año",
#         "year": "año",
#         "month": "mes"
#     }

#     # 2. Parsear agrupar_por
#     raw_keys = []
#     if agrupar_por is not None:
#         if isinstance(agrupar_por, list):
#             raw_keys = agrupar_por
#         elif isinstance(agrupar_por, str):
#             clean_str = agrupar_por.strip()
#             # Tratar de parsear como JSON array, ej: ["zona", "edad"]
#             if clean_str.startswith("[") and clean_str.endswith("]"):
#                 try:
#                     raw_keys = json.loads(clean_str)
#                 except Exception:
#                     clean_str = clean_str[1:-1].replace('"', '').replace("'", "")
#                     raw_keys = [k.strip() for k in clean_str.split(",") if k.strip()]
#             else:
#                 raw_keys = [k.strip() for k in clean_str.split(",") if k.strip()]
    
#     # 3. Normalizar y validar dimensiones de agrupación
#     valid_keys = []
#     for k in raw_keys:
#         if not isinstance(k, str):
#             continue
#         norm = k.lower().strip()
#         if norm in SYNONYMS:
#             norm = SYNONYMS[norm]
        
#         if norm == "total":
#             continue
            
#         if norm not in DIMENSIONS:
#             return f"ERROR: Criterio de agrupación '{k}' denegado por seguridad. Solo se permiten las siguientes dimensiones: {list(DIMENSIONS.keys())}"
            
#         if norm not in valid_keys:
#             valid_keys.append(norm)

#     # 4. Construcción segura y optimizada de filtros WHERE y sus parámetros
#     where_clauses = ["1=1"]
#     params = []
    
#     # Filtro clínico de cohorte (filtros_si / filtros_no)
#     if filtros_si or filtros_no:
#         cohort_sql, cohort_params = build_matching_patients_subquery(filtros_si, filtros_no)
#         where_clauses.append(f"hc_paciente IN (\n        {cohort_sql}\n    )")
#         params.extend(cohort_params)
        
#     # Filtro temporal (hc_fecha)
#     if fecha_inicio:
#         where_clauses.append("hc_fecha >= ?")
#         params.append(fecha_inicio)
#     if fecha_fin:
#         where_clauses.append("hc_fecha <= ?")
#         params.append(fecha_fin)
        
#     # Filtro de diagnóstico activo (fechaInicio y fechaCese)
#     if solo_activos:
#         where_clauses.append("(fechaInicio IS NOT NULL AND (fechaCese IS NULL OR fechaCese >= GETDATE()))")
        
#     # Filtro de tipo de registro en estructura
#     if tipo_registro:
#         where_clauses.append("estructura LIKE ?")
#         params.append(f"%{tipo_registro}%")
        
#     where_sql = "\n      AND ".join(where_clauses)
    
#     # 5. Armar la consulta SQL
#     if not valid_keys:
#         query = f"""
#         SELECT 
#             COUNT(DISTINCT hc_paciente) AS Total_Pacientes
#         FROM v_historiaClinica
#         WHERE {where_sql}
#         """
#     else:
#         select_exprs = [DIMENSIONS[k]["select"] for k in valid_keys]
#         group_exprs = [DIMENSIONS[k]["group"] for k in valid_keys]
        
#         query = f"""
#         SELECT 
#             {', '.join(select_exprs)},
#             COUNT(DISTINCT hc_paciente) AS Total_Pacientes
#         FROM v_historiaClinica
#         WHERE {where_sql}
#         GROUP BY {', '.join(group_exprs)}
#         ORDER BY Total_Pacientes DESC
#         """

#     conn = get_db_connection()
#     if not conn:
#         return "ERROR: No se pudo conectar a la base de datos."
        
#     try:
#         df = pd.read_sql_query(query, conn, params=params)
        
#         display_query = query
#         if params:
#             for p in params:
#                 display_query = display_query.replace('?', f"'{p}'", 1)
                
#         if df.empty:
#             result_data = "No se encontraron pacientes para estos criterios."
#         else:
#             # 6. Post-procesamiento
#             # Si hay exactamente 2 dimensiones, pivotar automáticamente
#             if len(valid_keys) == 2:
#                 try:
#                     alias1 = DIMENSIONS[valid_keys[0]]["alias"]
#                     alias2 = DIMENSIONS[valid_keys[1]]["alias"]
                    
#                     pivot_df = df.pivot(index=alias1, columns=alias2, values='Total_Pacientes').fillna(0).astype(int)
                    
#                     age_order = ['Pediátrico (0-14)', 'Jóvenes (15-24)', 'Adultos (25-64)', 'Adultos Mayores / Geriatría (65+)']
                    
#                     if alias2 == 'Rango_Etario':
#                         existing_cols = [c for c in age_order if c in pivot_df.columns]
#                         other_cols = [c for c in pivot_df.columns if c not in age_order]
#                         pivot_df = pivot_df[existing_cols + other_cols]
#                     elif alias1 == 'Rango_Etario':
#                         existing_idx = [r for r in age_order if r in pivot_df.index]
#                         other_idx = [r for r in pivot_df.index if r not in age_order]
#                         pivot_df = pivot_df.reindex(existing_idx + other_idx)
                        
#                     pivot_df['Total'] = pivot_df.sum(axis=1)
#                     grand_total = pivot_df.sum(axis=0)
#                     grand_total.name = 'Total General'
#                     pivot_df = pd.concat([pivot_df, grand_total.to_frame().T])
                    
#                     headers = [alias1] + pivot_df.columns.tolist()
#                     md = "| " + " | ".join(str(h) for h in headers) + " |\n"
#                     md += "|" + "|".join(["---"] * len(headers)) + "|\n"
#                     for idx, row in pivot_df.iterrows():
#                         md += f"| {idx} | " + " | ".join(str(x) for x in row.values) + " |\n"
#                     result_data = md
#                 except Exception as pivot_err:
#                     headers = df.columns.tolist()
#                     md = f"*(Nota: No se pudo pivotar la tabla debido a: {pivot_err})*\n\n"
#                     md += "| " + " | ".join(str(h) for h in headers) + " |\n"
#                     md += "|" + "|".join(["---"] * len(headers)) + "|\n"
#                     for _, row in df.iterrows():
#                         md += "| " + " | ".join(str(x) for x in row.values) + " |\n"
#                     result_data = md
#             else:
#                 headers = df.columns.tolist()
#                 md = "| " + " | ".join(str(h) for h in headers) + " |\n"
#                 md += "|" + "|".join(["---"] * len(headers)) + "|\n"
#                 for _, row in df.iterrows():
#                     md += "| " + " | ".join(str(x) for x in row.values) + " |\n"
#                 result_data = md
                
#         return {
#             "sql_ejecutado": display_query.strip(),
#             "datos": result_data
#         }
#     except Exception as e:
#         return f"ERROR al ejecutar la consulta SQL: {str(e)}"
#     finally:
#         conn.close()
import re
import json
import pandas as pd
from src.db.connection import get_db_connection

def fn_crypt(cadena: str) -> str:
    """Implementación en Python de la función SQL Server dbo.fnCrypt"""
    if cadena is None:
        return None
    crypt = ""
    for char in cadena:
        int_ascii = ord(char)
        if int_ascii < 128:
            crypt += chr(int_ascii + 128)
        elif int_ascii > 128:
            crypt += chr(int_ascii - 128)
        else:
            crypt += char
    return crypt

def build_matching_patients_subquery(filtros_si: str = None, filtros_no: str = None) -> tuple[str, list]:
    """Construye una subconsulta optimizada usando INTERSECT y EXCEPT.
    
    Busca los términos exclusivamente en la columna 'valor' (que contiene los datos encriptados).
    """
    subqueries = []
    params = []
    
    if filtros_si:
        terms_si = list(dict.fromkeys([t.strip() for t in filtros_si.split(",") if t.strip()]))
        for term in terms_si:
            variants = list(dict.fromkeys([
                term,
                term.lower(),
                term.upper(),
                term.capitalize()
            ]))
            term_clauses = []
            for v in variants:
                encrypted = fn_crypt(v)
                term_clauses.append("valor LIKE ?")
                params.append(f"%{encrypted}%")
            
            clause_sql = " OR ".join(term_clauses)
            subqueries.append(f"""(
                SELECT hc_paciente FROM v_historiaClinica WHERE {clause_sql}
            )""")
            
    if subqueries:
        pos_sql = "\n            INTERSECT\n            ".join(subqueries)
    else:
        pos_sql = "SELECT DISTINCT hc_paciente FROM v_historiaClinica"
        
    neg_subqueries = []
    if filtros_no:
        terms_no = list(dict.fromkeys([t.strip() for t in filtros_no.split(",") if t.strip()]))
        for term in terms_no:
            variants = list(dict.fromkeys([
                term,
                term.lower(),
                term.upper(),
                term.capitalize()
            ]))
            term_clauses = []
            for v in variants:
                encrypted = fn_crypt(v)
                term_clauses.append("valor LIKE ?")
                params.append(f"%{encrypted}%")
                
            clause_sql = " OR ".join(term_clauses)
            neg_subqueries.append(f"""(
                SELECT hc_paciente FROM v_historiaClinica WHERE {clause_sql}
            )""")
            
    if neg_subqueries:
        neg_sql = "\n            UNION\n            ".join(neg_subqueries)
        final_sql = f"""(
            {pos_sql}
            EXCEPT
            {neg_sql}
        )"""
    else:
        final_sql = pos_sql
        
    return final_sql, params

def consultar_estadisticas_hc(
    agrupar_por: list[str] | str,
    filtros_si: str = None,
    filtros_no: str = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    solo_activos: bool = False,
    tipo_registro: str = None,
    tipo_conteo: str = "pacientes"
) -> dict | str:
    """Consulta estadísticas de pacientes en la vista v_historiaClinica de forma flexible y segura."""
    # 1. Definición estricta de dimensiones permitidas y sus expresiones SQL
    DIMENSIONS = {
        "edad": {
            "select": """CASE 
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END < 15 THEN 'Pediátrico (0-14)'
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 15 AND 24 THEN 'Jóvenes (15-24)'
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 25 AND 64 THEN 'Adultos (25-64)'
                ELSE 'Adultos Mayores / Geriatría (65+)'
            END AS Rango_Etario""",
            "group": """CASE 
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END < 15 THEN 'Pediátrico (0-14)'
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 15 AND 24 THEN 'Jóvenes (15-24)'
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 25 AND 64 THEN 'Adultos (25-64)'
                ELSE 'Adultos Mayores / Geriatría (65+)'
            END""",
            "alias": "Rango_Etario"
        },
        "sexo": {
            "select": "COALESCE(NULLIF(UPPER(pac_Sexo), ''), 'Sin Dato') AS Sexo",
            "group": "COALESCE(NULLIF(UPPER(pac_Sexo), ''), 'Sin Dato')",
            "alias": "Sexo"
        },
        "zona": {
            "select": "COALESCE(NULLIF(proc_Descripcion, ''), 'Sin Dato') AS Zona",
            "group": "COALESCE(NULLIF(proc_Descripcion, ''), 'Sin Dato')",
            "alias": "Zona"
        },
        "servicio": {
            "select": "COALESCE(NULLIF(Servicio_Descripcion, ''), 'Sin Dato') AS Servicio",
            "group": "COALESCE(NULLIF(Servicio_Descripcion, ''), 'Sin Dato')",
            "alias": "Servicio"
        },
        "especialidad": {
            "select": "COALESCE(NULLIF(Especialidad_Descripcion, ''), 'Sin Dato') AS Especialidad",
            "group": "COALESCE(NULLIF(Especialidad_Descripcion, ''), 'Sin Dato')",
            "alias": "Especialidad"
        },
        "diagnostico": {
            "select": "COALESCE(NULLIF(estructura, ''), 'Sin Dato') AS Diagnostico",
            "group": "COALESCE(NULLIF(estructura, ''), 'Sin Dato')",
            "alias": "Diagnostico"
        },
        "obra_social": {
            "select": "COALESCE(NULLIF(CAST(pac_Os AS VARCHAR(50)), ''), 'Sin Obra Social') AS Obra_Social",
            "group": "COALESCE(NULLIF(CAST(pac_Os AS VARCHAR(50)), ''), 'Sin Obra Social')",
            "alias": "Obra_Social"
        },
        "año": {
            "select": "YEAR(hc_fecha) AS Año",
            "group": "YEAR(hc_fecha)",
            "alias": "Año"
        },
        "mes": {
            "select": "MONTH(hc_fecha) AS Mes",
            "group": "MONTH(hc_fecha)",
            "alias": "Mes"
        }
    }

    # Mapeo de sinónimos comunes a las claves de DIMENSIONS
    SYNONYMS = {
        "age": "edad",
        "rango_etario": "edad",
        "grupo_etario": "edad",
        "gender": "sexo",
        "genero": "sexo",
        "sex": "sexo",
        "zone": "zona",
        "procedencia": "zona",
        "service": "servicio",
        "specialty": "especialidad",
        "diagnosticos": "diagnostico",
        "estructura": "diagnostico",
        "obra social": "obra_social",
        "os": "obra_social",
        "año": "año",
        "mes": "mes",
        "anio": "año",
        "year": "año",
        "month": "mes"
    }

    # 2. Parsear agrupar_por
    raw_keys = []
    if agrupar_por is not None:
        if isinstance(agrupar_por, list):
            raw_keys = agrupar_por
        elif isinstance(agrupar_por, str):
            clean_str = agrupar_por.strip()
            # Tratar de parsear como JSON array, ej: ["zona", "edad"]
            if clean_str.startswith("[") and clean_str.endswith("]"):
                try:
                    raw_keys = json.loads(clean_str)
                except Exception:
                    clean_str = clean_str[1:-1].replace('"', '').replace("'", "")
                    raw_keys = [k.strip() for k in clean_str.split(",") if k.strip()]
            else:
                raw_keys = [k.strip() for k in clean_str.split(",") if k.strip()]
    
    # 3. Normalizar y validar dimensiones de agrupación
    valid_keys = []
    for k in raw_keys:
        if not isinstance(k, str):
            continue
        norm = k.lower().strip()
        if norm in SYNONYMS:
            norm = SYNONYMS[norm]
        
        if norm == "total":
            continue
            
        if norm not in DIMENSIONS:
            return f"ERROR: Criterio de agrupación '{k}' denegado por seguridad. Solo se permiten las siguientes dimensiones: {list(DIMENSIONS.keys())}"
            
        if norm not in valid_keys:
            valid_keys.append(norm)

    # 4. Construcción segura y optimizada de filtros WHERE y sus parámetros
    where_clauses = ["1=1"]
    params = []
    
    # Filtro clínico de cohorte (filtros_si / filtros_no)
    if filtros_si or filtros_no:
        cohort_sql, cohort_params = build_matching_patients_subquery(filtros_si, filtros_no)
        where_clauses.append(f"hc_paciente IN (\n        {cohort_sql}\n    )")
        params.extend(cohort_params)
        
    # Filtro temporal (hc_fecha)
    if fecha_inicio:
        where_clauses.append("hc_fecha >= ?")
        params.append(fecha_inicio)
    if fecha_fin:
        where_clauses.append("hc_fecha <= ?")
        params.append(fecha_fin)
        
    # Filtro de diagnóstico activo (fechaInicio y fechaCese)
    if solo_activos:
        where_clauses.append("(fechaInicio IS NOT NULL AND (fechaCese IS NULL OR fechaCese >= GETDATE()))")
        
    # Filtro de tipo de registro en estructura
    if tipo_registro:
        where_clauses.append("estructura LIKE ?")
        params.append(f"%{tipo_registro}%")
        
    where_sql = "\n      AND ".join(where_clauses)
    
    # 5. Armar la consulta SQL
    metric_sql = "COUNT(DISTINCT hc_paciente) AS Total_Pacientes" if tipo_conteo == "pacientes" else "COUNT(*) AS Total_Registros"
    alias_count = "Total_Pacientes" if tipo_conteo == "pacientes" else "Total_Registros"

    if not valid_keys:
        query = f"""
        SELECT 
            {metric_sql}
        FROM v_historiaClinica
        WHERE {where_sql}
        """
    else:
        select_exprs = [DIMENSIONS[k]["select"] for k in valid_keys]
        group_exprs = [DIMENSIONS[k]["group"] for k in valid_keys]
        
        query = f"""
        SELECT 
            {', '.join(select_exprs)},
            {metric_sql}
        FROM v_historiaClinica
        WHERE {where_sql}
        GROUP BY {', '.join(group_exprs)}
        ORDER BY {alias_count} DESC
        """

    conn = get_db_connection()
    if not conn:
        return "ERROR: No se pudo conectar a la base de datos."
        
    try:
        df = pd.read_sql_query(query, conn, params=params)
        
        display_query = query
        if params:
            for p in params:
                display_query = display_query.replace('?', f"'{p}'", 1)
                
        if df.empty:
            result_data = "No se encontraron pacientes para estos criterios."
        else:
            # 6. Post-procesamiento
            # Si hay exactamente 2 dimensiones, pivotar automáticamente
            if len(valid_keys) == 2:
                try:
                    alias1 = DIMENSIONS[valid_keys[0]]["alias"]
                    alias2 = DIMENSIONS[valid_keys[1]]["alias"]
                    
                    pivot_df = df.pivot(index=alias1, columns=alias2, values=alias_count).fillna(0).astype(int)
                    
                    age_order = ['Pediátrico (0-14)', 'Jóvenes (15-24)', 'Adultos (25-64)', 'Adultos Mayores / Geriatría (65+)']
                    
                    if alias2 == 'Rango_Etario':
                        existing_cols = [c for c in age_order if c in pivot_df.columns]
                        other_cols = [c for c in pivot_df.columns if c not in age_order]
                        pivot_df = pivot_df[existing_cols + other_cols]
                    elif alias1 == 'Rango_Etario':
                        existing_idx = [r for r in age_order if r in pivot_df.index]
                        other_idx = [r for r in pivot_df.index if r not in age_order]
                        pivot_df = pivot_df.reindex(existing_idx + other_idx)
                        
                    pivot_df['Total'] = pivot_df.sum(axis=1)
                    grand_total = pivot_df.sum(axis=0)
                    grand_total.name = 'Total General'
                    pivot_df = pd.concat([pivot_df, grand_total.to_frame().T])
                    
                    headers = [alias1] + pivot_df.columns.tolist()
                    md = "| " + " | ".join(str(h) for h in headers) + " |\n"
                    md += "|" + "|".join(["---"] * len(headers)) + "|\n"
                    for idx, row in pivot_df.iterrows():
                        md += f"| {idx} | " + " | ".join(str(x) for x in row.values) + " |\n"
                    result_data = md
                except Exception as pivot_err:
                    headers = df.columns.tolist()
                    md = f"*(Nota: No se pudo pivotar la tabla debido a: {pivot_err})*\n\n"
                    md += "| " + " | ".join(str(h) for h in headers) + " |\n"
                    md += "|" + "|".join(["---"] * len(headers)) + "|\n"
                    for _, row in df.iterrows():
                        md += "| " + " | ".join(str(x) for x in row.values) + " |\n"
                    result_data = md
            else:
                headers = df.columns.tolist()
                md = "| " + " | ".join(str(h) for h in headers) + " |\n"
                md += "|" + "|".join(["---"] * len(headers)) + "|\n"
                for _, row in df.iterrows():
                    md += "| " + " | ".join(str(x) for x in row.values) + " |\n"
                result_data = md
                
        return {
            "sql_ejecutado": display_query.strip(),
            "datos": result_data
        }
    except Exception as e:
        return f"ERROR al ejecutar la consulta SQL: {str(e)}"
    finally:
        conn.close()