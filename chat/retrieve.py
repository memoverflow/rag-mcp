"""
Bedrock Knowledge Base retrieval tools for RAG functionality.
Migrated and refactored from the original retrieve.py.
"""

import json
import boto3
import os
import tempfile
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .exceptions import KnowledgeBaseError

logger = logging.getLogger(__name__)


@dataclass
class IngestionJobResult:
    """Result of an ingestion job."""
    job_id: str
    status: str
    response: Dict[str, Any]


@dataclass
class QueryResult:
    """Result of a knowledge base query."""
    tools: List[Dict[str, Any]]
    total_results: int


class BedrockKnowledgeBaseTools:
    """
    Enhanced Bedrock Knowledge Base tools with improved error handling and logging.
    """
    
    def __init__(
        self, 
        knowledge_base_id: str, 
        data_source_id: str, 
        s3_bucket: str, 
        s3_prefix: str = "kb-data/",
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize Bedrock Knowledge Base tools.

        Args:
            knowledge_base_id: Bedrock Knowledge Base ID
            data_source_id: Bedrock Data Source ID
            s3_bucket: S3 bucket name for data source
            s3_prefix: S3 prefix for data source files
            region_name: AWS region name
            aws_access_key_id: AWS access key ID (optional)
            aws_secret_access_key: AWS secret access key (optional)
        """
        self.knowledge_base_id = knowledge_base_id
        self.data_source_id = data_source_id
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.region_name = region_name
        
        # Initialize AWS clients
        self._init_clients(aws_access_key_id, aws_secret_access_key)
        
    def _init_clients(self, aws_access_key_id: Optional[str], aws_secret_access_key: Optional[str]):
        """Initialize AWS clients with optional credentials."""
        try:
            client_kwargs = {"region_name": self.region_name}
            
            if aws_access_key_id and aws_secret_access_key:
                client_kwargs.update({
                    "aws_access_key_id": aws_access_key_id,
                    "aws_secret_access_key": aws_secret_access_key
                })
            
            self.bedrock_client = boto3.client(
                service_name="bedrock-agent-runtime", 
                **client_kwargs
            )
            self.bedrock_agent_client = boto3.client(
                "bedrock-agent", 
                **client_kwargs
            )
            self.s3_client = boto3.client("s3", **client_kwargs)
            
            logger.info("Successfully initialized AWS clients")
            
        except Exception as e:
            raise KnowledgeBaseError(f"Failed to initialize AWS clients: {str(e)}")

    def clear_knowledge_base_chunks(self) -> bool:
        """
        Clear all chunks in the Knowledge Base by deleting S3 data source files.

        Returns:
            True if clearing was successful, False otherwise
            
        Raises:
            KnowledgeBaseError: If clearing fails
        """
        try:
            logger.info(f"Clearing Knowledge Base chunks from s3://{self.s3_bucket}/{self.s3_prefix}")
            
            # List all objects in the S3 prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket, 
                Prefix=self.s3_prefix
            )
            
            if "Contents" not in response:
                logger.info(f"No objects found in s3://{self.s3_bucket}/{self.s3_prefix}")
                return True
                
            # Delete all objects
            objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
            self.s3_client.delete_objects(
                Bucket=self.s3_bucket, 
                Delete={"Objects": objects}
            )
            
            logger.info(f"Cleared {len(objects)} objects from s3://{self.s3_bucket}/{self.s3_prefix}")
            
            # Wait for deletion to propagate (handle eventual consistency)
            for obj in objects:
                try:
                    self.s3_client.get_waiter("object_not_exists").wait(
                        Bucket=self.s3_bucket, 
                        Key=obj["Key"],
                        WaiterConfig={'Delay': 1, 'MaxAttempts': 30}
                    )
                except Exception as e:
                    logger.warning(f"Failed to wait for object deletion {obj['Key']}: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing Knowledge Base chunks: {str(e)}")
            raise KnowledgeBaseError(f"Failed to clear Knowledge Base chunks: {str(e)}")

    def write_tools_to_knowledge_base(self, tools_data: Dict[str, Any]) -> IngestionJobResult:
        """
        Clear Knowledge Base and write new tools data.

        Args:
            tools_data: Dictionary containing tool definitions in format {"tools": [...]}

        Returns:
            IngestionJobResult with job information
            
        Raises:
            KnowledgeBaseError: If writing fails
            ValueError: If tools_data format is invalid
        """
        # Validate input
        if not isinstance(tools_data, dict) or "tools" not in tools_data:
            raise ValueError("Invalid tools_data format: must contain 'tools' key")
            
        if not tools_data["tools"]:
            raise ValueError("Invalid tools_data format: 'tools' list cannot be empty")

        try:
            # Clear existing chunks
            if not self.clear_knowledge_base_chunks():
                raise KnowledgeBaseError("Failed to clear Knowledge Base chunks")

            # Create temporary JSONL file
            temp_file_path = self._create_temp_jsonl_file(tools_data["tools"])
            
            try:
                # Upload to S3
                s3_key = self._upload_to_s3(temp_file_path)
                
                # Start ingestion job
                response = self._start_ingestion_job()
                ingestion_job_id = response["ingestionJob"]["ingestionJobId"]
                
                logger.info(f"Started ingestion job: {ingestion_job_id}")
                
                # Wait for completion
                status = self.wait_for_ingestion_job(ingestion_job_id)
                
                return IngestionJobResult(
                    job_id=ingestion_job_id,
                    status=status,
                    response=response
                )
                
            finally:
                # Clean up temporary file
                self._cleanup_temp_file(temp_file_path)
                
        except Exception as e:
            logger.error(f"Error writing tools to Knowledge Base: {str(e)}")
            raise KnowledgeBaseError(f"Failed to write tools to Knowledge Base: {str(e)}")

    def _create_temp_jsonl_file(self, tools: List[Dict[str, Any]]) -> str:
        """Create a temporary JSONL file with tools data."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", 
                suffix=".jsonl", 
                delete=False, 
                encoding="utf-8"
            ) as f:
                for tool in tools:
                    # Write each tool as a JSONL line with ensure_ascii=False for Chinese characters
                    f.write(json.dumps(tool, ensure_ascii=False) + "\n")
                temp_file_path = f.name
                
            logger.debug(f"Created temporary JSONL file: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            raise KnowledgeBaseError(f"Failed to create temporary JSONL file: {str(e)}")

    def _upload_to_s3(self, file_path: str) -> str:
        """Upload file to S3 and return the S3 key."""
        try:
            s3_key = f"{self.s3_prefix}{os.path.basename(file_path)}"
            self.s3_client.upload_file(file_path, self.s3_bucket, s3_key)
            
            logger.info(f"Uploaded file to s3://{self.s3_bucket}/{s3_key}")
            
            # Verify file exists in S3
            self.s3_client.get_waiter("object_exists").wait(
                Bucket=self.s3_bucket, 
                Key=s3_key,
                WaiterConfig={'Delay': 1, 'MaxAttempts': 30}
            )
            
            logger.info(f"Confirmed file exists: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            raise KnowledgeBaseError(f"Failed to upload file to S3: {str(e)}")

    def _start_ingestion_job(self) -> Dict[str, Any]:
        """Start an ingestion job."""
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id
            )
            return response
            
        except Exception as e:
            raise KnowledgeBaseError(f"Failed to start ingestion job: {str(e)}")

    def _cleanup_temp_file(self, file_path: str):
        """Clean up temporary file."""
        try:
            os.remove(file_path)
            logger.debug(f"Deleted temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {str(e)}")

    def wait_for_ingestion_job(
        self, 
        ingestion_job_id: str, 
        timeout: int = 600, 
        poll_interval: int = 5
    ) -> str:
        """
        Wait for the ingestion job to complete and return its status.

        Args:
            ingestion_job_id: ID of the ingestion job
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds

        Returns:
            Final status of the ingestion job
            
        Raises:
            KnowledgeBaseError: If job fails
            TimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.bedrock_agent_client.get_ingestion_job(
                    knowledgeBaseId=self.knowledge_base_id,
                    dataSourceId=self.data_source_id,
                    ingestionJobId=ingestion_job_id
                )
                
                status = response["ingestionJob"]["status"]
                
                if status == "COMPLETE":
                    logger.info(f"Ingestion job {ingestion_job_id} completed successfully")
                    return status
                elif status == "FAILED":
                    failure_reasons = response.get("failureReasons", ["Unknown error"])
                    error_msg = f"Ingestion job {ingestion_job_id} failed: {failure_reasons}"
                    logger.error(error_msg)
                    raise KnowledgeBaseError(error_msg)
                elif status == "STOPPED":
                    logger.warning(f"Ingestion job {ingestion_job_id} was stopped")
                    return status
                    
                logger.debug(f"Ingestion job {ingestion_job_id} status: {status}")
                time.sleep(poll_interval)
                
            except Exception as e:
                if isinstance(e, KnowledgeBaseError):
                    raise
                logger.error(f"Error checking ingestion job status: {str(e)}")
                raise KnowledgeBaseError(f"Failed to check ingestion job status: {str(e)}")
        
        raise TimeoutError(f"Ingestion job {ingestion_job_id} did not complete within {timeout} seconds")

    def query_semantic(self, query_text: str, max_results: int = 10) -> QueryResult:
        """
        Perform semantic query on the Knowledge Base.

        Args:
            query_text: Semantic query text, e.g., "get weather in Suzhou"
            max_results: Maximum number of results to return (top-k)

        Returns:
            QueryResult containing matching tool definitions and metadata
            
        Raises:
            KnowledgeBaseError: If query fails
        """
        try:
            logger.info(f"Performing semantic query: {query_text[:100]}...")
            
            response = self.bedrock_client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": query_text},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {"numberOfResults": max_results}
                }
            )
            
            results = []
            
            for result in response["retrievalResults"]:
                try:
                    content = json.loads(result["content"]["text"])
                    results.append(content)
                    logger.debug(f"Parsed query result: {content.get('toolSpec', {}).get('name', 'unknown')}")
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse result content: {result['content']['text'][:100]}... "
                        f"Error: {e}"
                    )
                    continue
            
            logger.info(f"Query returned {len(results)} valid results")
            
            return QueryResult(
                tools=results,
                total_results=len(results)
            )
            
        except Exception as e:
            logger.error(f"Error querying Knowledge Base: {str(e)}")
            raise KnowledgeBaseError(f"Failed to query Knowledge Base: {str(e)}")

    def get_knowledge_base_info(self) -> Dict[str, Any]:
        """
        Get information about the knowledge base.
        
        Returns:
            Dictionary containing knowledge base information
        """
        try:
            response = self.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=self.knowledge_base_id
            )
            return response["knowledgeBase"]
        except Exception as e:
            logger.error(f"Error getting knowledge base info: {str(e)}")
            raise KnowledgeBaseError(f"Failed to get knowledge base info: {str(e)}")

    def get_data_source_info(self) -> Dict[str, Any]:
        """
        Get information about the data source.
        
        Returns:
            Dictionary containing data source information
        """
        try:
            response = self.bedrock_agent_client.get_data_source(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id
            )
            return response["dataSource"]
        except Exception as e:
            logger.error(f"Error getting data source info: {str(e)}")
            raise KnowledgeBaseError(f"Failed to get data source info: {str(e)}") 