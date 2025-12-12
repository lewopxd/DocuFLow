#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  log_channel.py
Created: 2025-12-09
Author: @lewopxd (refactored by AI)

Description:
Unidirectional log streaming channel (Python → UI).
Provides real-time log updates to the UI without blocking job execution.
"""

from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
import queue
import json


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """Represents a single log entry."""
    level: LogLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    job_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "job_id": self.job_id,
            "extra": self.extra
        }


class LogChannel:
    """
    Unidirectional log streaming channel.
    
    Collects logs from Python and sends them to the UI in real-time.
    Uses a queue to decouple log production from sending.
    """
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the log channel.
        
        Args:
            max_queue_size: Maximum number of logs to buffer
        """
        self._queue: queue.Queue[LogEntry] = queue.Queue(maxsize=max_queue_size)
        self._sender: Optional[Callable[[Dict[str, Any]], None]] = None
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._log_history: List[LogEntry] = []
        self._max_history = 500
    
    def set_sender(self, sender: Callable[[Dict[str, Any]], None]):
        """
        Set the function that sends logs to the UI.
        
        Args:
            sender: Function that takes a log dict and sends it to UI
        """
        self._sender = sender
    
    def start(self):
        """Start the background log sending thread."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="LogChannel-Worker"
        )
        self._worker_thread.start()
    
    def stop(self):
        """Stop the log sending thread."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
    
    def _process_queue(self):
        """Background worker that sends queued logs to UI."""
        while self._running:
            try:
                entry = self._queue.get(timeout=0.1)
                self._send_entry(entry)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"LogChannel error: {e}")
    
    def _send_entry(self, entry: LogEntry):
        """Send a single log entry to the UI."""
        if self._sender:
            try:
                self._sender(entry.to_dict())
            except Exception as e:
                print(f"Failed to send log: {e}")
        
        # Also store in history
        self._log_history.append(entry)
        if len(self._log_history) > self._max_history:
            self._log_history = self._log_history[-self._max_history:]
    
    # --- Public Logging Methods ---
    
    def log(self, level: LogLevel, message: str, job_id: Optional[str] = None, **extra):
        """
        Add a log entry to the queue.
        
        Args:
            level: Log severity level
            message: Log message
            job_id: Optional job ID this log is associated with
            **extra: Additional data to include
        """
        entry = LogEntry(
            level=level,
            message=message,
            job_id=job_id,
            extra=extra
        )
        
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            # Drop oldest log if queue is full
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(entry)
            except queue.Empty:
                pass
    
    def debug(self, message: str, job_id: Optional[str] = None, **extra):
        """Log a debug message."""
        self.log(LogLevel.DEBUG, message, job_id, **extra)
    
    def info(self, message: str, job_id: Optional[str] = None, **extra):
        """Log an info message."""
        self.log(LogLevel.INFO, message, job_id, **extra)
    
    def warning(self, message: str, job_id: Optional[str] = None, **extra):
        """Log a warning message."""
        self.log(LogLevel.WARNING, message, job_id, **extra)
    
    def error(self, message: str, job_id: Optional[str] = None, **extra):
        """Log an error message."""
        self.log(LogLevel.ERROR, message, job_id, **extra)
    
    def critical(self, message: str, job_id: Optional[str] = None, **extra):
        """Log a critical message."""
        self.log(LogLevel.CRITICAL, message, job_id, **extra)
    
    def progress(self, job_id: str, current: int, total: int, message: str = ""):
        """
        Send a progress update.
        
        Args:
            job_id: Job this progress is for
            current: Current step
            total: Total steps
            message: Optional progress message
        """
        self.log(
            LogLevel.INFO,
            message or f"Progress: {current}/{total}",
            job_id=job_id,
            progress={"current": current, "total": total}
        )
    
    def get_history(self, limit: int = 100, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent log history.
        
        Args:
            limit: Maximum entries to return
            job_id: Filter by job ID (optional)
            
        Returns:
            List of log entry dictionaries
        """
        entries = self._log_history
        
        if job_id:
            entries = [e for e in entries if e.job_id == job_id]
        
        return [e.to_dict() for e in entries[-limit:]]


# Global instance (singleton pattern)
_log_channel: Optional[LogChannel] = None


def get_log_channel() -> LogChannel:
    """Get the global LogChannel instance."""
    global _log_channel
    if _log_channel is None:
        _log_channel = LogChannel()
    return _log_channel


def create_console_sender(prefix: str = "[PY→UI]") -> Callable[[Dict[str, Any]], None]:
    """
    Create a console sender for development/debugging.
    
    Prints logs to console with a prefix indicating they would go to UI.
    
    Args:
        prefix: Prefix to add to console output
        
    Returns:
        Sender function
    """
    def sender(log_dict: Dict[str, Any]):
        level = log_dict.get("level", "info").upper()
        message = log_dict.get("message", "")
        job_id = log_dict.get("job_id", "")
        extra = log_dict.get("extra", {})
        
        # Format for console
        job_str = f" [{job_id}]" if job_id else ""
        extra_str = f" {extra}" if extra else ""
        
        print(f"{prefix} {level}{job_str}: {message}{extra_str}")
    
    return sender


def create_webview_sender(window) -> Callable[[Dict[str, Any]], None]:
    """
    Create a sender that forwards logs to the UI via pywebview.
    
    Args:
        window: pywebview window instance
        
    Returns:
        Sender function
    """
    import json
    
    def sender(log_dict: Dict[str, Any]):
        try:
            # Send to JavaScript: window.bridgePy.receiveLog(log_dict)
            js_code = f"window.bridgePy && window.bridgePy.receiveLog && window.bridgePy.receiveLog({json.dumps(log_dict)})"
            window.evaluate_js(js_code)
        except Exception as e:
            print(f"[LogChannel] Failed to send to UI: {e}")
    
    return sender


def initialize_log_channel(
    window=None,
    console_fallback: bool = True,
    connect_to_logger: bool = True
) -> LogChannel:
    """
    Initialize and configure the global LogChannel.
    
    Args:
        window: pywebview window (if available)
        console_fallback: If True, print to console when no window
        connect_to_logger: If True, connect to DocuFlowLogger
        
    Returns:
        Configured LogChannel instance
    """
    channel = get_log_channel()
    
    # Set sender based on availability
    if window is not None:
        sender = create_webview_sender(window)
        channel.set_sender(sender)
        print("[LogChannel] Connected to pywebview window")
    elif console_fallback:
        sender = create_console_sender()
        channel.set_sender(sender)
        print("[LogChannel] Using console fallback (no pywebview window)")
    
    # Connect to Logger if requested
    if connect_to_logger:
        try:
            from core.logger import Logger
            
            # Create a sender that goes through the channel
            def logger_sender(event_dict: Dict[str, Any]):
                # Convert Logger events to LogChannel format
                event_type = event_dict.get("type", "")
                channel.log(
                    LogLevel.INFO,
                    f"[{event_type}] {json.dumps(event_dict)}",
                    job_id=event_dict.get("job_id")
                )
            
            Logger.set_ui_channel(logger_sender)
            print("[LogChannel] Connected to DocuFlowLogger")
        except ImportError:
            print("[LogChannel] Warning: Could not import Logger")
    
    # Start background worker
    channel.start()
    
    return channel
