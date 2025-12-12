#!/usr/bin/env python
"""
initial_test.py

Script de diagnóstico (v2) para verificar el entorno Python.
Comprueba:
1. Ejecución básica (Hola Mundo).
2. Si el intérprete de Python proviene de un venv (sys.prefix).
3. Si el shell tiene un venv activado (os.environ['VIRTUAL_ENV']).
4. Lista las librerías instaladas (pip freeze).
5. Compara las librerías instaladas con 'requirements.txt' (si existe).
"""

import sys
import os
import subprocess
import platform

# --- Configuración ---
HR = "=" * 60  # Separador horizontal

def print_header(title):
    """Imprime un encabezado bonito."""
    print(f"\n{HR}")
    print(f"  🐍 {title}")
    print(f"{HR}")

def get_installed_packages(freeze_output):
    """
    Convierte la salida de 'pip freeze' en un diccionario.
    Ej: {'bottle': '0.13.4', 'lxml': '6.0.2'}
    """
    packages = {}
    for line in freeze_output.strip().splitlines():
        # Manejar líneas estándar de 'pip freeze' (ej. package==1.2.3)
        # Ignorar instalaciones editables (-e) u otras líneas no estándar
        if '==' in line and not line.startswith('-'):
            try:
                name, version = line.split('==', 1)
                # Normalizamos el nombre a minúsculas para comparaciones
                packages[name.strip().lower()] = version.strip()
            except ValueError:
                # Ignorar líneas malformadas
                continue
    return packages

