import json
from abc import abstractmethod, ABC
from typing import List
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        raise NotImplementedError()

class SimpleChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        # Split text by newline and filter out empty lines
        return [line for line in text.split('\n') if line.strip()]

def lambda_handler(event, context):
    logger.debug('input={}'.format(json.dumps(event, ensure_ascii=False)))
    s3 = boto3.client('s3')

    # Extract relevant information from the input event
    input_files = event.get('inputFiles')
    input_bucket = event.get('bucketName')

    if not all([input_files, input_bucket]):
        raise ValueError("Missing required input parameters")
    
    output_files = []
    chunker = SimpleChunker()

    for input_file in input_files:
        content_batches = input_file.get('contentBatches', [])
        file_metadata = input_file.get('fileMetadata', {})
        original_file_location = input_file.get('originalFileLocation', {})

        processed_batches = []
        
        for batch in content_batches:
            input_key = batch.get('key')

            if not input_key:
                raise ValueError("Missing uri in content batch")
            
            # Read file from S3
            file_content = read_s3_file(s3, input_bucket, input_key)
            
            # Process content (chunking)
            chunked_content = process_content(file_content, chunker)
            
            output_key = f"Output/{input_key}"
            
            # Write processed content back to S3
            write_to_s3(s3, input_bucket, output_key, chunked_content)
            
            # Add processed batch information
            processed_batches.append({
                'key': output_key
            })
        
        # Prepare output file information
        output_file = {
            'originalFileLocation': original_file_location,
            'fileMetadata': file_metadata,
            'contentBatches': processed_batches
        }
        output_files.append(output_file)
    
    result = {'outputFiles': output_files}
    logger.debug('output={}'.format(json.dumps(result, ensure_ascii=False)))
    return result

def read_s3_file(s3_client, bucket, key):
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        # Try to parse as JSON first (for structured JSON input)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If not valid JSON, assume JSONL or plain text and return as-is
            return {'fileContents': [{'contentBody': content, 'contentType': 'text/plain', 'contentMetadata': {}}]}
    except Exception as e:
        logger.error(f"Error reading S3 file {bucket}/{key}: {str(e)}")
        raise

def write_to_s3(s3_client, bucket, key, content):
    try:
        s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(content, ensure_ascii=False).encode('utf-8'))
    except Exception as e:
        logger.error(f"Error writing to S3 {bucket}/{key}: {str(e)}")
        raise

def process_content(file_content: dict, chunker: Chunker) -> dict:
    chunked_content = {
        'fileContents': []
    }
    
    for content in file_content.get('fileContents', []):
        content_body = content.get('contentBody', '')
        content_type = content.get('contentType', 'text/plain')
        content_metadata = content.get('contentMetadata', {})
        
        # Chunk the content body by newlines
        chunks = chunker.chunk(content_body)
        
        for chunk in chunks:
            chunked_content['fileContents'].append({
                'contentType': content_type,
                'contentMetadata': content_metadata,
                'contentBody': chunk
            })
    
    return chunked_content