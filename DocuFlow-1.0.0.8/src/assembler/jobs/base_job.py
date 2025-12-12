#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  base_job.py
Created: 2025-12-09
Author: @lewopxd (refactored by AI)

Description:
Abstract base class for all DocuFlow jobs.
Provides a standard interface for job execution, cancellation,
pause/resume, and progress reporting.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import uuid
from datetime import datetime


class JobStatus(Enum):
    """Possible states for a job."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobProgress:
    """Represents the current progress of a job."""
    current_step: int = 0
    total_steps: int = 0
    message: str = ""
    percentage: float = 0.0
    
    def update(self, current: int, total: int, message: str = ""):
        """Updates progress values."""
        self.current_step = current
        self.total_steps = total
        self.message = message
        self.percentage = (current / total * 100) if total > 0 else 0.0


@dataclass
class JobResult:
    """Result of a job execution."""
    success: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: int = 0
    cancelled: bool = False


class BaseJob(ABC):
    """
    Abstract base class for all DocuFlow jobs.
    
    Provides:
    - Unique job ID generation
    - Cancel/Pause/Resume control
    - Progress tracking
    - Standard execution interface
    
    Subclasses must implement:
    - execute(): Main job logic
    - validate_config(): Configuration validation
    """
    
    def __init__(self, config: Dict[str, Any], job_id: Optional[str] = None):
        """
        Initialize a new job.
        
        Args:
            config: Job configuration dictionary
            job_id: Optional custom job ID (auto-generated if not provided)
        """
        self.job_id = job_id or f"job_{uuid.uuid4().hex[:8]}"
        self.config = config
        self.status = JobStatus.PENDING
        self.progress = JobProgress()
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        
        # Control events for cancellation and pause
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        
        # Optional progress callback
        self._on_progress: Optional[Callable[[JobProgress], None]] = None
    
    @abstractmethod
    def execute(self) -> JobResult:
        """
        Execute the job.
        
        Must be implemented by subclasses.
        Should check is_cancelled() and wait_if_paused() periodically.
        
        Returns:
            JobResult with execution outcome
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> tuple[bool, Optional[str]]:
        """
        Validate the job configuration before execution.
        
        Must be implemented by subclasses.
        
        Returns:
            (is_valid, error_message)
        """
        pass
    
    def run(self) -> JobResult:
        """
        Run the job with proper lifecycle management.
        
        Handles validation, status updates, and timing.
        Prefer calling this over execute() directly.
        
        Returns:
            JobResult with execution outcome
        """
        # Validate configuration
        is_valid, error = self.validate_config()
        if not is_valid:
            self.status = JobStatus.FAILED
            return JobResult(success=False, error=error or "Invalid configuration")
        
        # Start execution
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now()
        
        try:
            result = self.execute()
            
            if self.is_cancelled():
                self.status = JobStatus.CANCELLED
                result.cancelled = True
            elif result.success:
                self.status = JobStatus.COMPLETED
            else:
                self.status = JobStatus.FAILED
                
        except Exception as e:
            self.status = JobStatus.FAILED
            result = JobResult(success=False, error=str(e))
        
        self.finished_at = datetime.now()
        
        if self.started_at:
            result.duration_ms = int((self.finished_at - self.started_at).total_seconds() * 1000)
        
        return result
    
    # --- Control Methods ---
    
    def cancel(self) -> bool:
        """
        Request cancellation of the job.
        
        The job should check is_cancelled() periodically and exit gracefully.
        
        Returns:
            True if cancellation was requested
        """
        self._cancel_event.set()
        self.status = JobStatus.CANCELLED
        return True
    
    def pause(self) -> bool:
        """
        Pause the job.
        
        The job will block on wait_if_paused() calls.
        
        Returns:
            True if pause was initiated
        """
        if self.status == JobStatus.RUNNING:
            self._pause_event.clear()
            self.status = JobStatus.PAUSED
            return True
        return False
    
    def resume(self) -> bool:
        """
        Resume a paused job.
        
        Returns:
            True if resume was initiated
        """
        if self.status == JobStatus.PAUSED:
            self._pause_event.set()
            self.status = JobStatus.RUNNING
            return True
        return False
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_event.is_set()
    
    def wait_if_paused(self, timeout: Optional[float] = None) -> bool:
        """
        Block if the job is paused.
        
        Call this periodically in execute() to support pause functionality.
        
        Args:
            timeout: Maximum seconds to wait (None = wait forever)
            
        Returns:
            True if not paused, False if timeout expired while paused
        """
        return self._pause_event.wait(timeout=timeout)
    
    # --- Progress Methods ---
    
    def report_progress(self, current: int, total: int, message: str = ""):
        """
        Report job progress.
        
        Args:
            current: Current step number
            total: Total number of steps
            message: Optional progress message
        """
        self.progress.update(current, total, message)
        
        if self._on_progress:
            try:
                self._on_progress(self.progress)
            except Exception:
                pass  # Don't let callback errors affect job execution
    
    def set_progress_callback(self, callback: Callable[[JobProgress], None]):
        """Set a callback to receive progress updates."""
        self._on_progress = callback
    
    # --- Utility Methods ---
    
    def get_info(self) -> Dict[str, Any]:
        """Get job information as a dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": {
                "current": self.progress.current_step,
                "total": self.progress.total_steps,
                "percentage": self.progress.percentage,
                "message": self.progress.message
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.job_id} status={self.status.value}>"
