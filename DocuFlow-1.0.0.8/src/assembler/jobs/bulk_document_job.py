#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  bulk_document_job.py
Created: 2025-12-09
Author: @lewopxd

Description:
Resilient bulk document generation job with:
- Cancel/Pause/Resume support
- Checkpoint persistence for crash recovery
- Configurable retry policy
- Progress reporting via Logger
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from .base_job import BaseJob, JobResult, JobStatus

# Import checkpoint system
try:
    from .job_state import JobCheckpoint, JobStateManager
except ImportError:
    from assembler.job_state import JobCheckpoint, JobStateManager

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
        @staticmethod
        def job_start(job_id, total_items, description=""): pass
        @staticmethod
        def job_progress(current, total, item_name="", step=""): pass
        @staticmethod
        def job_item_result(item_name, status, details=None): pass
        @staticmethod
        def job_complete(summary): pass


# Default retry configuration
DEFAULT_RETRY_POLICY = {
    "max_retries": 0,
    "retry_delay_seconds": 2,
    "skip_after_max_retries": True
}


class BulkDocumentJob(BaseJob):
    """
    Resilient bulk document generation job.
    
    Features:
    - Cancellable mid-execution
    - Pausable and resumable  
    - Checkpoint-based crash recovery
    - Configurable retry per row
    - Logger integration for progress
    
    Config Structure:
    {
        "excel_config": {...},
        "template_config": {...},
        "job_config": {
            "checkpoint_interval": 10,
            "retry_policy": {
                "max_retries": 3,
                "retry_delay_seconds": 2,
                "skip_after_max_retries": true
            },
            ...
        }
    }
    """
    
    def __init__(self, config: Dict[str, Any], job_id: Optional[str] = None):
        super().__init__(config, job_id)
        
        job_config = config.get("job_config", {})
        
        # Configuration
        self._checkpoint_interval = job_config.get("checkpoint_interval", 10)
        self._retry_policy = {
            **DEFAULT_RETRY_POLICY,
            **job_config.get("retry_policy", {})
        }
        
        # State for resume
        self._resume_from_index: int = 0
        self._checkpoint: Optional[JobCheckpoint] = None
        
        # Results accumulator
        self._success_count: int = 0
        self._failure_count: int = 0
        self._skipped_count: int = 0
        self._failure_details: List[Dict] = []
        self._job_results: List[Dict] = []
    
    def validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate the job configuration."""
        config = self.config
        
        # Check required sections
        if "excel_config" not in config:
            return False, "Missing 'excel_config' in configuration"
        
        if "template_config" not in config:
            return False, "Missing 'template_config' in configuration"
        
        excel = config["excel_config"]
        if not excel.get("filePath"):
            return False, "Missing 'filePath' in excel_config"
        
        template = config["template_config"]
        if not template.get("source_path"):
            return False, "Missing 'source_path' in template_config"
        
        if not template.get("target_directory"):
            return False, "Missing 'target_directory' in template_config"
        
        return True, None
    
    def execute(self) -> JobResult:
        """
        Execute the bulk document generation job.
        
        Main loop with:
        - Cancel checking
        - Pause waiting
        - Checkpoint saving
        - Retry logic
        """
        # Import core modules here to avoid circular imports
        try:
            from core.data_sheet.data_sheet_parser import get_row_data_sheet
            from core.ms_word.replace_holders_text import generate_document_from_template
        except ImportError as e:
            return JobResult(success=False, error=f"Failed to import core modules: {e}")
        
        # Create initial checkpoint
        self._create_checkpoint()
        
        try:
            # === STEP 1: Extract data from Excel ===
            Logger.info(f"Reading data from Excel...")
            excel_config = self.config.get("excel_config", {})
            
            row_data_list = get_row_data_sheet(excel_config)
            
            if row_data_list is None:
                raise Exception("Failed to read Excel data")
            
            if not row_data_list:
                Logger.info("No rows found in specified range")
                self._delete_checkpoint()
                return JobResult(success=True, data={"total_processed": 0})
            
            total_rows = len(row_data_list)
            self._checkpoint.total_rows = total_rows
            
            # Job start logging
            Logger.job_start(
                self.job_id,
                total_rows,
                f"Processing {total_rows} rows"
            )
            
            # === STEP 2: Process rows ===
            start_index = self._resume_from_index
            
            for idx in range(start_index, total_rows):
                row_data = row_data_list[idx]
                row_index = row_data.get("row_index", idx + 1)
                
                # --- Control check: Cancel ---
                if self.is_cancelled():
                    Logger.info(f"Job cancelled at row {idx + 1}/{total_rows}")
                    self._save_checkpoint("cancelled", idx)
                    return JobResult(
                        success=False,
                        cancelled=True,
                        data=self._get_results_data()
                    )
                
                # --- Control check: Pause ---
                if not self.wait_if_paused(timeout=0.1):
                    # We're paused, save checkpoint and wait
                    Logger.info(f"Job paused at row {idx + 1}/{total_rows}")
                    self._save_checkpoint("paused", idx)
                    
                    # Block until resumed or cancelled
                    while not self.wait_if_paused(timeout=1.0):
                        if self.is_cancelled():
                            Logger.info("Job cancelled while paused")
                            return JobResult(
                                success=False,
                                cancelled=True,
                                data=self._get_results_data()
                            )
                    
                    Logger.info("Job resumed")
                    self._save_checkpoint("running", idx)
                
                # --- Process row with retry ---
                self.report_progress(idx + 1, total_rows, f"Processing row {row_index}")
                Logger.job_progress(idx + 1, total_rows, f"Row {row_index}", "Processing...")
                
                result = self._process_row_with_retry(row_data, row_index)
                self._job_results.append(result)
                
                if result.get("status") == "success":
                    self._success_count += 1
                elif result.get("status") == "skipped":
                    self._skipped_count += 1
                else:
                    self._failure_count += 1
                    self._failure_details.append({
                        "row_index": row_index,
                        "error": result.get("error", "Unknown error")
                    })
                
                Logger.job_item_result(
                    f"Row {row_index}",
                    result.get("status", "error"),
                    result
                )
                
                # --- Checkpoint save ---
                if (idx + 1) % self._checkpoint_interval == 0:
                    self._save_checkpoint("running", idx + 1)
            
            # === STEP 3: Complete ===
            Logger.job_complete({
                "total": total_rows,
                "success": self._success_count,
                "failed": self._failure_count,
                "skipped": self._skipped_count
            })
            
            # Delete checkpoint on success
            self._delete_checkpoint()
            
            return JobResult(
                success=self._failure_count == 0,
                data=self._get_results_data()
            )
            
        except Exception as e:
            Logger.error(f"Job failed with error: {e}")
            self._save_checkpoint("failed", self._checkpoint.last_processed_index if self._checkpoint else 0)
            return JobResult(success=False, error=str(e))
    
    def _process_row_with_retry(self, row_data: Dict, row_index: int) -> Dict[str, Any]:
        """
        Process a single row with retry logic.
        
        Args:
            row_data: The row data to process
            row_index: The row index for logging
            
        Returns:
            Result dictionary with status and details
        """
        max_retries = self._retry_policy.get("max_retries", 0)
        delay = self._retry_policy.get("retry_delay_seconds", 2)
        skip_on_fail = self._retry_policy.get("skip_after_max_retries", True)
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Check cancel before each attempt
                if self.is_cancelled():
                    return {"status": "cancelled", "row_index": row_index}
                
                # Process the row
                result = self._process_single_row(row_data, row_index)
                return result
                
            except Exception as e:
                last_error = str(e)
                
                if attempt < max_retries:
                    Logger.warn(f"Row {row_index} attempt {attempt + 1}/{max_retries + 1} failed: {e}")
                    Logger.debug(f"Retrying in {delay} seconds...")
                    
                    # Wait with cancel check
                    for _ in range(int(delay * 10)):
                        if self.is_cancelled():
                            return {"status": "cancelled", "row_index": row_index}
                        time.sleep(0.1)
                else:
                    Logger.error(f"Row {row_index} failed after {max_retries + 1} attempts: {e}")
        
        # Max retries exceeded
        if skip_on_fail:
            return {
                "status": "skipped",
                "row_index": row_index,
                "error": f"Skipped after {max_retries + 1} failed attempts: {last_error}"
            }
        else:
            return {
                "status": "failure",
                "row_index": row_index,
                "error": last_error
            }
    
    def _process_single_row(self, row_data: Dict, row_index: int) -> Dict[str, Any]:
        """
        Process a single row (actual document generation).
        
        This is a simplified version - the full logic should be extracted
        from orchestrator.py in a future refactor.
        """
        # For now, delegate to existing orchestrator logic
        # TODO: Extract row processing logic from orchestrator
        
        # Placeholder - this will be replaced with actual logic
        return {
            "status": "success",
            "row_index": row_index,
            "message": "Processed (placeholder)"
        }
    
    def _create_checkpoint(self):
        """Create initial checkpoint when job starts."""
        self._checkpoint = JobCheckpoint(
            job_id=self.job_id,
            status="running",
            config=self.config
        )
        JobStateManager.save(self._checkpoint)
    
    def _save_checkpoint(self, status: str, last_index: int):
        """Save current progress to checkpoint."""
        if self._checkpoint:
            self._checkpoint.status = status
            self._checkpoint.update_progress(
                last_index,
                self._success_count,
                self._failure_count,
                self._skipped_count
            )
            self._checkpoint.failure_details = self._failure_details
            self._checkpoint.job_results = self._job_results
            JobStateManager.save(self._checkpoint)
    
    def _delete_checkpoint(self):
        """Delete checkpoint on successful completion."""
        JobStateManager.delete(self.job_id)
    
    def _get_results_data(self) -> Dict[str, Any]:
        """Get current results as dictionary."""
        return {
            "job_summary": {
                "total_rows_processed": len(self._job_results),
                "success_count": self._success_count,
                "failure_count": self._failure_count,
                "skipped_count": self._skipped_count
            },
            "job_results": self._job_results,
            "failure_details": self._failure_details
        }
    
    @classmethod
    def resume_from_checkpoint(cls, job_id: str) -> Optional["BulkDocumentJob"]:
        """
        Resume a previously interrupted job from checkpoint.
        
        Args:
            job_id: The job ID to resume
            
        Returns:
            BulkDocumentJob instance ready to continue, or None if not found
        """
        checkpoint = JobStateManager.load(job_id)
        
        if not checkpoint:
            Logger.warn(f"No checkpoint found for job {job_id}")
            return None
        
        if checkpoint.status not in ("running", "paused"):
            Logger.warn(f"Checkpoint {job_id} has status '{checkpoint.status}', cannot resume")
            return None
        
        Logger.info(f"Resuming job {job_id} from row {checkpoint.last_processed_index + 1}")
        
        # Create job with original config
        job = cls(checkpoint.config, job_id)
        
        # Restore state
        job._resume_from_index = checkpoint.last_processed_index
        job._success_count = checkpoint.success_count
        job._failure_count = checkpoint.failure_count
        job._skipped_count = checkpoint.skipped_count
        job._failure_details = checkpoint.failure_details
        job._job_results = checkpoint.job_results
        job._checkpoint = checkpoint
        
        return job
