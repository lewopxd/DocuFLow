# DocuFlow v1.0.0.7 - Changelog

> **Fecha:** 2025-12-10  
> **Comparación:** v1.0.0.6 → v1.0.0.7

---

## Índice

| Sección | Descripción |
|---------|-------------|
| [1. Arquitectura](#1-arquitectura) | Nueva estructura de carpetas y módulos |
| [1.1](#11-nueva-carpeta-srcassembler) | Nueva carpeta `src/assembler/` |
| [1.2](#12-nueva-carpeta-srcbridge) | Nueva carpeta `src/bridge/` |
| [1.3](#13-nueva-carpeta-srctools) | Nueva carpeta `src/tools/` |
| [2. Core](#2-core) | Cambios en módulos centrales |
| [2.1](#21-orchester--orchestrator) | Migración de orchester → assembler |
| [2.2](#22-pdf-helpers-expansión) | Expansión de conversores PDF |
| [2.3](#23-nuevo-logger-centralizado) | Nuevo sistema de logging |
| [2.4](#24-renombrado-de-archivos) | Renombrado de archivos |
| [3. UI](#3-ui) | Cambios en la interfaz de usuario |
| [3.1](#31-nuevas-librerías) | ExcelViewer y SimpleGrid |
| [3.2](#32-data-paneljs-reescritura) | Reescritura completa de data-panel |
| [3.3](#33-iconos-nuevos) | Nuevos iconos |
| [3.4](#34-split-api) | Implementación Split API |
| [4. Eliminados](#4-eliminados) | Archivos removidos |

---

## Resumen

La versión 1.0.0.7 representa una **refactorización arquitectónica mayor**. Se extrajo el sistema de orquestación de jobs a una nueva carpeta `assembler/` con clases base reutilizables, se creó un sistema de canales de comunicación bidireccional en `bridge/`, y se añadieron conversores PDF modulares (LibreOffice + MSOffice). En la UI, se implementó un ExcelViewer completo con Split API para carga rápida, y se reescribió totalmente `data-panel.js` con toggle de vistas Tree/Spreadsheet.

---

## 1. Arquitectura

### 1.1 Nueva carpeta `src/assembler/`

**Nuevo módulo de orquestación de jobs con arquitectura extensible:**

| Archivo | Descripción |
|---------|-------------|
| `orchestrator.py` | Orquestador principal (fusión de main_orchester + main_orchester2) |
| `job_manager.py` | Gestor de estado y ejecución de jobs |
| `job_state.py` | Estados y transiciones de jobs |
| `jobs/base_job.py` | Clase abstracta con cancel/pause/progress |
| `jobs/bulk_document_job.py` | Job para generación masiva de documentos |
| `jobs/word_to_pdf_job.py` | Job para conversión Word → PDF |
| `README.md` | Documentación completa del sistema |

### 1.2 Nueva carpeta `src/bridge/`

**Canales de comunicación UI ↔ Python:**

| Archivo | Descripción |
|---------|-------------|
| `instruction_channel.py` | Canal bidireccional (comandos: pause, cancel, resume) |
| `log_channel.py` | Canal unidireccional (streaming de logs a UI) |

### 1.3 Nueva carpeta `src/tools/`

**Herramientas de desarrollo/debug:**

| Archivo | Descripción |
|---------|-------------|
| `debug_docx_inspector.py` | Inspector de estructura de documentos Word (antes `docx_analyzer.py`) |

---

## 2. Core

### 2.1 Orchester → Orchestrator

**Migración completa de la carpeta `core/orchester/` a `assembler/`:**

| v1.0.0.6 | v1.0.0.7 | Cambio |
|----------|----------|--------|
| `core/orchester/main_orchester.py` | `assembler/orchestrator.py` | Fusionado y renombrado |
| `core/orchester/main_orchester2.py` | `assembler/orchestrator.py` | Fusionado |
| `core/orchester/readme.md` | `assembler/README.md` | Actualizado |

### 2.2 PDF Helpers (Expansión)

**De 2 archivos a 6 archivos:**

| v1.0.0.6 | v1.0.0.7 |
|----------|----------|
| `pdf_converter.py` | Eliminado/fusionado |
| `word_to_pdf_converter.py` | Mantenido |
| — | `pdf_converter_engine.py` *(nuevo)* |
| — | `pdf_post_processor.py` *(nuevo)* |
| — | `pdf_to_image_converter.py` *(nuevo)* |
| — | `word_to_pdf_converter_LibreOffice.py` *(nuevo)* |
| — | `word_to_pdf_converter_msOffice.py` *(nuevo)* |

### 2.3 Nuevo Logger Centralizado

**Archivo nuevo:** `src/core/logger.py` (12KB)

- Sistema de logging con eventos estructurados
- Tipos de evento: `JOB_START`, `JOB_PROGRESS`, `ITEM_RESULT`, `JOB_COMPLETE`
- Integración con LogChannel para streaming a UI

### 2.4 Renombrado de Archivos

| Anterior (v0.6) | Nuevo (v0.7) |
|-----------------|--------------|
| `path_utils.py` | `safe_file_handler.py` |
| `image_transform_policies.py` | `auto_rotate_policy.py` |
| `document_assembler.py` | `media_document_assembler.py` |
| `docx_analyzer.py` | `debug_docx_inspector.py` |

---

## 3. UI

### 3.1 Nuevas Librerías

**Añadidas a `src/ui/js/lib/`:**

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `excel-viewer.js` | 15KB | Visor de hojas Excel con tabs, selección, formula bar |
| `excel-viewer.css` | 8KB | Estilos del ExcelViewer |
| `simple-grid.js` | 7KB | Grid básico virtualizado |
| `simple-grid.css` | 2KB | Estilos del SimpleGrid |

### 3.2 `data-panel.js` (Reescritura)

**Cambios principales:**

- **Split API**: `getExcelStructure()` + `getExcelFullData()`
- **Toggle View**: Cambio entre Tree y ExcelViewer
- **Single Tab Mode**: `ALLOW_MULTIPLE_TABS = false`
- **Reload Controls**: Botón de recarga con spinner
- **Lazy Loading**: ExcelViewer se inicializa solo cuando se necesita

### 3.3 Iconos Nuevos

**Añadidos a `icons.js`:**

| Icono | Uso |
|-------|-----|
| `ICON_RELOAD` | Botón de recarga |
| `ICON_LAYOUT_GRID` | Toggle a vista spreadsheet |
| `ICON_LAYOUT_TREE` | Toggle a vista árbol |

### 3.4 Split API

**Nueva API en `provider.python.js`:**

```javascript
getExcelStructure(filePath)  // Paso 1: Estructura (rápido, para Tree)
getExcelFullData(filePath)   // Paso 2: Datos completos (para ExcelViewer)
```

---

## 4. Eliminados

| Archivo | Razón |
|---------|-------|
| `src/analizar_carpetas.py` | Script no relacionado con el proyecto |
| `core/orchester/main_orchester.py` | Fusionado en orchestrator.py |
| `core/orchester/main_orchester2.py` | Fusionado en orchestrator.py |
| `core/orchester/` (carpeta) | Migrada a `assembler/` |
| `core/pdf_helpers/pdf_converter.py` | Reemplazado por pdf_converter_engine.py |
| `ui/js/lib/pntn.tree.js` | Eliminado (duplicado de paneton.tree.js) |

---

## Estadísticas

| Métrica | v1.0.0.6 | v1.0.0.7 | Δ |
|---------|----------|----------|---|
| `main.py` | 37KB | 55KB | +18KB |
| `icons.js` | 7.6KB | 9.1KB | +1.5KB |
| `services.js` | 4.7KB | 5.7KB | +1KB |
| Archivos en `pdf_helpers/` | 2 | 6 | +4 |
| Librerías JS en `lib/` | 2 | 5 | +3 |
| Nuevas carpetas | — | 3 | +3 |
