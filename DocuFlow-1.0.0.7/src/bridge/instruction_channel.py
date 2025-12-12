#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  instruction_channel.py
Created: 2025-12-09
Author: @lewopxd (refactored by AI)

Description:
Bidirectional instruction channel (UI ↔ Python).
Handles command/response communication between the UI and Python backend.
"""

from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json


@dataclass
class Message:
    """Represents a message in the instruction channel."""
    id: str
    msg: str
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "msg": self.msg,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            msg=data.get("msg", ""),
            content=data.get("content", {})
        )


@dataclass
class Response:
    """Represents a response to a message."""
    id: str
    response: str  # "ok" or "error"
    content: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "response": self.response,
            "content": self.content
        }


class InstructionChannel:
    """
    Bidirectional instruction channel for UI-Python communication.
    
    Handles:
    - Registering message handlers
    - Processing incoming messages from UI
    - Sending responses back to UI
    - Sending proactive messages to UI
    """
    
    def __init__(self):
        """Initialize the instruction channel."""
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._js_evaluator: Optional[Callable[[str], None]] = None
        self._pending_responses: Dict[str, Response] = {}
    
    def set_js_evaluator(self, evaluator: Callable[[str], None]):
        """
        Set the function that evaluates JavaScript in the UI.
        
        Args:
            evaluator: Function that takes JS code and executes it
        """
        self._js_evaluator = evaluator
    
    def register_handler(self, msg_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Register a handler for a message type.
        
        Args:
            msg_type: The message type to handle (e.g., "get_excel_structure")
            handler: Function that takes content dict and returns response dict
        """
        self._handlers[msg_type] = handler
        print(f"✓ Handler registered: {msg_type}")
    
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming message from the UI.
        
        Args:
            message: Message dictionary with id, msg, and content
            
        Returns:
            Response dictionary with id, response, and content
        """
        msg_id = message.get("id", "unknown")
        msg_type = message.get("msg", "")
        content = message.get("content", {})
        
        # Validate message structure
        if not msg_id or not msg_type:
            return Response(
                id=msg_id,
                response="error",
                content={"error": "Invalid message: missing id or msg"}
            ).to_dict()
        
        # Find handler
        handler = self._handlers.get(msg_type)
        
        if not handler:
            return Response(
                id=msg_id,
                response="error",
                content={"error": f"No handler for message type: {msg_type}"}
            ).to_dict()
        
        # Execute handler
        try:
            result = handler(content)
            return Response(
                id=msg_id,
                response="ok",
                content=result if result else {}
            ).to_dict()
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Error handling message '{msg_type}': {e}")
            
            return Response(
                id=msg_id,
                response="error",
                content={"error": str(e), "traceback": error_details}
            ).to_dict()
    
    def send_to_ui(self, msg_type: str, content: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Send a proactive message to the UI.
        
        Args:
            msg_type: Type of message to send
            content: Optional message content
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        if not self._js_evaluator:
            print("⚠️ Cannot send to UI: no JS evaluator set")
            return None
        
        message = Message(
            id=str(uuid.uuid4()),
            msg=msg_type,
            content=content or {}
        )
        
        try:
            js_code = f"window.bridgePy.receiveFromPython({json.dumps(message.to_dict())})"
            self._js_evaluator(js_code)
            return message.id
        except Exception as e:
            print(f"❌ Failed to send message to UI: {e}")
            return None
    
    def get_registered_handlers(self) -> list:
        """Get list of registered message types."""
        return list(self._handlers.keys())


# Global instance (singleton pattern)
_instruction_channel: Optional[InstructionChannel] = None


def get_instruction_channel() -> InstructionChannel:
    """Get the global InstructionChannel instance."""
    global _instruction_channel
    if _instruction_channel is None:
        _instruction_channel = InstructionChannel()
    return _instruction_channel
