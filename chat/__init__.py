"""
Chat package for AWS Bedrock Converse API with MCP tool integration.
"""

from .config import ChatConfig, BedrockConfig, MCPConfig, KnowledgeBaseConfig, load_config
from .bedrock_client import BedrockClient
from .mcp_client import MCPClient
from .knowledge_base import BedrockKnowledgeBase
from .chat_session import ChatSession
from .chat_manager import ChatManager
from .exceptions import ChatError, MCPToolError, BedrockError, KnowledgeBaseError
from .retrieve import BedrockKnowledgeBaseTools, QueryResult, IngestionJobResult
# Evaluator moved to test/ directory
# from .evaluator import RAGMCPEvaluator, EvaluationMethod, EvaluationResult, BenchmarkSummary

__all__ = [
    'ChatConfig',
    'BedrockConfig', 
    'MCPConfig',
    'KnowledgeBaseConfig',
    'load_config',
    'BedrockClient',
    'MCPClient', 
    'BedrockKnowledgeBase',
    'ChatSession',
    'ChatManager',
    'ChatError',
    'MCPToolError',
    'BedrockError', 
    'KnowledgeBaseError',
    'BedrockKnowledgeBaseTools',
    'QueryResult',
    'IngestionJobResult',
    # Evaluator classes moved to test/ directory
    # 'RAGMCPEvaluator',
    # 'EvaluationMethod',
    # 'EvaluationResult',
    # 'BenchmarkSummary',
    # 'MCPStressTester',
    # 'StressTestResult'
] 