"""
AWS Bedrock client for conversation management.
"""

import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional

from .config import BedrockConfig
from .exceptions import BedrockError

logger = logging.getLogger(__name__)


class BedrockClient:
    """AWS Bedrock client for handling conversations."""
    
    def __init__(self, config: BedrockConfig):
        """Initialize Bedrock client with configuration."""
        self.config = config
        self._client = None
        
    @property
    def client(self):
        """Lazy initialization of Bedrock client."""
        if self._client is None:
            try:
                self._client = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=self.config.region_name,
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key
                )
            except Exception as e:
                raise BedrockError(f"Failed to initialize Bedrock client: {str(e)}")
        return self._client
    
    def converse(
        self, 
        messages: List[Dict[str, Any]], 
        model_id: Optional[str] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Send a conversation request to Bedrock.
        
        Args:
            messages: List of conversation messages
            model_id: Model ID to use (defaults to config default)
            tool_config: Tool configuration for function calling
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response generation
            
        Returns:
            Response from Bedrock API
            
        Raises:
            BedrockError: If the API call fails
        """
        try:
            request_params = {
                'modelId': model_id or self.config.default_model_id,
                'messages': messages,
                'inferenceConfig': {
                    'maxTokens': max_tokens or self.config.max_tokens,
                    'temperature': temperature or self.config.temperature
                }
            }
            
            if tool_config:
                request_params['toolConfig'] = tool_config
                
            logger.info(f"Sending request to Bedrock with model {request_params['modelId']}")
            response = self.client.converse(**request_params)
            
            return response
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            logger.error(f"Bedrock API error: {error_message}")
            raise BedrockError(f"Bedrock API error: {error_message}")
        except Exception as e:
            logger.error(f"Unexpected error in Bedrock conversation: {str(e)}")
            raise BedrockError(f"Unexpected error: {str(e)}")
    
    def get_usage_info(self, response: Dict[str, Any]) -> Dict[str, int]:
        """Extract usage information from Bedrock response."""
        usage = response.get('usage', {})
        return {
            'input_tokens': usage.get('inputTokens', 0),
            'output_tokens': usage.get('outputTokens', 0),
            'total_tokens': usage.get('totalTokens', 0)
        } 