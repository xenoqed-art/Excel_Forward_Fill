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
    separador = ","

    with open(ruta_archivo, "r", encoding="utf-8-sig", errors="ignore") as f:
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
            dtype=str,
        )
    except Exception as e:
        print(f"⚠️ Error al leer {nombre_activo}: {e}")
        return None, None

    df.columns = df.columns.str.strip().str.title()
    if "Date" not in df.columns or "Close" not in df.columns:
        print(f"⚠️ {nombre_activo} ignorado: No se encontraron columnas Date/Close.")
        return None, None

    df["Date"] = pd.to_datetime(
        df["Date"], format="mixed", dayfirst=True, errors="coerce"
    ).dt.normalize()
    df.dropna(subset=["Date"], inplace=True)
    df.set_index("Date", inplace=True)

    df = df[~df.index.duplicated(keep="last")]

    df["Close"] = pd.to_numeric(
        df["Close"].str.replace(",", "", regex=False), errors="coerce"
    )

    return nombre_activo, df["Close"]


# ==========================================
# BLOQUE 2: ENSAMBLAJE Y CORTES
# ==========================================
def ensamblar_portafolio(diccionario_datos):
    df_bruto = pd.DataFrame(diccionario_datos)
    df_ordenado = df_bruto.sort_index(ascending=True)
    df_laboral = df_ordenado[df_ordenado.index.dayofweek < 5]

    return df_laboral


# ==========================================
# BLOQUE 3: REPARACIÓN E INTERSECCIÓN
# ==========================================
def reparar_huecos_historicos(df_laboral):
    df_rellenado = df_laboral.ffill()
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
        return None, None, None, None, None

    # Extracción de Precio Inicial y Final
    precio_inicial = df_matriz.iloc[0]
    precio_final = df_matriz.iloc[-1]

    df_resumen_precios = pd.DataFrame(
        {
            "Precio_Compra_Inicial": precio_inicial,
            "Precio_Valuacion_Final": precio_final,
        }
    )

    # Cálculo de Rendimientos
    df_rendimientos = df_matriz.pct_change().dropna()

    # 1. EL DATO PARA EL FONDO DE TU EXCEL (-1.28% de Femsa)
    vector_base_historico = df_rendimientos.iloc[[0]].T
    vector_base_historico.columns = ["Rend_Fila_Final_Excel"]

    # 2. El dato del día más reciente
    vector_ultimo_rend = df_rendimientos.iloc[[-1]].T
    vector_ultimo_rend.columns = ["Rend_Mas_Reciente"]

    # Unimos ambas columnas en una sola tabla de Excel
    df_resumen_rend = pd.concat([vector_base_historico, vector_ultimo_rend], axis=1)

    # Emparejamos precios
    df_precios_final = df_matriz.iloc[1:].copy()
    df_precios_final = df_precios_final.sort_index(ascending=False)

    # Formato visual de fechas
    fecha_vieja = df_precios_final.index.min()
    fecha_nueva = df_precios_final.index.max()
    df_precios_final.index = df_precios_final.index.strftime("%d-%m-%Y")

    return (
        df_precios_final,
        df_resumen_rend,
        df_resumen_precios,
        fecha_vieja,
        fecha_nueva,
    )


