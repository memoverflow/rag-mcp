#!/usr/bin/env python3
"""
Data Validator for MCP vs RAG-MCP Test Results
"""

import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Data validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    summary: Dict[str, Any]


class DataValidator:
    """Test result data validator"""
    
    def __init__(self):
        self.validation_rules = {
            'token_range': (0, 100000),  # Reasonable token count range
            'response_time_range': (0.0, 300.0),  # Reasonable response time range (seconds)
            'accuracy_range': (0.0, 1.0),  # Accuracy range
            'tool_rounds_range': (0, 20),  # Reasonable tool rounds range
        }
    
    def validate_test_results(self, results: Dict[str, Any]) -> ValidationResult:
        """Validate complete test results"""
        errors = []
        warnings = []
        summary = {}
        
        try:
            # Validate basic structure
            structure_errors = self._validate_structure(results)
            errors.extend(structure_errors)
            
            # Validate detailed results
            if 'detailed_results' in results:
                detail_errors, detail_warnings, detail_summary = self._validate_detailed_results(
                    results['detailed_results']
                )
                errors.extend(detail_errors)
                warnings.extend(detail_warnings)
                summary.update(detail_summary)
            
            # Validate summary data
            if 'summaries' in results:
                summary_errors, summary_warnings = self._validate_summaries(results['summaries'])
                errors.extend(summary_errors)
                warnings.extend(summary_warnings)
            
            # Validate comparison metrics
            if 'comparison_metrics' in results:
                comparison_errors = self._validate_comparison_metrics(results['comparison_metrics'])
                errors.extend(comparison_errors)
            
            # Generate validation summary
            summary.update({
                'validation_timestamp': datetime.now().isoformat(),
                'total_errors': len(errors),
                'total_warnings': len(warnings),
                'overall_quality': self._assess_data_quality(errors, warnings)
            })
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                summary=summary
            )
            
        except Exception as e:
            errors.append(f"Validation process failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                summary={'validation_failed': True}
            )
    
    def _validate_structure(self, results: Dict[str, Any]) -> List[str]:
        """Validate result structure"""
        errors = []
        
        required_fields = ['test_info', 'summaries', 'comparison_metrics', 'detailed_results']
        for field in required_fields:
            if field not in results:
                errors.append(f"Missing required field: {field}")
        
        # Validate test info
        if 'test_info' in results:
            test_info = results['test_info']
            if 'total_queries' not in test_info or test_info['total_queries'] <= 0:
                errors.append("Invalid or missing total_queries in test_info")
            
            if 'timestamp' not in test_info:
                errors.append("Missing timestamp in test_info")
        
        return errors
    
    def _validate_detailed_results(self, detailed_results: List[Dict[str, Any]]) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Validate detailed result data"""
        errors = []
        warnings = []
        summary = {}
        
        if not detailed_results:
            errors.append("No detailed results found")
            return errors, warnings, summary
        
        # Statistics
        total_results = len(detailed_results)
        successful_results = sum(1 for r in detailed_results if r.get('success', False))
        methods = set(r.get('method', 'unknown') for r in detailed_results)
        
        summary.update({
            'total_detailed_results': total_results,
            'successful_results': successful_results,
            'success_rate': successful_results / total_results if total_results > 0 else 0,
            'methods_found': list(methods)
        })
        
        # Validate each result
        for i, result in enumerate(detailed_results):
            result_errors, result_warnings = self._validate_single_result(result, i)
            errors.extend(result_errors)
            warnings.extend(result_warnings)
        
        # Validate method balance
        if len(methods) < 2:
            warnings.append(f"Only {len(methods)} method(s) found, expected at least 2 for comparison")
        
        # Validate data balance
        method_counts = {}
        for result in detailed_results:
            method = result.get('method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        if len(set(method_counts.values())) > 1:
            warnings.append(f"Unbalanced method data: {method_counts}")
        
        return errors, warnings, summary
    
    def _validate_single_result(self, result: Dict[str, Any], index: int) -> Tuple[List[str], List[str]]:
        """Validate single result"""
        errors = []
        warnings = []
        prefix = f"Result {index}"
        
        # Validate required fields
        required_fields = ['method', 'query', 'success']
        for field in required_fields:
            if field not in result:
                errors.append(f"{prefix}: Missing required field '{field}'")
        
        # If successful, validate metric data
        if result.get('success', False):
            # Validate token data
            for token_field in ['prompt_tokens', 'completion_tokens', 'total_tokens']:
                if token_field in result:
                    value = result[token_field]
                    if not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"{prefix}: Invalid {token_field}: {value}")
                    elif value > self.validation_rules['token_range'][1]:
                        warnings.append(f"{prefix}: Unusually high {token_field}: {value}")
            
            # Validate response time
            if 'response_time' in result:
                response_time = result['response_time']
                if not isinstance(response_time, (int, float)) or response_time < 0:
                    errors.append(f"{prefix}: Invalid response_time: {response_time}")
                elif response_time > self.validation_rules['response_time_range'][1]:
                    warnings.append(f"{prefix}: Unusually long response_time: {response_time}s")
            
            # Validate accuracy
            if 'accuracy' in result:
                accuracy = result['accuracy']
                if not isinstance(accuracy, (int, float)):
                    errors.append(f"{prefix}: Invalid accuracy type: {type(accuracy)}")
                elif not (0.0 <= accuracy <= 1.0):
                    errors.append(f"{prefix}: Accuracy out of range [0,1]: {accuracy}")
            
            # Validate tool rounds
            if 'tool_rounds' in result:
                tool_rounds = result['tool_rounds']
                if not isinstance(tool_rounds, int) or tool_rounds < 0:
                    errors.append(f"{prefix}: Invalid tool_rounds: {tool_rounds}")
                elif tool_rounds > self.validation_rules['tool_rounds_range'][1]:
                    warnings.append(f"{prefix}: Unusually high tool_rounds: {tool_rounds}")
        
        return errors, warnings
    
    def _validate_summaries(self, summaries: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate summary data"""
        errors = []
        warnings = []
        
        if not summaries:
            errors.append("No summary data found")
            return errors, warnings
        
        expected_methods = ['rag_mcp', 'all_tools']
        for method in expected_methods:
            if method not in summaries:
                warnings.append(f"Missing summary for method: {method}")
                continue
            
            summary = summaries[method]
            
            # Validate summary fields
            required_summary_fields = [
                'total_queries', 'success_rate', 'average_accuracy',
                'average_total_tokens', 'average_response_time'
            ]
            
            for field in required_summary_fields:
                if field not in summary:
                    errors.append(f"Missing {field} in {method} summary")
                    continue
                
                value = summary[field]
                
                # Validate value ranges
                if field == 'success_rate' and not (0.0 <= value <= 1.0):
                    errors.append(f"Invalid success_rate in {method}: {value}")
                elif field == 'average_accuracy' and not (0.0 <= value <= 1.0):
                    errors.append(f"Invalid average_accuracy in {method}: {value}")
                elif field in ['average_total_tokens', 'average_response_time'] and value < 0:
                    errors.append(f"Invalid {field} in {method}: {value}")
        
        return errors, warnings
    
    def _validate_comparison_metrics(self, comparison_metrics: Dict[str, Any]) -> List[str]:
        """Validate comparison metrics"""
        errors = []
        
        required_comparison_fields = [
            'token_reduction_percentage', 'accuracy_difference',
            'rag_mcp_tokens', 'full_mcp_tokens'
        ]
        
        for field in required_comparison_fields:
            if field not in comparison_metrics:
                errors.append(f"Missing comparison metric: {field}")
        
        # Validate token reduction rate reasonableness
        if 'token_reduction_percentage' in comparison_metrics:
            reduction = comparison_metrics['token_reduction_percentage']
            if not isinstance(reduction, (int, float)):
                errors.append(f"Invalid token_reduction_percentage type: {type(reduction)}")
            elif reduction < -100 or reduction > 100:
                errors.append(f"Token reduction percentage out of reasonable range: {reduction}%")
        
        return errors
    
    def _assess_data_quality(self, errors: List[str], warnings: List[str]) -> str:
        """Assess data quality"""
        if len(errors) > 0:
            return "Poor"
        elif len(warnings) > 5:
            return "Fair"
        elif len(warnings) > 0:
            return "Good"
        else:
            return "Excellent"
    
    def generate_validation_report(self, validation_result: ValidationResult) -> str:
        """Generate validation report"""
        report = []
        report.append("=" * 60)
        report.append("Data Validation Report")
        report.append("=" * 60)
        
        # Overall status
        status = "✅ PASSED" if validation_result.is_valid else "❌ FAILED"
        report.append(f"Validation Status: {status}")
        report.append(f"Data Quality: {validation_result.summary.get('overall_quality', 'Unknown')}")
        report.append("")
        
        # Statistics
        if validation_result.summary:
            report.append("📊 Statistics:")
            for key, value in validation_result.summary.items():
                if key not in ['validation_timestamp', 'total_errors', 'total_warnings', 'overall_quality']:
                    report.append(f"  {key}: {value}")
            report.append("")
        
        # Error information
        if validation_result.errors:
            report.append(f"❌ Errors ({len(validation_result.errors)}):")
            for error in validation_result.errors:
                report.append(f"  • {error}")
            report.append("")
        
        # Warning information
        if validation_result.warnings:
            report.append(f"⚠️  Warnings ({len(validation_result.warnings)}):")
            for warning in validation_result.warnings:
                report.append(f"  • {warning}")
            report.append("")
        
        # Recommendations
        report.append("💡 Recommendations:")
        if validation_result.is_valid:
            report.append("  • Data validation passed, test results can be used safely")
        else:
            report.append("  • Please fix the above errors and re-run the test")
            report.append("  • Check if test environment and configuration are correct")
        
        if validation_result.warnings:
            report.append("  • Pay attention to warnings, they may affect result interpretation")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


def validate_test_file(file_path: str) -> ValidationResult:
    """Validate test result file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        validator = DataValidator()
        return validator.validate_test_results(results)
        
    except FileNotFoundError:
        return ValidationResult(
            is_valid=False,
            errors=[f"File not found: {file_path}"],
            warnings=[],
            summary={}
        )
    except json.JSONDecodeError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid JSON format: {str(e)}"],
            warnings=[],
            summary={}
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Validation failed: {str(e)}"],
            warnings=[],
            summary={}
        )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python data_validator.py <test_results_file.json>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    validation_result = validate_test_file(file_path)
    
    validator = DataValidator()
    report = validator.generate_validation_report(validation_result)
    print(report)
    
    sys.exit(0 if validation_result.is_valid else 1) 