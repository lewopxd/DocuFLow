# README: orchestrator.py

## 1. Propósito

Este script es un motor de procesamiento batch (ETL) que genera documentos Word (.docx) a partir de datos de Excel (.xlsx) y una plantilla Word. Toda la operación se controla mediante un único objeto de configuración **config** (JSON) que la UI debe construir y enviar. El script no tiene estado propio; depende 100% de este objeto.

## 2. API Principal

**Python**

```python
execute_bulk_document_job(config: dict) -> dict
```

**Entrada (config):** Objeto JSON que describe el trabajo.
**Salida (dict):** Objeto JSON con el resumen y log detallado del trabajo.

## 3. El Objeto config (Contrato de la UI)

El objeto **config** es la "orden de trabajo". Tiene tres claves raíz obligatorias:

```json
{
  "excel_config": { ... },
  "template_config": { ... },
  "job_config": { ... }
}
```

### 3.1. excel_config (Fuente de Datos)

Define **QUÉ** datos leer. Este objeto se pasa directamente al módulo `data_sheet_parser.py`.

| Clave       | Tipo   | Descripción                                                 |
| ----------- | ------ | ----------------------------------------------------------- |
| filePath    | string | Ruta absoluta al archivo .xlsx.                             |
| sheetName   | string | Nombre exacto de la hoja de cálculo.                        |
| tableName   | string | Nombre exacto de la tabla de Excel (ej: "Tabla1").          |
| columns     | array  | Lista de strings con los nombres de las columnas a extraer. |
| rangeConfig | object | Define qué filas de la tabla procesar.                      |

#### rangeConfig (Detalle)

El objeto **rangeConfig** define el subconjunto de filas a leer.

| type           | data (Ejemplo) | Descripción                                                         |
| -------------- | -------------- | ------------------------------------------------------------------- |
| "all"          | null o "none"  | Procesa todas las filas de datos de la tabla (omite el encabezado). |
| "unique_row"   | "5"            | Procesa únicamente la fila 5 (relativa al inicio de la tabla).      |
| "multiple_row" | "2-23"         | Procesa el rango de filas desde la 2 hasta la 23 (inclusivo).       |

**Ejemplo:**

```json
"excel_config": {
  "filePath": "C:\\temp\\datos.xlsx",
  "sheetName": "Hoja1",
  "tableName": "DatosClientes",
  "columns": ["ID_Contrato", "NombreCliente", "PAIS", "CIUDAD"],
  "rangeConfig": {
    "type": "all",
    "data": null
  }
}
```

### 3.2. template_config (Plantilla y Destino)

Define la plantilla base y las opciones del documento de salida. Este objeto se usa como base para el módulo `replace_holders_text.py`.

| Clave            | Tipo    | Descripción                                                              |
| ---------------- | ------- | ------------------------------------------------------------------------ |
| source_path      | string  | Ruta absoluta a la plantilla .docx maestra.                              |
| target_directory | string  | Carpeta raíz donde se guardarán los documentos generados.                |
| clear_highlight  | boolean | (Opcional) True si se debe quitar el resaltado de los tags reemplazados. |
| author           | string  | (Opcional) Establece el "Autor" en los metadatos del .docx generado.     |
| last_modified_by | string  | (Opcional) Establece "Última modificación por" en los metadatos.         |

**Ejemplo:**

```json
"template_config": {
  "source_path": "C:\\temp\\plantilla_contrato.docx",
  "target_directory": "C:\\temp\\documentos_generados",
  "clear_highlight": true,
  "author": "DocuFlow Bot"
}
```

### 3.3. job_config (Lógica de Negocio)

Define **CÓMO** procesar los datos. Esta es la lógica interna del orquestador.

| Clave              | Tipo    | Descripción                                             |
| ------------------ | ------- | ------------------------------------------------------- |
| filter_rules       | object  | (Opcional) Reglas para omitir filas leídas del Excel.   |
| direct_mapping     | object  | Mapeo 1:1 de COLUMNA_EXCEL a TAG_WORD.                  |
| computed_mapping   | array   | (Opcional) Reglas para TAG_WORD calculados (lógica).    |
| folder_pattern     | object  | (Opcional) Patrón para crear subcarpetas dinámicas.     |
| filename_pattern   | object  | Patrón para nombrar el archivo .docx de salida.         |
| overwrite_existing | boolean | True para sobrescribir archivos existentes.             |
| debug              | boolean | True para imprimir logs detallados de transformaciones. |

#### A. filter_rules (Filtrado de Filas)

Objeto recursivo para filtrar filas. Si se omite o es nulo, se procesan todas.

**Operadores Lógicos:** AND, OR
**Operadores de Regla:** equal, not_equal, contains, is_empty, is_not_empty

**Ejemplo:**

```json
"filter_rules": {
  "AND": [
    {"column": "ESTADO", "operator": "equal", "value": "Activo"},
    {
      "OR": [
        {"column": "PAIS", "operator": "equal", "value": "COL"},
        {"column": "PAIS", "operator": "equal", "value": "MEX"}
      ]
    }
  ]
}
```

#### B. direct_mapping (Mapeo 1:1)

Conecta **TAG_WORD** con **COLUMNA_EXCEL** y aplica una cadena de transformaciones.

