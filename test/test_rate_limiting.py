#!/usr/bin/env python3
"""
Rate Limiting Test Script
"""

import asyncio
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comprehensive_mcp_comparison_test import ComprehensiveMCPTest


async def test_rate_limiting():
    """Test rate limiting functionality"""
    print("🧪 Testing Rate Limiting Functionality")
    print("=" * 50)
    
    # Create test suite
    test_suite = ComprehensiveMCPTest()
    
    # Create simplified test queries (only 2 queries)
    test_queries = [
        {
            'query': 'List files in current directory',
            'expected_tools': ['list_directory']
        },
        {
            'query': 'Create a test file test_rate_limit.txt',
            'expected_tools': ['write_file']
        }
    ]
    
    print(f"📋 Number of test queries: {len(test_queries)}")
    print(f"🔄 Number of test methods: 2 (RAG-MCP + Full MCP)")
    print(f"📞 Total calls: {len(test_queries) * 2}")
    
    # Test different delay settings
    delays = [1.0, 3.0]  # Use shorter delays for quick testing
    
    for delay in delays:
        print(f"\n⏱️  Testing delay: {delay} seconds")
        print("-" * 30)
        
        start_time = time.time()
        
        try:
            # Run test (only use first 2 queries)
            results = await test_suite.run_comprehensive_test(
                test_queries=test_queries,
                delay_between_calls=delay
            )
            
            end_time = time.time()
            actual_duration = end_time - start_time
            expected_delay_time = (len(test_queries) * 2 - 1) * delay  # Minus 1 because first call has no delay
            processing_time = actual_duration - expected_delay_time
            
            print(f"✅ Test completed")
            print(f"   Total duration: {actual_duration:.1f} seconds")
            print(f"   Delay time: {expected_delay_time:.1f} seconds")
            print(f"   Actual processing time: {processing_time:.1f} seconds")
            
            # Verify response time is correct (should not include delay)
            if 'summaries' in results:
                for method_name, summary in results['summaries'].items():
                    avg_response_time = summary.get('average_response_time', 0)
                    print(f"   {method_name} average response time: {avg_response_time:.2f}s (should not include delay)")
                    
                    # Check if response time is reasonable (should not include delay time)
                    if avg_response_time < delay * 0.8:  # Response time should be significantly less than delay time
                        print(f"   ✅ Response time measurement is correct (excludes delay)")
                    else:
                        print(f"   ⚠️  Response time may include delay time")
            
            # Verify results
            if 'summaries' in results and len(results['summaries']) == 2:
                print(f"   ✅ Successfully generated results for {len(results['summaries'])} methods")
            else:
                print(f"   ⚠️  Results incomplete")
                
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
    
    print(f"\n🎉 Rate limiting test completed!")


async def test_single_query_rate_limiting():
    """Test single query rate limiting"""
    print(f"\n🔍 Testing Single Query Rate Limiting")
    print("-" * 30)
    
    test_suite = ComprehensiveMCPTest()
    query = "List files in current directory"
    delay = 2.0
    
    print(f"Query: {query}")
    print(f"Delay: {delay} seconds")
    
    start_time = time.time()
    
    try:
        results = await test_suite.run_single_query_comparison(query, delay)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        print(f"✅ Single query test completed")
        print(f"   Total duration: {actual_duration:.1f} seconds")
        print(f"   Includes {delay} second delay")
        
        # Verify response time is correct (should not include delay)
        if results.get('comparison', {}).get('valid_comparison'):
            print(f"   ✅ Successfully generated comparison results")
            
            rag_time = results.get('rag_mcp', {}).get('response_time', 0)
            full_time = results.get('full_mcp', {}).get('response_time', 0)
            
            print(f"   RAG-MCP response time: {rag_time:.2f}s")
            print(f"   Full MCP response time: {full_time:.2f}s")
            
            # Check if response time is reasonable (should not include delay time)
            if rag_time < delay * 0.8 and full_time < delay * 0.8:
                print(f"   ✅ Response time measurement is correct (excludes delay)")
            else:
                print(f"   ⚠️  Response time may include delay time")
        else:
            print(f"   ⚠️  Comparison results invalid")
            
    except Exception as e:
        print(f"❌ Single query test failed: {str(e)}")


async def main():
    """Main function"""
    print("🚀 Starting Rate Limiting Test")
    
    try:
        # Test rate limiting in benchmark tests
        await test_rate_limiting()
        
        # Test rate limiting in single query
        await test_single_query_rate_limiting()
        
        print(f"\n✨ All tests completed!")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Error occurred during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 