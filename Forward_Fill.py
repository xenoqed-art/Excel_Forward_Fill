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


def procesar_archivos_financieros(ruta_archivos):
    all_data = {}

    # ==========================================
    # BLOQUE 1: LECTURA DE DATOS BRUTOS
    # ==========================================
    archivos = glob.glob(os.path.join(ruta_archivos, "*.csv"))

    if not archivos:
        print(f"No se encontraron archivos en: '{ruta_archivos}'")
        return None, None

    for archivo in archivos:
        nombre_activo = os.path.basename(archivo).replace(".csv", "")

        df = pd.read_csv(
            archivo,
            encoding="utf-8-sig",
            parse_dates=["Date"],
            index_col="Date",
            dayfirst=True,
            # Eliminamos los parámetros de miles y decimales de pandas
            # para manejar los formatos mixtos manualmente.
        )

        # ESTANDARIZACIÓN DE DECIMALES:
        # Forzamos la columna a texto, cambiamos comas por puntos, y convertimos a número flotante real.
        # Así "299,500" -> 299.50 y "52.950" -> 52.95
        df["Close"] = df["Close"].astype(str).str.replace(",", ".").astype(float)

        all_data[nombre_activo] = df["Close"]

    # ==========================================
    # BLOQUE 2: CONSOLIDACIÓN, FILTRO Y RASTREO
    # ==========================================
    tabla_bruta = pd.DataFrame(all_data)

    # Filtro de seguridad para eliminar fines de semana (Lunes=0 ... Domingo=6)
    tabla_bruta = tabla_bruta[tabla_bruta.index.dayofweek < 5]

    # Aplicamos el ffill a la tabla filtrada
    tabla_consolidada = tabla_bruta.ffill()

    # RASTREO de fechas rellenadas
    reporte_relleno = {}
    for activo in tabla_bruta.columns:
        nulos_antes = tabla_bruta[activo].isna()
        nulos_despues = tabla_consolidada[activo].isna()
        fechas_rellenadas = tabla_bruta.index[nulos_antes & ~nulos_despues]
        reporte_relleno[activo] = fechas_rellenadas

    # ==========================================
    # BLOQUE 3: CÁLCULO MATEMÁTICO Y ORDENAMIENTO
    # ==========================================
    # 1. El rendimiento se DEBE calcular con el orden cronológico (viejo -> nuevo)
    tabla_rendimientos = tabla_consolidada.pct_change().dropna()

    ultimo_rendimiento = tabla_rendimientos.iloc[[-1]].T
    ultimo_rendimiento.columns = ["Ultimo_Rendimiento"]

    # 2. INVERTIMOS LA TABLA PRINCIPAL para Excel (nuevo -> viejo)
    tabla_consolidada = tabla_consolidada.sort_index(ascending=False)

    # Limpiamos el formato de fecha para que en Excel no aparezca el "00:00:00"
    fecha_mas_vieja_raw = tabla_consolidada.index.min()
    fecha_mas_nueva_raw = tabla_consolidada.index.max()

    # Formateamos el índice a strings limpios (DD-MM-YYYY) para la exportación
    tabla_consolidada.index = tabla_consolidada.index.strftime("%d-%m-%Y")

    # ==========================================
    # BLOQUE 4: REPORTE DETALLADO EN CONSOLA
    # ==========================================
    total_datos = len(tabla_consolidada)

    print("-" * 60)
    print("           REPORTE DE PROCESAMIENTO DE ACTIVOS")
    print("-" * 60)
    print(f"Fecha de inicio (más vieja) : {fecha_mas_vieja_raw.strftime('%d-%m-%Y')}")
    print(f"Fecha final (más nueva)     : {fecha_mas_nueva_raw.strftime('%d-%m-%Y')}")
    print(f"Total de datos por activo   : {total_datos} fechas unificadas")
    print("-" * 60)

    for activo in tabla_consolidada.columns:
        print(f"Activo: {activo}")

        if activo in ultimo_rendimiento.index:
            retorno = ultimo_rendimiento.loc[activo, "Ultimo_Rendimiento"]
            print(f"  ↳ Rendimiento Diario : {retorno:.2%}")

        fechas = reporte_relleno[activo]
        if not fechas.empty:
            str_fechas = ", ".join(fechas.strftime("%d-%m-%Y"))
            print(f"  ↳ Huecos rellenados  : {len(fechas)} días -> [{str_fechas}]")
        else:
            print("  ↳ Huecos rellenados  : 0 días (Serie completa)")

        print("")

    print("-" * 60)

    return tabla_consolidada, ultimo_rendimiento


# ==========================================
# BLOQUE 5: EJECUCIÓN Y EXPORTACIÓN A EXCEL
# ==========================================
if __name__ == "__main__":
    ruta_carpeta = "datos_csv"
    tabla_precios, tabla_rend = procesar_archivos_financieros(ruta_carpeta)

    if tabla_precios is not None:
        nombre_excel = "Portafolio_Consolidado.xlsx"

        with pd.ExcelWriter(nombre_excel, engine="xlsxwriter") as writer:
            tabla_precios.to_excel(writer, sheet_name="Historico_Precios")
            tabla_rend.to_excel(writer, sheet_name="Ultimos_Rendimientos")

            # Formato visual en LibreOffice/Excel
            workbook = writer.book
            worksheet = writer.sheets["Historico_Precios"]

            # Esto forzará visualmente los decimales en todas tus columnas numéricas
            formato_decimales = workbook.add_format({"num_format": "0.00"})

            for col_num in range(1, len(tabla_precios.columns) + 1):
                worksheet.set_column(col_num, col_num, 15, formato_decimales)

        print(f"¡Éxito! Archivo '{nombre_excel}' generado listo para la plantilla.")