```json
"direct_mapping": {
  "TAG_CONTRATO": {
    "source_column": "ID_Contrato",
    "transforms": [
      {"type": "trim"},
      {"type": "pad_left", "width": 10, "fillchar": "0"}
    ]
  },
  "TAG_CLIENTE": {
    "source_column": "NombreCliente",
    "transforms": [{"type": "uppercase"}]
  }
}
```

#### C. computed_mapping (Mapeo Calculado)

Genera valores para **TAG_WORD** usando lógica, no una sola columna.

| type            | Descripción                                    |
| --------------- | ---------------------------------------------- |
| concatenate     | Une columnas.                                  |
| conditional_map | Mapea un valor a otro (como un switch o dict). |

**Ejemplo:**

```json
"computed_mapping": [
  {
    "placeholder": "TAG_NOMBRE_COMPLETO",
    "rule": {
      "type": "concatenate",
      "columns": ["Nombre", "Apellido"],
      "separator": " "
    },
    "transforms": [{"type": "title_case"}]
  }
]
```

#### D. folder_pattern y filename_pattern (Ruta de Salida)

Definen el nombre y carpeta del archivo. Usa `{[NOMBRE_COLUMNA]}` para insertar datos de la fila.

**Ejemplo:**

```json
"folder_pattern": {
  "template": "Clientes/{[PAIS]}/{[CIUDAD]}",
  "columns": [
    {"name": "PAIS", "transforms": [{"type": "uppercase"}]},
    {"name": "CIUDAD", "transforms": [{"type": "title_case"}]}
  ]
},
"filename_pattern": {
  "template": "Contrato - {[ID_Contrato]}.docx",
  "columns": [
    {"name": "ID_Contrato", "transforms": []}
  ]
}
```

## 4. Sistema de Transformaciones (transforms)

La UI debe permitir al usuario construir una "tubería" (pipeline) de estas transformaciones, ejecutadas en orden.

| type             | Configuración (JSON)                                        | Descripción                                           |
| ---------------- | ----------------------------------------------------------- | ----------------------------------------------------- |
| trim             | {}                                                          | Elimina espacios al inicio y final.                   |
| uppercase        | {}                                                          | Convierte a MAYÚSCULAS.                               |
| lowercase        | {}                                                          | Convierte a minúsculas.                               |
| sentence_case    | {}                                                          | Convierte a Tipo frase.                               |
| title_case       | {}                                                          | Convierte a Tipo Título.                              |
| replace          | {"from": "a", "to": "b"}                                    | Reemplazo de texto simple.                            |
| regex_replace    | {"pattern": "\s+", "replacement": " "}                      | Reemplazo usando Expresiones Regulares.               |
| truncate         | {"max_length": 10, "suffix": "..."}                         | Acorta el texto a *max_length*.                       |
| pad_left         | {"width": 5, "fillchar": "0"}                               | Rellena a la izquierda (ej: 123 -> 00123).            |
| pad_right        | {"width": 5, "fillchar": " "}                               | Rellena a la derecha (ej: 123 -> 123  ).              |
| substring        | {"start": 0, "end": 5}                                      | Extrae una subcadena (Python slice).                  |
| date_format      | {"input_format": "%Y-%m-%d", "output_template": "%d/%m/%Y"} | Formatea fechas.                                      |
| number_format    | {"decimals": 2, "decimal_sep": ",", "thousands_sep": "."}   | Formatea números.                                     |
| round            | {"decimals": 0}                                             | Redondea un número.                                   |
| ceil             | {}                                                          | Redondea hacia arriba (ej: 4.1 -> 5).                 |
| floor            | {}                                                          | Redondea hacia abajo (ej: 4.9 -> 4).                  |
| default_if_empty | {"default": "N/A"}                                          | Devuelve *default* si el valor está vacío.            |
| validate_regex   | {"pattern": "^[A-Z0-9]+$", "fallback": "INVALIDO"}          | Si no coincide con el *pattern*, devuelve *fallback*. |

## 5. Salida del Script (Respuesta a la UI)

La función **execute_bulk_document_job** siempre devuelve un objeto JSON con dos claves:

| Clave       | Descripción                                        |
| ----------- | -------------------------------------------------- |
| job_summary | Resumen general del trabajo.                       |
| job_results | Array con el log detallado de cada fila procesada. |

**Ejemplo:**

```json
{
  "job_summary": {
    "status": "partial_success", // pending, complete_success, partial_success, total_failure
    "total_rows_processed": 100,
    "success_count": 95,
    "failure_count": 5,
    "total_skipped": 0,
    "error": null
  },
  "job_results": [
    {
      "row_index": 2,
      "input_data": {"ID_Contrato": "C-001", ...},
      "filename_generated": "Clientes/COL/Bogota/Contrato - C-001.docx",
      "status": "success",
      "output_log": {
        "success": true,
        "target_path": "C:\\temp\\...\\Contrato - C-001.docx",
        "error": null,
        "details": {
          "placeholder_status": {
            "all_found": true,
            "total_requested": 5,
            "total_found": 5,
            "found": ["TAG_CIUDAD", "TAG_CLIENTE", ...],
            "not_found": []
          }
        }
      }
    },
    {
      "row_index": 3,
      "status": "failure"
    }
  ]
}
```
