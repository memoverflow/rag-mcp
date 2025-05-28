"""
MCP (Model Context Protocol) client for tool integration.
"""

import logging
from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from .config import MCPConfig
from .exceptions import MCPToolError

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client for handling tool interactions."""
    
    def __init__(self, config: MCPConfig):
        """Initialize MCP client with configuration."""
        self.config = config
        self._session = None
        self._tools = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        
    async def connect(self):
        """Connect to MCP server."""
        try:
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env
            )
            
            self._stdio_context = stdio_client(server_params)
            self._read, self._write = await self._stdio_context.__aenter__()
            
            self._session_context = ClientSession(self._read, self._write)
            self._session = await self._session_context.__aenter__()
            
            # Initialize the connection
            await self._session.initialize()
            logger.info("Successfully connected to MCP server")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {str(e)}")
            raise MCPToolError(f"Failed to connect to MCP server: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        try:
            # Close session first
            if hasattr(self, '_session_context') and self._session_context:
                try:
                    await self._session_context.__aexit__(None, None, None)
                except Exception as session_error:
                    logger.warning(f"Error closing session: {str(session_error)}")
                finally:
                    self._session_context = None
                    self._session = None
                    
            # Then close stdio connection
            if hasattr(self, '_stdio_context') and self._stdio_context:
                try:
                    # Use asyncio.wait_for to add timeout protection
                    import asyncio
                    await asyncio.wait_for(
                        self._stdio_context.__aexit__(None, None, None),
                        timeout=5.0  # 5 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("MCP stdio disconnect timed out")
                except Exception as stdio_error:
                    logger.warning(f"Error closing stdio: {str(stdio_error)}")
                finally:
                    self._stdio_context = None
                    
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.warning(f"Error during MCP disconnect: {str(e)}")
    
    async def list_tools(self):
        """List available tools from MCP server."""
        if not self._session:
            raise MCPToolError("MCP session not initialized")
            
        try:
            tools_response = await self._session.list_tools()
            self._tools = tools_response.tools
            logger.info(f"Retrieved {len(self._tools)} tools from MCP server")
            return tools_response
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {str(e)}")
            raise MCPToolError(f"Failed to list MCP tools: {str(e)}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """
        Call a specific tool with given arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            MCPToolError: If tool call fails
        """
        if not self._session:
            raise MCPToolError("MCP session not initialized")
            
        try:
            logger.info(f"Calling tool {tool_name} with arguments: {arguments}")
            result = await self._session.call_tool(tool_name, arguments=arguments)
            logger.info(f"Tool {tool_name} result: {result}")
            
            if result.isError:
                error_msg = f"Tool {tool_name} execution failed"
                logger.error(error_msg)
                raise MCPToolError(error_msg)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {str(e)}")
            raise MCPToolError(f"Failed to call tool {tool_name}: {str(e)}")
    
    def convert_tools_to_bedrock_format(self, tools: List[Any]) -> Dict[str, Any]:
        """
        Convert MCP tools to Bedrock toolSpec format.
        
        Args:
            tools: List of MCP tools
            
        Returns:
            Bedrock-compatible tool configuration
            
        Raises:
            MCPToolError: If conversion fails
        """
        try:
            bedrock_tools = []
            for tool in tools:
                tool_spec = {
                    "toolSpec": {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": {
                            "json": tool.inputSchema
                        }
                    }
                }
                bedrock_tools.append(tool_spec)
            
            return {"tools": bedrock_tools}
            
        except Exception as e:
            logger.error(f"Failed to convert tools to Bedrock format: {str(e)}")
            raise MCPToolError(f"Failed to convert tools to Bedrock format: {str(e)}")
    
    def extract_text_content(self, result) -> Optional[str]:
        """
        Extract text content from MCP tool result.
        
        Args:
            result: MCP tool result
            
        Returns:
            Extracted text content or None
        """
        for content in result.content:
            if isinstance(content, TextContent):
                return content.text
        return None 