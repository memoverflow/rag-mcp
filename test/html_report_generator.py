#!/usr/bin/env python3
"""
HTML Report Generator for MCP vs RAG-MCP Comparison
"""

import json
import os
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics


class HTMLReportGenerator:
    """Generate detailed HTML test reports"""
    
    def __init__(self):
        self.template = self._get_html_template()
    
    def generate_report(self, results: Dict[str, Any], output_path: str = None) -> str:
        """
        Generate detailed HTML report
        
        Args:
            results: Test result data
            output_path: Output file path
            
        Returns:
            Generated HTML content
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"test/mcp_comparison_report_{timestamp}.html"
        
        # Prepare report data
        report_data = self._prepare_report_data(results)
        
        # Generate HTML content
        html_content = self._generate_html_content(report_data)
        
        # Save file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML report generated: {output_path}")
        return html_content
    
    def _prepare_report_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare report data"""
        test_info = results.get('test_info', {})
        summaries = results.get('summaries', {})
        comparison_metrics = results.get('comparison_metrics', {})
        analysis = results.get('analysis', {})
        detailed_results = results.get('detailed_results', [])
        
        # Calculate detailed statistics
        rag_results = [r for r in detailed_results if r.get('method') == 'rag_mcp']
        full_results = [r for r in detailed_results if r.get('method') == 'all_tools']
        
        return {
            'test_info': test_info,
            'summaries': summaries,
            'comparison_metrics': comparison_metrics,
            'analysis': analysis,
            'detailed_results': detailed_results,
            'rag_results': rag_results,
            'full_results': full_results,
            'charts_data': self._prepare_charts_data(rag_results, full_results),
            'query_details': self._prepare_query_details(detailed_results)
        }
    
    def _prepare_charts_data(self, rag_results: List[Dict], full_results: List[Dict]) -> Dict[str, Any]:
        """Prepare chart data"""
        charts_data = {}
        
        # Token usage comparison data
        if rag_results and full_results:
            # Ensure data consistency
            min_length = min(len(rag_results), len(full_results))
            if len(rag_results) != len(full_results):
                print(f"Warning: RAG results ({len(rag_results)}) and Full results ({len(full_results)}) have different lengths")
            
            # Filter valid token data
            rag_tokens = []
            full_tokens = []
            labels = []
            
            for i in range(min_length):
                rag_token = rag_results[i].get('total_tokens', 0)
                full_token = full_results[i].get('total_tokens', 0)
                
                # Only include valid data points
                if rag_token >= 0 and full_token >= 0:
                    rag_tokens.append(rag_token)
                    full_tokens.append(full_token)
                    labels.append(f"Query {len(labels)+1}")
            
            charts_data['token_comparison'] = {
                'labels': labels,
                'rag_tokens': rag_tokens,
                'full_tokens': full_tokens
            }
            
            # Response time comparison
            rag_times = []
            full_times = []
            time_labels = []
            
            for i in range(min_length):
                rag_time = rag_results[i].get('response_time', 0)
                full_time = full_results[i].get('response_time', 0)
                
                # Only include valid time data (positive values)
                if rag_time >= 0 and full_time >= 0:
                    rag_times.append(rag_time)
                    full_times.append(full_time)
                    time_labels.append(f"Query {len(time_labels)+1}")
            
            charts_data['time_comparison'] = {
                'labels': time_labels,
                'rag_times': rag_times,
                'full_times': full_times
            }
            
            # Accuracy distribution
            rag_accuracy = []
            full_accuracy = []
            
            for i in range(min_length):
                rag_acc = rag_results[i].get('accuracy', 0)
                full_acc = full_results[i].get('accuracy', 0)
                
                # Validate accuracy values (should be between 0 and 1)
                if 0.0 <= rag_acc <= 1.0 and 0.0 <= full_acc <= 1.0:
                    rag_accuracy.append(rag_acc * 100)
                    full_accuracy.append(full_acc * 100)
            
            charts_data['accuracy_distribution'] = {
                'rag_accuracy': rag_accuracy,
                'full_accuracy': full_accuracy
            }
            
            # Tool usage statistics
            rag_tool_counts = [len(r.get('selected_tools', [])) for r in rag_results]
            full_tool_counts = [len(r.get('selected_tools', [])) for r in full_results]
            
            charts_data['tool_usage'] = {
                'labels': [f"Query {i+1}" for i in range(len(rag_results))],
                'rag_tool_counts': rag_tool_counts,
                'full_tool_counts': full_tool_counts
            }
        
        return charts_data
    
    def _prepare_query_details(self, detailed_results: List[Dict]) -> List[Dict]:
        """Prepare query detail information"""
        query_details = []
        
        # Group by query
        queries = {}
        for result in detailed_results:
            query = result.get('query', 'Unknown')
            if query not in queries:
                queries[query] = {}
            queries[query][result.get('method', 'unknown')] = result
        
        for query, methods in queries.items():
            rag_result = methods.get('rag_mcp', {})
            full_result = methods.get('all_tools', {})
            
            detail = {
                'query': query,
                'rag_result': rag_result,
                'full_result': full_result,
                'comparison': self._compare_query_results(rag_result, full_result)
            }
            query_details.append(detail)
        
        return query_details
    
    def _compare_query_results(self, rag_result: Dict, full_result: Dict) -> Dict:
        """Compare single query results"""
        if not rag_result or not full_result:
            return {'valid': False, 'reason': 'Missing results'}
        
        rag_tokens = rag_result.get('total_tokens', 0)
        full_tokens = full_result.get('total_tokens', 0)
        
        token_reduction = 0
        if full_tokens > 0:
            token_reduction = ((full_tokens - rag_tokens) / full_tokens) * 100
        
        return {
            'valid': True,
            'token_reduction': token_reduction,
            'time_difference': rag_result.get('response_time', 0) - full_result.get('response_time', 0),
            'accuracy_difference': rag_result.get('accuracy', 0) - full_result.get('accuracy', 0),
            'rag_tools': rag_result.get('selected_tools', []),
            'full_tools': full_result.get('selected_tools', [])
        }
    
    def _generate_html_content(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML content"""
        test_info = report_data['test_info']
        summaries = report_data['summaries']
        comparison_metrics = report_data['comparison_metrics']
        analysis = report_data['analysis']
        charts_data = report_data['charts_data']
        query_details = report_data['query_details']
        
        # Generate HTML for each section
        header_html = self._generate_header(test_info)
        summary_html = self._generate_summary_section(summaries, comparison_metrics)
        charts_html = self._generate_charts_section(charts_data)
        analysis_html = self._generate_analysis_section(analysis)
        details_html = self._generate_details_section(query_details)
        
        # Combine complete HTML
        html_content = self.template.format(
            title="MCP vs RAG-MCP Detailed Comparison Report",
            header=header_html,
            summary=summary_html,
            charts=charts_html,
            analysis=analysis_html,
            details=details_html,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return html_content
    
    def _generate_header(self, test_info: Dict) -> str:
        """Generate report header"""
        return f"""
        <div class="header">
            <h1>🔍 MCP vs RAG-MCP Performance Comparison Report</h1>
            <div class="test-info">
                <p><strong>Test Time:</strong> {test_info.get('timestamp', 'Unknown')}</p>
                <p><strong>Number of Test Queries:</strong> {test_info.get('total_queries', 0)}</p>
                <p><strong>Test Methods:</strong> {', '.join(test_info.get('methods_tested', []))}</p>
            </div>
        </div>
        """
    
    def _generate_summary_section(self, summaries: Dict, comparison_metrics: Dict) -> str:
        """Generate summary section"""
        rag_summary = summaries.get('rag_mcp', {})
        full_summary = summaries.get('all_tools', {})
        
        return f"""
        <div class="summary-section">
            <h2>📊 Test Results Summary</h2>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Token Efficiency</h3>
                    <div class="metric-value">{comparison_metrics.get('token_reduction_percentage', 0):.1f}%</div>
                    <div class="metric-label">Token Reduction</div>
                    <div class="metric-details">
                        <p>RAG-MCP: {comparison_metrics.get('rag_mcp_tokens', 0)} tokens</p>
                        <p>Full MCP: {comparison_metrics.get('full_mcp_tokens', 0)} tokens</p>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Accuracy Comparison</h3>
                    <div class="metric-value">{comparison_metrics.get('rag_mcp_accuracy', 0)*100:.1f}%</div>
                    <div class="metric-label">RAG-MCP Accuracy</div>
                    <div class="metric-details">
                        <p>RAG-MCP: {comparison_metrics.get('rag_mcp_accuracy', 0)*100:.1f}%</p>
                        <p>Full MCP: {comparison_metrics.get('full_mcp_accuracy', 0)*100:.1f}%</p>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Response Time</h3>
                    <div class="metric-value">{comparison_metrics.get('rag_mcp_response_time', 0):.2f}s</div>
                    <div class="metric-label">RAG-MCP Average Time</div>
                    <div class="metric-details">
                        <p>RAG-MCP: {comparison_metrics.get('rag_mcp_response_time', 0):.2f}s</p>
                        <p>Full MCP: {comparison_metrics.get('full_mcp_response_time', 0):.2f}s</p>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Success Rate</h3>
                    <div class="metric-value">{comparison_metrics.get('rag_mcp_success_rate', 0)*100:.1f}%</div>
                    <div class="metric-label">RAG-MCP Success Rate</div>
                    <div class="metric-details">
                        <p>RAG-MCP: {comparison_metrics.get('rag_mcp_success_rate', 0)*100:.1f}%</p>
                        <p>Full MCP: {comparison_metrics.get('full_mcp_success_rate', 0)*100:.1f}%</p>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _generate_charts_section(self, charts_data: Dict) -> str:
        """Generate charts section"""
        if not charts_data:
            return "<div class='charts-section'><h2>📈 Chart Analysis</h2><p>No chart data available</p></div>"
        
        return f"""
        <div class="charts-section">
            <h2>📈 Chart Analysis</h2>
            
            <div class="chart-container">
                <h3>Token Usage Comparison</h3>
                <canvas id="tokenChart" width="800" height="400"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>Response Time Comparison</h3>
                <canvas id="timeChart" width="800" height="400"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>Tool Usage Count Comparison</h3>
                <canvas id="toolChart" width="800" height="400"></canvas>
            </div>
            
            <script>
                // Token usage chart
                const tokenCtx = document.getElementById('tokenChart').getContext('2d');
                new Chart(tokenCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(charts_data.get('token_comparison', {}).get('labels', []))},
                        datasets: [{{
                            label: 'RAG-MCP',
                            data: {json.dumps(charts_data.get('token_comparison', {}).get('rag_tokens', []))},
                            backgroundColor: 'rgba(54, 162, 235, 0.8)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }}, {{
                            label: 'Full MCP',
                            data: {json.dumps(charts_data.get('token_comparison', {}).get('full_tokens', []))},
                            backgroundColor: 'rgba(255, 99, 132, 0.8)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Token Count'
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Response time chart
                const timeCtx = document.getElementById('timeChart').getContext('2d');
                new Chart(timeCtx, {{
                    type: 'line',
                    data: {{
                        labels: {json.dumps(charts_data.get('time_comparison', {}).get('labels', []))},
                        datasets: [{{
                            label: 'RAG-MCP',
                            data: {json.dumps(charts_data.get('time_comparison', {}).get('rag_times', []))},
                            borderColor: 'rgba(54, 162, 235, 1)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            tension: 0.1
                        }}, {{
                            label: 'Full MCP',
                            data: {json.dumps(charts_data.get('time_comparison', {}).get('full_times', []))},
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            tension: 0.1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Response Time (seconds)'
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Tool usage count chart
                const toolCtx = document.getElementById('toolChart').getContext('2d');
                new Chart(toolCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(charts_data.get('tool_usage', {}).get('labels', []))},
                        datasets: [{{
                            label: 'RAG-MCP Tool Count',
                            data: {json.dumps(charts_data.get('tool_usage', {}).get('rag_tool_counts', []))},
                            backgroundColor: 'rgba(75, 192, 192, 0.8)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }}, {{
                            label: 'Full MCP Tool Count',
                            data: {json.dumps(charts_data.get('tool_usage', {}).get('full_tool_counts', []))},
                            backgroundColor: 'rgba(153, 102, 255, 0.8)',
                            borderColor: 'rgba(153, 102, 255, 1)',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Number of Tools Used'
                                }}
                            }}
                        }}
                    }}
                }});
            </script>
        </div>
        """
    
    def _generate_analysis_section(self, analysis: Dict) -> str:
        """Generate analysis section"""
        performance_summary = analysis.get('performance_summary', {})
        recommendations = analysis.get('recommendations', [])
        
        return f"""
        <div class="analysis-section">
            <h2>🔍 Detailed Analysis</h2>
            
            <div class="analysis-grid">
                <div class="analysis-card">
                    <h3>Token Efficiency Analysis</h3>
                    <p><strong>Reduction Percentage:</strong> {performance_summary.get('token_efficiency', {}).get('reduction_percentage', 0):.1f}%</p>
                    <p><strong>Interpretation:</strong> {performance_summary.get('token_efficiency', {}).get('interpretation', 'No analysis available')}</p>
                </div>
                
                <div class="analysis-card">
                    <h3>Accuracy Analysis</h3>
                    <p><strong>Difference:</strong> {performance_summary.get('accuracy_comparison', {}).get('difference', 0)*100:.1f}%</p>
                    <p><strong>Interpretation:</strong> {performance_summary.get('accuracy_comparison', {}).get('interpretation', 'No analysis available')}</p>
                </div>
                
                <div class="analysis-card">
                    <h3>Speed Analysis</h3>
                    <p><strong>Time Difference:</strong> {performance_summary.get('speed_comparison', {}).get('time_difference', 0):.2f}s</p>
                    <p><strong>Interpretation:</strong> {performance_summary.get('speed_comparison', {}).get('interpretation', 'No analysis available')}</p>
                </div>
            </div>
            
            <div class="recommendations">
                <h3>💡 Recommendations</h3>
                <ul>
                    {''.join([f'<li>{rec}</li>' for rec in recommendations])}
                </ul>
            </div>
        </div>
        """
    
    def _generate_details_section(self, query_details: List[Dict]) -> str:
        """Generate details section"""
        details_html = """
        <div class="details-section">
            <h2>📋 Query Detailed Results</h2>
            <div class="query-details">
        """
        
        for i, detail in enumerate(query_details):
            query = detail['query']
            rag_result = detail['rag_result']
            full_result = detail['full_result']
            comparison = detail['comparison']
            
            details_html += f"""
            <div class="query-detail-card">
                <h3>Query {i+1}: {query}</h3>
                
                <div class="result-comparison">
                    <div class="result-column">
                        <h4>🔹 RAG-MCP Results</h4>
                        <p><strong>Success:</strong> {'✅' if rag_result.get('success', False) else '❌'}</p>
                        <p><strong>Token Usage:</strong> {rag_result.get('total_tokens', 0)}</p>
                        <p><strong>Response Time:</strong> {rag_result.get('response_time', 0):.2f}s</p>
                        <p><strong>Accuracy:</strong> {rag_result.get('accuracy', 0)*100:.1f}%</p>
                        <p><strong>Tools Used:</strong> {', '.join(rag_result.get('selected_tools', []))}</p>
                    </div>
                    
                    <div class="result-column">
                        <h4>🔸 Full MCP Results</h4>
                        <p><strong>Success:</strong> {'✅' if full_result.get('success', False) else '❌'}</p>
                        <p><strong>Token Usage:</strong> {full_result.get('total_tokens', 0)}</p>
                        <p><strong>Response Time:</strong> {full_result.get('response_time', 0):.2f}s</p>
                        <p><strong>Accuracy:</strong> {full_result.get('accuracy', 0)*100:.1f}%</p>
                        <p><strong>Tools Used:</strong> {', '.join(full_result.get('selected_tools', []))}</p>
                    </div>
                </div>
                
                {self._generate_comparison_summary(comparison)}
            </div>
            """
        
        details_html += """
            </div>
        </div>
        """
        
        return details_html
    
    def _generate_comparison_summary(self, comparison: Dict) -> str:
        """Generate comparison summary"""
        return f"""
        <div class="comparison-summary">
            <h4>📊 Comparison Summary</h4>
            <div class="comparison-metrics">
                <span class="metric">Token Reduction: {comparison.get('token_reduction', 0):.1f}%</span>
                <span class="metric">Time Difference: {comparison.get('time_difference', 0):.2f}s</span>
                <span class="metric">Accuracy Difference: {comparison.get('accuracy_difference', 0)*100:.1f}%</span>
            </div>
        </div>
        """
    
    def _get_html_template(self) -> str:
        """Get HTML template"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 20px;
        }}
        
        .test-info {{
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 8px;
            display: inline-block;
        }}
        
        .summary-section, .charts-section, .analysis-section, .details-section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .metric-card h3 {{
            font-size: 1.2em;
            margin-bottom: 10px;
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .metric-details {{
            margin-top: 15px;
            font-size: 0.85em;
            background: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 5px;
        }}
        
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .chart-container h3 {{
            margin-bottom: 20px;
            color: #495057;
        }}
        
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .analysis-card {{
            background: #e3f2fd;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
        }}
        
        .recommendations {{
            margin-top: 30px;
            background: #f1f8e9;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #4caf50;
        }}
        
        .recommendations ul {{
            margin-left: 20px;
        }}
        
        .recommendations li {{
            margin: 10px 0;
        }}
        
        .query-detail-card {{
            background: #fafafa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
        }}
        
        .result-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        
        .result-column {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
        
        .result-column h4 {{
            margin-bottom: 15px;
            color: #495057;
        }}
        
        .comparison-summary {{
            background: #fff3e0;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        .comparison-metrics {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}
        
        .metric {{
            background: #ff9800;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
        
        h2 {{
            color: #495057;
            margin-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }}
        
        @media (max-width: 768px) {{
            .result-comparison {{
                grid-template-columns: 1fr;
            }}
            
            .comparison-metrics {{
                flex-direction: column;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {header}
        {summary}
        {charts}
        {analysis}
        {details}
        
        <div class="footer">
            <p>Report generated time: {timestamp}</p>
            <p>MCP vs RAG-MCP Performance Comparison Test System</p>
        </div>
    </div>
</body>
</html>
        """


# Usage example
if __name__ == "__main__":
    # Test code can be added here
    generator = HTMLReportGenerator()
    print("HTML report generator is ready") 