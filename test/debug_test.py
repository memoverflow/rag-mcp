#!/usr/bin/env python3
"""
Debug test script to understand why accuracy is 0%
"""

import asyncio
import logging
import sys
import os
from typing import Dict, List, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat.config import ChatConfig
from chat.chat_manager import ChatManager

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def debug_single_query(query: str, use_kb_tools: bool = True):
    """Debug a single query to see what's happening."""
    print(f"\n{'='*60}")
    print(f"Debugging Query: {query}")
    print(f"Use KB Tools: {use_kb_tools}")
    print(f"{'='*60}")
    
    config = ChatConfig()
    
    async with ChatManager(config) as chat_manager:
        try:
            # Initialize with tools
            print("Initializing ChatManager...")
            await chat_manager.initialize(is_init_mcp=True)
            
            print("Processing message...")
            response = await chat_manager.process_message(query, use_kb_tools=use_kb_tools)
            
            print(f"\nResponse received:")
            print(f"  Success: {response is not None}")
            print(f"  Text: {response.get('text', 'No text')[:200]}...")
            print(f"  Usage: {response.get('usage', {})}")
            print(f"  Tool rounds: {response.get('tool_rounds', 0)}")
            print(f"  Stop reason: {response.get('stop_reason', 'Unknown')}")
            
            # Get conversation history
            history = chat_manager.get_conversation_history()
            print(f"\nConversation History ({len(history)} messages):")
            
            tools_used = []
            for i, message in enumerate(history):
                role = message.get('role', 'unknown')
                content = message.get('content', [])
                print(f"  Message {i+1}: Role={role}, Content length={len(str(content))}")
                
                # Look for tool usage
                for content_item in content:
                    if isinstance(content_item, dict) and 'toolUse' in content_item:
                        tool_name = content_item['toolUse'].get('name', 'unknown')
                        tool_input = content_item['toolUse'].get('input', {})
                        tools_used.append(tool_name)
                        print(f"    Tool used: {tool_name}")
                        print(f"    Tool input: {tool_input}")
            
            print(f"\nTools Used: {tools_used}")
            print(f"Unique Tools: {list(set(tools_used))}")
            
            return {
                'success': True,
                'response': response,
                'tools_used': list(set(tools_used)),
                'conversation_length': len(history)
            }
            
        except Exception as e:
            print(f"Error: {str(e)}")
            logger.exception("Query failed")
            return {
                'success': False,
                'error': str(e),
                'tools_used': [],
                'conversation_length': 0
            }


async def compare_methods(query: str):
    """Compare RAG-MCP vs Full MCP for a single query."""
    print(f"\n{'='*80}")
    print(f"COMPARING METHODS FOR: {query}")
    print(f"{'='*80}")
    
    # Test RAG-MCP
    print("\n--- Testing RAG-MCP (use_kb_tools=True) ---")
    rag_result = await debug_single_query(query, use_kb_tools=True)
    
    # Test Full MCP
    print("\n--- Testing Full MCP (use_kb_tools=False) ---")
    full_result = await debug_single_query(query, use_kb_tools=False)
    
    # Compare results
    print(f"\n--- COMPARISON ---")
    print(f"RAG-MCP Success: {rag_result['success']}")
    print(f"Full MCP Success: {full_result['success']}")
    
    if rag_result['success'] and full_result['success']:
        rag_usage = rag_result['response'].get('usage', {})
        full_usage = full_result['response'].get('usage', {})
        
        print(f"\nToken Usage:")
        print(f"  RAG-MCP: {rag_usage.get('total_tokens', 0)} tokens")
        print(f"  Full MCP: {full_usage.get('total_tokens', 0)} tokens")
        
        if full_usage.get('total_tokens', 0) > 0:
            reduction = ((full_usage.get('total_tokens', 0) - rag_usage.get('total_tokens', 0)) / 
                        full_usage.get('total_tokens', 0)) * 100
            print(f"  Token Reduction: {reduction:.1f}%")
        
        print(f"\nTools Used:")
        print(f"  RAG-MCP: {rag_result['tools_used']}")
        print(f"  Full MCP: {full_result['tools_used']}")
        
        # Calculate accuracy with expected tools (use actual tool names)
        expected_tools = ['list_directory']  # Updated to match actual tool name
        
        def calculate_accuracy(selected_tools, expected_tools):
            if not expected_tools:
                return 1.0
            if not selected_tools:
                return 0.0
            
            def normalize_tool_name(name):
                name = name.lower().strip()
                # Keep specific tool names as they are for accurate matching
                return name
            
            normalized_selected = set(normalize_tool_name(tool) for tool in selected_tools)
            normalized_expected = set(normalize_tool_name(tool) for tool in expected_tools)
            
            intersection = len(normalized_selected.intersection(normalized_expected))
            union = len(normalized_selected.union(normalized_expected))
            
            accuracy = intersection / union if union > 0 else 0.0
            
            print(f"    Debug accuracy calculation:")
            print(f"      Selected: {selected_tools} -> {normalized_selected}")
            print(f"      Expected: {expected_tools} -> {normalized_expected}")
            print(f"      Intersection: {intersection}, Union: {union}")
            
            return accuracy
        
        rag_accuracy = calculate_accuracy(rag_result['tools_used'], expected_tools)
        full_accuracy = calculate_accuracy(full_result['tools_used'], expected_tools)
        
        print(f"\nAccuracy (vs expected {expected_tools}):")
        print(f"  RAG-MCP: {rag_accuracy*100:.1f}%")
        print(f"  Full MCP: {full_accuracy*100:.1f}%")


async def main():
    """Main debug function."""
    print("MCP vs RAG-MCP Debug Test")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "List files in current directory",
        "Read test.txt file content",
        "Create a new file debug.txt"
    ]
    
    for query in test_queries:
        try:
            await compare_methods(query)
            print("\n" + "-" * 80)
            
        except Exception as e:
            print(f"Failed to test query '{query}': {str(e)}")
            logger.exception("Query test failed")
    
    print("\nDebug test completed!")


if __name__ == "__main__":
    asyncio.run(main()) 