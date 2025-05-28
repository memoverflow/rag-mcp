"""
Configuration management for the chat application.
All configuration values are loaded from environment variables.
The .env file is automatically loaded from the project root.
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict
from pathlib import Path

# Auto-load .env file from project root
def load_env_file():
    """Load .env file from project root if it exists."""
    try:
        from dotenv import load_dotenv
        # Find project root (where .env should be located)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent  # Go up one level from chat/ to project root
        env_file = project_root / '.env'
        
        if env_file.exists():
            load_dotenv(env_file)
            print(f"Loaded environment variables from {env_file}")
        else:
            print(f"No .env file found at {env_file}")
    except ImportError:
        print("python-dotenv not available, skipping .env file loading")
    except Exception as e:
        print(f"Error loading .env file: {e}")

# Load .env file when module is imported
load_env_file()


@dataclass
class BedrockConfig:
    """Configuration for AWS Bedrock."""
    region_name: str = os.getenv('AWS_REGION', 'us-east-1')
    aws_access_key_id: Optional[str] = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key: Optional[str] = os.getenv('AWS_SECRET_ACCESS_KEY')
    default_model_id: str = os.getenv('BEDROCK_MODEL_ID', "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    max_tokens: int = int(os.getenv('BEDROCK_MAX_TOKENS', '4096'))
    temperature: float = float(os.getenv('BEDROCK_TEMPERATURE', '0.7'))


@dataclass
class MCPConfig:
    """Configuration for MCP server."""
    command: str = os.getenv('MCP_COMMAND', 'npx')
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.args is None:
            # Get MCP args from environment variable, fallback to default
            mcp_args_str = os.getenv('MCP_ARGS', '-y,@modelcontextprotocol/server-filesystem,/Users/xrre/Documents/SA/repos/rag-mcp')
            self.args = [arg.strip() for arg in mcp_args_str.split(',')]
        
        if self.env is None:
            self.env = {}


@dataclass
class KnowledgeBaseConfig:
    """Configuration for Knowledge Base."""
    knowledge_base_id: str = os.getenv('KB_KNOWLEDGE_BASE_ID', 'R0LR957R1P')
    data_source_id: str = os.getenv('KB_DATA_SOURCE_ID', '3WHCQFIVXB')
    s3_bucket: str = os.getenv('KB_S3_BUCKET', 'rag-mcp-s3-source')


@dataclass
class ChatConfig:
    """Main configuration class."""
    bedrock: BedrockConfig = None
    mcp: MCPConfig = None
    knowledge_base: KnowledgeBaseConfig = None
    max_tool_rounds: int = int(os.getenv('CHAT_MAX_TOOL_ROUNDS', '5'))
    enable_auto_tool_calling: bool = os.getenv('CHAT_ENABLE_AUTO_TOOLS', 'true').lower() == 'true'
    
    def __post_init__(self):
        if self.bedrock is None:
            self.bedrock = BedrockConfig()
        if self.mcp is None:
            self.mcp = MCPConfig()
        if self.knowledge_base is None:
            self.knowledge_base = KnowledgeBaseConfig()
    
    def validate(self) -> None:
        """Validate configuration and raise errors for missing required values."""
        errors = []
        
        # Check required AWS credentials
        if not self.bedrock.aws_access_key_id:
            errors.append("AWS_ACCESS_KEY_ID environment variable is required")
        if not self.bedrock.aws_secret_access_key:
            errors.append("AWS_SECRET_ACCESS_KEY environment variable is required")
        
        # Check required knowledge base configuration
        if not self.knowledge_base.knowledge_base_id:
            errors.append("KB_KNOWLEDGE_BASE_ID environment variable is required")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))


def load_config() -> ChatConfig:
    """
    Load and validate configuration from environment variables.
    
    Returns:
        ChatConfig: Validated configuration object
        
    Raises:
        ValueError: If required environment variables are missing
    """
    config = ChatConfig()
    config.validate()
    return config 