# Forward Fill

# Debe funcionar para n archivos csv
# Debe buscar en los archivos la columna de Close
# Debe dar una nueva tabla con una columna de fechas y las demas columnas con los nombres de los activos

# Se debe de calcular solo el ultimo rendimiento diario y entregarse en el mismo CSV pero en otra tabla peque.
# Para que tenga sentido matematico, la tabla debe perder el ultimo close, es decir, el dia mas viejo.
# Si se tienen n fechas en el activo con mas dias, todo debe estar unificado con esas n fechas, siendo n-1.

import pandas as pd
import os
import glob

# ==========================================
# BLOQUE 1: EXTRACCIÓN Y LIMPIEZA INDIVIDUAL
# ==========================================
def extraer_y_limpiar_activo(ruta_archivo):
    nombre_activo = os.path.basename(ruta_archivo).replace(".csv", "")
    fila_inicio = 0
    separador = ','
    
    with open(ruta_archivo, 'r', encoding='utf-8-sig', errors='ignore') as f:
        for i, linea in enumerate(f):
            linea_lower = linea.lower()
            if "date" in linea_lower:
                fila_inicio = i
                if ";" in linea_lower:
                    separador = ";"
                break

    try:
        df = pd.read_csv(
            ruta_archivo,
            encoding="utf-8-sig",
            skiprows=fila_inicio,
            sep=separador,
            dtype=str
        )
    except Exception as e:
        print(f"⚠️ Error al leer {nombre_activo}: {e}")
        return None, None

    df.columns = df.columns.str.strip().str.title()
    if "Date" not in df.columns or "Close" not in df.columns:
        print(f"⚠️ {nombre_activo} ignorado: No se encontraron columnas Date/Close.")
        return None, None

    df["Date"] = pd.to_datetime(df["Date"], format='mixed', dayfirst=True, errors='coerce').dt.normalize()
    df.dropna(subset=["Date"], inplace=True)
    df.set_index("Date", inplace=True)

    df = df[~df.index.duplicated(keep='last')]

    df["Close"] = pd.to_numeric(
        df["Close"].str.replace(",", "", regex=False),
        errors='coerce'
    )

    return nombre_activo, df["Close"]


# ==========================================
# BLOQUE 2: ENSAMBLAJE Y CORTES
# ==========================================
def ensamblar_portafolio(diccionario_datos):
    df_bruto = pd.DataFrame(diccionario_datos)
    
    # ORDENAMIENTO ESTRICTO: Viejo -> Nuevo.
    df_ordenado = df_bruto.sort_index(ascending=True)
    
    # PURGA DE FINES DE SEMANA
    df_laboral = df_ordenado[df_ordenado.index.dayofweek < 5]
    
    return df_laboral


# ==========================================
# BLOQUE 3: REPARACIÓN (FORWARD FILL)
# ==========================================
def reparar_huecos_historicos(df_laboral):
    # Rellenamos huecos
    df_rellenado = df_laboral.ffill()
    
    # CORTE DE INTERSECCIÓN: 
    # Aquí el modelo empatará con el activo que tenga la fecha MÁS NUEVA de inicio.
    # Si descargaste mal un CSV, aquí es donde la matriz se encogerá para empatarlo.
    df_final = df_rellenado.dropna()
    
    reporte = {}
    for activo in df_laboral.columns:
        rango_orig = df_laboral.loc[df_final.index, activo]
        rango_nuevo = df_final[activo]
        fechas_parchadas = rango_orig.index[rango_orig.isna() & ~rango_nuevo.isna()]
        reporte[activo] = fechas_parchadas
        
    return df_final, reporte


# ==========================================
# BLOQUE 4: MATEMÁTICA Y ORDENAMIENTO EXCEL
# ==========================================
def procesar_matematicas_y_formato(df_matriz):
    if df_matriz.empty:
        return None, None, None, None

    df_rendimientos = df_matriz.pct_change().dropna()
    
    vector_ultimo_rend = df_rendimientos.iloc[[-1]].T
    vector_ultimo_rend.columns = ["Ultimo_Rendimiento"]
    
    df_precios_final = df_matriz.iloc[1:].copy()
    df_precios_final = df_precios_final.sort_index(ascending=False)
    
    fecha_vieja = df_precios_final.index.min()
    fecha_nueva = df_precios_final.index.max()
    df_precios_final.index = df_precios_final.index.strftime("%d-%m-%Y")
    
    return df_precios_final, vector_ultimo_rend, fecha_vieja, fecha_nueva


