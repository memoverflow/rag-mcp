#!/usr/bin/env python3
"""
Quick test to verify accuracy calculation is working
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.comprehensive_mcp_comparison_test import ComprehensiveMCPTest


async def test_accuracy_calculation():
    """Test accuracy calculation with updated tool names."""
    print("Testing Accuracy Calculation")
    print("=" * 40)
    
    test_suite = ComprehensiveMCPTest()
    
    # Test a single query
    query = "List files in current directory"
    print(f"Testing query: {query}")
    
    try:
        result = await test_suite.run_single_query_comparison(query)
        
        if result['comparison']['valid_comparison']:
            comp = result['comparison']
            print(f"\nResults:")
            print(f"RAG-MCP Tools Used: {comp['rag_tools_used']}")
            print(f"Full MCP Tools Used: {comp['full_tools_used']}")
            print(f"Token Reduction: {comp['token_reduction_percentage']:.1f}%")
            print(f"Response Time Difference: {comp['time_difference_seconds']:.2f}s")
            
            # Check if tools were actually used
            if comp['rag_tools_used'] or comp['full_tools_used']:
                print("\n✓ Tools were successfully detected!")
            else:
                print("\n⚠ No tools detected - this might indicate an issue")
                
        else:
            print(f"Comparison failed: {result['comparison']['reason']}")
            
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_comprehensive_with_updated_queries():
    """Test the comprehensive test with updated queries."""
    print("\n" + "=" * 60)
    print("Testing Comprehensive Test with Updated Queries")
    print("=" * 60)
    
    test_suite = ComprehensiveMCPTest()
    
    # Use only first 3 queries for quick test
    quick_queries = test_suite._get_default_test_queries()[:3]
    
    print(f"Testing {len(quick_queries)} queries:")
    for i, query in enumerate(quick_queries):
        print(f"  {i+1}. {query['query']} (expected: {query['expected_tools']})")
    
    try:
        results = await test_suite.run_comprehensive_test(quick_queries)
        
        print(f"\nTest Results:")
        metrics = results['comparison_metrics']
        print(f"RAG-MCP Accuracy: {metrics['rag_mcp_accuracy']*100:.1f}%")
        print(f"Full MCP Accuracy: {metrics['full_mcp_accuracy']*100:.1f}%")
        print(f"Token Reduction: {metrics['token_reduction_percentage']:.1f}%")
        print(f"RAG-MCP Success Rate: {metrics['rag_mcp_success_rate']*100:.1f}%")
        print(f"Full MCP Success Rate: {metrics['full_mcp_success_rate']*100:.1f}%")
        
        if metrics['rag_mcp_accuracy'] > 0 or metrics['full_mcp_accuracy'] > 0:
            print("\n✓ Accuracy calculation is now working!")
        else:
            print("\n⚠ Accuracy is still 0% - need further investigation")
            
    except Exception as e:
        print(f"Comprehensive test failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function."""
    print("Quick Accuracy Test for MCP vs RAG-MCP")
    print("=" * 50)
    
    # Test 1: Single query comparison
    await test_accuracy_calculation()
    
    # Test 2: Comprehensive test with updated queries
    await test_comprehensive_with_updated_queries()
    
    print("\nQuick test completed!")


if __name__ == "__main__":
    asyncio.run(main()) 