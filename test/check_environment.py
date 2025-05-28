#!/usr/bin/env python3
"""
Environment Check for MCP vs RAG-MCP Testing
"""

import sys
import os
import importlib

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
        return False

def check_modules():
    """Check required modules"""
    required_modules = [
        'asyncio', 'json', 'logging', 'typing', 'dataclasses', 
        'statistics', 'time', 'datetime'
    ]
    
    optional_modules = [
        ('matplotlib', 'for chart generation'),
        ('pandas', 'for data analysis'),
        ('numpy', 'for numerical computation')
    ]
    
    print("\n📦 Checking required modules:")
    all_good = True
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            all_good = False
    
    print("\n📦 Checking optional modules:")
    for module, purpose in optional_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module} ({purpose})")
        except ImportError:
            print(f"⚠️  {module} ({purpose}) - optional")
    
    return all_good

def check_test_files():
    """Check test files"""
    test_files = [
        'evaluator.py',
        'comprehensive_mcp_comparison_test.py',
        'html_report_generator.py',
        'run_complete_test.py',
        'README.md'
    ]
    
    print("\n📁 Checking test files:")
    all_good = True
    for file in test_files:
        if os.path.exists(f"test/{file}"):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            all_good = False
    
    return all_good

def main():
    """Main check function"""
    print("🔍 MCP vs RAG-MCP Testing Environment Check")
    print("=" * 40)
    
    checks = [
        ("Python version", check_python_version),
        ("Python modules", check_modules),
        ("Test files", check_test_files)
    ]
    
    all_passed = True
    for name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {name} check failed: {str(e)}")
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 Environment check passed! Ready to start testing")
        print("\nRecommended run:")
        print("  python test/run_complete_test.py --demo")
    else:
        print("⚠️  Environment check found issues, please fix before running tests")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 