# --- Inicio del Script ---
try:
    # --- 1. Hola Mundo ---
    print_header("1. Prueba de Ejecución Básica")
    print("¡Hola Mundo! El script se está ejecutando correctamente.")
    print(f"Versión de Python: {sys.version.split()[0]} ({platform.python_implementation()})")
    print(f"Ejecutable de Python: {sys.executable}")


    # --- 2. Verificación de Intérprete (sys.prefix) ---
    print_header("2. Verificación del Intérprete (¿Es un VENV?)")
    print(f"  Ruta base de Python (base_prefix): {sys.base_prefix}")
    print(f"  Ruta actual de Python (prefix):   {sys.prefix}")

    is_venv_interpreter = sys.prefix != sys.base_prefix
    if is_venv_interpreter:
        print("\n  [✓] ¡ÉXITO! El intérprete de Python SÍ pertenece a un entorno virtual.")
    else:
        print("\n  [!] ADVERTENCIA: Estás usando el intérprete de Python global del sistema.")


    # --- 3. Verificación de Activación de Shell (VIRTUAL_ENV) ---
    print_header("3. Verificación de Activación de Shell (¿Está 'activado'?)")
    venv_path = os.environ.get('VIRTUAL_ENV')

    if venv_path:
        print(f"\n  [✓] ¡ÉXITO! La variable de entorno VIRTUAL_ENV está configurada.")
        print(f"  Ruta del VENV detectada: {venv_path}")
        if venv_path.lower() != sys.prefix.lower():
             print("\n  [!] ADVERTENCIA: La variable VIRTUAL_ENV no coincide con el 'prefix' del intérprete.")
    else:
        print("\n  [!] ADVERTENCIA: No se encontró la variable de entorno VIRTUAL_ENV.")
        print("      Si esperabas estar en un VENV, asegúrate de haberlo activado.")


    # --- 4. Librerías Instaladas (pip freeze) ---
    print_header("4. Librerías Instaladas (pip freeze)")
    print("Intentando obtener la lista de paquetes con 'pip freeze'...")
    
    installed_packages_output = ""
    installed_dict = {}

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'freeze'],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        
        installed_packages_output = result.stdout.strip()
        
        if installed_packages_output:
            print("\n  Librerías encontradas en este entorno:")
            print("  -------------------------------------")
            for line in installed_packages_output.splitlines():
                print(f"    {line}")
            print("  -------------------------------------")
            
            # Convertimos la salida en un diccionario para la siguiente prueba
            installed_dict = get_installed_packages(installed_packages_output)
            
        else:
            print("\n  [i] No hay librerías de terceros instaladas en este entorno.")
            
    except FileNotFoundError:
        print("\n  [X] ERROR: 'pip' no parece estar disponible (FileNotFoundError).")
    except subprocess.CalledProcessError as e:
        print(f"\n  [X] ERROR al ejecutar 'pip freeze'. Código de error: {e.returncode}")
        print(f"      Error: {e.stderr}")
    except Exception as e:
        print(f"\n  [X] Ocurrió un error inesperado al listar librerías: {e}")


    # --- 5. Verificación de 'requirements.txt' ---
    print_header("5. Verificación de 'requirements.txt'")
    req_file = 'requirements.txt'
    
    if not os.path.exists(req_file):
        print(f"  [i] No se encontró el archivo '{req_file}'. Omitiendo esta verificación.")
    
    elif not os.path.getsize(req_file) > 0:
        print(f"  [i] El archivo '{req_file}' está vacío. Omitiendo esta verificación.")

    elif not installed_dict and os.path.getsize(req_file) > 0:
         print(f"  [!] ADVERTENCIA: Se encontró '{req_file}', pero no hay paquetes instalados.")
         print("      Probablemente falte instalar todo. Corre:")
         print(f"      {sys.executable} -m pip install -r {req_file}")
    
    else:
        print(f"  Analizando '{req_file}' contra las librerías instaladas...")
        print("  --------------------------------------------------")
        all_ok = True
        missing_count = 0
        mismatch_count = 0

        with open(req_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Ignorar comentarios, líneas vacías o flags (como -r, -e)
                if not line or line.startswith('#') or line.startswith('-'):
                    continue

                req_name, req_version = None, None
                
                # Parser simple: solo maneja 'package==version' y 'package'
                # No es un parser completo de PEP 508 (ignora >=, <=, ~=)
                if '==' in line:
                    try:
                        req_name, req_version = line.split('==', 1)
                        req_name = req_name.strip().lower()
                        req_version = req_version.strip()
                    except ValueError:
                        req_name = line.strip().lower() # Línea malformada, tomar solo nombre
                else:
                    # Tomar solo el nombre, ignorar extras (ej. requests[security])
                    req_name = line.split('[')[0].split('>')[0].split('<')[0].split('~')[0].strip().lower()

                if not req_name:
                    continue

                # --- Iniciar comprobación ---
                if req_name not in installed_dict:
                    all_ok = False
                    missing_count += 1
                    print(f"    [X] FALTA: {req_name} (requerido en línea {line_num})")
                
                elif req_version:
                    # Si se especificó una versión exacta (==)
                    installed_version = installed_dict[req_name]
                    if installed_version != req_version:
                        all_ok = False
                        mismatch_count += 1
                        print(f"    [!] MISMATCH: {req_name} (requerido: {req_version}, instalado: {installed_version})")
                    else:
                        print(f"    [✓] OK: {req_name}=={req_version}")
                else:
                    # Solo se pidió el paquete (sin versión) y está instalado.
                    print(f"    [✓] OK: {req_name} (instalado)")
        
        print("  --------------------------------------------------")
        if all_ok:
            print("  [✓] ¡ÉXITO! Todas las dependencias de 'requirements.txt' están instaladas y coinciden.")
        else:
            print(f"  [!] ADVERTENCIA: Se encontraron {missing_count} paquetes faltantes y {mismatch_count} versiones incorrectas.")
            print("      Revisa los detalles arriba y considera correr:")
            print(f"      {sys.executable} -m pip install -r {req_file}")


except Exception as e:
    print(f"\n{HR}")
    print(f"[X] ERROR CRÍTICO INESPERADO: {e}")
    print("El script no pudo completarse.")
finally:
    print(f"\n{HR}")
    print("--- TEST DE ENTORNO (v2) COMPLETADO ---")