#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow Tools
File: fix_folder_structure.py
Description: 
    Script de reestructuración post-generación.
    Mueve el contenido de la carpeta raíz del estudiante a una subcarpeta 'F2 - CURSOS CORTOS'.
    
    ANTES:  /CERTIFICADOS/JUAN PEREZ/acta.docx
    DESPUES: /CERTIFICADOS/JUAN PEREZ/F2 - CURSOS CORTOS/acta.docx
"""

import shutil
import sys
from pathlib import Path

# =============================================================================
# ⚙️ CONFIGURACIÓN
# =============================================================================

# La misma ruta principal donde están las carpetas de los jóvenes (JUAN PEREZ, MARIA...)
BASE_PATH = Path(r"C:\Users\Admin\Desktop\PLAYGROUND MARCELA\F2 CURSOS CORTOS\OUTPUT\CERTIFICADOS")

# Nombre de la nueva subcarpeta donde se meterá todo
NEW_SUBFOLDER_NAME = "F2 - CURSOS CORTOS"

# =============================================================================
# 🚀 LÓGICA DE REESTRUCTURACIÓN
# =============================================================================

def reorganize_structure():
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║   REPARADOR DE ESTRUCTURA DE CARPETAS                        ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    
    if not BASE_PATH.exists():
        print(f"❌ Error: La ruta no existe: {BASE_PATH}")
        sys.exit(1)

    # Listar carpetas de estudiantes
    student_folders = [f for f in BASE_PATH.iterdir() if f.is_dir()]
    print(f"📂 Ruta Base: {BASE_PATH}")
    print(f"👥 Carpetas encontradas: {len(student_folders)}")
    print("-" * 60)

    processed_count = 0
    errors = []

    for student_folder in student_folders:
        try:
            student_name = student_folder.name
            # Definir la ruta de la nueva subcarpeta
            target_subfolder = student_folder / NEW_SUBFOLDER_NAME
            
            # Crear la subcarpeta si no existe
            target_subfolder.mkdir(parents=True, exist_ok=True)
            
            print(f"🔸 Procesando: {student_name}")

            # Listar todo el contenido actual de la carpeta del estudiante
            items_to_move = list(student_folder.iterdir())
            
            moved_items = 0
            
            for item in items_to_move:
                # 🛑 SEGURIDAD CRÍTICA: No intentar mover la carpeta destino dentro de sí misma
                if item.name == NEW_SUBFOLDER_NAME:
                    continue
                
                # Definir destino final del archivo/carpeta
                destination = target_subfolder / item.name
                
                # Mover
                shutil.move(str(item), str(destination))
                moved_items += 1
            
            if moved_items > 0:
                print(f"   ✅ Movidos {moved_items} items a '{NEW_SUBFOLDER_NAME}'")
            else:
                print(f"   ℹ️  Nada que mover (o ya estaba organizado)")
                
            processed_count += 1

        except Exception as e:
            err_msg = f"Error en {student_folder.name}: {e}"
            print(f"   ❌ {err_msg}")
            errors.append(err_msg)

    print("-" * 60)
    print(f"🏁 PROCESO TERMINADO")
    print(f"   Carpetas procesadas: {processed_count}")
    print(f"   Errores: {len(errors)}")

    if errors:
        print("\nLista de Errores:")
        for err in errors:
            print(f"- {err}")

if __name__ == "__main__":
    reorganize_structure()