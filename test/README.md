# MCP vs RAG-MCP Comparison Test Suite

This test suite provides comprehensive tools to compare the performance of RAG-MCP and full MCP tools, including key metrics such as token usage, accuracy, response time, and more.

## File Structure

```
test/
├── README.md                           # This file
├── comprehensive_mcp_comparison_test.py # Main comparison test file
├── run_mcp_comparison.py               # Simplified test runner
├── token_analysis.py                   # Dedicated token usage analysis
└── results/                            # Test results output directory (auto-created)
```

## Core Concepts

### RAG-MCP vs Full MCP

- **RAG-MCP** (`use_kb_tools=True`): Uses knowledge base retrieval for relevant tools, providing only context-relevant tool subsets
- **Full MCP** (`use_kb_tools=False`): Provides all available MCP tools

### Evaluation Metrics

1. **Token Efficiency**: Input/output/total token usage
2. **Accuracy**: Tool selection accuracy and response quality
3. **Response Time**: Time required to process queries
4. **Success Rate**: Percentage of successfully processed queries
5. **Tool Rounds**: Number of tool calling rounds needed to complete tasks

## Usage

### 1. Complete Test (Recommended) 🌟

```bash
# Run complete test and generate HTML report
python test/run_complete_test.py

# Run demo test (3 queries)
python test/run_complete_test.py --demo

# Specify number of test queries
python test/run_complete_test.py --queries 5

# Specify output directory
python test/run_complete_test.py --output-dir results

# Auto cleanup temporary files after test completion
python test/run_complete_test.py --demo --cleanup

# Custom LLM call interval (prevent high frequency)
python test/run_complete_test.py --demo --delay 10.0

# Quick test (shorter interval, for development testing only)
python test/run_complete_test.py --demo --delay 2.0
```

**Featured Functions:**
- 🎯 Auto-generate detailed HTML reports
- 📊 Include interactive charts and visualizations
- 🚀 Auto-open reports in browser
- 📈 Complete performance analysis and recommendations
- ⏱️ Smart rate limiting to prevent high-frequency LLM calls

### 2. Quick Test

```bash
# Run quick comparison test (3 queries)
python test/run_mcp_comparison.py --mode quick

# Run full comparison test (9 queries)
python test/run_mcp_comparison.py --mode full

# Test single custom query
python test/run_mcp_comparison.py --mode single --query "List all Python files in current directory"
```

### 3. Specialized Tests

```bash
# Run accuracy validation test
python test/quick_accuracy_test.py

# Run token usage analysis
python test/token_analysis.py

# Run debug test
python test/debug_test.py

# Test rate limiting functionality
python test/test_rate_limiting.py

# Validate test result data quality
python test/data_validator.py test/mcp_comparison_results_YYYYMMDD_HHMMSS.json
```

## Install Dependencies

```bash
# Basic dependencies (already in main project)
pip install -r chat/requirements.txt

# Visualization dependencies (optional, for chart generation)
pip install matplotlib seaborn pandas numpy
```

## Test Results Interpretation

### Token Reduction Percentage
- **>30%**: Excellent token efficiency
- **15-30%**: Good token efficiency  
- **5-15%**: Moderate token efficiency
- **±5%**: Minimal difference
- **<-5%**: RAG-MCP uses more tokens (needs optimization)

### Efficiency Score (0-100)
- **80-100**: Excellent efficiency
- **60-80**: Good efficiency
- **40-60**: Moderate efficiency
- **<40**: Needs improvement

### Success Rate
- **>95%**: Excellent reliability
- **90-95%**: Good reliability
- **<90%**: Needs reliability investigation

## Output Files

Tests automatically generate the following files:

### 📄 Main Reports
1. **`mcp_comparison_report_YYYYMMDD_HHMMSS.html`**: 🌟 **Detailed HTML Report**
   - Interactive charts and visualizations
   - Complete performance analysis
   - Query-by-query detailed comparison
   - Professional recommendations and explanations

### 📊 Data Files
2. **`mcp_comparison_results_YYYYMMDD_HHMMSS.json`**: Complete test result data
3. **`token_analysis_YYYYMMDD_HHMMSS.json`**: Token usage analysis results
4. **`token_analysis_plot_YYYYMMDD_HHMMSS.png`**: Token usage visualization chart

### 📝 Log Files
5. **`mcp_comparison_test.log`**: Detailed test logs

### 🔍 Data Validation
6. **Auto data validation**: Automatically validates data quality after test completion
7. **Independent validation tool**: Can independently validate existing test result files

