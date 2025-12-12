# 📋 Configuración Final - Script Bulk Marcela

## **1. RUTAS**
```
Excel:      C:\Users\Admin\Desktop\PLAYGROUND MARCELA\F2 CURSOS CORTOS\DB_C1F2_MARCELA.xlsx
Plantillas: C:\Users\Admin\Desktop\PLAYGROUND MARCELA\F2 CURSOS CORTOS\plantillas\
Imágenes:   C:\Users\Admin\Documents\MARCELA SDIS\JÓVENES JCO COHORTE 1 V2\JÓVENES JCO COHORTE 1 V2\JÓVENES JCO COHORTE 1 - V2\{NOMBRE_NORMALIZADO}\F2 - CURSOS CORTOS\SOPORTES\
Salida:     C:\Users\Admin\Desktop\PLAYGROUND MARCELA\F2 CURSOS CORTOS\OUTPUT\CERTIFICADOS\
```

## **2. PLANTILLAS**
```
Acta 1: ACTA 1 - INICIO RUTA.docx
Acta 2: ACTA 2 - PERMANENCIA.docx
Acta 3: ACTA 3 - FINALIZACION.docx
```

## **3. EXCEL CONFIG**
```
Hoja:   "COHORTE 1"
Tabla:  "Tabla_1"
Rango:  {"type": "multiple_row", "data": "2-5"}
Filtro: {"column": "REPORTE SENA", "operator": "equal", "value": "CERTIFICADO"}
```

## **4. COLUMNAS REQUERIDAS**
```
NOMBRES
APELLIDOS
EL/LA
TIPO DE DOCUMENTO
NUM_DOCUMENTO
CURSO REPORTADO SENA
APRENDIZAJE
REPORTE SENA
```

## **5. PLACEHOLDERS TEXTO**
```
{{NOMBRE_JOVEN}}      → [NOMBRES] + [APELLIDOS] (uppercase, trim, sin espacios extra)
{{EL/LA}}             → [EL/LA] (lowercase, trim)
{{TIPO_DOCUMENTO}}    → [TIPO DE DOCUMENTO] (trim)
{{NUM_DOCUMENTO}}     → [NUM_DOCUMENTO] (trim)
{{NOMBRE_CURSO}}      → [CURSO REPORTADO SENA] (trim)
{{APRENDIZAJE}}       → [APRENDIZAJE] (trim)
```

## **6. PLACEHOLDERS IMÁGENES**
```
Acta 1:
  $IMG{{01_PANTALLAZO_INSCRIPCION}}
  $IMG{{01_DETALLE_INSCRIPCION}}

Acta 2:
  $IMG{{02_CRONOGRAMA}}

Acta 3:
  $IMG{{03_CORREO_APROBADO}}
  $IMG{{03_CERTIFICADO_SENA}}
```

## **7. BÚSQUEDA IMÁGENES**
```
Extensiones: .png, .jpg, .jpeg, .PNG, .JPG, .JPEG (orden de prioridad)
Normalización nombre carpeta: sin tildes, lowercase, trim, espacios únicos
Ejemplo: "Juan Pérez  López" → "juan perez lopez"
```

## **8. NOMBRES SALIDA**
```
Carpeta: {NOMBRES_UPPERCASE} {APELLIDOS_UPPERCASE}
Archivos:
  - ACTA 1 - INICIO RUTA - {NOMBRES} {APELLIDOS}.docx
  - ACTA 2 - PERMANENCIA - {NOMBRES} {APELLIDOS}.docx
  - ACTA 3 - FINALIZACION - {NOMBRES} {APELLIDOS}.docx
```

## **9. POLÍTICAS**
```
on_missing_data:     "REPLACE_EMPTY"
imagen_faltante:     Advertencia + continuar
layout_policy:       {"width": "auto", "height": "auto", "alignment": "CENTER"}
debug:               true
overwrite_existing:  true
```

---

✅ **TODO CONFIRMADO. LISTO PARA CÓDIGO.**