#!/usr/bin/env python3
"""
Simple test runner for MCP vs RAG-MCP comparison

Usage:
    python test/run_mcp_comparison.py --mode [quick|full|single]
    python test/run_mcp_comparison.py --query "your custom query"
"""

import asyncio
import argparse
import sys
import os
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comprehensive_mcp_comparison_test import ComprehensiveMCPTest


def get_quick_test_queries() -> List[Dict[str, Any]]:
    """Get a small set of queries for quick testing."""
    return [
        {
            'query': 'List files in current directory',
            'expected_tools': ['filesystem'],
            'category': 'file_list'
        },
        {
            'query': 'Read README.md file',
            'expected_tools': ['filesystem'],
            'category': 'file_read'
        },
        {
            'query': 'Create a test file',
            'expected_tools': ['filesystem'],
            'category': 'file_create'
        }
    ]


async def run_quick_test():
    """Run a quick comparison test with 3 queries."""
    print("Running Quick MCP Comparison Test (3 queries)")
    print("-" * 50)
    
    test_suite = ComprehensiveMCPTest()
    queries = get_quick_test_queries()
    
    results = await test_suite.run_comprehensive_test(queries)
    
    print("\nQuick Test Summary:")
    metrics = results['comparison_metrics']
    print(f"Token Reduction: {metrics['token_reduction_percentage']:.1f}%")
    print(f"RAG-MCP Success Rate: {metrics['rag_mcp_success_rate']*100:.1f}%")
    print(f"Full MCP Success Rate: {metrics['full_mcp_success_rate']*100:.1f}%")
    
    return results


async def run_full_test():
    """Run the complete comprehensive test."""
    print("Running Full MCP Comparison Test (10 queries)")
    print("-" * 50)
    
    test_suite = ComprehensiveMCPTest()
    results = await test_suite.run_comprehensive_test()
    
    return results


async def run_single_query_test(query: str):
    """Run test for a single custom query."""
    print(f"Running Single Query Test: '{query}'")
    print("-" * 50)
    
    test_suite = ComprehensiveMCPTest()
    result = await test_suite.run_single_query_comparison(query)
    
    if result['comparison']['valid_comparison']:
        comp = result['comparison']
        print(f"\nResults:")
        print(f"Token Reduction: {comp['token_reduction_percentage']:.1f}%")
        print(f"RAG-MCP Tokens: {comp['rag_tokens']}")
        print(f"Full MCP Tokens: {comp['full_tokens']}")
        print(f"Response Time Difference: {comp['time_difference_seconds']:.2f}s")
        print(f"RAG-MCP Tools Used: {comp['rag_tools_used']}")
        print(f"Full MCP Tools Used: {comp['full_tools_used']}")
    else:
        print(f"Comparison failed: {result['comparison']['reason']}")
    
    return result


async def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(description='MCP vs RAG-MCP Comparison Test Runner')
    parser.add_argument('--mode', choices=['quick', 'full', 'single'], default='quick',
                       help='Test mode: quick (3 queries), full (10 queries), or single query')
    parser.add_argument('--query', type=str, help='Custom query for single mode')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'quick':
            await run_quick_test()
        elif args.mode == 'full':
            await run_full_test()
        elif args.mode == 'single':
            if not args.query:
                print("Error: --query is required for single mode")
                return 1
            await run_single_query_test(args.query)
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Ensure test directory exists
    os.makedirs("test", exist_ok=True)
    
    # Run the test
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 