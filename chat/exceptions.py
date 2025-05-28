"""
Custom exceptions for the chat package.
"""


class ChatError(Exception):
    """Base exception for chat-related errors."""
    pass


class MCPToolError(ChatError):
    """Raised when an MCP tool call fails."""
    pass


class BedrockError(ChatError):
    """Raised when Bedrock API calls fail."""
    pass


class KnowledgeBaseError(ChatError):
    """Raised when knowledge base operations fail."""
    pass 