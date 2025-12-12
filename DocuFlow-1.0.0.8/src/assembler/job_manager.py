#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  job_manager.py
Created: 2025-12-09
Author: @lewopxd

Description:
Central registry for managing active jobs.
Provides control API for cancel/pause/resume from UI.
"""

from typing import Dict, Optional, List, Any
import threading

# Import job classes
try:
    from .jobs.base_job import BaseJob, JobStatus
    from .job_state import JobStateManager
except ImportError:
    from assembler.jobs.base_job import BaseJob, JobStatus
    from assembler.job_state import JobStateManager

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


class JobManager:
    """
    Central registry for active jobs.
    
    Provides:
    - Job registration and tracking
    - Control API (cancel, pause, resume)
    - Status queries
    - Checkpoint discovery for resume
    
    Usage:
        # Start a job
        job = BulkDocumentJob(config)
        JobManager.register(job)
        result = job.run()
        JobManager.unregister(job.job_id)
        
        # Cancel from UI
        JobManager.cancel("job_12345abc")
        
        # List resumable jobs
        resumable = JobManager.list_resumable()
    """
    
    # Active jobs registry (thread-safe)
    _jobs: Dict[str, BaseJob] = {}
    _lock = threading.Lock()
    
    # --- Registration ---
    
    @classmethod
    def register(cls, job: BaseJob) -> bool:
        """
        Register a job for tracking.
        
        Args:
            job: The job to register
            
        Returns:
            True if registered successfully
        """
        with cls._lock:
            if job.job_id in cls._jobs:
                Logger.warn(f"Job {job.job_id} already registered")
                return False
            
            cls._jobs[job.job_id] = job
            Logger.debug(f"Job registered: {job.job_id}")
            return True
    
    @classmethod
    def unregister(cls, job_id: str) -> bool:
        """
        Remove a job from tracking.
        
        Args:
            job_id: The job ID to remove
            
        Returns:
            True if removed
        """
        with cls._lock:
            if job_id in cls._jobs:
                del cls._jobs[job_id]
                Logger.debug(f"Job unregistered: {job_id}")
                return True
            return False
    
    @classmethod
    def get(cls, job_id: str) -> Optional[BaseJob]:
        """
        Get a registered job by ID.
        
        Args:
            job_id: The job ID to find
            
        Returns:
            The job if found, None otherwise
        """
        with cls._lock:
            return cls._jobs.get(job_id)
    
    # --- Control API ---
    
    @classmethod
    def cancel(cls, job_id: str) -> Dict[str, Any]:
        """
        Cancel a running job.
        
        Args:
            job_id: The job ID to cancel
            
        Returns:
            Result dictionary with success status
        """
        job = cls.get(job_id)
        
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        if job.status not in (JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.PENDING):
            return {"success": False, "error": f"Job {job_id} cannot be cancelled (status: {job.status.value})"}
        
        result = job.cancel()
        Logger.info(f"Job {job_id} cancel requested: {result}")
        
        return {"success": result, "job_id": job_id, "action": "cancel"}
    
    @classmethod
    def pause(cls, job_id: str) -> Dict[str, Any]:
        """
        Pause a running job.
        
        Args:
            job_id: The job ID to pause
            
        Returns:
            Result dictionary with success status
        """
        job = cls.get(job_id)
        
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        if job.status != JobStatus.RUNNING:
            return {"success": False, "error": f"Job {job_id} cannot be paused (status: {job.status.value})"}
        
        result = job.pause()
        Logger.info(f"Job {job_id} pause requested: {result}")
        
        return {"success": result, "job_id": job_id, "action": "pause"}
    
    @classmethod
    def resume(cls, job_id: str) -> Dict[str, Any]:
        """
        Resume a paused job.
        
        Args:
            job_id: The job ID to resume
            
        Returns:
            Result dictionary with success status
        """
        job = cls.get(job_id)
        
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}
        
        if job.status != JobStatus.PAUSED:
            return {"success": False, "error": f"Job {job_id} cannot be resumed (status: {job.status.value})"}
        
        result = job.resume()
        Logger.info(f"Job {job_id} resume requested: {result}")
        
        return {"success": result, "job_id": job_id, "action": "resume"}
    
    # --- Status Queries ---
    
    @classmethod
    def get_status(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job.
        
        Args:
            job_id: The job ID to query
            
        Returns:
            Job info dictionary or None
        """
        job = cls.get(job_id)
        return job.get_info() if job else None
    
    @classmethod
    def list_active(cls) -> List[Dict[str, Any]]:
        """
        List all active (registered) jobs.
        
        Returns:
            List of job info dictionaries
        """
        with cls._lock:
            return [job.get_info() for job in cls._jobs.values()]
    
    @classmethod
    def list_resumable(cls) -> List[Dict[str, Any]]:
        """
        List jobs that can be resumed from checkpoints.
        
        Returns:
            List of checkpoint summaries
        """
        return JobStateManager.get_resumable()
    
    @classmethod
    def has_active_jobs(cls) -> bool:
        """Check if there are any active jobs."""
        with cls._lock:
            return len(cls._jobs) > 0
    
    @classmethod
    def has_resumable_jobs(cls) -> bool:
        """Check if there are any jobs that can be resumed."""
        return JobStateManager.has_incomplete_jobs()
    
    # --- Convenience Methods ---
    
    @classmethod
    def cancel_all(cls) -> int:
        """
        Cancel all active jobs.
        
        Returns:
            Number of jobs cancelled
        """
        count = 0
        with cls._lock:
            for job_id in list(cls._jobs.keys()):
                result = cls.cancel(job_id)
                if result.get("success"):
                    count += 1
        
        Logger.info(f"Cancelled {count} jobs")
        return count
    
    @classmethod
    def cleanup(cls):
        """
        Clean up completed/failed jobs from registry.
        Called periodically or on app close.
        """
        with cls._lock:
            completed = [
                job_id for job_id, job in cls._jobs.items()
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            ]
            
            for job_id in completed:
                del cls._jobs[job_id]
            
            if completed:
                Logger.debug(f"Cleaned up {len(completed)} finished jobs")
