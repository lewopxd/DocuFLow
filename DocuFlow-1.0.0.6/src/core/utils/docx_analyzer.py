#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  docx_analyzer.py (v2)
Created: 2025-11-06
Author: @lewopxd
Last Updated: 2025-11-06

Description:
A diagnostic tool to inspect the internal structure of a .docx file.

v2 now performs a full relationship consistency check:
1. Reads [Content_Types].xml
2. Maps all relationships in .rels files.
3. Lists all physical media files.
4. Scans document.xml, headers, footers for all used rId's.
5. Cross-references all three to find inconsistencies.
"""

import zipfile
import sys
from lxml import etree
from typing import Dict, Any, List, Set

# Definiciones de Namespace para parsear
XML_NS_MAP = {
    'ct': "http://schemas.openxmlformats.org/package/2006/content-types",
    'rel': "http://schemas.openxmlformats.org/package/2006/relationships",
    'w': "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    'a': "http://schemas.openxmlformats.org/drawingml/2006/main",
    'pic': "http://schemas.openxmlformats.org/drawingml/2006/picture",
    'r': "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
}

def _pretty_print_xml(xml_bytes: bytes) -> str:
    """Parsea y formatea XML para una salida legible."""
    try:
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        tree = etree.fromstring(xml_bytes)
        return etree.tostring(tree, pretty_print=True, encoding="unicode")
    except Exception as e:
        return f"Error al parsear XML: {e}\nRaw: {xml_bytes.decode('utf-8', 'ignore')}"

def _parse_rels(xml_bytes: bytes) -> Dict[str, str]:
    """Parsea un archivo .rels y devuelve un mapa rId -> Target."""
    rels_map = {}
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(xml_bytes)
        relationships = tree.xpath("//rel:Relationship", namespaces=XML_NS_MAP)
        for rel in relationships:
            rId = rel.get("Id")
            target = rel.get("Target")
            if rId and target:
                rels_map[rId] = target
    except Exception:
        pass
    return rels_map

def _find_used_rIds(xml_bytes: bytes) -> Set[str]:
    """Escanea un XML (ej. document.xml) y extrae todos los rId's de imagen."""
    used_ids = set()
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(xml_bytes)
        
        # Buscar todos los rId's de imágenes (en <a:blip r:embed="..."/>)
        blips = tree.xpath("//a:blip", namespaces=XML_NS_MAP)
        for blip in blips:
            rId = blip.get(f"{{{XML_NS_MAP['r']}}}embed")
            if rId:
                used_ids.add(rId)
                
        # (Se pueden añadir más búsquedas aquí si es necesario, ej. hyperlinks)
        
    except Exception:
        pass
    return used_ids

def analyze_docx_structure(docx_path: str) -> Dict[str, Any]:
    """
    Abre un .docx y extrae un reporte de diagnóstico completo.
    """
    report = {
        "file_path": docx_path,
        "manifest_content_types": None,
        "media_files_found": [],
        "relationships": {},
        "rIds_used_in_content": {},
        "consistency_report": {}
    }
    
    all_files = []
    xml_content: Dict[str, bytes] = {}
    
    try:
        # 1. Leer todo el ZIP en memoria
        with zipfile.ZipFile(docx_path, 'r') as zf:
            all_files = zf.namelist()
            for f in all_files:
                if f.startswith("word/media/"):
                    report["media_files_found"].append(f)
                elif f.endswith(".xml") or f.endswith(".rels"):
                    xml_content[f] = zf.read(f)

        # 2. Analizar Manifiesto y Relaciones
        if "[Content_Types].xml" in xml_content:
            report["manifest_content_types"] = _pretty_print_xml(xml_content["[Content_Types].xml"])

        rels_map: Dict[str, str] = {}
        if "word/_rels/document.xml.rels" in xml_content:
            rels_map = _parse_rels(xml_content["word/_rels/document.xml.rels"])
            report["relationships"]["document.xml.rels"] = rels_map
        # (Se podrían añadir .rels de header/footer aquí si fuera necesario)

        # 3. Analizar Contenido (document.xml, headers, footers)
        used_rIds: Set[str] = set()
        content_files_to_scan = [
            "word/document.xml",
            "word/header1.xml", "word/header2.xml", "word/header3.xml",
            "word/footer1.xml", "word/footer2.xml", "word/footer3.xml"
        ]
        
        for f in content_files_to_scan:
            if f in xml_content:
                ids_in_file = _find_used_rIds(xml_content[f])
                if ids_in_file:
                    report["rIds_used_in_content"][f] = sorted(list(ids_in_file))
                    used_rIds.update(ids_in_file)

        # 4. Generar Reporte de Consistencia
        rIds_defined = set(rels_map.keys())
        targets_defined = set(rels_map.values())
        
        report["consistency_report"]["defined_rIds"] = sorted(list(rIds_defined))
        report["consistency_report"]["used_rIds"] = sorted(list(used_rIds))

        # A. ¿Hay rId's usados en el XML que NO están definidos en .rels? (¡CORRUPCIÓN!)
        orphan_rIds = used_rIds - rIds_defined
        report["consistency_report"]["[CRITICAL] Orphan rIds (Used but not Defined)"] = sorted(list(orphan_rIds))

        # B. ¿Hay rId's definidos en .rels que NO se usan en el XML? (Sloppy)
        unreferenced_rIds = rIds_defined - used_rIds
        report["consistency_report"]["[INFO] Unreferenced rIds (Defined but not Used)"] = sorted(list(unreferenced_rIds))
        
        # C. ¿Hay Targets en .rels que NO apuntan a un archivo de media existente? (¡CORRUPCIÓN!)
        broken_links = set()
        for rId, target in rels_map.items():
            if target.startswith("media/"):
                if f"word/{target}" not in report["media_files_found"]:
                    broken_links.add(f"{rId} -> {target}")
        report["consistency_report"]["[CRITICAL] Broken Media Links (Target file missing)"] = sorted(list(broken_links))

        # D. ¿Hay archivos de media que NO están en .rels? (Sloppy)
        media_targets_in_rels = {f"word/{t}" for t in targets_defined if t.startswith("media/")}
        orphan_media = set(report["media_files_found"]) - media_targets_in_rels
        report["consistency_report"]["[INFO] Orphan Media (File exists but not in .rels)"] = sorted(list(orphan_media))

    except Exception as e:
        report["error"] = str(e)
        
    return report

# --------------------------------------> END [ docx_analyzer.py ]