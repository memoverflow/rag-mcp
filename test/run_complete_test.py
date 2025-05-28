#!/usr/bin/env python3
"""
Complete Test Runner with HTML Report Generation

Usage:
    python test/run_complete_test.py [--queries N] [--output-dir DIR]
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from current directory
from comprehensive_mcp_comparison_test import ComprehensiveMCPTest
from html_report_generator import HTMLReportGenerator
from data_validator import DataValidator


async def run_complete_test(num_queries: int = None, output_dir: str = "test", delay_between_calls: float = 5.0) -> Dict[str, Any]:
    """
    Run complete MCP vs RAG-MCP comparison test
    
    Args:
        num_queries: Number of queries to test (None = all)
        output_dir: Output directory
        delay_between_calls: LLM call interval (seconds)
        
    Returns:
        Test results
    """
    print("🚀 Starting MCP vs RAG-MCP Complete Comparison Test")
    print("=" * 60)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize test suite
    test_suite = ComprehensiveMCPTest()
    
    # Get test queries
    all_queries = test_suite._get_default_test_queries()
    if num_queries:
        test_queries = all_queries[:num_queries]
        print(f"📝 Using first {num_queries} test queries")
    else:
        test_queries = all_queries
        print(f"📝 Using all {len(test_queries)} test queries")
    
    # Display test queries
    print(f"\n📋 Test Query List:")
    for i, query in enumerate(test_queries):
        print(f"  {i+1}. {query['query']}")
        print(f"     Expected tools: {', '.join(query['expected_tools'])}")
    
    print(f"\n⏳ Starting test execution...")
    start_time = datetime.now()
    
    try:
        # Run test
        results = await test_suite.run_comprehensive_test(test_queries, delay_between_calls)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Test completed! Duration: {duration:.1f} seconds")
        
        # Display basic results
        print_basic_results(results)
        
        # Validate data quality
        print(f"\n🔍 Validating data quality...")
        validator = DataValidator()
        validation_result = validator.validate_test_results(results)
        
        if validation_result.is_valid:
            print(f"✅ Data validation passed - Quality: {validation_result.summary.get('overall_quality', 'Unknown')}")
        else:
            print(f"⚠️  Data validation found issues:")
            for error in validation_result.errors[:3]:  # Only show first 3 errors
                print(f"   • {error}")
            if len(validation_result.errors) > 3:
                print(f"   ... and {len(validation_result.errors) - 3} more errors")
        
        if validation_result.warnings:
            print(f"⚠️  Found {len(validation_result.warnings)} warnings")
        
        # Generate HTML report
        await generate_enhanced_html_report(results, output_dir)
        
        return results
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}


def print_basic_results(results: Dict[str, Any]) -> None:
    """Print basic test results"""
    print(f"\n📊 Test Results Summary:")
    print("-" * 40)
    
    test_info = results.get('test_info', {})
    comparison_metrics = results.get('comparison_metrics', {})
    
    print(f"Test time: {test_info.get('timestamp', 'Unknown')}")
    print(f"Test queries: {test_info.get('total_queries', 0)}")
    
    print(f"\n🎯 Key Metrics:")
    print(f"  Token reduction: {comparison_metrics.get('token_reduction_percentage', 0):.1f}%")
    print(f"  RAG-MCP accuracy: {comparison_metrics.get('rag_mcp_accuracy', 0)*100:.1f}%")
    print(f"  Full MCP accuracy: {comparison_metrics.get('full_mcp_accuracy', 0)*100:.1f}%")
    print(f"  RAG-MCP success rate: {comparison_metrics.get('rag_mcp_success_rate', 0)*100:.1f}%")
    print(f"  Full MCP success rate: {comparison_metrics.get('full_mcp_success_rate', 0)*100:.1f}%")
    print(f"  RAG-MCP avg response time: {comparison_metrics.get('rag_mcp_response_time', 0):.2f}s")
    print(f"  Full MCP avg response time: {comparison_metrics.get('full_mcp_response_time', 0):.2f}s")


async def generate_enhanced_html_report(results: Dict[str, Any], output_dir: str) -> None:
    """Generate enhanced HTML report"""
    print(f"\n📄 Generating HTML report...")
    
    try:
        html_generator = HTMLReportGenerator()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = os.path.join(output_dir, f"mcp_comparison_report_{timestamp}.html")
        
        html_generator.generate_report(results, html_filename)
        
        # Get absolute path
        abs_path = os.path.abspath(html_filename)
        
        print(f"✅ HTML report generated:")
        print(f"   File path: {abs_path}")
        print(f"   Browser access: file://{abs_path}")
        
        # Try to auto-open report (optional)
        try_open_report(abs_path)
        
    except Exception as e:
        print(f"❌ HTML report generation failed: {str(e)}")


def try_open_report(file_path: str) -> None:
    """Try to auto-open HTML report"""
    try:
        import webbrowser
        print(f"\n🌐 Trying to open report in browser...")
        webbrowser.open(f"file://{file_path}")
        print(f"✅ Report opened in default browser")
    except Exception as e:
        print(f"⚠️  Cannot auto-open browser: {str(e)}")
        print(f"   Please manually open in browser: file://{file_path}")


async def run_demo_test(delay_between_calls: float = 5.0) -> None:
    """Run demo test (only 3 queries)"""
    print("🎬 Running demo test")
    await run_complete_test(num_queries=3, delay_between_calls=delay_between_calls)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='MCP vs RAG-MCP Complete Comparison Test')
    parser.add_argument('--queries', type=int, help='Number of test queries (default: all)')
    parser.add_argument('--output-dir', default='test', help='Output directory (default: test)')
    parser.add_argument('--demo', action='store_true', help='Run demo test (3 queries)')
    parser.add_argument('--cleanup', action='store_true', help='Auto cleanup temporary files after test')
    parser.add_argument('--delay', type=float, default=5.0, help='LLM call interval in seconds (default: 5.0)')
    
    args = parser.parse_args()
    
    try:
        if args.demo:
            await run_demo_test(args.delay)
        else:
            await run_complete_test(args.queries, args.output_dir, args.delay)
        
        print(f"\n🎉 Test process completed!")
        
        # Provide cleanup option
        if args.cleanup:
            await cleanup_test_files(auto=True)
        else:
            await cleanup_test_files(auto=False)
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Error occurred during test: {str(e)}")
        return 1
    
    return 0


async def cleanup_test_files(auto: bool = False) -> None:
    """Cleanup test files"""
    try:
        import subprocess
        import glob
        
        # Find test files
        test_files = []
        patterns = ['test_file_*.txt', 'sample_*.txt', 'backup_*.txt']
        for pattern in patterns:
            test_files.extend(glob.glob(pattern))
        
        test_dirs = [d for d in glob.glob('test_dir_*') if os.path.isdir(d)]
        
        if not test_files and not test_dirs:
            print("✨ No test files found to cleanup")
            return
        
        if auto:
            print(f"\n🧹 Auto-cleaning test files...")
            subprocess.run(['python', 'test/cleanup_test_files.py', '--execute'], 
                         capture_output=False)
        else:
            print(f"\n💡 Found {len(test_files)} test files and {len(test_dirs)} test directories")
            print("   You can cleanup with:")
            print("   python test/cleanup_test_files.py --execute")
            
            # Ask user if they want to cleanup
            try:
                response = input("\nCleanup these files now? (y/N): ").strip().lower()
                if response in ['y', 'yes']:
                    subprocess.run(['python', 'test/cleanup_test_files.py', '--execute'], 
                                 capture_output=False)
            except (KeyboardInterrupt, EOFError):
                print("\nSkipping cleanup")
                
    except Exception as e:
        print(f"⚠️  Error during cleanup: {str(e)}")
        print("   You can manually run: python test/cleanup_test_files.py --execute")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 