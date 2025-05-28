# Chat Package

An elegant object-oriented chat application that integrates AWS Bedrock Converse API, MCP (Model Context Protocol) tools, and knowledge base functionality.

## Features

- 🎯 **Object-Oriented Design**: Clear modular architecture, easy to extend and maintain
- 🔧 **MCP Tool Integration**: Supports Model Context Protocol tool calling
- 📚 **Knowledge Base Support**: Integrates AWS Bedrock knowledge base for RAG retrieval
- ⚙️ **Flexible Configuration**: All configuration loaded from environment variables
- 🛡️ **Error Handling**: Comprehensive exception handling mechanism
- 📝 **Session Management**: Intelligent conversation history management
- 🎨 **Command Line Interface**: User-friendly interactive command line tool

## Architecture Design

```
chat/
├── __init__.py          # Package initialization
├── config.py            # Configuration management
├── exceptions.py        # Custom exceptions
├── bedrock_client.py    # Bedrock client
├── mcp_client.py        # MCP client
├── knowledge_base.py    # Knowledge base management
├── chat_session.py      # Session management
├── chat_manager.py      # Main manager
├── cli.py              # Command line interface
├── main.py             # Main entry point
├── example.py          # Usage examples
└── README.md           # Documentation
```

## Environment Variables

All configuration is managed through environment variables loaded from a `.env` file. The application automatically loads environment variables from `.env` file in the project root.

### Required Variables

```bash
# AWS Bedrock Configuration (Required)
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
KB_KNOWLEDGE_BASE_ID=your_knowledge_base_id_here
```

### All Available Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here

# Bedrock Configuration
BEDROCK_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0
BEDROCK_MAX_TOKENS=4096
BEDROCK_TEMPERATURE=0.7

# MCP Server Configuration
MCP_COMMAND=npx
MCP_ARGS=-y,@modelcontextprotocol/server-filesystem,<your path>

# Knowledge Base Configuration
KB_KNOWLEDGE_BASE_ID=your_knowledge_base_id_here
KB_DATA_SOURCE_ID=your_data_source_id_here
KB_S3_BUCKET=your_s3_bucket_name_here

# Chat Configuration
CHAT_MAX_TOOL_ROUNDS=5
CHAT_ENABLE_AUTO_TOOLS=true

```

### Environment Setup

1. **Copy the sample environment file**:
   ```bash
   cp .env.sample .env
   ```

2. **Edit `.env` with your actual values**:
   ```bash
   # Edit the .env file with your editor
   nano .env
   # or
   code .env
   ```

3. **The application automatically loads `.env` file** - no additional setup needed.

## Core Components

### 1. ChatManager
Main chat manager that coordinates all components:
- Initialize and manage all clients
- Process user messages
- Coordinate tool calls
- Manage conversation flow

### 2. BedrockClient
AWS Bedrock API client:
- Handle conversation requests
- Support tool configuration
- Manage inference parameters

### 3. MCPClient
MCP protocol client:
- Connect to MCP server
- Manage tool list
- Execute tool calls

### 4. BedrockKnowledgeBase
Knowledge base management:
- Semantic search
- Context retrieval
- Tool configuration storage

### 5. ChatSession
Session history management:
- Message storage
- Format conversion
- Context building

## Installation and Usage

### Prerequisites

1. **Activate conda environment**:
   ```bash
   conda activate base
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.sample .env
   # Edit .env with your actual values
   ```

3. **Verify AWS credentials**:
   ```bash
   aws configure list
   # or ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set in .env
   ```

### Command Line Usage

```bash
# Basic usage
python -m chat.cli

# Custom parameters (override environment variables)
python -m chat.cli --model "us.anthropic.claude-3-7-sonnet-20250219-v1:0" --temperature 0.8 --verbose

# View help
python -m chat.cli --help
```

### Programmatic Usage

```python
import asyncio
from chat import ChatManager, load_config

async def main():
    # Load configuration from .env file
    config = load_config()  # Validates required env vars
    
    async with ChatManager(config) as chat_manager:
        response = await chat_manager.process_message("Hello!")
        print(response['text'])

asyncio.run(main())
```

## Configuration Details

### AWS Configuration
- `AWS_REGION`: AWS region (default: us-east-1)
- `AWS_ACCESS_KEY_ID`: AWS access key (required)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (required)

### Bedrock Configuration
- `BEDROCK_MODEL_ID`: Model ID (default: us.anthropic.claude-3-7-sonnet-20250219-v1:0)
- `BEDROCK_MAX_TOKENS`: Maximum token count (default: 4096)
- `BEDROCK_TEMPERATURE`: Temperature parameter (default: 0.7)

### MCP Configuration
- `MCP_COMMAND`: MCP server command (default: npx)
- `MCP_ARGS`: Command argument list, comma-separated (default: -y,@modelcontextprotocol/server-filesystem,/Users/xrre/Documents/SA/repos/rag-mcp)

### Knowledge Base Configuration
- `KB_KNOWLEDGE_BASE_ID`: Knowledge base ID (required)
- `KB_DATA_SOURCE_ID`: Data source ID (default: 3WHCQFIVXB)
- `KB_S3_BUCKET`: S3 bucket name (default: rag-mcp-s3-source)

### Chat Configuration
- `CHAT_MAX_TOOL_ROUNDS`: Maximum tool calling rounds (default: 5)
- `CHAT_ENABLE_AUTO_TOOLS`: Enable automatic multi-round tool calling (default: true)

## Error Handling

Includes comprehensive exception handling mechanism:

- `ChatError`: Base chat error
- `MCPToolError`: MCP tool error
- `BedrockError`: Bedrock API error
- `KnowledgeBaseError`: Knowledge base error

Configuration validation will raise `ValueError` if required environment variables are missing.

## Special Commands

Supports the following special commands in command line mode:

- `q` or `exit`: Exit chat
- `clear`: Clear conversation history
- `history`: View conversation history
- `tools`: View all available tools
- `sync`: Sync tools to knowledge base
- `help`: Show help information

## Security Best Practices

1. **Never commit `.env` file** to version control (it's in .gitignore)
2. **Use environment variables** for all sensitive configuration
3. **Use IAM roles** when running on AWS infrastructure
4. **Rotate credentials regularly**
5. **Use least privilege principle** for AWS permissions
6. **Keep `.env.sample` updated** but without actual credentials

## Notes

1. **System Prompt**: As required, Bedrock does not support system prompt, all prompts are handled through user messages
2. **Async Design**: All major operations are asynchronous and need to be used in async environment
3. **Resource Management**: Uses async context manager to ensure proper resource cleanup
4. **Logging**: Supports detailed logging, can be enabled with `--verbose`
5. **Configuration Validation**: Automatically validates required environment variables on startup
6. **Environment Loading**: Automatically loads `.env` file from project root

## Extensibility

This architecture design has good extensibility:

- Can easily add new client types
- Supports plugin-style tool integration
- Configuration system supports dynamic extension
- Exception handling mechanism can be customized

## Examples

See `example.py` file for more usage examples. 