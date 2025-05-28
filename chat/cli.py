"""
Command line interface for the chat application.
"""

import asyncio
import json
import logging
import click

from .config import ChatConfig, BedrockConfig, MCPConfig, KnowledgeBaseConfig, load_config
from .chat_manager import ChatManager
from .exceptions import ChatError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@click.command()
@click.option('--model', '-m', 
              help='Bedrock model ID (overrides BEDROCK_MODEL_ID env var)')
@click.option('--temperature', '-t', 
              type=float, 
              help='Temperature parameter (overrides BEDROCK_TEMPERATURE env var)')
@click.option('--max-tokens', '-mt', 
              type=int, 
              help='Maximum tokens to generate (overrides BEDROCK_MAX_TOKENS env var)')
@click.option('--mcp-command', 
              help='MCP server command (overrides MCP_COMMAND env var)')
@click.option('--mcp-args', 
              help='MCP server arguments (comma-separated, overrides MCP_ARGS env var)')
@click.option('--kb-id', 
              help='Knowledge Base ID (overrides KB_KNOWLEDGE_BASE_ID env var)')
@click.option('--max-tool-rounds', 
              type=int,
              help='Maximum number of tool calling rounds (overrides CHAT_MAX_TOOL_ROUNDS env var)')
@click.option('--disable-auto-tools', 
              is_flag=True, 
              help='Disable automatic multi-round tool calling')
@click.option('--verbose', '-v', 
              is_flag=True, 
              help='Enable verbose logging')
