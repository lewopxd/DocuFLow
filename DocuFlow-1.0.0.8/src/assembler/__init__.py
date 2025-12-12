# DocuFlow Assembler Module
# This package contains the job orchestration system

# Lazy imports to avoid circular dependencies
def get_orchestrator():
    """Get the orchestrator module (legacy, backward compatible)."""
    from .orchestrator import execute_bulk_document_job
    return execute_bulk_document_job

def get_job_manager():
    """Get the JobManager for controlling active jobs."""
    from .job_manager import JobManager
    return JobManager

def get_bulk_job():
    """Get the BulkDocumentJob class for resilient job execution."""
    from .jobs.bulk_document_job import BulkDocumentJob
    return BulkDocumentJob

def get_checkpoint_manager():
    """Get the JobStateManager for checkpoint operations."""
    from .job_state import JobStateManager
    return JobStateManager

__all__ = [
    'get_orchestrator',
    'get_job_manager',
    'get_bulk_job',
    'get_checkpoint_manager'
]