# ==========================================
# BLOQUE 5: ORQUESTADOR PRINCIPAL Y EXPORTACIÓN
# ==========================================
def ejecutar_pipeline(ruta_carpeta):
    archivos = glob.glob(os.path.join(ruta_carpeta, "*.csv"))
    if not archivos:
        print("No se encontraron CSVs.")
        return None, None, None

    all_data = {}
    for archivo in archivos:
        nombre, serie = extraer_y_limpiar_activo(archivo)
        if nombre and serie is not None:
            all_data[nombre] = serie

    print("=" * 75)
    print("      DIAGNÓSTICO INDIVIDUAL DE ARCHIVOS CSV (IDENTIFICACIÓN DE ERRORES)")
    print("=" * 75)
    print(
        f"{'Activo':<18} | {'Fecha de Inicio':<15} | {'Fecha Final':<15} | {'Días Extraídos'}"
    )
    print("-" * 75)
    for nombre, serie in all_data.items():
        if serie.empty:
            continue
        inicio_str = serie.index.min().strftime("%d-%m-%Y")
        fin_str = serie.index.max().strftime("%d-%m-%Y")
        total = len(serie)
        print(f"{nombre:<18} | {inicio_str:<15} | {fin_str:<15} | {total}")
    print("=" * 75)
    print("\n")

    df_ensamblado = ensamblar_portafolio(all_data)
    df_matriz, reporte_relleno = reparar_huecos_historicos(df_ensamblado)

    if df_matriz.empty:
        print(
            "Error: La matriz quedó completamente vacía. Los activos no tienen fechas en común."
        )
        return None, None, None

    df_precios, df_resumen_rend, df_resumen_precios, fecha_vieja, fecha_nueva = (
        procesar_matematicas_y_formato(df_matriz)
    )

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
        if activo in df_resumen_precios.index:
            p_compra = df_resumen_precios.loc[activo, "Precio_Compra_Inicial"]
            p_valuacion = df_resumen_precios.loc[activo, "Precio_Valuacion_Final"]
            print(f"  ↳ P. Compra: {p_compra:.2f} | P. Valuación: {p_valuacion:.2f}")

        if activo in df_resumen_rend.index:
            r_fondo = df_resumen_rend.loc[activo, "Rend_Fila_Final_Excel"]
            print(f"  ↳ Rendimiento Fondo Excel   : {r_fondo:.2%}")

        fechas = reporte_relleno[activo]
        if not fechas.empty:
            str_fechas = ", ".join(fechas[:5].strftime("%d-%m-%Y"))
            extra = "..." if len(fechas) > 5 else ""
            print(
                f"  ↳ Huecos Parchados          : {len(fechas)} días -> [{str_fechas}{extra}]"
            )
        else:
            print("  ↳ Huecos Parchados          : 0 días")
        print("")

    return df_precios, df_resumen_rend, df_resumen_precios


# ==========================================
# EJECUCIÓN DEL SCRIPT
# ==========================================
if __name__ == "__main__":
    df_precios, df_resumen_rend, df_resumen_precios = ejecutar_pipeline("datos_csv")

    if df_precios is not None:
        print("\n" + "=" * 75)

        try:
            mensaje = "Ingresa el nombre del Excel (presiona Enter para usar 'Portafolio_Consolidado'): "
            nombre_input = input(mensaje).strip()
        except EOFError:
            print("⚠️ Entorno de solo lectura detectado. Se omitió la entrada manual.")
            nombre_input = ""

        if nombre_input:
            if not nombre_input.endswith(".xlsx"):
                nombre_excel = f"{nombre_input}.xlsx"
            else:
                nombre_excel = nombre_input
        else:
            nombre_excel = "Portafolio_Consolidado.xlsx"

        print("=" * 75)

        try:
            with pd.ExcelWriter(nombre_excel, engine="xlsxwriter") as writer:
                df_precios.to_excel(writer, sheet_name="Historico_Precios")
                df_resumen_rend.to_excel(writer, sheet_name="Rendimientos_Base")
                df_resumen_precios.to_excel(
                    writer, sheet_name="Precios_Compra_Valuacion"
                )

                workbook = writer.book
                formato_decimales = workbook.add_format({"num_format": "0.00"})
                formato_porcentaje = workbook.add_format({"num_format": "0.00%"})

                # Hoja 1: Precios
                ws_precios = writer.sheets["Historico_Precios"]
                for col_num in range(1, len(df_precios.columns) + 1):
                    ws_precios.set_column(col_num, col_num, 15, formato_decimales)

                # Hoja 2: Rendimientos (Aplicamos formato de porcentaje real para Excel)
                ws_rendimientos = writer.sheets["Rendimientos_Base"]
                ws_rendimientos.set_column(1, 2, 22, formato_porcentaje)

                # Hoja 3: Compra/Valuación
                ws_resumen = writer.sheets["Precios_Compra_Valuacion"]
                ws_resumen.set_column(1, 2, 22, formato_decimales)

            print(
                f"\n¡Éxito! Tu matriz ha sido generada y guardada como: '{nombre_excel}'."
            )

        except PermissionError:
            print(
                f"\n❌ ERROR DE SISTEMA: El archivo '{nombre_excel}' está abierto o bloqueado."
            )
            print("Por favor, cierra LibreOffice/Excel y vuelve a ejecutar el script.")
