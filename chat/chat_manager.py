"""
Main chat manager that orchestrates all components.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from .config import ChatConfig
from .bedrock_client import BedrockClient
from .mcp_client import MCPClient
from .knowledge_base import BedrockKnowledgeBase
from .chat_session import ChatSession
from .exceptions import ChatError, MCPToolError, BedrockError, KnowledgeBaseError

logger = logging.getLogger(__name__)


class ChatManager:
    """Main chat manager that orchestrates all components."""
    
    def __init__(self, config: Optional[ChatConfig] = None):
        """
        Initialize chat manager with configuration.
        
        Args:
            config: Chat configuration (uses default if None)
        """
        self.config = config or ChatConfig()
        self.bedrock_client = BedrockClient(self.config.bedrock)
        self.knowledge_base = BedrockKnowledgeBase(self.config.knowledge_base)
        self.session = ChatSession()
        self._tool_config = None
        
    async def initialize(self, is_init_mcp: bool = False) -> None:
        """Initialize all components."""
        try:
            # Initialize MCP client
            self._mcp_client = MCPClient(self.config.mcp)
            await self._mcp_client.connect()
            
            if is_init_mcp:
                # Get tools and convert to Bedrock format
                tools_response = await self._mcp_client.list_tools()
                print(f"tools_response: {tools_response}")
                self._tool_config = self._mcp_client.convert_tools_to_bedrock_format(tools_response.tools)
                
                # Optionally write tools to knowledge base
                await self.knowledge_base.write_tools(self._tool_config)
            
            logger.info("Chat manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chat manager: {str(e)}")
            raise ChatError(f"Failed to initialize chat manager: {str(e)}")
    
    async def sync_tools_to_kb(self) -> None:
        """Sync MCP tools to knowledge base without reinitializing the client."""
        try:
            if not hasattr(self, '_mcp_client') or self._mcp_client is None:
                raise ChatError("MCP client not initialized. Cannot sync tools.")
            
            # Get tools and convert to Bedrock format
            tools_response = await self._mcp_client.list_tools()
            print(f"tools_response: {tools_response}")
            self._tool_config = self._mcp_client.convert_tools_to_bedrock_format(tools_response.tools)
            
            # Write tools to knowledge base
            await self.knowledge_base.write_tools(self._tool_config)
            logger.info("Successfully synced tools to knowledge base")
            
        except Exception as e:
            logger.error(f"Failed to sync tools to KB: {str(e)}")
            raise ChatError(f"Failed to sync tools to KB: {str(e)}")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self._mcp_client:
                # Use a more robust cleanup approach
                try:
                    await self._mcp_client.disconnect()
                except Exception as disconnect_error:
                    logger.warning(f"Error during MCP disconnect: {str(disconnect_error)}")
                finally:
                    self._mcp_client = None
            logger.info("Chat manager cleaned up successfully")
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize(False)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def process_message(self, user_input: str, model_id: Optional[str] = None, use_kb_tools: bool = False) -> Dict[str, Any]:
        """
        Process a user message and generate response.
        
        Args:
            user_input: User input message
            model_id: Model ID to use (optional)
            use_kb_tools: Whether to use knowledge base tools instead of MCP tools
            
        Returns:
            Response information including text and usage
            
        Raises:
            ChatError: If message processing fails
        """
        try:
            # Add user message to session
            self.session.add_user_message(user_input)
            
            # Determine which tools to use
            if use_kb_tools:
                # Query knowledge base for context-specific tools
                conversation_context = self.session.get_conversation_context()
                kb_result = await self.knowledge_base.query(conversation_context, top_k=2)
                tool_config = kb_result
                
            else:
                # Query knowledge base for context-specific tools
                conversation_context = self.session.get_conversation_context()
                kb_result = await self.get_all_kb_tools()
                tool_config = kb_result
            
            # Generate response with selected tool configuration
            response = await self._generate_response_with_tools(
                model_id=model_id,
                tool_config=tool_config,
                max_tool_rounds=self.config.max_tool_rounds if self.config.enable_auto_tool_calling else 1
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            raise ChatError(f"Failed to process message: {str(e)}")
    
    async def _generate_response_with_tools(
        self, 
        model_id: Optional[str] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        max_tool_rounds: int = 5
    ) -> Dict[str, Any]:
        """
        Generate response using Bedrock with tool support and automatic multi-round tool calling.
        
        Args:
            model_id: Model ID to use
            tool_config: Tool configuration
            max_tool_rounds: Maximum number of tool calling rounds to prevent infinite loops
            
        Returns:
            Response information
        """
        total_usage = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        tool_rounds = 0
        
        while tool_rounds < max_tool_rounds:
            messages = self.session.get_messages()
            
            # Make API call to Bedrock
            response = self.bedrock_client.converse(
                messages=messages,
                model_id=model_id,
                tool_config=tool_config or self._tool_config
            )
            
            # Accumulate usage statistics
            current_usage = self.bedrock_client.get_usage_info(response)
            logger.info(f'current_usage: {current_usage}')
            for key in total_usage:
                total_usage[key] += current_usage[key]
            
            output_message = response['output']['message']
            stop_reason = response['stopReason']
            
            logger.info(f"Tool round {tool_rounds + 1}: stop_reason = {stop_reason}")
            
            # Extract text content from response
            response_text = self._extract_text_content(output_message)
            if response_text:
                self.session.add_assistant_message(response_text)
            
            # Check if we need to handle tool use
            if stop_reason == 'tool_use':
                tool_rounds += 1
                logger.info(f"Starting tool round {tool_rounds}/{max_tool_rounds}")
                
                # Handle tool use
                await self._handle_tool_use(output_message, model_id, tool_config)
                
                # Continue the loop to make another API call with tool results
                continue
            else:
                # No more tool use needed, return final response
                logger.info(f"Conversation completed after {tool_rounds} tool rounds")
                return {
                    'text': response_text,
                    'usage': total_usage,
                    'stop_reason': stop_reason,
                    'tool_rounds': tool_rounds
                }
        
        # If we reach here, we've hit the max tool rounds limit
        logger.warning(f"Reached maximum tool rounds limit ({max_tool_rounds})")
        
        # Make one final call to get a response
        # Note: When conversation history contains toolUse/toolResult blocks,
        # we must still provide tool_config even if we don't want to use tools
        messages = self.session.get_messages()
        final_response = self.bedrock_client.converse(
            messages=messages,
            model_id=model_id,
            tool_config=tool_config or self._tool_config  # Keep tool config to avoid API error
        )
        
        final_usage = self.bedrock_client.get_usage_info(final_response)
        for key in total_usage:
            total_usage[key] += final_usage[key]
        
        final_output = final_response['output']['message']
        final_text = self._extract_text_content(final_output)
        if final_text:
            self.session.add_assistant_message(final_text)
        
        return {
            'text': final_text,
            'usage': total_usage,
            'stop_reason': final_response['stopReason'],
            'tool_rounds': tool_rounds,
            'max_rounds_reached': True
        }
    
    async def _handle_tool_use(
        self, 
        output_message: Dict[str, Any], 
        model_id: Optional[str],
        tool_config: Optional[Dict[str, Any]]
    ) -> None:
        """Handle tool use requests from the model."""
        tool_requests = [
            content for content in output_message['content'] 
            if 'toolUse' in content
        ]
        
        for tool_request in tool_requests:
            tool = tool_request['toolUse']
            tool_name = tool['name']
            tool_use_id = tool['toolUseId']
            parameters = tool['input']
            
            logger.info(f"Executing tool {tool_name} with ID {tool_use_id}")
            
            # Add tool use to session
            self.session.add_tool_use(tool)
            
            try:
                print(f"self._mcp_client: {self._mcp_client}")
                # Execute tool
                result = await self._mcp_client.call_tool(tool_name, parameters)
                
                # Process result
                text_content = self._mcp_client.extract_text_content(result)
                
                if text_content:
                    try:
                        # Try to parse as JSON
                        processed_result = json.loads(text_content)
                        self.session.add_tool_result(tool_use_id, processed_result, "success")
                    except json.JSONDecodeError:
                        # Send as text if not valid JSON
                        self.session.add_tool_result(tool_use_id, text_content, "success")
                else:
                    error_msg = f"Tool {tool_name} didn't return text content"
                    self.session.add_tool_result(tool_use_id, error_msg, "error")
                    
            except MCPToolError as e:
                error_msg = f"Tool {tool_name} failed: {str(e)}"
                logger.error(error_msg)
                self.session.add_tool_result(tool_use_id, error_msg, "error")
    
    def _extract_text_content(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract text content from a message."""
        text_parts = []
        for content in message.get('content', []):
            if 'text' in content:
                text_parts.append(content['text'])
        return ''.join(text_parts) if text_parts else None
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the current conversation history."""
        return self.session.get_messages()
    
    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self.session.clear()
    
    def get_message_count(self) -> int:
        """Get the number of messages in the conversation."""
        return self.session.get_message_count()
    
    async def get_all_kb_tools(self) -> Dict[str, Any]:
        """
        Get all tools from the knowledge base.
        
        Returns:
            All tools from knowledge base
            
        Raises:
            ChatError: If getting tools fails
        """
        try:
            return await self.knowledge_base.queryall()
        except Exception as e:
            logger.error(f"Failed to get all KB tools: {str(e)}")
            raise ChatError(f"Failed to get all KB tools: {str(e)}") 