# ==========================================
# BLOQUE 5: ORQUESTADOR PRINCIPAL Y DIAGNÓSTICO
# ==========================================
def ejecutar_pipeline(ruta_carpeta):
    archivos = glob.glob(os.path.join(ruta_carpeta, "*.csv"))
    if not archivos:
        print("No se encontraron CSVs.")
        return None, None
        
    all_data = {}
    
    # Fase 1: Extracción
    for archivo in archivos:
        nombre, serie = extraer_y_limpiar_activo(archivo)
        if nombre and serie is not None:
            all_data[nombre] = serie

    # ---------------------------------------------------------
    # NUEVO: DIAGNÓSTICO DE RAYOS X (PRE-ENSAMBLAJE)
    # ---------------------------------------------------------
    print("=" * 75)
    print("      DIAGNÓSTICO INDIVIDUAL DE ARCHIVOS CSV (IDENTIFICACIÓN DE ERRORES)")
    print("=" * 75)
    print(f"{'Activo':<18} | {'Fecha de Inicio':<15} | {'Fecha Final':<15} | {'Días Extraídos'}")
    print("-" * 75)
    for nombre, serie in all_data.items():
        if serie.empty:
            continue
        inicio_str = serie.index.min().strftime('%d-%m-%Y')
        fin_str = serie.index.max().strftime('%d-%m-%Y')
        total = len(serie)
        print(f"{nombre:<18} | {inicio_str:<15} | {fin_str:<15} | {total}")
    print("=" * 75)
    print("\n")
            
    # Fase 2: Ensamblaje
    df_ensamblado = ensamblar_portafolio(all_data)
    
    # Fase 3: Reparación e Intersección
    df_matriz, reporte_relleno = reparar_huecos_historicos(df_ensamblado)

    if df_matriz.empty:
        print("Error: La matriz quedó completamente vacía. Los activos no tienen ninguna fecha en común.")
        return None, None
    
    # Fase 4: Matemáticas
    df_precios, df_rend, fecha_vieja, fecha_nueva = procesar_matematicas_y_formato(df_matriz)
    
    # Fase 5: Reporte Final Consolidado
    total_reales = len(df_precios)
    dias_teoricos = len(pd.bdate_range(start=fecha_vieja, end=fecha_nueva))
    
    print("-" * 75)
    print("           AUDITORÍA DEL PORTAFOLIO CONSOLIDADO")
    print("-" * 75)
    print(f"Fecha Inicio Común (Más vieja) : {fecha_vieja.strftime('%d-%m-%Y')}")
    print(f"Fecha Final Común (Más nueva)  : {fecha_nueva.strftime('%d-%m-%Y')}")
    print(f"Días Teóricos (L-V)            : {dias_teoricos}")
    print(f"Días Consolidados (Matriz)     : {total_reales}")
    print(f"Diferencia (Feriados mundiales): {dias_teoricos - total_reales} días")
    print("-" * 75)
    
    for activo in df_precios.columns:
        print(f"Activo: {activo}")
        if activo in df_rend.index:
            print(f"  ↳ Último Rendimiento : {df_rend.loc[activo, 'Ultimo_Rendimiento']:.2%}")
        
        fechas = reporte_relleno[activo]
        if not fechas.empty:
            str_fechas = ", ".join(fechas[:5].strftime("%d-%m-%Y"))
            extra = "..." if len(fechas) > 5 else ""
            print(f"  ↳ Huecos Parchados   : {len(fechas)} días -> [{str_fechas}{extra}]")
        else:
            print("  ↳ Huecos Parchados   : 0 días")
        print("")
        
    return df_precios, df_rend


# ==========================================
# EJECUCIÓN DEL SCRIPT
# ==========================================
if __name__ == "__main__":
    df_precios, df_rend = ejecutar_pipeline("datos_csv")

    if df_precios is not None:
        nombre_excel = "Portafolio_Consolidado.xlsx"
        with pd.ExcelWriter(nombre_excel, engine="xlsxwriter") as writer:
            df_precios.to_excel(writer, sheet_name="Historico_Precios")
            df_rend.to_excel(writer, sheet_name="Ultimos_Rendimientos")
            
            workbook = writer.book
            worksheet = writer.sheets["Historico_Precios"]
            formato_decimales = workbook.add_format({"num_format": "0.00"})
            for col_num in range(1, len(df_precios.columns) + 1):
                worksheet.set_column(col_num, col_num, 15, formato_decimales)

        print(f"¡Éxito! Archivo guardado como '{nombre_excel}'.")
