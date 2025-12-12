"""
============================================
Project: DocuFlow
File: project_manager.py
Created: 2025-12-11
Author: @lewopxd

Description:
Project Manager for DocuFlow.
Handles .bkproj file operations and in-memory caching.
============================================
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Importar Logger centralizado
try:
    from ..logger import Logger
except ImportError:
    class Logger:
        @staticmethod
        def debug(msg): print(f"DEBUG: {msg}")
        @staticmethod
        def info(msg): print(f"INFO: {msg}")
        @staticmethod
        def warn(msg): print(f"WARN: {msg}")
        @staticmethod
        def error(msg): print(f"ERROR: {msg}")


#-------------------------------------------------------------
#-------------[   PROJECT MANAGER CLASS   ]-------------------
#-------------------------------------------------------------

class ProjectManager:
    """
    Manages .bkproj project files and in-memory data cache.
    
    Responsibilities:
    - Create, load, save, validate .bkproj files
    - Maintain in-memory cache of parsed data (Excel structures, template placeholders)
    - Handle file existence validation for project resources
    """
    
    PROJECT_VERSION = "1.0.0"
    
    def __init__(self):
        """Initialize ProjectManager with empty cache."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.current_project_path: Optional[str] = None
        self.current_project_data: Optional[Dict[str, Any]] = None
    
    #-------------------------------------------------------------
    #-------------[   PROJECT CRUD OPERATIONS   ]-----------------
    #-------------------------------------------------------------
    
    def create(self, path: str, name: str) -> Dict[str, Any]:
        """
        Creates a new project file at the specified path.
        
        Args:
            path: Full path for the .bkproj file
            name: Display name for the project
            
        Returns:
            The created project data dict
        """
        now = datetime.now().isoformat()
        
        project_data = {
            "meta": {
                "version": self.PROJECT_VERSION,
                "appVersion": "1.0.0.8",
                "createdAt": now,
                "lastModifiedAt": now,
                "name": name
            },
            "layout": {
                "columns": {
                    "leftColumnPercent": 50,
                    "rightColumnPercent": 50
                },
                "leftColumn": {
                    "topPanelPercent": 60,
                    "bottomPanelPercent": 40,
                    "topCollapsed": False,
                    "bottomCollapsed": False
                },
                "rightColumn": {
                    "topPanelPercent": 70,
                    "bottomPanelPercent": 30,
                    "topCollapsed": False,
                    "bottomCollapsed": False
                }
            },
            "panels": {
                "dataPanel": {
                    "activeTabIndex": 0,
                    "tabs": []
                },
                "templatesPanel": {
                    "activeTabIndex": 0,
                    "tabs": []
                }
            },
            "automation": {
                "outputFolder": None,
                "namingPattern": "output_{{ROW}}",
                "format": "pdf"
            }
        }
        
        # Save to file
        self._save_to_file(path, project_data)
        
        # Set as current
        self.current_project_path = path
        self.current_project_data = project_data
        
        Logger.info(f"[ProjectManager] Created project: {path}")
        return project_data
    
    def load(self, path: str) -> Dict[str, Any]:
        """
        Loads a project file and validates file references.
        
        Args:
            path: Path to the .bkproj file
            
        Returns:
            Dict with 'project' data and 'missingFiles' list
        """
        if not Path(path).exists():
            raise FileNotFoundError(f"Project file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # Validate file references
        missing_files = []
        
        # Check data panel files
        for tab in project_data.get("panels", {}).get("dataPanel", {}).get("tabs", []):
            file_path = tab.get("filePath")
            if file_path and not Path(file_path).exists():
                missing_files.append({"type": "data", "path": file_path, "fileName": tab.get("fileName", "")})
        
        # Check templates panel files
        for tab in project_data.get("panels", {}).get("templatesPanel", {}).get("tabs", []):
            file_path = tab.get("filePath")
            if file_path and not Path(file_path).exists():
                missing_files.append({"type": "template", "path": file_path, "fileName": tab.get("fileName", "")})
        
        # Load any embedded cache data
        if "_cache" in project_data:
            for cache_id, cache_entry in project_data["_cache"].items():
                self.cache[cache_id] = cache_entry
            Logger.debug(f"[ProjectManager] Loaded {len(project_data['_cache'])} cache entries")
        
        # Set as current
        self.current_project_path = path
        self.current_project_data = project_data
        
        Logger.info(f"[ProjectManager] Loaded project: {path}")
        if missing_files:
            Logger.warn(f"[ProjectManager] Missing files: {len(missing_files)}")
        
        return {
            "project": project_data,
            "missingFiles": missing_files
        }
    
    def save(self, path: str, project_config: Dict[str, Any]) -> bool:
        """
        Saves project configuration with embedded cache.
        
        Args:
            path: Path for the .bkproj file
            project_config: Project configuration from UI
            
        Returns:
            True if saved successfully
        """
        # Ensure meta exists
        if "meta" not in project_config:
            project_config["meta"] = {
                "version": self.PROJECT_VERSION,
                "appVersion": "1.0.0.8",
                "createdAt": datetime.now().isoformat()
            }
        
        # Update modification time
        project_config["meta"]["lastModifiedAt"] = datetime.now().isoformat()
        
        # Embed relevant cache data
        project_config["_cache"] = {}
        
        # Gather cache IDs from tabs
        cache_ids = set()
        for tab in project_config.get("panels", {}).get("dataPanel", {}).get("tabs", []):
            if tab.get("structureCacheId"):
                cache_ids.add(tab["structureCacheId"])
        for tab in project_config.get("panels", {}).get("templatesPanel", {}).get("tabs", []):
            if tab.get("placeholdersCacheId"):
                cache_ids.add(tab["placeholdersCacheId"])
        
        # Copy relevant cache entries
        for cache_id in cache_ids:
            if cache_id in self.cache:
                project_config["_cache"][cache_id] = self.cache[cache_id]
        
        # Save to file
        success = self._save_to_file(path, project_config)
        
        if success:
            self.current_project_path = path
            self.current_project_data = project_config
        
        return success
    
    def validate(self, path: str) -> Dict[str, Any]:
        """
        Validates a project file without fully loading it.
        
        Args:
            path: Path to the .bkproj file
            
        Returns:
            Dict with 'valid' bool and 'error' message if invalid
        """
        if not Path(path).exists():
            return {"valid": False, "error": "File not found"}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required fields
            if "meta" not in data:
                return {"valid": False, "error": "Missing 'meta' section"}
            if "version" not in data["meta"]:
                return {"valid": False, "error": "Missing project version"}
            
            return {"valid": True, "error": None, "name": data["meta"].get("name", "Unknown")}
            
        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    #---------------------------------------> END [ PROJECT CRUD OPERATIONS ... ]
    
    #-------------------------------------------------------------
    #-------------[   CACHE MANAGEMENT   ]------------------------
    #-------------------------------------------------------------
    
    def get_cache_id(self, file_path: str) -> str:
        """
        Generates a unique cache ID for a file.
        
        Args:
            file_path: Path to the file being cached
            
        Returns:
            Unique cache ID string
        """
        return f"cache-{uuid.uuid4().hex[:8]}"
    
    def cache_excel_data(self, file_path: str, structure: Dict, full_data: Dict = None) -> str:
        """
        Caches parsed Excel data.
        
        Args:
            file_path: Path to the Excel file
            structure: Parsed structure data
            full_data: Optional full row data
            
        Returns:
            The cache ID for referencing this data
        """
        cache_id = self.get_cache_id(file_path)
        self.cache[cache_id] = {
            "filePath": file_path,
            "structure": structure,
            "fullData": full_data,
            "lastParsed": datetime.now().isoformat()
        }
        Logger.debug(f"[ProjectManager] Cached Excel data: {cache_id}")
        return cache_id
    
    def cache_template_data(self, file_path: str, placeholders: List, metadata: Dict = None) -> str:
        """
        Caches parsed template data.
        
        Args:
            file_path: Path to the template file
            placeholders: List of parsed placeholders
            metadata: Optional metadata
            
        Returns:
            The cache ID for referencing this data
        """
        cache_id = self.get_cache_id(file_path)
        self.cache[cache_id] = {
            "filePath": file_path,
            "placeholders": placeholders,
            "metadata": metadata or {},
            "lastParsed": datetime.now().isoformat()
        }
        Logger.debug(f"[ProjectManager] Cached template data: {cache_id}")
        return cache_id
    
    def get_cached_data(self, cache_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached data by ID.
        
        Args:
            cache_id: The cache ID to look up
            
        Returns:
            Cached data dict or None if not found
        """
        return self.cache.get(cache_id)
    
    def clear_cache(self):
        """Clears all cached data."""
        self.cache.clear()
        Logger.debug("[ProjectManager] Cache cleared")
    
    def remove_from_cache(self, cache_id: str) -> bool:
        """
        Removes a specific entry from the cache.
        
        Args:
            cache_id: The cache ID to remove
            
        Returns:
            True if removed, False if not found
        """
        if cache_id in self.cache:
            del self.cache[cache_id]
            Logger.debug(f"[ProjectManager] Removed from cache: {cache_id}")
            return True
        return False
    
    #---------------------------------------> END [ CACHE MANAGEMENT ... ]
    
    #-------------------------------------------------------------
    #-------------[   INTERNAL HELPERS   ]------------------------
    #-------------------------------------------------------------
    
    def _save_to_file(self, path: str, data: Dict) -> bool:
        """
        Writes project data to file.
        
        Args:
            path: File path to save to
            data: Data dict to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            Logger.info(f"[ProjectManager] Saved project: {path}")
            return True
            
        except Exception as e:
            Logger.error(f"[ProjectManager] Failed to save: {e}")
            return False
    
    def get_current_project(self) -> Optional[Dict[str, Any]]:
        """
        Returns the currently loaded project data.
        
        Returns:
            Current project data or None
        """
        return self.current_project_data
    
    def get_current_path(self) -> Optional[str]:
        """
        Returns the path to the currently loaded project.
        
        Returns:
            Current project path or None
        """
        return self.current_project_path
    
    #---------------------------------------> END [ INTERNAL HELPERS ... ]

#---------------------------------------> END [ PROJECT MANAGER CLASS ... ]


#-------------------------------------------------------------
#-------------[   SINGLETON INSTANCE   ]----------------------
#-------------------------------------------------------------

_project_manager: Optional[ProjectManager] = None

def get_project_manager() -> ProjectManager:
    """
    Returns the singleton ProjectManager instance.
    
    Returns:
        The shared ProjectManager instance
    """
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
        Logger.info("[ProjectManager] Singleton instance created")
    return _project_manager

#---------------------------------------> END [ SINGLETON INSTANCE ... ]
