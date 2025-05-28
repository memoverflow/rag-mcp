"""
Knowledge Base management for RAG functionality.
"""

import logging
from typing import Dict, List, Any, Optional

from .config import KnowledgeBaseConfig
from .exceptions import KnowledgeBaseError
from .retrieve import BedrockKnowledgeBaseTools, QueryResult, IngestionJobResult

logger = logging.getLogger(__name__)


class BedrockKnowledgeBase:
    """Manages Bedrock Knowledge Base operations."""
    
    def __init__(self, config: KnowledgeBaseConfig):
        """Initialize Knowledge Base with configuration."""
        self.config = config
        self._kb_tools = None
        
    @property
    def kb_tools(self) -> BedrockKnowledgeBaseTools:
        """Lazy initialization of Knowledge Base tools."""
        if self._kb_tools is None:
            try:
                self._kb_tools = BedrockKnowledgeBaseTools(
                    knowledge_base_id=self.config.knowledge_base_id,
                    data_source_id=self.config.data_source_id,
                    s3_bucket=self.config.s3_bucket
                )
            except Exception as e:
                raise KnowledgeBaseError(f"Failed to initialize Knowledge Base tools: {str(e)}")
        return self._kb_tools
    
    async def query(self, query_text: str, top_k: int = 1) -> Dict[str, Any]:
        """
        Query the knowledge base for relevant information.
        
        Args:
            query_text: Text to search for
            top_k: Number of top results to return
            
        Returns:
            Query results from knowledge base in Bedrock-compatible format
            
        Raises:
            KnowledgeBaseError: If query fails
        """
        try:
            logger.info(f"Querying knowledge base with: {query_text[:100]}...")
            
            # Use the enhanced query method
            result: QueryResult = self.kb_tools.query_semantic(query_text, max_results=top_k)
            
            # Convert to the expected format for backward compatibility
            bedrock_format = {"tools": result.tools}
            
            logger.info(f"Knowledge base returned {result.total_results} results")
            return bedrock_format
            
        except Exception as e:
            logger.error(f"Knowledge base query failed: {str(e)}")
            raise KnowledgeBaseError(f"Knowledge base query failed: {str(e)}")
    
    async def queryall(self) -> Dict[str, Any]:
        """
        Query all tools from the knowledge base.
        
        Returns:
            All tools from knowledge base in Bedrock-compatible format
            
        Raises:
            KnowledgeBaseError: If query fails
        """
        try:
            logger.info("Querying all tools from knowledge base...")
            
            # Use a broad query to get all tools
            # We use a generic query that should match most tool descriptions
            broad_query = "tool function API method service utility helper"
            
            # Query with a high max_results to get all available tools
            result: QueryResult = self.kb_tools.query_semantic(broad_query, max_results=100)
            
            # Convert to the expected format for backward compatibility
            bedrock_format = {"tools": result.tools}
            
            logger.info(f"Knowledge base returned all {result.total_results} tools")
            return bedrock_format
            
        except Exception as e:
            logger.error(f"Knowledge base queryall failed: {str(e)}")
            raise KnowledgeBaseError(f"Knowledge base queryall failed: {str(e)}")
    
    async def write_tools(self, tools: Dict[str, Any]) -> IngestionJobResult:
        """
        Write tools configuration to knowledge base.
        
        Args:
            tools: Tools configuration to write
            
        Returns:
            IngestionJobResult with job information
            
        Raises:
            KnowledgeBaseError: If write operation fails
        """
        try:
            logger.info("Writing tools to Knowledge Base...")
            result = self.kb_tools.write_tools_to_knowledge_base(tools)
            logger.info(f"Successfully wrote tools to Knowledge Base. Job ID: {result.job_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to write tools to Knowledge Base: {str(e)}")
            raise KnowledgeBaseError(f"Failed to write tools to Knowledge Base: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if knowledge base is available."""
        try:
            # Simple availability check
            return self.kb_tools is not None
        except Exception:
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get knowledge base information.
        
        Returns:
            Dictionary containing knowledge base information
        """
        try:
            return self.kb_tools.get_knowledge_base_info()
        except Exception as e:
            logger.error(f"Failed to get knowledge base info: {str(e)}")
            raise KnowledgeBaseError(f"Failed to get knowledge base info: {str(e)}")
    
    def get_data_source_info(self) -> Dict[str, Any]:
        """
        Get data source information.
        
        Returns:
            Dictionary containing data source information
        """
        try:
            return self.kb_tools.get_data_source_info()
        except Exception as e:
            logger.error(f"Failed to get data source info: {str(e)}")
            raise KnowledgeBaseError(f"Failed to get data source info: {str(e)}")
    
    async def clear_chunks(self) -> bool:
        """
        Clear all chunks in the knowledge base.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Clearing knowledge base chunks...")
            result = self.kb_tools.clear_knowledge_base_chunks()
            if result:
                logger.info("Successfully cleared knowledge base chunks")
            return result
        except Exception as e:
            logger.error(f"Failed to clear knowledge base chunks: {str(e)}")
            raise KnowledgeBaseError(f"Failed to clear knowledge base chunks: {str(e)}") 