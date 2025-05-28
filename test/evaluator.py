"""
Performance evaluation framework for RAG-MCP implementation.
Based on the paper: RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection via Retrieval-Augmented Generation
"""

import asyncio
import json
import logging
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from chat.config import ChatConfig
from chat.chat_manager import ChatManager
from chat.exceptions import ChatError

logger = logging.getLogger(__name__)


class EvaluationMethod(Enum):
    """Different evaluation methods as described in the paper."""
    RAG_MCP = "rag_mcp"  # Our implementation using KB retrieval
    MCP_DIRECT = "mcp_direct"  # Direct MCP tools (like "Actual Match" in paper)
    ALL_TOOLS = "all_tools"  # All tools provided (like "Blank Conditioning" in paper)
    RANDOM_SELECTION = "random_selection"  # Random tool selection baseline


@dataclass
class EvaluationResult:
    """Results from a single evaluation run."""
    method: str
    query: str
    success: bool
    accuracy: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time: float
    tool_rounds: int
    selected_tools: List[str]
    error_message: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Summary statistics for a benchmark run."""
    method: str
    total_queries: int
    success_rate: float
    average_accuracy: float
    average_prompt_tokens: float
    average_completion_tokens: float
    average_total_tokens: float
    average_response_time: float
    average_tool_rounds: float
    token_reduction_percentage: float
    std_prompt_tokens: float
    std_completion_tokens: float
    std_response_time: float


class RAGMCPEvaluator:
    """
    Comprehensive evaluator for RAG-MCP performance comparison.
    Implements the evaluation methodology from the paper.
    """
    
    def __init__(self, config: Optional[ChatConfig] = None):
        """Initialize evaluator with configuration."""
        self.config = config or ChatConfig()
        self.results: List[EvaluationResult] = []
        
    async def evaluate_single_query(
        self, 
        query: str, 
        method: EvaluationMethod,
        expected_tools: Optional[List[str]] = None,
        chat_manager: Optional[ChatManager] = None
    ) -> EvaluationResult:
        """
        Evaluate a single query using the specified method.
        
        Args:
            query: User query to evaluate
            method: Evaluation method to use
            expected_tools: Expected tools for accuracy calculation
            chat_manager: Pre-initialized chat manager (optional)
            
        Returns:
            EvaluationResult with detailed metrics
        """
        start_time = time.time()
        
        # Initialize chat manager if not provided
        if chat_manager is None:
            chat_manager = ChatManager(self.config)
            await chat_manager.initialize()
            should_cleanup = True
        else:
            should_cleanup = False
        
        try:
            # Configure method-specific parameters
            use_kb_tools = method == EvaluationMethod.RAG_MCP
            
            # Process the query
            response = await chat_manager.process_message(
                query, 
                use_kb_tools=use_kb_tools
            )
            
            response_time = time.time() - start_time
            
            # Extract metrics with validation
            usage = response.get('usage', {})
            prompt_tokens = usage.get('input_tokens', 0)
            completion_tokens = usage.get('output_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            tool_rounds = response.get('tool_rounds', 0)
            
            # Validate token data consistency
            if total_tokens == 0 and (prompt_tokens > 0 or completion_tokens > 0):
                total_tokens = prompt_tokens + completion_tokens
                logger.warning(f"Total tokens was 0, calculated as {total_tokens}")
            
            # Log detailed metrics for debugging
            logger.debug(f"Metrics extracted - Prompt: {prompt_tokens}, Completion: {completion_tokens}, "
                        f"Total: {total_tokens}, Tool rounds: {tool_rounds}, Response time: {response_time:.3f}s")
            
            # Extract selected tools from conversation history
            selected_tools = self._extract_selected_tools(chat_manager)
            
            # Calculate accuracy if expected tools provided
            accuracy = self._calculate_accuracy_with_tools(selected_tools, expected_tools) if expected_tools else 1.0
            
            result = EvaluationResult(
                method=method.value,
                query=query,
                success=True,
                accuracy=accuracy,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                response_time=response_time,
                tool_rounds=tool_rounds,
                selected_tools=selected_tools
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Evaluation failed for method {method.value}: {str(e)}")
            
            result = EvaluationResult(
                method=method.value,
                query=query,
                success=False,
                accuracy=0.0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                response_time=response_time,
                tool_rounds=0,
                selected_tools=[],
                error_message=str(e)
            )
        
        finally:
            if should_cleanup:
                await chat_manager.cleanup()
        
        return result
    
    async def run_benchmark(
        self, 
        test_queries: List[Dict[str, Any]], 
        methods: List[EvaluationMethod] = None,
        delay_between_calls: float = 5.0
    ) -> Dict[str, BenchmarkSummary]:
        """
        Run comprehensive benchmark comparing different methods.
        
        Args:
            test_queries: List of test queries with expected results
            methods: Methods to evaluate (defaults to all methods)
            delay_between_calls: Delay in seconds between LLM calls (default: 5.0)
            
        Returns:
            Dictionary mapping method names to benchmark summaries
        """
        if methods is None:
            methods = list(EvaluationMethod)
        
        total_calls = len(test_queries) * len(methods)
        estimated_time = total_calls * delay_between_calls / 60  # Convert to minutes
        
        logger.info(f"Starting benchmark with {len(test_queries)} queries and {len(methods)} methods")
        logger.info(f"Rate limiting: {delay_between_calls}s delay between calls")
        logger.info(f"Estimated total time: {estimated_time:.1f} minutes ({total_calls} calls)")
        
        results = {}
        call_count = 0
        
        for method_idx, method in enumerate(methods):
            logger.info(f"Evaluating method {method_idx + 1}/{len(methods)}: {method.value}")
            method_results = []
            
            # Initialize chat manager once per method for efficiency
            async with ChatManager(self.config) as chat_manager:
                for i, test_case in enumerate(test_queries):
                    query = test_case.get('query', '')
                    expected_tools = test_case.get('expected_tools', [])
                    
                    call_count += 1
                    logger.info(f"Processing call {call_count}/{total_calls}: Query {i+1}/{len(test_queries)} - {query[:50]}...")
                    
                    # Add delay before each LLM call (except the first one)
                    if call_count > 1:
                        logger.debug(f"Waiting {delay_between_calls}s before next LLM call...")
                        delay_start = time.time()
                        await asyncio.sleep(delay_between_calls)
                        delay_end = time.time()
                        actual_delay = delay_end - delay_start
                        logger.debug(f"Actual delay: {actual_delay:.2f}s")
                    
                    # Measure only the actual query processing time (excluding delay)
                    result = await self.evaluate_single_query(
                        query=query,
                        method=method,
                        expected_tools=expected_tools,
                        chat_manager=chat_manager
                    )
                    
                    method_results.append(result)
                    
                    # Clear conversation for next query
                    chat_manager.clear_conversation()
                    
                    # Show progress
                    progress = (call_count / total_calls) * 100
                    remaining_calls = total_calls - call_count
                    remaining_time = remaining_calls * delay_between_calls / 60
                    logger.info(f"Progress: {progress:.1f}% ({call_count}/{total_calls}), "
                              f"Estimated remaining time: {remaining_time:.1f} minutes")
            
            # Store results for this method
            self.results.extend(method_results)
            
            # Calculate summary statistics
            summary = self._calculate_summary(method.value, method_results)
            results[method.value] = summary
            
            logger.info(f"Method {method.value} completed: {summary.success_rate:.2%} success rate")
            
            # Add delay between methods (except after the last method)
            if method_idx < len(methods) - 1:
                logger.info(f"Waiting {delay_between_calls}s before next method...")
                await asyncio.sleep(delay_between_calls)
        
        logger.info("Benchmark completed successfully!")
        return results
    
    def _calculate_accuracy(self, response: Dict[str, Any], expected_tools: List[str]) -> float:
        """Calculate accuracy based on tool selection (deprecated - use _calculate_accuracy_with_tools)."""
        if not expected_tools:
            return 1.0
        
        # Extract actual tools used from response
        # This is a simplified accuracy calculation
        # In practice, you might want more sophisticated metrics
        selected_tools = response.get('selected_tools', [])
        
        if not selected_tools:
            return 0.0
        
        # Calculate intersection over union
        selected_set = set(selected_tools)
        expected_set = set(expected_tools)
        
        intersection = len(selected_set.intersection(expected_set))
        union = len(selected_set.union(expected_set))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_accuracy_with_tools(self, selected_tools: List[str], expected_tools: List[str]) -> float:
        """Calculate accuracy based on actual tool selection."""
        if not expected_tools:
            return 1.0
        
        if not selected_tools:
            return 0.0
        
        # Normalize tool names for comparison (handle different naming conventions)
        def normalize_tool_name(name: str) -> str:
            """Normalize tool names for comparison."""
            name = name.lower().strip()
            return name
        
        normalized_selected = set(normalize_tool_name(tool) for tool in selected_tools)
        normalized_expected = set(normalize_tool_name(tool) for tool in expected_tools)
        
        # Calculate intersection over union (Jaccard similarity)
        intersection = len(normalized_selected.intersection(normalized_expected))
        union = len(normalized_selected.union(normalized_expected))
        
        accuracy = intersection / union if union > 0 else 0.0
        
        # Log for debugging and validation
        logger.debug(f"Tool accuracy calculation:")
        logger.debug(f"  Selected tools: {selected_tools} -> {normalized_selected}")
        logger.debug(f"  Expected tools: {expected_tools} -> {normalized_expected}")
        logger.debug(f"  Intersection: {intersection}, Union: {union}, Accuracy: {accuracy:.3f}")
        
        # Additional validation
        if accuracy > 1.0:
            logger.warning(f"Accuracy > 1.0 detected: {accuracy}, capping at 1.0")
            accuracy = 1.0
        elif accuracy < 0.0:
            logger.warning(f"Accuracy < 0.0 detected: {accuracy}, setting to 0.0")
            accuracy = 0.0
        
        return accuracy
    
    def _extract_selected_tools(self, chat_manager: ChatManager) -> List[str]:
        """Extract tools that were actually selected/used."""
        history = chat_manager.get_conversation_history()
        selected_tools = []
        
        for message in history:
            for content in message.get('content', []):
                if 'toolUse' in content:
                    tool_name = content['toolUse'].get('name', 'unknown')
                    if tool_name not in selected_tools:
                        selected_tools.append(tool_name)
        
        return selected_tools
    
    def _calculate_summary(self, method: str, results: List[EvaluationResult]) -> BenchmarkSummary:
        """Calculate summary statistics for a method."""
        if not results:
            return BenchmarkSummary(
                method=method,
                total_queries=0,
                success_rate=0.0,
                average_accuracy=0.0,
                average_prompt_tokens=0.0,
                average_completion_tokens=0.0,
                average_total_tokens=0.0,
                average_response_time=0.0,
                average_tool_rounds=0.0,
                token_reduction_percentage=0.0,
                std_prompt_tokens=0.0,
                std_completion_tokens=0.0,
                std_response_time=0.0
            )
        
        successful_results = [r for r in results if r.success]
        
        # Log summary statistics
        logger.info(f"Summary calculation for {method}: {len(successful_results)}/{len(results)} successful")
        
        # Calculate averages with validation
        success_rate = len(successful_results) / len(results) if results else 0.0
        
        if successful_results:
            # Filter out invalid values for more robust statistics
            valid_accuracies = [r.accuracy for r in successful_results if 0.0 <= r.accuracy <= 1.0]
            valid_prompt_tokens = [r.prompt_tokens for r in successful_results if r.prompt_tokens >= 0]
            valid_completion_tokens = [r.completion_tokens for r in successful_results if r.completion_tokens >= 0]
            valid_total_tokens = [r.total_tokens for r in successful_results if r.total_tokens >= 0]
            valid_response_times = [r.response_time for r in successful_results if r.response_time >= 0]
            valid_tool_rounds = [r.tool_rounds for r in successful_results if r.tool_rounds >= 0]
            
            avg_accuracy = statistics.mean(valid_accuracies) if valid_accuracies else 0.0
            avg_prompt_tokens = statistics.mean(valid_prompt_tokens) if valid_prompt_tokens else 0.0
            avg_completion_tokens = statistics.mean(valid_completion_tokens) if valid_completion_tokens else 0.0
            avg_total_tokens = statistics.mean(valid_total_tokens) if valid_total_tokens else 0.0
            avg_response_time = statistics.mean(valid_response_times) if valid_response_times else 0.0
            avg_tool_rounds = statistics.mean(valid_tool_rounds) if valid_tool_rounds else 0.0
        else:
            avg_accuracy = avg_prompt_tokens = avg_completion_tokens = 0.0
            avg_total_tokens = avg_response_time = avg_tool_rounds = 0.0
        
        # Calculate standard deviations with validation
        if successful_results and len(valid_prompt_tokens) > 1:
            std_prompt_tokens = statistics.stdev(valid_prompt_tokens)
        else:
            std_prompt_tokens = 0.0
            
        if successful_results and len(valid_completion_tokens) > 1:
            std_completion_tokens = statistics.stdev(valid_completion_tokens)
        else:
            std_completion_tokens = 0.0
            
        if successful_results and len(valid_response_times) > 1:
            std_response_time = statistics.stdev(valid_response_times)
        else:
            std_response_time = 0.0
        
        # Calculate token reduction (compared to a baseline)
        # This would need to be calculated relative to the ALL_TOOLS method
        token_reduction_percentage = 0.0  # Will be calculated in comparison
        
        return BenchmarkSummary(
            method=method,
            total_queries=len(results),
            success_rate=success_rate,
            average_accuracy=avg_accuracy,
            average_prompt_tokens=avg_prompt_tokens,
            average_completion_tokens=avg_completion_tokens,
            average_total_tokens=avg_total_tokens,
            average_response_time=avg_response_time,
            average_tool_rounds=avg_tool_rounds,
            token_reduction_percentage=token_reduction_percentage,
            std_prompt_tokens=std_prompt_tokens,
            std_completion_tokens=std_completion_tokens,
            std_response_time=std_response_time
        )
    
    def generate_comparison_report(self, summaries: Dict[str, BenchmarkSummary]) -> str:
        """Generate a detailed comparison report."""
        report = []
        report.append("=" * 80)
        report.append("RAG-MCP Performance Benchmark Report")
        report.append("=" * 80)
        report.append("")
        
        # Summary table
        report.append("Method Comparison Summary:")
        report.append("-" * 80)
        report.append(f"{'Method':<15} {'Success%':<10} {'Accuracy%':<12} {'Prompt Tokens':<15} {'Completion Tokens':<18} {'Response Time(s)':<16}")
        report.append("-" * 80)
        
        for method, summary in summaries.items():
            report.append(
                f"{method:<15} "
                f"{summary.success_rate*100:<10.2f} "
                f"{summary.average_accuracy*100:<12.2f} "
                f"{summary.average_prompt_tokens:<15.0f} "
                f"{summary.average_completion_tokens:<18.0f} "
                f"{summary.average_response_time:<16.3f}"
            )
        
        report.append("")
        
        # Detailed analysis
        if EvaluationMethod.RAG_MCP.value in summaries and EvaluationMethod.ALL_TOOLS.value in summaries:
            rag_summary = summaries[EvaluationMethod.RAG_MCP.value]
            all_tools_summary = summaries[EvaluationMethod.ALL_TOOLS.value]
            
            token_reduction = ((all_tools_summary.average_prompt_tokens - rag_summary.average_prompt_tokens) / 
                             all_tools_summary.average_prompt_tokens * 100) if all_tools_summary.average_prompt_tokens > 0 else 0
            
            accuracy_improvement = ((rag_summary.average_accuracy - all_tools_summary.average_accuracy) / 
                                  all_tools_summary.average_accuracy * 100) if all_tools_summary.average_accuracy > 0 else 0
            
            report.append("Key Findings:")
            report.append(f"• RAG-MCP reduces prompt tokens by {token_reduction:.1f}%")
            report.append(f"• RAG-MCP improves accuracy by {accuracy_improvement:.1f}%")
            report.append(f"• RAG-MCP success rate: {rag_summary.success_rate*100:.1f}%")
            report.append("")
        
        # Detailed statistics
        report.append("Detailed Statistics:")
        report.append("-" * 40)
        
        for method, summary in summaries.items():
            report.append(f"\n{method.upper()}:")
            report.append(f"  Total Queries: {summary.total_queries}")
            report.append(f"  Success Rate: {summary.success_rate*100:.2f}%")
            report.append(f"  Average Accuracy: {summary.average_accuracy*100:.2f}%")
            report.append(f"  Average Prompt Tokens: {summary.average_prompt_tokens:.0f} (±{summary.std_prompt_tokens:.0f})")
            report.append(f"  Average Completion Tokens: {summary.average_completion_tokens:.0f} (±{summary.std_completion_tokens:.0f})")
            report.append(f"  Average Total Tokens: {summary.average_total_tokens:.0f}")
            report.append(f"  Average Response Time: {summary.average_response_time:.3f}s (±{summary.std_response_time:.3f})")
            report.append(f"  Average Tool Rounds: {summary.average_tool_rounds:.1f}")
        
        return "\n".join(report)
    
    def export_results(self, filename: str, summaries: Dict[str, BenchmarkSummary]) -> None:
        """Export results to JSON file."""
        export_data = {
            'summaries': {k: asdict(v) for k, v in summaries.items()},
            'detailed_results': [asdict(r) for r in self.results],
            'timestamp': time.time()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results exported to {filename}")
