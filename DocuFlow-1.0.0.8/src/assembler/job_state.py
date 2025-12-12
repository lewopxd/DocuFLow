#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  job_state.py
Created: 2025-12-09
Author: @lewopxd

Description:
Manages job checkpoint persistence for crash recovery and resume.
Checkpoints are saved to %APPDATA%/DocuFlow/jobs/
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Import Logger
try:
    from core.logger import Logger
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


@dataclass
class JobCheckpoint:
    """Represents a saved job state for recovery."""
    
    job_id: str
    status: str  # "running", "paused", "cancelled"
    config: Dict[str, Any]
    
    # Progress tracking
    total_rows: int = 0
    last_processed_index: int = 0  # Resume from here
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    
    # Results collected so far
    failure_details: List[Dict[str, Any]] = field(default_factory=list)
    job_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    created_at: str = ""
    last_checkpoint_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.last_checkpoint_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobCheckpoint":
        """Create from dictionary."""
        return cls(**data)
    
    def update_progress(
        self,
        last_index: int,
        success: int,
        failed: int,
        skipped: int
    ):
        """Update progress counters."""
        self.last_processed_index = last_index
        self.success_count = success
        self.failure_count = failed
        self.skipped_count = skipped
        self.last_checkpoint_at = datetime.now().isoformat()


class JobStateManager:
    """
    Manages checkpoint file operations.
    
    Checkpoints are stored in: %APPDATA%/DocuFlow/jobs/{job_id}.checkpoint.json
    """
    
    # Default checkpoint directory
    _checkpoint_dir: Optional[Path] = None
    
    @classmethod
    def _get_checkpoint_dir(cls) -> Path:
        """Get or create the checkpoint directory."""
        if cls._checkpoint_dir is None:
            # Use APPDATA on Windows, ~/.config on Unix
            if os.name == 'nt':
                base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
            else:
                base = Path.home() / '.config'
            
            cls._checkpoint_dir = base / 'DocuFlow' / 'jobs'
        
        # Ensure directory exists
        cls._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return cls._checkpoint_dir
    
    @classmethod
    def _get_checkpoint_path(cls, job_id: str) -> Path:
        """Get the file path for a specific job checkpoint."""
        return cls._get_checkpoint_dir() / f"{job_id}.checkpoint.json"
    
    @classmethod
    def save(cls, checkpoint: JobCheckpoint) -> bool:
        """
        Save a checkpoint to disk.
        
        Args:
            checkpoint: The checkpoint to save
            
        Returns:
            True if saved successfully
        """
        try:
            path = cls._get_checkpoint_path(checkpoint.job_id)
            checkpoint.last_checkpoint_at = datetime.now().isoformat()
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)
            
            Logger.debug(f"Checkpoint saved: {path.name}")
            return True
            
        except Exception as e:
            Logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    @classmethod
    def load(cls, job_id: str) -> Optional[JobCheckpoint]:
        """
        Load a checkpoint from disk.
        
        Args:
            job_id: The job ID to load
            
        Returns:
            JobCheckpoint if found, None otherwise
        """
        try:
            path = cls._get_checkpoint_path(job_id)
            
            if not path.exists():
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            Logger.debug(f"Checkpoint loaded: {path.name}")
            return JobCheckpoint.from_dict(data)
            
        except Exception as e:
            Logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    @classmethod
    def delete(cls, job_id: str) -> bool:
        """
        Delete a checkpoint (called on successful completion).
        
        Args:
            job_id: The job ID to delete
            
        Returns:
            True if deleted or didn't exist
        """
        try:
            path = cls._get_checkpoint_path(job_id)
            
            if path.exists():
                path.unlink()
                Logger.debug(f"Checkpoint deleted: {path.name}")
            
            return True
            
        except Exception as e:
            Logger.error(f"Failed to delete checkpoint: {e}")
            return False
    
    @classmethod
    def list_checkpoints(cls) -> List[Dict[str, Any]]:
        """
        List all available checkpoints (for resume UI).
        
        Returns:
            List of checkpoint summaries
        """
        checkpoints = []
        
        try:
            checkpoint_dir = cls._get_checkpoint_dir()
            
            for file_path in checkpoint_dir.glob("*.checkpoint.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Return summary info only
                    checkpoints.append({
                        "job_id": data.get("job_id"),
                        "status": data.get("status"),
                        "total_rows": data.get("total_rows", 0),
                        "last_processed_index": data.get("last_processed_index", 0),
                        "created_at": data.get("created_at"),
                        "last_checkpoint_at": data.get("last_checkpoint_at"),
                        "file_path": str(file_path)
                    })
                except Exception as e:
                    Logger.warn(f"Failed to read checkpoint {file_path.name}: {e}")
            
        except Exception as e:
            Logger.error(f"Failed to list checkpoints: {e}")
        
        return checkpoints
    
    @classmethod
    def has_incomplete_jobs(cls) -> bool:
        """Check if there are any incomplete jobs that can be resumed."""
        checkpoints = cls.list_checkpoints()
        return any(cp.get("status") in ("running", "paused") for cp in checkpoints)
    
    @classmethod
    def get_resumable(cls) -> List[Dict[str, Any]]:
        """Get only checkpoints that can be resumed (running or paused)."""
        return [
            cp for cp in cls.list_checkpoints()
            if cp.get("status") in ("running", "paused")
        ]
