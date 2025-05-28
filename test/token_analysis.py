#!/usr/bin/env python3
"""
Token Usage Analysis for MCP vs RAG-MCP

This script provides detailed analysis of:
1. Token usage patterns
2. Prompt size distribution
3. Tool selection efficiency
4. Memory usage optimization
"""

import asyncio
import json
import logging
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import sys
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat.config import ChatConfig
from chat.chat_manager import ChatManager

logger = logging.getLogger(__name__)


class TokenAnalyzer:
    """Detailed token usage analyzer for MCP comparison."""
    
    def __init__(self, config: ChatConfig = None):
        """Initialize token analyzer."""
        self.config = config or ChatConfig()
        self.analysis_data = []
        
    async def analyze_token_patterns(self, test_queries: List[str]) -> Dict[str, Any]:
        """
        Analyze token usage patterns for different query types.
        
        Args:
            test_queries: List of queries to analyze
            
        Returns:
            Detailed token analysis results
        """
        logger.info(f"Analyzing token patterns for {len(test_queries)} queries")
        
        results = {
            'rag_mcp_data': [],
            'full_mcp_data': [],
            'comparison_data': []
        }
        
        for i, query in enumerate(test_queries):
            logger.info(f"Analyzing query {i+1}/{len(test_queries)}: {query[:50]}...")
            
            # Test RAG-MCP
            rag_data = await self._analyze_single_query(query, use_kb_tools=True)
            results['rag_mcp_data'].append(rag_data)
            
            # Test Full MCP
            full_data = await self._analyze_single_query(query, use_kb_tools=False)
            results['full_mcp_data'].append(full_data)
            
            # Compare
            comparison = self._compare_token_usage(rag_data, full_data, query)
            results['comparison_data'].append(comparison)
        
        # Generate analysis summary
        summary = self._generate_token_summary(results)
        results['summary'] = summary
        
        # Save detailed results
        await self._save_token_analysis(results)
        
        return results
    
    async def _analyze_single_query(self, query: str, use_kb_tools: bool) -> Dict[str, Any]:
        """Analyze token usage for a single query."""
        async with ChatManager(self.config) as chat_manager:
            try:
                # Initialize
                await chat_manager.initialize(is_init_mcp=True)
                
                # Get initial conversation state
                initial_messages = len(chat_manager.get_conversation_history())
                
                # Process query
                response = await chat_manager.process_message(query, use_kb_tools=use_kb_tools)
                
                # Get final conversation state
                final_messages = len(chat_manager.get_conversation_history())
                conversation_history = chat_manager.get_conversation_history()
                
                # Analyze token distribution
                token_breakdown = self._analyze_token_breakdown(conversation_history, response)
                
                return {
                    'query': query,
                    'use_kb_tools': use_kb_tools,
                    'success': True,
                    'total_tokens': response.get('usage', {}).get('total_tokens', 0),
                    'input_tokens': response.get('usage', {}).get('input_tokens', 0),
                    'output_tokens': response.get('usage', {}).get('output_tokens', 0),
                    'message_count': final_messages - initial_messages,
                    'tool_rounds': response.get('tool_rounds', 0),
                    'token_breakdown': token_breakdown,
                    'conversation_length': len(str(conversation_history)),
                    'tools_used': self._extract_tools_used(conversation_history)
                }
                
            except Exception as e:
                logger.error(f"Query analysis failed: {str(e)}")
                return {
                    'query': query,
                    'use_kb_tools': use_kb_tools,
                    'success': False,
                    'error': str(e),
                    'total_tokens': 0,
                    'input_tokens': 0,
                    'output_tokens': 0
                }
    
    def _analyze_token_breakdown(self, conversation_history: List[Dict], response: Dict) -> Dict[str, Any]:
        """Analyze how tokens are distributed across different parts."""
        breakdown = {
            'user_message_tokens': 0,
            'assistant_message_tokens': 0,
            'tool_use_tokens': 0,
            'tool_result_tokens': 0,
            'system_tokens': 0
        }
        
        for message in conversation_history:
            role = message.get('role', '')
            content = message.get('content', [])
            
            # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
            message_text = str(content)
            estimated_tokens = len(message_text) // 4
            
            if role == 'user':
                breakdown['user_message_tokens'] += estimated_tokens
            elif role == 'assistant':
                # Check if this is a tool use or regular response
                has_tool_use = any('toolUse' in str(c) for c in content)
                if has_tool_use:
                    breakdown['tool_use_tokens'] += estimated_tokens
                else:
                    breakdown['assistant_message_tokens'] += estimated_tokens
            elif role == 'tool':
                breakdown['tool_result_tokens'] += estimated_tokens
            else:
                breakdown['system_tokens'] += estimated_tokens
        
        return breakdown
    
    def _extract_tools_used(self, conversation_history: List[Dict]) -> List[str]:
        """Extract list of tools used in conversation."""
        tools_used = []
        
        for message in conversation_history:
            for content in message.get('content', []):
                if isinstance(content, dict) and 'toolUse' in content:
                    tool_name = content['toolUse'].get('name', 'unknown')
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
        
        return tools_used
    
    def _compare_token_usage(self, rag_data: Dict, full_data: Dict, query: str) -> Dict[str, Any]:
        """Compare token usage between RAG-MCP and Full MCP."""
        if not rag_data['success'] or not full_data['success']:
            return {
                'query': query,
                'valid_comparison': False,
                'reason': 'One or both queries failed'
            }
        
        rag_tokens = rag_data['total_tokens']
        full_tokens = full_data['total_tokens']
        
        reduction_percentage = 0
        if full_tokens > 0:
            reduction_percentage = ((full_tokens - rag_tokens) / full_tokens) * 100
        
        return {
            'query': query,
            'valid_comparison': True,
            'rag_tokens': rag_tokens,
            'full_tokens': full_tokens,
            'token_reduction': reduction_percentage,
            'rag_input_tokens': rag_data['input_tokens'],
            'full_input_tokens': full_data['input_tokens'],
            'rag_output_tokens': rag_data['output_tokens'],
            'full_output_tokens': full_data['output_tokens'],
            'rag_tools_count': len(rag_data['tools_used']),
            'full_tools_count': len(full_data['tools_used']),
            'rag_tool_rounds': rag_data['tool_rounds'],
            'full_tool_rounds': full_data['tool_rounds'],
            'efficiency_score': self._calculate_efficiency_score(rag_data, full_data)
        }
    
    def _calculate_efficiency_score(self, rag_data: Dict, full_data: Dict) -> float:
        """Calculate overall efficiency score (0-100)."""
        # Factors: token reduction, tool selection accuracy, response quality
        token_efficiency = 0
        if full_data['total_tokens'] > 0:
            token_efficiency = max(0, (full_data['total_tokens'] - rag_data['total_tokens']) / full_data['total_tokens'])
        
        # Tool selection efficiency (fewer tools used = more efficient)
        tool_efficiency = 0
        if full_data['tools_used'] and rag_data['tools_used']:
            tool_efficiency = max(0, (len(full_data['tools_used']) - len(rag_data['tools_used'])) / len(full_data['tools_used']))
        
        # Combine factors (weighted average)
        efficiency_score = (token_efficiency * 0.7 + tool_efficiency * 0.3) * 100
        return min(100, max(0, efficiency_score))
    
    def _generate_token_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive token usage summary."""
        valid_comparisons = [c for c in results['comparison_data'] if c['valid_comparison']]
        
        if not valid_comparisons:
            return {'error': 'No valid comparisons available'}
        
        # Calculate statistics
        token_reductions = [c['token_reduction'] for c in valid_comparisons]
        rag_tokens = [c['rag_tokens'] for c in valid_comparisons]
        full_tokens = [c['full_tokens'] for c in valid_comparisons]
        efficiency_scores = [c['efficiency_score'] for c in valid_comparisons]
        
        summary = {
            'total_queries_analyzed': len(valid_comparisons),
            'average_token_reduction': np.mean(token_reductions),
            'median_token_reduction': np.median(token_reductions),
            'std_token_reduction': np.std(token_reductions),
            'max_token_reduction': np.max(token_reductions),
            'min_token_reduction': np.min(token_reductions),
            'average_rag_tokens': np.mean(rag_tokens),
            'average_full_tokens': np.mean(full_tokens),
            'average_efficiency_score': np.mean(efficiency_scores),
            'token_reduction_distribution': {
                'excellent_reduction': len([r for r in token_reductions if r > 30]),
                'good_reduction': len([r for r in token_reductions if 15 < r <= 30]),
                'modest_reduction': len([r for r in token_reductions if 5 < r <= 15]),
                'minimal_difference': len([r for r in token_reductions if -5 <= r <= 5]),
                'increased_usage': len([r for r in token_reductions if r < -5])
            }
        }
        
        return summary
    
    async def _save_token_analysis(self, results: Dict[str, Any]) -> None:
        """Save token analysis results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test/token_analysis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Token analysis saved to {filename}")
    
    def generate_token_visualization(self, results: Dict[str, Any]) -> None:
        """Generate visualizations for token usage analysis."""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Set style
            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            
            valid_comparisons = [c for c in results['comparison_data'] if c['valid_comparison']]
            
            if not valid_comparisons:
                print("No valid comparisons for visualization")
                return
            
            # 1. Token reduction distribution
            token_reductions = [c['token_reduction'] for c in valid_comparisons]
            axes[0, 0].hist(token_reductions, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
            axes[0, 0].set_title('Token Reduction Distribution')
            axes[0, 0].set_xlabel('Token Reduction (%)')
            axes[0, 0].set_ylabel('Frequency')
            axes[0, 0].axvline(np.mean(token_reductions), color='red', linestyle='--', label=f'Mean: {np.mean(token_reductions):.1f}%')
            axes[0, 0].legend()
            
            # 2. RAG vs Full MCP token comparison
            rag_tokens = [c['rag_tokens'] for c in valid_comparisons]
            full_tokens = [c['full_tokens'] for c in valid_comparisons]
            
            x = np.arange(len(valid_comparisons))
            width = 0.35
            
            axes[0, 1].bar(x - width/2, rag_tokens, width, label='RAG-MCP', alpha=0.7, color='lightgreen')
            axes[0, 1].bar(x + width/2, full_tokens, width, label='Full MCP', alpha=0.7, color='lightcoral')
            axes[0, 1].set_title('Token Usage Comparison by Query')
            axes[0, 1].set_xlabel('Query Index')
            axes[0, 1].set_ylabel('Total Tokens')
            axes[0, 1].legend()
            
            # 3. Efficiency score distribution
            efficiency_scores = [c['efficiency_score'] for c in valid_comparisons]
            axes[1, 0].boxplot(efficiency_scores)
            axes[1, 0].set_title('Efficiency Score Distribution')
            axes[1, 0].set_ylabel('Efficiency Score (0-100)')
            
            # 4. Input vs Output token comparison
            rag_input = [c['rag_input_tokens'] for c in valid_comparisons]
            rag_output = [c['rag_output_tokens'] for c in valid_comparisons]
            full_input = [c['full_input_tokens'] for c in valid_comparisons]
            full_output = [c['full_output_tokens'] for c in valid_comparisons]
            
            axes[1, 1].scatter(rag_input, rag_output, alpha=0.7, label='RAG-MCP', color='green')
            axes[1, 1].scatter(full_input, full_output, alpha=0.7, label='Full MCP', color='red')
            axes[1, 1].set_title('Input vs Output Tokens')
            axes[1, 1].set_xlabel('Input Tokens')
            axes[1, 1].set_ylabel('Output Tokens')
            axes[1, 1].legend()
            
            plt.tight_layout()
            
            # Save plot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_filename = f"test/token_analysis_plot_{timestamp}.png"
            plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
            plt.show()
            
            print(f"Visualization saved to {plot_filename}")
            
        except ImportError:
            print("Matplotlib not available. Install with: pip install matplotlib seaborn")
        except Exception as e:
            print(f"Visualization failed: {str(e)}")


async def main():
    """Main function for token analysis."""
    print("Token Usage Analysis for MCP vs RAG-MCP")
    print("=" * 50)
    
    # Test queries focused on different complexity levels
    test_queries = [
        "List files in current directory",
        "Read README.md file content",
        "Create a new file test.txt with content Hello World",
        "Search for files containing config",
        "Copy a file to another directory",
        "Delete temporary file",
        "Get detailed file information",
        "Create a new directory",
        "Move file to specified location",
        "Check if file exists"
    ]
    
    analyzer = TokenAnalyzer()
    
    try:
        # Run token analysis
        results = await analyzer.analyze_token_patterns(test_queries)
        
        # Print summary
        summary = results['summary']
        if 'error' not in summary:
            print(f"\nToken Analysis Summary:")
            print(f"Queries Analyzed: {summary['total_queries_analyzed']}")
            print(f"Average Token Reduction: {summary['average_token_reduction']:.1f}%")
            print(f"Median Token Reduction: {summary['median_token_reduction']:.1f}%")
            print(f"Average RAG-MCP Tokens: {summary['average_rag_tokens']:.0f}")
            print(f"Average Full MCP Tokens: {summary['average_full_tokens']:.0f}")
            print(f"Average Efficiency Score: {summary['average_efficiency_score']:.1f}/100")
            
            # Distribution analysis
            dist = summary['token_reduction_distribution']
            print(f"\nToken Reduction Distribution:")
            print(f"Excellent (>30%): {dist['excellent_reduction']} queries")
            print(f"Good (15-30%): {dist['good_reduction']} queries")
            print(f"Modest (5-15%): {dist['modest_reduction']} queries")
            print(f"Minimal (±5%): {dist['minimal_difference']} queries")
            print(f"Increased usage: {dist['increased_usage']} queries")
        
        # Generate visualization
        analyzer.generate_token_visualization(results)
        
        print("\nToken analysis completed successfully!")
        
    except Exception as e:
        print(f"Token analysis failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Ensure test directory exists
    os.makedirs("test", exist_ok=True)
    
    # Run analysis
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 