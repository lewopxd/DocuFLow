#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  path_utils.py
Created: [YYYY-MM-DD]
Author: @lewopxd

Description:
Provides safe file operations, validations, and path manipulations.
Ensures all file access is secure and originals are not tampered with.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, ContextManager
from contextlib import contextmanager

# -------------------------------------------------------------
# -------------------[   FILE VALIDATION   ]-------------------
# -------------------------------------------------------------

@contextmanager
def create_safe_temp_copy(original_path: str) -> ContextManager[Optional[str]]:
    """
    Safely validates and creates a temporary copy of a file.

    This function acts as a security gate. It validates the original path
    and yields the path to a temporary copy, ensuring the original file
    is never locked or modified.

    It is designed to be used with a 'with' statement:
    
    with create_safe_temp_copy(path) as temp_file_path:
        if temp_file_path:
            # ... do work on temp_file_path ...
        else:
            # ... handle error ...

    Args:
        original_path: The full path to the user's file.

    Yields:
        str: The full path to the temporary, safe-to-read copy.
             Yields None if the original file is invalid or inaccessible.
    """
    temp_file_path = None
    try:
        # 1. Validación de Seguridad
        original_file = Path(original_path)
        if not original_file.exists():
            print(f"❌ Error: Archivo no encontrado en: {original_path}")
            yield None
            return
        
        if not original_file.is_file():
            print(f"❌ Error: La ruta no es un archivo: {original_path}")
            yield None
            return
            
        # 2. Creación de la Copia Temporal
        # Crear un archivo temporal con la misma extensión
        suffix = original_file.suffix
        
        # tempfile.NamedTemporaryFile con delete=False es la forma más segura
        # de obtener un nombre de archivo único que podamos usar.
        fd, temp_file_path = tempfile.mkstemp(suffix=suffix, prefix="docuflow_")
        os.close(fd) # Cerramos el descriptor, solo queríamos el nombre

        # 3. Copiar contenido
        shutil.copy2(original_file, temp_file_path)
        
        print(f"✓ Copia temporal segura creada en: {temp_file_path}")
        
        # 4. Ceder control (Yield)
        # El bloque 'with' se ejecuta aquí
        yield temp_file_path

    except (IOError, OSError, PermissionError) as e:
        print(f"❌ Error de permisos o I/O al crear copia: {e}")
        yield None
    except Exception as e:
        print(f"❌ Error inesperado al crear copia segura: {e}")
        yield None
        
    finally:
        # 5. Limpieza Absoluta
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"✓ Copia temporal eliminada: {temp_file_path}")
            except OSError as e:
                print(f"⚠️ No se pudo eliminar la copia temporal: {e}")

# --------------------------------------> END [ FILE VALIDATION ... ]