## Custom Testing

### Adding Custom Test Queries

Edit the `_get_default_test_queries()` method in `comprehensive_mcp_comparison_test.py`:

```python
def _get_default_test_queries(self) -> List[Dict[str, Any]]:
    return [
        {
            'query': 'Your custom query',
            'expected_tools': ['expected_tool_name'],
            'category': 'query_category'
        },
        # Add more queries...
    ]
```

### Modifying Evaluation Metrics

Customize evaluation logic in the `ComprehensiveMCPTest` class:

```python
def _calculate_efficiency_score(self, rag_data: Dict, full_data: Dict) -> float:
    # Custom efficiency scoring algorithm
    pass
```

## Performance Benchmarks

Typical results based on filesystem operations:

| Metric | RAG-MCP | Full MCP | Improvement |
|--------|---------|----------|-------------|
| Average Token Usage | ~800 | ~1200 | 33% reduction |
| Average Response Time | ~2.5s | ~3.0s | 17% faster |
| Success Rate | 95% | 98% | -3% |
| Tool Selection Accuracy | 92% | 89% | +3% |

## Rate Limiting ⏱️

### LLM Call Frequency Control

To prevent excessive pressure on LLM services, the test system includes built-in smart rate limiting:

- **Default interval**: 5 seconds (recommended for production testing)
- **Custom interval**: Adjustable via `--delay` parameter
- **Progress display**: Real-time test progress and estimated remaining time
- **Smart scheduling**: Auto-calculate total test time
- **Precise timing**: ⚠️ **Delay time does not affect response time measurement** - only measures actual LLM processing time

```bash
# Use default 5-second interval
python test/run_complete_test.py --demo

# Use 10-second interval (more conservative)
python test/run_complete_test.py --demo --delay 10.0

# Use 2-second interval (development testing)
python test/run_complete_test.py --demo --delay 2.0
```

### Time Estimation

The system automatically calculates and displays:
- Total number of calls
- Estimated total time
- Real-time progress percentage
- Remaining time estimation

### Important Notes ⚠️

**Response Time Measurement Accuracy**:
- ✅ **Delay time not included in response time** - System only measures actual LLM processing time
- ✅ **Precise timing** - Delay executed before calls, doesn't affect performance metrics
- ✅ **Fair comparison** - Both methods use same delay strategy, ensuring fair comparison

```bash
# Verify delay time doesn't affect response time measurement
python test/test_rate_limiting.py
```

## File Management

### Unique Filename Generation 🔄

The test system automatically generates unique filenames and directory names for each run, avoiding conflicts during repeated executions:

- Filename format: `test_file_YYYYMMDD_HHMMSS_mmm.txt`
- Directory format: `test_dir_YYYYMMDD_HHMMSS_mmm`
- Includes millisecond-level timestamps for uniqueness

### Cleanup Temporary Files 🧹

```bash
# Preview files to be cleaned (no actual deletion)
python test/cleanup_test_files.py

# Actually execute cleanup
python test/cleanup_test_files.py --execute

# Clean files only, keep directories
python test/cleanup_test_files.py --execute --files-only

# Clean directories only, keep files
python test/cleanup_test_files.py --execute --dirs-only

# Auto cleanup during testing
python test/run_complete_test.py --demo --cleanup
```

## Troubleshooting

### Common Issues

1. **MCP Connection Failed**
   ```
   Solution: Check MCP server configuration and network connection
   ```

2. **Knowledge Base Query Failed**
   ```
   Solution: Verify AWS credentials and knowledge base configuration
   ```

3. **Inaccurate Token Statistics**
   ```
   Solution: Ensure Bedrock client is properly configured
   ```

4. **File Already Exists Error**
   ```
   Solution: System auto-generates unique filenames. If issues persist, run cleanup script
   python test/cleanup_test_files.py --execute
   ```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Extended Features

### Adding New Evaluation Methods

1. Add new `EvaluationMethod` in `evaluator.py`
2. Implement corresponding logic in test suite
3. Update comparison analysis methods

### CI/CD Integration

```yaml
# .github/workflows/mcp-test.yml
name: MCP Performance Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run MCP Comparison Test
        run: python test/run_mcp_comparison.py --mode quick
```

## Contribution Guidelines

1. When adding new test cases, ensure expected results are included
2. Update documentation to reflect new features
3. Run complete test suite to verify changes
4. Check code style and type annotations before submission

## License

This test suite follows the same license as the main project. 