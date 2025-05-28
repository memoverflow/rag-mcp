"""
Chat session management for conversation history.
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ChatSession:
    """Manages conversation history for Bedrock Converse API."""

    def __init__(self):
        """Initialize chat session."""
        self.messages = []
        self.user_inputs = []

    def add_user_message(self, content: str) -> None:
        """
        Add a user message to the conversation.
        
        Args:
            content: User message content
        """
        message = {"role": "user", "content": [{"text": content}]}
        self.messages.append(message)
        self.user_inputs.append(f"user: {content}")
        logger.debug(f"Added user message: {content[:100]}...")

    def add_assistant_message(self, content: str) -> None:
        """
        Add an assistant message to the conversation.
        
        Args:
            content: Assistant message content
        """
        message = {"role": "assistant", "content": [{"text": content}]}
        self.messages.append(message)
        logger.debug(f"Added assistant message: {content[:100]}...")

    def add_tool_use(self, tool_use: Dict[str, Any]) -> None:
        """
        Add a tool use request from assistant.
        
        Args:
            tool_use: Tool use configuration
        """
        message = {"role": "assistant", "content": [{"toolUse": tool_use}]}
        self.messages.append(message)
        logger.debug(f"Added tool use: {tool_use.get('name', 'unknown')}")

    def add_tool_result(self, tool_use_id: str, content: Any, status: str = "success") -> None:
        """
        Add a tool result as a user message.
        
        Args:
            tool_use_id: ID of the tool use request
            content: Tool result content
            status: Result status (success/error)
        """
        # Determine content format based on type and status
        if status == "success" and isinstance(content, str):
            try:
                # Try to parse as JSON
                json.loads(content)
                # If successful, send as text format for better compatibility
                tool_result_content = [{"text": content}]
            except json.JSONDecodeError:
                # If not valid JSON, send as text
                tool_result_content = [{"text": content}]
        elif status == "success" and isinstance(content, (dict, list)):
            # For dict/list objects, send as JSON
            tool_result_content = [{"json": content}]
        else:
            # For errors or other cases, send as text
            tool_result_content = [{"text": str(content)}]

        tool_result = {
            "toolResult": {
                "toolUseId": tool_use_id,
                "content": tool_result_content,
                "status": status
            }
        }
        
        message = {"role": "user", "content": [tool_result]}
        self.messages.append(message)
        logger.debug(f"Added tool result for {tool_use_id} with status {status}")

    def get_messages(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Returns:
            List of conversation messages
        """
        return self.messages

    def get_user_inputs(self) -> List[str]:
        """
        Get all user inputs for context building.
        
        Returns:
            List of user input strings
        """
        return self.user_inputs

    def get_conversation_context(self) -> str:
        """
        Get conversation context as a single string.
        
        Returns:
            Formatted conversation context
        """
        return "\n".join(self.user_inputs)

    def clear(self) -> None:
        """Clear the conversation history."""
        self.messages.clear()
        self.user_inputs.clear()
        logger.info("Cleared conversation history")

    def get_message_count(self) -> int:
        """Get the number of messages in the conversation."""
        return len(self.messages)

    def get_last_assistant_message(self) -> Optional[str]:
        """
        Get the last assistant message content.
        
        Returns:
            Last assistant message text or None
        """
        for message in reversed(self.messages):
            if message["role"] == "assistant":
                for content in message["content"]:
                    if "text" in content:
                        return content["text"]
        return None 