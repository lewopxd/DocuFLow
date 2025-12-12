#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  logger.py
Created: 2025-12-09
Author: @lewopxd

Description:
Centralized logging system for DocuFlow.
Provides:
- Multi-level terminal logging (DEBUG, INFO, WARN, ERROR)
- Structured UI events (JOB_START, JOB_PROGRESS, ITEM_RESULT, JOB_COMPLETE)
- Optional log channel for real-time UI updates
"""

from enum import IntEnum
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import json
import sys


class LogLevel(IntEnum):
    """Log severity levels (lower = more verbose)."""
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    SILENT = 100


class UIEventType:
    """Types of structured UI events."""
    JOB_START = "JOB_START"
    JOB_PROGRESS = "JOB_PROGRESS"
    ITEM_RESULT = "ITEM_RESULT"
    JOB_COMPLETE = "JOB_COMPLETE"
    STEP_UPDATE = "STEP_UPDATE"


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    GRAY = "\033[90m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"


class DocuFlowLogger:
    """
    Centralized logger for DocuFlow.
    
    Singleton pattern - use Logger.* methods directly.
    
    Terminal Logging:
        Logger.debug("message")  → Only shown if level <= DEBUG
        Logger.info("message")   → Standard information
        Logger.warn("message")   → Warnings (yellow)
        Logger.error("message")  → Errors (red)
    
    UI Events (sent to LogChannel if connected):
        Logger.job_start(job_id, total_items, description)
        Logger.job_progress(current, total, item_name, step)
        Logger.job_item_result(item_name, status, details)
        Logger.job_complete(summary)
    """
    
    # Class-level state (singleton)
    _level: LogLevel = LogLevel.INFO
    _use_colors: bool = True
    _ui_channel: Optional[Callable[[Dict[str, Any]], None]] = None
    _current_job_id: Optional[str] = None
    _log_to_file: Optional[str] = None
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def set_level(cls, level: str | LogLevel):
        """
        Set minimum log level for terminal output.
        
        Args:
            level: "DEBUG", "INFO", "WARN", "ERROR", "SILENT" or LogLevel enum
        """
        if isinstance(level, str):
            level_map = {
                "DEBUG": LogLevel.DEBUG,
                "INFO": LogLevel.INFO,
                "WARN": LogLevel.WARN,
                "WARNING": LogLevel.WARN,
                "ERROR": LogLevel.ERROR,
                "SILENT": LogLevel.SILENT
            }
            cls._level = level_map.get(level.upper(), LogLevel.INFO)
        else:
            cls._level = level
    
    @classmethod
    def enable_colors(cls, enabled: bool = True):
        """Enable/disable ANSI colors in terminal output."""
        cls._use_colors = enabled
    
    @classmethod
    def set_ui_channel(cls, sender: Callable[[Dict[str, Any]], None]):
        """
        Connect UI channel for real-time updates.
        
        Args:
            sender: Function that sends dict to UI (from LogChannel)
        """
        cls._ui_channel = sender
    
    @classmethod
    def disable_ui_channel(cls):
        """Disconnect UI channel."""
        cls._ui_channel = None
    
    @classmethod
    def set_log_file(cls, path: Optional[str]):
        """Set file path for logging (None to disable)."""
        cls._log_to_file = path
    
    # ═══════════════════════════════════════════════════════════
    # TERMINAL LOGGING
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _format_message(cls, level: LogLevel, message: str) -> str:
        """Format log message with timestamp and level."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_str = level.name.ljust(5)
        
        if cls._use_colors:
            color = {
                LogLevel.DEBUG: Colors.GRAY,
                LogLevel.INFO: Colors.GREEN,
                LogLevel.WARN: Colors.YELLOW,
                LogLevel.ERROR: Colors.RED
            }.get(level, Colors.RESET)
            
            return f"{Colors.GRAY}{timestamp}{Colors.RESET} {color}{level_str}{Colors.RESET} {message}"
        else:
            return f"{timestamp} {level_str} {message}"
    
    @classmethod
    def _log(cls, level: LogLevel, message: str):
        """Internal log method."""
        if level >= cls._level:
            formatted = cls._format_message(level, message)
            print(formatted, file=sys.stderr if level >= LogLevel.ERROR else sys.stdout)
            
            # Also write to file if configured
            if cls._log_to_file:
                try:
                    with open(cls._log_to_file, "a", encoding="utf-8") as f:
                        # Strip colors for file
                        clean_msg = f"{datetime.now().isoformat()} {level.name} {message}\n"
                        f.write(clean_msg)
                except Exception:
                    pass
    
    @classmethod
    def debug(cls, message: str):
        """Log debug message (only if level <= DEBUG)."""
        cls._log(LogLevel.DEBUG, message)
    
    @classmethod
    def info(cls, message: str):
        """Log info message."""
        cls._log(LogLevel.INFO, message)
    
    @classmethod
    def warn(cls, message: str):
        """Log warning message."""
        cls._log(LogLevel.WARN, message)
    
    @classmethod
    def error(cls, message: str):
        """Log error message."""
        cls._log(LogLevel.ERROR, message)
    
    # ═══════════════════════════════════════════════════════════
    # UI EVENTS (Structured JSON)
    # ═══════════════════════════════════════════════════════════
    
    @classmethod
    def _send_ui_event(cls, event: Dict[str, Any]):
        """Send structured event to UI channel if connected."""
        if cls._ui_channel:
            try:
                cls._ui_channel(event)
            except Exception as e:
                cls.warn(f"Failed to send UI event: {e}")
    
    @classmethod
    def job_start(cls, job_id: str, total_items: int, description: str = ""):
        """
        Signal start of a job.
        
        Args:
            job_id: Unique job identifier
            total_items: Total items to process
            description: Human-readable job description
        """
        cls._current_job_id = job_id
        
        event = {
            "type": UIEventType.JOB_START,
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "total_items": total_items,
            "description": description or f"Procesando {total_items} elementos"
        }
        
        cls._send_ui_event(event)
        cls.info(f"🚀 Trabajo iniciado: {description or job_id} ({total_items} items)")
    
    @classmethod
    def job_progress(cls, current: int, total: int, item_name: str = "", step: str = ""):
        """
        Report job progress.
        
        Args:
            current: Current item number (1-based)
            total: Total items
            item_name: Name of current item being processed
            step: Current processing step (e.g., "Insertando imágenes...")
        """
        percentage = round((current / total) * 100) if total > 0 else 0
        
        event = {
            "type": UIEventType.JOB_PROGRESS,
            "timestamp": datetime.now().isoformat(),
            "job_id": cls._current_job_id,
            "current": current,
            "total": total,
            "percentage": percentage,
            "item_name": item_name,
            "step": step
        }
        
        cls._send_ui_event(event)
        
        # Terminal output with visual progress bar
        bar_width = 20
        filled = int(bar_width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        item_str = f" {item_name}" if item_name else ""
        step_str = f" - {step}" if step else ""
        cls.info(f"[{bar}] {current}/{total}{item_str}{step_str}")
    
    @classmethod
    def step_update(cls, step: str, details: Optional[Dict[str, Any]] = None):
        """
        Report a step within current item processing.
        
        Args:
            step: Current step description
            details: Optional additional details
        """
        event = {
            "type": UIEventType.STEP_UPDATE,
            "timestamp": datetime.now().isoformat(),
            "job_id": cls._current_job_id,
            "step": step,
            "details": details or {}
        }
        
        cls._send_ui_event(event)
        cls.debug(f"   → {step}")
    
    @classmethod
    def job_item_result(cls, item_name: str, status: str, details: Optional[Dict[str, Any]] = None):
        """
        Report result of processing a single item.
        
        Args:
            item_name: Name of the processed item
            status: "success", "warning", "error", "skipped"
            details: Additional details (files created, images found, etc.)
        """
        event = {
            "type": UIEventType.ITEM_RESULT,
            "timestamp": datetime.now().isoformat(),
            "job_id": cls._current_job_id,
            "item_name": item_name,
            "status": status,
            "details": details or {}
        }
        
        cls._send_ui_event(event)
        
        # Terminal output with icon
        icon = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "skipped": "⊘"
        }.get(status, "•")
        
        if status == "error":
            cls.error(f"{icon} {item_name}: {details.get('error', 'Error desconocido')}")
        elif status == "warning":
            cls.warn(f"{icon} {item_name}: {details.get('message', '')}")
        else:
            cls.debug(f"{icon} {item_name}")
    
    @classmethod
    def job_complete(cls, summary: Dict[str, Any]):
        """
        Signal completion of a job.
        
        Args:
            summary: Job summary with success/failed counts, duration, etc.
        """
        event = {
            "type": UIEventType.JOB_COMPLETE,
            "timestamp": datetime.now().isoformat(),
            "job_id": cls._current_job_id,
            "summary": summary
        }
        
        cls._send_ui_event(event)
        
        # Terminal output
        success = summary.get("success", 0)
        failed = summary.get("failed", 0)
        total = summary.get("total", success + failed)
        duration = summary.get("duration_seconds", 0)
        
        cls.info(f"🏁 Trabajo completado: {success}/{total} exitosos, {failed} fallidos ({duration}s)")
        
        cls._current_job_id = None


# ═══════════════════════════════════════════════════════════════════
# CONVENIENCE ALIAS
# ═══════════════════════════════════════════════════════════════════

Logger = DocuFlowLogger
"""Convenience alias for DocuFlowLogger."""