def chat(model, temperature, max_tokens, mcp_command, mcp_args, kb_id, max_tool_rounds, disable_auto_tools, verbose):
    """Start an interactive chat session with Bedrock Converse API and MCP tools."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load base configuration from environment variables
        config = load_config()
        
        # Override with command line arguments if provided
        if model:
            config.bedrock.default_model_id = model
        if temperature is not None:
            config.bedrock.temperature = temperature
        if max_tokens is not None:
            config.bedrock.max_tokens = max_tokens
        if mcp_command:
            config.mcp.command = mcp_command
        if mcp_args:
            config.mcp.args = [arg.strip() for arg in mcp_args.split(',')]
        if kb_id:
            config.knowledge_base.knowledge_base_id = kb_id
        if max_tool_rounds is not None:
            config.max_tool_rounds = max_tool_rounds
        if disable_auto_tools:
            config.enable_auto_tool_calling = False
            
        # Use the model from config for display
        model_id = config.bedrock.default_model_id
        
    except ValueError as e:
        click.echo(f"❌ Configuration Error: {str(e)}")
        click.echo("\nPlease set the required environment variables:")
        click.echo("- AWS_ACCESS_KEY_ID")
        click.echo("- AWS_SECRET_ACCESS_KEY") 
        click.echo("- KB_KNOWLEDGE_BASE_ID")
        click.echo("\nSee README.md for complete environment variable documentation.")
        return
    except Exception as e:
        click.echo(f"❌ Unexpected configuration error: {str(e)}")
        return
    
    asyncio.run(async_chat(config, model_id))


async def async_chat(config: ChatConfig, model_id: str):
    """Run the asynchronous chat loop."""
    click.echo(f"\nWelcome to Cassie Chatbot! (using {model_id})\n")
    click.echo("Type 'q' or 'exit' to quit")
    click.echo("Type 'clear' to clear conversation history")
    click.echo("Type 'history' to view conversation history")
    click.echo("Type 'tools' to view all tools")
    click.echo("Type 'sync' to sync tools to KB")
    click.echo("Type 'help' for help\n")
    
    
    async with ChatManager(config) as chat_manager:
        while True:
            try:
                user_input = click.prompt("User")
                
                # Handle special commands
                if user_input.lower() in ['q', 'exit']:
                    click.echo("Goodbye!")
                    break
                elif user_input.lower() == 'clear':
                    chat_manager.clear_conversation()
                    click.echo("Conversation history cleared\n")
                    continue
                elif user_input.lower() == 'history':
                    display_conversation_history(chat_manager)
                    continue
                elif user_input.lower() == 'tools':
                    await display_all_tools(chat_manager)
                    continue
                elif user_input.lower() == 'help':
                    display_help()
                    continue
                elif user_input.lower() == 'sync':
                    try:
                        click.echo("Syncing tools to knowledge base...")
                        await chat_manager.sync_tools_to_kb()
                        click.echo("✅ Tools synced successfully!\n")
                    except Exception as e:
                        click.echo(f"❌ Tool sync failed: {str(e)}\n")
                    continue
                click.echo("\nThinking...\n")
                
                # Process message
                response = await chat_manager.process_message(user_input, model_id, use_kb_tools=True)
                
                # Display response
                if response['text']:
                    click.echo(f"Assistant: {response['text']}\n")
                
                # Display usage information
                usage = response['usage']
                tool_rounds = response.get('tool_rounds', 0)
                max_rounds_reached = response.get('max_rounds_reached', False)
                
                usage_info = (
                    f"(Input tokens: {usage['input_tokens']}, "
                    f"Output tokens: {usage['output_tokens']}, "
                    f"Total tokens: {usage['total_tokens']}"
                )
                
                if tool_rounds > 0:
                    usage_info += f", Tool rounds: {tool_rounds}"
                    if max_rounds_reached:
                        usage_info += " [Max rounds reached]"
                
                usage_info += ")\n"
                click.echo(usage_info)
                
            except KeyboardInterrupt:
                click.echo("\n\nGoodbye!")
                break
            except ChatError as e:
                click.echo(f"Chat error: {str(e)}\n")
            except Exception as e:
                click.echo(f"Unexpected error occurred: {str(e)}\n")
                logger.exception("Unexpected error in chat loop")


def display_conversation_history(chat_manager: ChatManager):
    """Display the conversation history."""
    history = chat_manager.get_conversation_history()
    
    if not history:
        click.echo("No conversation history\n")
        return
    
    click.echo("=== Conversation History ===")
    for i, message in enumerate(history, 1):
        role = message['role']
        role_display = "User" if role == "user" else "Assistant"
        
        # Extract text content
        text_content = []
        for content in message.get('content', []):
            if 'text' in content:
                text_content.append(content['text'])
            elif 'toolUse' in content:
                tool_name = content['toolUse'].get('name', 'unknown')
                text_content.append(f"[Using tool: {tool_name}]")
            elif 'toolResult' in content:
                text_content.append("[Tool result]")
        
        if text_content:
            content_str = ' '.join(text_content)
            click.echo(f"{i}. {role_display}: {content_str}")
    
    click.echo(f"\nTotal {len(history)} messages\n")


async def display_all_tools(chat_manager: ChatManager):
    """Display all available tools from knowledge base."""
    try:
        click.echo("🔧 Getting all available tools...")
        
        # Get all tools from knowledge base
        all_tools = await chat_manager.get_all_kb_tools()
        tools_list = all_tools.get('tools', [])
        
        if not tools_list:
            click.echo("❌ No tools found")
            return
        
        click.echo(f"\n=== All Available Tools ({len(tools_list)} tools) ===")
        
        for i, tool in enumerate(tools_list, 1):
            tool_spec = tool.get('toolSpec', {})
            tool_name = tool_spec.get('name', 'unknown')
            tool_desc = tool_spec.get('description', 'No description')
            
            click.echo(f"\n{i}. 🔧 {tool_name}")
            click.echo(f"   Description: {tool_desc}")
            
            # Show input schema if available
            input_schema = tool_spec.get('inputSchema', {}).get('json', {})
            if input_schema and 'properties' in input_schema:
                properties = input_schema['properties']
                if properties:
                    click.echo(f"   Parameters: {', '.join(properties.keys())}")
        
        click.echo(f"\nTotal {len(tools_list)} tools\n")
        
    except Exception as e:
        click.echo(f"❌ Failed to get tools list: {str(e)}\n")


def display_help():
    """Display help information."""
    click.echo("\n=== Help Information ===")
    click.echo("Available commands:")
    click.echo("  q, exit    - Exit chat")
    click.echo("  clear      - Clear conversation history")
    click.echo("  history    - View detailed conversation history")
    click.echo("  tools      - View all available tools")
    click.echo("  sync       - Sync tools to knowledge base")
    click.echo("  help       - Show this help information")
    click.echo("\nFeatures:")
    click.echo("  • Supports automatic multi-round tool calling")
    click.echo("  • Tool call results are automatically recorded in conversation history")
    click.echo("  • Tool calling behavior can be controlled via command line parameters")
    click.echo("  • Supports both Chinese and English interaction")
    click.echo("\nConfiguration:")
    click.echo("  • All configuration is loaded from environment variables")
    click.echo("  • Command line options override environment variables")
    click.echo("  • See README.md for complete environment variable documentation\n")


if __name__ == "__main__":
    chat() 