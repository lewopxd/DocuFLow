import pathlib
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.worksheet import Worksheet
import sys

# --- CONFIGURACIÓN ---
# ¡OJO! Revisa bien esta ruta. La copié tal cual la escribiste.
BASE_PATH = pathlib.Path(r"C:\Users\Admin\Desktop\JOSE\CARPETAS JOVENES\CARPETAS JOVENES\JOVENES")

# Los tipos de carpetas principales que se convertirán en hojas de Excel
TIPOS_PRINCIPALES = ["PRESENCIAL", "VIRTUAL", "GUIAS"]

# Nombres exactos de las carpetas a verificar
FASE_2_NOMBRE = "FASE 2 - CURSOS CORTOS"
FASE_3_NOMBRE = "FASE 3 - INTERMEDIACION"
SOPORTES_NOMBRE = "SOPORTES"

# Nombre del archivo de salida
OUTPUT_FILE = "reporte_faltantes_v2.xlsx"
# --- FIN DE LA CONFIGURACIÓN ---

def dar_formato_cabecera(ws: Worksheet):
    """Aplica estilo a la fila de cabecera de una hoja."""
    for cell in ws[1]: # Itera sobre las celdas de la fila 1
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

def analizar_directorios():
    """
    Función principal que recorre los directorios y genera el reporte
    con una hoja por cada tipo.
    """
    print(f"Iniciando análisis en: {BASE_PATH}\n")

    # Verificación inicial: ¿Existe la carpeta base?
    if not BASE_PATH.is_dir():
        print(f"--- ERROR CRÍTICO ---")
        print(f"La ruta base no existe o no es un directorio:")
        print(f"{BASE_PATH}")
        print("Por favor, revisa la variable 'BASE_PATH' en el script.")
        sys.exit(1) # Termina el script

    # Crear el libro de trabajo (Excel)
    wb = Workbook()
    
    # Eliminamos la hoja "Sheet" que se crea por defecto
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    # Iteramos sobre cada tipo principal (PRESENCIAL, VIRTUAL, GUIAS)
    for tipo in TIPOS_PRINCIPALES:
        tipo_path = BASE_PATH / tipo
        print(f"Analizando '{tipo}'...")

        # Crear una nueva hoja para este tipo
        ws = wb.create_sheet(title=tipo)

        # Definir las cabeceras según tu solicitud
        col_joven = "Nombre Joven"
        col_fase_2 = f"'{FASE_2_NOMBRE}'"
        col_fase_3 = f"'{FASE_3_NOMBRE}'"
        col_soportes = f"'{SOPORTES_NOMBRE}' (Dentro de FASE 3)"
        col_ruta = "Ruta Completa"
        
        headers = [col_joven, col_fase_2, col_fase_3, col_soportes, col_ruta]
        ws.append(headers)
        dar_formato_cabecera(ws)

        # Lista para guardar los hallazgos de ESTA HOJA
        hallazgos_hoja = []

        # Revisamos si la carpeta del tipo (ej. "PRESENCIAL") existe
        if not tipo_path.is_dir():
            print(f"  ADVERTENCIA: No se encontró la carpeta principal '{tipo}' en {BASE_PATH}")
            ws.append([f"ERROR: No se encontró la carpeta '{tipo}'", "", "", "", str(tipo_path)])
            continue # Saltamos a la siguiente hoja (ej. "VIRTUAL")

        # Si existe, iteramos sobre las carpetas de adentro (las de los jóvenes)
        for joven_path in tipo_path.iterdir():
            
            # Nos aseguramos de que sea un directorio
            if not joven_path.is_dir():
                continue 

            joven_nombre = joven_path.name
            
            # --- Verificaciones ---
            fase_2_path = joven_path / FASE_2_NOMBRE
            fase_3_path = joven_path / FASE_3_NOMBRE
            soportes_path = fase_3_path / SOPORTES_NOMBRE

            # Comprobamos el estado de cada carpeta
            estado_fase_2 = "OK" if fase_2_path.is_dir() else "NO EXISTE"
            estado_fase_3 = "OK" if fase_3_path.is_dir() else "NO EXISTE"
            
            # 'Soportes' solo se revisa si 'Fase 3' existe
            estado_soportes = "OK"
            if estado_fase_3 == "NO EXISTE":
                estado_soportes = "N/A (Falta FASE 3)"
            elif not soportes_path.is_dir():
                estado_soportes = "NO EXISTE"

            # --- Agregar al reporte solo si hay algún error ---
            if any(status != "OK" for status in [estado_fase_2, estado_fase_3, estado_soportes]):
                hallazgos_hoja.append([
                    joven_nombre,
                    estado_fase_2,
                    estado_fase_3,
                    estado_soportes,
                    str(joven_path)
                ])

        # Escribir todos los problemas encontrados para esta hoja
        if not hallazgos_hoja:
            print(f"  -> ¡Perfecto! No se encontraron errores en '{tipo}'.")
            ws.append(["¡Felicidades!", "Estructura correcta en todas las carpetas.", "", "", ""])
        else:
            print(f"  -> Se encontraron problemas en {len(hallazgos_hoja)} carpetas de '{tipo}'.")
            for hallazgo in hallazgos_hoja:
                ws.append(hallazgo)
        
        # Ajustar el ancho de las columnas
        ws.column_dimensions['A'].width = 35  # Joven
        ws.column_dimensions['B'].width = 30  # Fase 2
        ws.column_dimensions['C'].width = 30  # Fase 3
        ws.column_dimensions['D'].width = 30  # Soportes
        ws.column_dimensions['E'].width = 70  # Ruta

    # Guardar el archivo
    try:
        wb.save(OUTPUT_FILE)
        print(f"\n¡Listo! Reporte guardado como: '{OUTPUT_FILE}'")
        print(f"Lo encontrarás en la misma carpeta donde ejecutaste este script.")
    except PermissionError:
        print(f"\n--- ERROR AL GUARDAR ---")
        print(f"No se pudo guardar el archivo '{OUTPUT_FILE}'.")
        print(f"Asegúrate de que no tienes el archivo abierto en Excel.")
        print(f"Intenta cerrarlo y vuelve a ejecutar el script.")
    except IndexError:
        print("\n--- ERROR ---")
        print("Parece que no se encontró ninguna de las carpetas principales (PRESENCIAL, VIRTUAL, GUIAS).")
        print(f"El Excel '{OUTPUT_FILE}' se ha creado, pero está vacío.")
        print("Verifica la ruta 'BASE_PATH' y los nombres en 'TIPOS_PRINCIPALES'.")


# --- Ejecutar la función principal ---
if __name__ == "__main__":
    analizar_directorios()