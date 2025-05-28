#!/usr/bin/env python3
"""
Comprehensive test for comparing RAG MCP and full MCP tools
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat.config import ChatConfig
from chat.chat_manager import ChatManager
from evaluator import RAGMCPEvaluator, EvaluationMethod, BenchmarkSummary

# Try to import HTML report generator
try:
    from html_report_generator import HTMLReportGenerator
except ImportError:
    print("Warning: HTML report generator not available")
    HTMLReportGenerator = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test/mcp_comparison_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ComparisonMetrics:
    """Detailed comparison metrics between RAG-MCP and Full MCP."""
    rag_mcp_tokens: int
    full_mcp_tokens: int
    token_reduction_percentage: float
    rag_mcp_accuracy: float
    full_mcp_accuracy: float
    accuracy_difference: float
    rag_mcp_response_time: float
    full_mcp_response_time: float
    time_difference: float
    rag_mcp_success_rate: float
    full_mcp_success_rate: float
    rag_mcp_tool_rounds: float
    full_mcp_tool_rounds: float


class ComprehensiveMCPTest:
    """Comprehensive test suite for MCP vs RAG-MCP comparison."""
    
    def __init__(self, config: Optional[ChatConfig] = None):
        """Initialize test suite."""
        self.config = config or ChatConfig()
        self.evaluator = RAGMCPEvaluator(self.config)
        self.test_results: List[Dict[str, Any]] = []
        
    async def run_comprehensive_test(self, test_queries: List[Dict[str, Any]] = None, delay_between_calls: float = 5.0) -> Dict[str, Any]:
        """
        Run comprehensive comparison test.
        
        Args:
            test_queries: Custom test queries (uses default if None)
            delay_between_calls: Delay in seconds between LLM calls (default: 5.0)
            
        Returns:
            Complete test results and analysis
        """
        logger.info("Starting comprehensive MCP vs RAG-MCP comparison test")
        
        # Use default test queries if none provided
        if test_queries is None:
            test_queries = self._get_default_test_queries()
        
        logger.info(f"Testing with {len(test_queries)} queries")
        logger.info(f"Rate limiting enabled: {delay_between_calls}s delay between calls")
        
        # Run benchmark for both methods
        methods = [EvaluationMethod.RAG_MCP, EvaluationMethod.ALL_TOOLS]
        summaries = await self.evaluator.run_benchmark(test_queries, methods, delay_between_calls)
        
        # Calculate detailed comparison metrics
        comparison_metrics = self._calculate_comparison_metrics(summaries)
        
        # Generate detailed analysis
        analysis = self._generate_detailed_analysis(summaries, comparison_metrics)
        
        # Prepare final results
        results = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'total_queries': len(test_queries),
                'methods_tested': [method.value for method in methods],
                'config': asdict(self.config)
            },
            'summaries': {k: asdict(v) for k, v in summaries.items()},
            'comparison_metrics': asdict(comparison_metrics),
            'analysis': analysis,
            'detailed_results': [asdict(r) for r in self.evaluator.results]
        }
        
        # Save results
        await self._save_results(results)
        
        # Generate HTML report
        await self._generate_html_report(results)
        
        # Print summary
        self._print_summary(summaries, comparison_metrics)
        
        return results
    
    async def run_single_query_comparison(self, query: str, delay_between_calls: float = 5.0) -> Dict[str, Any]:
        """
        Run detailed comparison for a single query.
        
        Args:
            query: Query to test
            delay_between_calls: Delay in seconds between LLM calls
            
        Returns:
            Detailed comparison results
        """
        logger.info(f"Running single query comparison: {query}")
        logger.info(f"Rate limiting: {delay_between_calls}s delay between calls")
        
        results = {}
        
        # Test with RAG-MCP (use_kb_tools=True)
        logger.info("Testing with RAG-MCP...")
        rag_result = await self._test_single_query(query, use_kb_tools=True)
        results['rag_mcp'] = rag_result
        
        # Add delay before second call (this delay is NOT counted in response time)
        logger.info(f"Waiting {delay_between_calls}s before next LLM call...")
        delay_start = time.time()
        await asyncio.sleep(delay_between_calls)
        delay_end = time.time()
        actual_delay = delay_end - delay_start
        logger.debug(f"Actual delay: {actual_delay:.2f}s (not counted in response time)")
        
        # Test with Full MCP (use_kb_tools=False)
        logger.info("Testing with Full MCP...")
        full_result = await self._test_single_query(query, use_kb_tools=False)
        results['full_mcp'] = full_result
        
        # Calculate comparison
        comparison = self._compare_single_results(rag_result, full_result)
        results['comparison'] = comparison
        
        return results
    
    async def _test_single_query(self, query: str, use_kb_tools: bool) -> Dict[str, Any]:
        """Test a single query with specified configuration."""
        start_time = time.time()
        
        async with ChatManager(self.config) as chat_manager:
            try:
                # Initialize with tools
                await chat_manager.initialize(is_init_mcp=True)
                
                # Process message
                response = await chat_manager.process_message(query, use_kb_tools=use_kb_tools)
                
                end_time = time.time()
                
                # Extract metrics
                usage = response.get('usage', {})
                
                result = {
                    'success': True,
                    'query': query,
                    'use_kb_tools': use_kb_tools,
                    'response_text': response.get('text', ''),
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0),
                    'response_time': end_time - start_time,
                    'tool_rounds': response.get('tool_rounds', 0),
                    'stop_reason': response.get('stop_reason', ''),
                    'selected_tools': self._extract_tools_from_history(chat_manager),
                    'conversation_length': chat_manager.get_message_count()
                }
                
            except Exception as e:
                end_time = time.time()
                logger.error(f"Query failed: {str(e)}")
                result = {
                    'success': False,
                    'query': query,
                    'use_kb_tools': use_kb_tools,
                    'error': str(e),
                    'response_time': end_time - start_time,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'tool_rounds': 0
                }
        
        return result
    
    def _extract_tools_from_history(self, chat_manager: ChatManager) -> List[str]:
        """Extract tools used from conversation history."""
        history = chat_manager.get_conversation_history()
        tools_used = []
        
        for message in history:
            for content in message.get('content', []):
                if 'toolUse' in content:
                    tool_name = content['toolUse'].get('name', 'unknown')
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
        
        return tools_used
    
    def _compare_single_results(self, rag_result: Dict[str, Any], full_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare results from single query test."""
        if not rag_result['success'] or not full_result['success']:
            return {
                'valid_comparison': False,
                'reason': 'One or both queries failed'
            }
        
        token_reduction = 0
        if full_result['total_tokens'] > 0:
            token_reduction = ((full_result['total_tokens'] - rag_result['total_tokens']) / 
                             full_result['total_tokens']) * 100
        
        time_difference = rag_result['response_time'] - full_result['response_time']
        
        return {
            'valid_comparison': True,
            'token_reduction_percentage': token_reduction,
            'rag_tokens': rag_result['total_tokens'],
            'full_tokens': full_result['total_tokens'],
            'time_difference_seconds': time_difference,
            'rag_response_time': rag_result['response_time'],
            'full_response_time': full_result['response_time'],
            'rag_tool_rounds': rag_result['tool_rounds'],
            'full_tool_rounds': full_result['tool_rounds'],
            'rag_tools_used': rag_result.get('selected_tools', []),
            'full_tools_used': full_result.get('selected_tools', []),
            'tools_overlap': len(set(rag_result.get('selected_tools', [])).intersection(
                set(full_result.get('selected_tools', []))))
        }
    
    def _calculate_comparison_metrics(self, summaries: Dict[str, BenchmarkSummary]) -> ComparisonMetrics:
        """Calculate detailed comparison metrics."""
        rag_summary = summaries.get(EvaluationMethod.RAG_MCP.value)
        full_summary = summaries.get(EvaluationMethod.ALL_TOOLS.value)
        
        if not rag_summary or not full_summary:
            raise ValueError("Missing summary data for comparison")
        
        # Calculate token reduction
        token_reduction = 0
        if full_summary.average_total_tokens > 0:
            token_reduction = ((full_summary.average_total_tokens - rag_summary.average_total_tokens) / 
                             full_summary.average_total_tokens) * 100
        
        # Calculate accuracy difference
        accuracy_diff = rag_summary.average_accuracy - full_summary.average_accuracy
        
        # Calculate time difference
        time_diff = rag_summary.average_response_time - full_summary.average_response_time
        
        return ComparisonMetrics(
            rag_mcp_tokens=int(rag_summary.average_total_tokens),
            full_mcp_tokens=int(full_summary.average_total_tokens),
            token_reduction_percentage=token_reduction,
            rag_mcp_accuracy=rag_summary.average_accuracy,
            full_mcp_accuracy=full_summary.average_accuracy,
            accuracy_difference=accuracy_diff,
            rag_mcp_response_time=rag_summary.average_response_time,
            full_mcp_response_time=full_summary.average_response_time,
            time_difference=time_diff,
            rag_mcp_success_rate=rag_summary.success_rate,
            full_mcp_success_rate=full_summary.success_rate,
            rag_mcp_tool_rounds=rag_summary.average_tool_rounds,
            full_mcp_tool_rounds=full_summary.average_tool_rounds
        )
    
    def _generate_detailed_analysis(self, summaries: Dict[str, BenchmarkSummary], 
                                  metrics: ComparisonMetrics) -> Dict[str, Any]:
        """Generate detailed analysis of results."""
        analysis = {
            'performance_summary': {
                'token_efficiency': {
                    'reduction_percentage': metrics.token_reduction_percentage,
                    'interpretation': self._interpret_token_reduction(metrics.token_reduction_percentage)
                },
                'accuracy_comparison': {
                    'difference': metrics.accuracy_difference,
                    'interpretation': self._interpret_accuracy_difference(metrics.accuracy_difference)
                },
                'speed_comparison': {
                    'time_difference': metrics.time_difference,
                    'interpretation': self._interpret_time_difference(metrics.time_difference)
                }
            },
            'recommendations': self._generate_recommendations(metrics),
            'statistical_significance': self._assess_statistical_significance(summaries)
        }
        
        return analysis
    
    def _interpret_token_reduction(self, reduction: float) -> str:
        """Interpret token reduction percentage."""
        if reduction > 30:
            return "Excellent token reduction - RAG-MCP significantly more efficient"
        elif reduction > 15:
            return "Good token reduction - RAG-MCP moderately more efficient"
        elif reduction > 5:
            return "Modest token reduction - RAG-MCP slightly more efficient"
        elif reduction > -5:
            return "Minimal difference in token usage"
        else:
            return "RAG-MCP uses more tokens - may need optimization"
    
    def _interpret_accuracy_difference(self, diff: float) -> str:
        """Interpret accuracy difference."""
        if diff > 0.1:
            return "RAG-MCP significantly more accurate"
        elif diff > 0.05:
            return "RAG-MCP moderately more accurate"
        elif diff > -0.05:
            return "Similar accuracy between methods"
        else:
            return "Full MCP more accurate - RAG retrieval may need improvement"
    
    def _interpret_time_difference(self, diff: float) -> str:
        """Interpret response time difference."""
        if diff < -1.0:
            return "RAG-MCP significantly faster"
        elif diff < -0.5:
            return "RAG-MCP moderately faster"
        elif diff < 0.5:
            return "Similar response times"
        else:
            return "Full MCP faster - RAG overhead may be significant"
    
    def _generate_recommendations(self, metrics: ComparisonMetrics) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []
        
        if metrics.token_reduction_percentage > 20:
            recommendations.append("RAG-MCP shows excellent token efficiency - recommended for production")
        elif metrics.token_reduction_percentage < 5:
            recommendations.append("Consider optimizing RAG retrieval to improve token efficiency")
        
        if metrics.accuracy_difference < -0.1:
            recommendations.append("Improve knowledge base quality or retrieval algorithm")
        
        if metrics.time_difference > 1.0:
            recommendations.append("Optimize RAG retrieval speed or consider caching")
        
        if metrics.rag_mcp_success_rate < 0.9:
            recommendations.append("Investigate and fix reliability issues in RAG-MCP")
        
        return recommendations
    
    def _assess_statistical_significance(self, summaries: Dict[str, BenchmarkSummary]) -> Dict[str, str]:
        """Assess statistical significance of differences."""
        # This is a simplified assessment - in practice, you'd use proper statistical tests
        rag_summary = summaries.get(EvaluationMethod.RAG_MCP.value)
        full_summary = summaries.get(EvaluationMethod.ALL_TOOLS.value)
        
        significance = {}
        
        # Token usage significance
        if abs(rag_summary.average_total_tokens - full_summary.average_total_tokens) > 100:
            significance['token_usage'] = "Likely significant"
        else:
            significance['token_usage'] = "May not be significant"
        
        # Response time significance
        if abs(rag_summary.average_response_time - full_summary.average_response_time) > 0.5:
            significance['response_time'] = "Likely significant"
        else:
            significance['response_time'] = "May not be significant"
        
        return significance
    
    async def _save_results(self, results: Dict[str, Any]) -> None:
        """Save test results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test/mcp_comparison_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {filename}")
    
    async def _generate_html_report(self, results: Dict[str, Any]) -> None:
        """Generate detailed HTML report."""
        try:
            html_generator = HTMLReportGenerator()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_filename = f"test/mcp_comparison_report_{timestamp}.html"
            
            html_generator.generate_report(results, html_filename)
            logger.info(f"HTML report generated: {html_filename}")
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {str(e)}")
            print(f"Warning: HTML report generation failed: {str(e)}")
    
    def _print_summary(self, summaries: Dict[str, BenchmarkSummary], 
                      metrics: ComparisonMetrics) -> None:
        """Print test summary to console."""
        print("\n" + "="*80)
        print("MCP vs RAG-MCP Comprehensive Comparison Results")
        print("="*80)
        
        print(f"\nToken Efficiency:")
        print(f"  RAG-MCP Average Tokens: {metrics.rag_mcp_tokens}")
        print(f"  Full MCP Average Tokens: {metrics.full_mcp_tokens}")
        print(f"  Token Reduction: {metrics.token_reduction_percentage:.1f}%")
        
        print(f"\nAccuracy Comparison:")
        print(f"  RAG-MCP Accuracy: {metrics.rag_mcp_accuracy*100:.1f}%")
        print(f"  Full MCP Accuracy: {metrics.full_mcp_accuracy*100:.1f}%")
        print(f"  Accuracy Difference: {metrics.accuracy_difference*100:.1f}%")
        
        print(f"\nPerformance Comparison:")
        print(f"  RAG-MCP Response Time: {metrics.rag_mcp_response_time:.2f}s")
        print(f"  Full MCP Response Time: {metrics.full_mcp_response_time:.2f}s")
        print(f"  Time Difference: {metrics.time_difference:.2f}s")
        
        print(f"\nReliability:")
        print(f"  RAG-MCP Success Rate: {metrics.rag_mcp_success_rate*100:.1f}%")
        print(f"  Full MCP Success Rate: {metrics.full_mcp_success_rate*100:.1f}%")
        
        print("\n" + "="*80)
    
    def _generate_unique_names(self) -> Dict[str, str]:
        """Generate unique file and directory names for this test run."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        return {
            'test_file': f'test_file_{timestamp}.txt',
            'test_dir': f'test_dir_{timestamp}',
            'sample_file': f'sample_{timestamp}.txt',
            'backup_file': f'backup_{timestamp}.txt'
        }
    
    def _get_default_test_queries(self) -> List[Dict[str, Any]]:
        """Get default test queries for comprehensive testing with unique names."""
        # Generate unique names for this test run
        names = self._generate_unique_names()
        
        return [
            {
                'query': 'List files in current directory',
                'expected_tools': ['list_directory']
            },
            {
                'query': f'Create a new text file {names["test_file"]} with content "Hello World from MCP Test"',
                'expected_tools': ['write_file']
            },
            {
                'query': f'Read the content of {names["test_file"]} file',
                'expected_tools': ['read_file']
            },
            {
                'query': f'Search for files containing "test_file" in directory /Users/xrre/Documents/SA/repos/rag-mcp',
                'expected_tools': ['search_files']
            },
            {
                'query': f'Create a new directory called {names["test_dir"]}',
                'expected_tools': ['create_directory']
            },
            {
                'query': f'Check detailed information of {names["test_file"]} file',
                'expected_tools': ['get_file_info']
            },
            {
                'query': f'Create another file {names["sample_file"]} with content "Hello World from MCP Test Again", then read both {names["test_file"]} and {names["sample_file"]} files',
                'expected_tools': ['write_file', 'read_multiple_files']
            },
            {
                'query': 'View directory tree structure',
                'expected_tools': ['directory_tree']
            },
            {
                'query': 'View list of allowed directories',
                'expected_tools': ['list_allowed_directories']
            }
        ]


