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

def build_matching_patients_subquery(filtros_si: str = None, filtros_no: str = None, use_csv_fallback: bool = False, modo_filtro: str = "AND") -> tuple[str, list]:
    """Construye una subconsulta optimizada usando INTERSECT/UNION y EXCEPT.
    
    Busca los términos exclusivamente en la columna 'valor' (que contiene los datos encriptados).
    
    Args:
        modo_filtro: 'AND' usa INTERSECT (paciente debe tener TODOS los términos).
                     'OR' usa UNION (paciente debe tener AL MENOS UNO de los términos).
    """
    subqueries = []
    params = []
    
    # Normalizar modo_filtro
    modo = modo_filtro.upper().strip() if modo_filtro else "AND"
    if modo not in ("AND", "OR"):
        modo = "AND"
    
    # Operador SQL: INTERSECT para AND, UNION para OR
    set_operator = "INTERSECT" if modo == "AND" else "UNION"
    
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
        pos_sql = f"\n            {set_operator}\n            ".join(subqueries)
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
    agrupar_por: list[str] = None,
    filtros_si: str = None,
    filtros_no: str = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    solo_activos: bool = False,
    tipo_registro: str = None,
    tipo_conteo: str = "pacientes",
    filtro_sexo: str = None,
    filtro_zona: str = None,
    filtro_servicio: str = None,
    filtro_especialidad: str = None,
    edad_min: int = None,
    edad_max: int = None,
    modo_filtro: str = "AND",
    metricas: str = "conteo"
) -> str | dict:
    conn = get_db_connection()
    use_csv_fallback = (conn == "FALLBACK_CSV")
    if not conn:
        return "ERROR: No se pudo conectar a la base de datos."

    # Parsear agrupar_por de forma segura al inicio para evitar TypeErrors y configurar defaults
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

    raw_keys_lower = [k.lower().strip() for k in raw_keys if isinstance(k, str)]
    if ("diagnostico" in raw_keys_lower or "valor_clinico" in raw_keys_lower) and not tipo_registro:
        tipo_registro = "Diagnóstico"


    age_sql_tsql = """CASE 
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END < 15 THEN 'Pediátrico (0-14)'
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 15 AND 24 THEN 'Jóvenes (15-24)'
                WHEN DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() THEN 1 ELSE 0 END BETWEEN 25 AND 64 THEN 'Adultos (25-64)'
                ELSE 'Adultos Mayores / Geriatría (65+)'
            END"""
            
    age_sql_duckdb = """CASE 
                WHEN date_diff('year', CAST(pac_Nacimiento AS DATE), CURRENT_DATE) < 15 THEN 'Pediátrico (0-14)'
                WHEN date_diff('year', CAST(pac_Nacimiento AS DATE), CURRENT_DATE) BETWEEN 15 AND 24 THEN 'Jóvenes (15-24)'
                WHEN date_diff('year', CAST(pac_Nacimiento AS DATE), CURRENT_DATE) BETWEEN 25 AND 64 THEN 'Adultos (25-64)'
                ELSE 'Adultos Mayores / Geriatría (65+)'
            END"""

    age_sql = age_sql_duckdb if use_csv_fallback else age_sql_tsql

    diag_sql_tsql = "COALESCE(NULLIF(CAST(dbo.fnCrypt(valor) AS VARCHAR(MAX)), ''), 'Sin Dato')"
    diag_sql_duckdb = "COALESCE(NULLIF(valor, ''), 'Sin Dato')"
    diag_sql = diag_sql_duckdb if use_csv_fallback else diag_sql_tsql

    alias_clinico = tipo_registro.replace(" ", "_") if tipo_registro else "Dato_Clinico"

    # 1. Definición estricta de dimensiones permitidas y sus expresiones SQL
    DIMENSIONS = {
        "edad": {
            "select": f"{age_sql} AS Rango_Etario",
            "group": age_sql,
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
            "select": f"{diag_sql} AS Diagnostico",
            "group": diag_sql,
            "alias": "Diagnostico"
        },
        "valor_clinico": {
            "select": f"{diag_sql} AS {alias_clinico}",
            "group": diag_sql,
            "alias": alias_clinico
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

    # 2. agrupar_por ya fue parseado al inicio como raw_keys
    
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
        cohort_sql, cohort_params = build_matching_patients_subquery(filtros_si, filtros_no, use_csv_fallback=use_csv_fallback, modo_filtro=modo_filtro)
        where_clauses.append(f"hc_paciente IN (\n        {cohort_sql}\n    )")
        params.extend(cohort_params)
        
    # Filtro temporal (hc_fecha)
    # Usamos CONVERT con estilo 120 (ISO 8601: yyyy-mm-dd hh:mi:ss) para evitar
    # errores de conversión nvarchar→datetime por configuración regional del servidor
    if fecha_inicio:
        if use_csv_fallback:
            where_clauses.append("hc_fecha >= ?")
        else:
            where_clauses.append("hc_fecha >= CONVERT(DATETIME, ?, 120)")
        params.append(fecha_inicio)
    if fecha_fin:
        if use_csv_fallback:
            where_clauses.append("hc_fecha <= ?")
        else:
            where_clauses.append("hc_fecha <= CONVERT(DATETIME, ?, 120)")
        params.append(fecha_fin)
        
    # Filtro de diagnóstico activo (fechaInicio y fechaCese)
    if solo_activos:
        where_clauses.append("(fechaInicio IS NOT NULL AND (fechaCese IS NULL OR fechaCese >= GETDATE()))")
        
    # Filtro de tipo de registro en estructura (búsqueda inteligente e insensible a mayúsculas/acentos)
    if tipo_registro:
        term = tipo_registro
        if tipo_registro.lower().strip() in ["diagnóstico", "diagnostico", "diagnósticos", "diagnosticos"]:
            term = "Diagnóstic"
        
        if use_csv_fallback:
            where_clauses.append("estructura ILIKE ?")
        else:
            where_clauses.append("estructura LIKE ?")
        params.append(f"%{term}%")

    # Filtro por Sexo (insensible a espacios al final comunes en tipos CHAR)
    if filtro_sexo:
        where_clauses.append("TRIM(pac_Sexo) = ?")
        params.append(filtro_sexo.strip().upper())

    # Filtro por Zona/Procedencia
    if filtro_zona:
        where_clauses.append("proc_Descripcion = ?")
        params.append(filtro_zona.strip())

    # Filtro por Servicio
    if filtro_servicio:
        if use_csv_fallback:
            where_clauses.append("Servicio_Descripcion ILIKE ?")
        else:
            where_clauses.append("Servicio_Descripcion LIKE ?")
        params.append(f"%{filtro_servicio.strip()}%")

    # Filtro por Especialidad
    if filtro_especialidad:
        if use_csv_fallback:
            where_clauses.append("Especialidad_Descripcion ILIKE ?")
        else:
            where_clauses.append("Especialidad_Descripcion LIKE ?")
        params.append(f"%{filtro_especialidad.strip()}%")

    # Filtros de Edad (calculados dinámicamente)
    if edad_min:
        if use_csv_fallback:
            where_clauses.append("date_diff('year', CAST(pac_Nacimiento AS DATE), CURRENT_DATE) >= ?")
        else:
            where_clauses.append("DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) >= ?")
        params.append(int(edad_min))

    if edad_max:
        if use_csv_fallback:
            where_clauses.append("date_diff('year', CAST(pac_Nacimiento AS DATE), CURRENT_DATE) <= ?")
        else:
            where_clauses.append("DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) <= ?")
        params.append(int(edad_max))
        
    where_sql = "\n      AND ".join(where_clauses)
    
    # ═══════════════════════════════════════════════════════════════════════
    # FUNCIONES AUXILIARES REUTILIZABLES
    # ═══════════════════════════════════════════════════════════════════════
    def calcular_estadisticas(series, prefijo=""):
        """Calcula 10 métricas estadísticas descriptivas sobre una serie numérica."""
        n = len(series)
        p = f"{prefijo}_" if prefijo else ""
        return pd.Series({
            'Total_Pacientes': int(n),
            f'{p}Promedio': round(series.mean(), 1),
            f'{p}Mediana': round(float(series.median()), 1),
            f'{p}Desv_Estandar': round(series.std(), 1) if n > 1 else 0.0,
            f'{p}Minimo': int(series.min()) if series.min() == int(series.min()) else round(float(series.min()), 1),
            f'{p}Maximo': int(series.max()) if series.max() == int(series.max()) else round(float(series.max()), 1),
            f'{p}P25': round(float(series.quantile(0.25)), 1),
            f'{p}P75': round(float(series.quantile(0.75)), 1),
            f'{p}Rango_IQR': round(float(series.quantile(0.75) - series.quantile(0.25)), 1),
            f'{p}Rango': int(series.max() - series.min())
        })
    
    def formatear_tabla_md(df_stats):
        """Convierte un DataFrame de estadísticas a tabla markdown."""
        headers = df_stats.columns.tolist()
        md = "| " + " | ".join(str(h) for h in headers) + " |\n"
        md += "|" + "|".join(["---"] * len(headers)) + "|\n"
        for _, row in df_stats.iterrows():
            md += "| " + " | ".join(str(x) for x in row.values) + " |\n"
        return md
    
    def ejecutar_query_raw(query_sql, params_list):
        """Ejecuta una query y devuelve el DataFrame crudo + la query formateada."""
        q = query_sql
        if use_csv_fallback:
            import duckdb
            q = q.replace("v_historiaClinica", "read_csv_auto('data/sample_v_historiaClinica.csv', sep=';', header=True)")
            q = q.replace("GETDATE()", "CURRENT_DATE")
            df_result = duckdb.execute(q, params_list).df()
        else:
            df_result = pd.read_sql_query(q, conn, params=params_list)
        
        display_q = q
        if params_list:
            for p in params_list:
                display_q = display_q.replace('?', f"'{p}'", 1)
        return df_result, display_q
    
    def ordenar_rango_etario(df_stats):
        """Ordena filas por rango etario si esa dimensión está presente."""
        if 'Rango_Etario' in df_stats.columns:
            age_order = ['Pediátrico (0-14)', 'Jóvenes (15-24)', 'Adultos (25-64)', 'Adultos Mayores / Geriatría (65+)']
            df_stats['_sort'] = df_stats['Rango_Etario'].apply(lambda x: age_order.index(x) if x in age_order else 999)
            df_stats = df_stats.sort_values('_sort').drop(columns=['_sort'])
        return df_stats
    
    def procesar_metricas(query_sql, col_valor, group_aliases, prefijo=""):
        """Pipeline genérico: ejecutar query → agrupar → calcular stats → formatear."""
        try:
            df_raw, display_q = ejecutar_query_raw(query_sql, params)
            
            if df_raw.empty:
                return {"sql_ejecutado": display_q.strip(), "datos": "No se encontraron pacientes para estos criterios."}
            
            if group_aliases:
                stats_df = df_raw.groupby(group_aliases)[col_valor].apply(
                    lambda s: calcular_estadisticas(s, prefijo)
                ).unstack().reset_index()
                stats_df = stats_df.sort_values('Total_Pacientes', ascending=False)
            else:
                stats = calcular_estadisticas(df_raw[col_valor], prefijo)
                stats_df = pd.DataFrame([stats])
            
            # Convertir columnas enteras
            int_cols = ['Total_Pacientes'] + [c for c in stats_df.columns if 'Rango' in c and 'IQR' not in c or 'Minimo' in c or 'Maximo' in c]
            for col in int_cols:
                if col in stats_df.columns:
                    try:
                        stats_df[col] = stats_df[col].astype(int)
                    except (ValueError, TypeError):
                        pass
            
            stats_df = ordenar_rango_etario(stats_df)
            return {"sql_ejecutado": display_q.strip(), "datos": formatear_tabla_md(stats_df)}
        except Exception as e:
            return f"ERROR al ejecutar la consulta SQL: {str(e)}"
        finally:
            if not use_csv_fallback and conn:
                conn.close()
    
    # ═══════════════════════════════════════════════════════════════════════
    # MODOS ESTADÍSTICOS (metricas != "conteo")
    # ═══════════════════════════════════════════════════════════════════════
    metricas_mode = metricas.lower().strip() if metricas else "conteo"
    
    if metricas_mode == "estadisticas_edad":
        # Cálculo de edad numérica exacta
        raw_age_tsql = """(DATEDIFF(YEAR, pac_Nacimiento, GETDATE()) - 
            CASE WHEN DATEADD(YEAR, DATEDIFF(YEAR, pac_Nacimiento, GETDATE()), pac_Nacimiento) > GETDATE() 
            THEN 1 ELSE 0 END)"""
        raw_age_duckdb = "date_diff('year', CAST(pac_Nacimiento AS DATE), CURRENT_DATE)"
        raw_age = raw_age_duckdb if use_csv_fallback else raw_age_tsql
        
        cte_cols = ["hc_paciente", f"{raw_age} AS edad"]
        group_aliases = []
        for k in valid_keys:
            cte_cols.append(DIMENSIONS[k]["select"])
            group_aliases.append(DIMENSIONS[k]["alias"])
        
        query = f"""
        WITH pacientes_unicos AS (
            SELECT DISTINCT {', '.join(cte_cols)}
            FROM v_historiaClinica
            WHERE {where_sql}
        )
        SELECT * FROM pacientes_unicos
        WHERE edad IS NOT NULL AND edad >= 0 AND edad <= 130
        """
        return procesar_metricas(query, 'edad', group_aliases, prefijo="Edad")
    
    elif metricas_mode == "estadisticas_visitas":
        # Contar visitas (hc_id distintos) por paciente
        cte_cols = ["hc_paciente", "COUNT(DISTINCT hc_id) AS visitas"]
        group_aliases = []
        group_by_inner = ["hc_paciente"]
        
        for k in valid_keys:
            dim = DIMENSIONS[k]
            cte_cols.append(dim["select"])
            group_aliases.append(dim["alias"])
            group_by_inner.append(dim["group"])
        
        query = f"""
        SELECT {', '.join(cte_cols)}
        FROM v_historiaClinica
        WHERE {where_sql}
        GROUP BY {', '.join(group_by_inner)}
        """
        return procesar_metricas(query, 'visitas', group_aliases, prefijo="Visitas")
    
    elif metricas_mode == "estadisticas_antiguedad":
        # Antigüedad del diagnóstico en días desde fechaInicio
        if use_csv_fallback:
            days_calc = "date_diff('day', CAST(fechaInicio AS DATE), CURRENT_DATE)"
        else:
            days_calc = "DATEDIFF(DAY, fechaInicio, GETDATE())"
        
        cte_cols = ["hc_paciente", f"{days_calc} AS dias_diagnostico"]
        group_aliases = []
        for k in valid_keys:
            cte_cols.append(DIMENSIONS[k]["select"])
            group_aliases.append(DIMENSIONS[k]["alias"])
        
        extra_where = f"{where_sql}\n      AND fechaInicio IS NOT NULL"
        
        query = f"""
        WITH diagnosticos AS (
            SELECT DISTINCT {', '.join(cte_cols)}
            FROM v_historiaClinica
            WHERE {extra_where}
        )
        SELECT * FROM diagnosticos
        WHERE dias_diagnostico IS NOT NULL AND dias_diagnostico >= 0
        """
        return procesar_metricas(query, 'dias_diagnostico', group_aliases, prefijo="Dias")
    
    # ═══════════════════════════════════════════════════════════════════════
    # MODO CONTEO (comportamiento original, metricas="conteo")
    # ═══════════════════════════════════════════════════════════════════════
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

    try:
        if use_csv_fallback:
            import duckdb
            # Adaptaciones para DuckDB (SQLite / Postgres engine)
            query = query.replace("v_historiaClinica", "read_csv_auto('data/sample_v_historiaClinica.csv', sep=';', header=True)")
            query = query.replace("GETDATE()", "CURRENT_DATE")
            df = duckdb.execute(query, params).df()
        else:
            df = pd.read_sql_query(query, conn, params=params)
        
        if use_csv_fallback and not df.empty:
            # Decriptar columnas clínicas si estamos en fallback local
            cols_to_decrypt = ["Diagnostico", alias_clinico]
            for col in cols_to_decrypt:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: fn_crypt(str(x)) if pd.notna(x) and x != 'Sin Dato' else x)

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
                    # Forzar que la dimensión clínica sea siempre las filas (index) para evitar miles de columnas
                    if valid_keys[1] in ["diagnostico", "valor_clinico"]:
                        valid_keys[0], valid_keys[1] = valid_keys[1], valid_keys[0]

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
        if not use_csv_fallback and conn:
            conn.close()