async def main():
    """Main test execution function."""
    print("Starting Comprehensive MCP vs RAG-MCP Comparison Test")
    print("=" * 60)
    
    # Initialize test suite
    test_suite = ComprehensiveMCPTest()
    
    try:
        # Run comprehensive test
        results = await test_suite.run_comprehensive_test()
        
        print("\nTest completed successfully!")
        print(f"Results saved with timestamp: {results['test_info']['timestamp']}")
        
        # Optionally run single query test for demonstration
        print("\n" + "-" * 60)
        print("Running single query demonstration...")
        
        demo_query = "List all Python files in current directory"
        single_result = await test_suite.run_single_query_comparison(demo_query, delay_between_calls=5.0)
        
        print(f"\nSingle Query Test Results for: '{demo_query}'")
        if single_result['comparison']['valid_comparison']:
            comp = single_result['comparison']
            print(f"Token Reduction: {comp['token_reduction_percentage']:.1f}%")
            print(f"RAG-MCP Tokens: {comp['rag_tokens']}")
            print(f"Full MCP Tokens: {comp['full_tokens']}")
            print(f"Response Time Difference: {comp['time_difference_seconds']:.2f}s")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"Test failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Ensure test directory exists
    os.makedirs("test", exist_ok=True)
    
    # Run the test
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 