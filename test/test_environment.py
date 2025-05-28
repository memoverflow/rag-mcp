#!/usr/bin/env python3
"""
Environment Test for MCP vs RAG-MCP Comparison

This script verifies that all dependencies and configurations are properly set up
for running the MCP comparison tests.
"""

import sys
import os
import asyncio
import importlib
from typing import List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        return True, f"✓ Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)"


def check_required_modules() -> List[Tuple[bool, str]]:
    """Check if required modules are available."""
    required_modules = [
        'asyncio',
        'json',
        'logging',
        'typing',
        'dataclasses',
        'statistics',
        'time',
        'datetime'
    ]
    
    results = []
    for module in required_modules:
        try:
            importlib.import_module(module)
            results.append((True, f"✓ {module}"))
        except ImportError:
            results.append((False, f"✗ {module} (missing)"))
    
    return results


def check_optional_modules() -> List[Tuple[bool, str]]:
    """Check if optional modules are available."""
    optional_modules = [
        ('matplotlib', 'for visualization'),
        ('seaborn', 'for enhanced plots'),
        ('pandas', 'for data analysis'),
        ('numpy', 'for numerical operations')
    ]
    
    results = []
    for module, purpose in optional_modules:
        try:
            importlib.import_module(module)
            results.append((True, f"✓ {module} ({purpose})"))
        except ImportError:
            results.append((False, f"○ {module} (optional - {purpose})"))
    
    return results


def check_chat_modules() -> List[Tuple[bool, str]]:
    """Check if chat modules are available."""
    chat_modules = [
        'chat.config',
        'chat.chat_manager',
        'chat.mcp_client',
        'chat.knowledge_base',
        'chat.evaluator',
        'chat.bedrock_client'
    ]
    
    results = []
    for module in chat_modules:
        try:
            importlib.import_module(module)
            results.append((True, f"✓ {module}"))
        except ImportError as e:
            results.append((False, f"✗ {module} ({str(e)})"))
    
    return results


async def check_chat_manager_initialization() -> Tuple[bool, str]:
    """Check if ChatManager can be initialized."""
    try:
        from chat.config import ChatConfig
        from chat.chat_manager import ChatManager
        
        config = ChatConfig()
        chat_manager = ChatManager(config)
        
        # Try basic initialization (without MCP connection)
        return True, "✓ ChatManager initialization successful"
        
    except Exception as e:
        return False, f"✗ ChatManager initialization failed: {str(e)}"


async def check_mcp_connection() -> Tuple[bool, str]:
    """Check if MCP connection can be established."""
    try:
        from chat.config import ChatConfig
        from chat.chat_manager import ChatManager
        
        config = ChatConfig()
        async with ChatManager(config) as chat_manager:
            await chat_manager.initialize(is_init_mcp=True)
            return True, "✓ MCP connection successful"
            
    except Exception as e:
        return False, f"✗ MCP connection failed: {str(e)}"


def check_test_directory() -> Tuple[bool, str]:
    """Check if test directory structure is correct."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    required_files = [
        'comprehensive_mcp_comparison_test.py',
        'run_mcp_comparison.py',
        'token_analysis.py',
        'README.md'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(test_dir, file)):
            missing_files.append(file)
    
    if not missing_files:
        return True, "✓ All test files present"
    else:
        return False, f"✗ Missing files: {', '.join(missing_files)}"


def check_aws_configuration() -> Tuple[bool, str]:
    """Check AWS configuration for Bedrock."""
    try:
        from chat.config import BedrockConfig
        
        config = BedrockConfig()
        
        # Check if basic configuration is present
        if config.aws_access_key_id and config.aws_secret_access_key:
            return True, "✓ AWS credentials configured"
        else:
            return False, "○ AWS credentials not configured (may use default profile)"
            
    except Exception as e:
        return False, f"✗ AWS configuration error: {str(e)}"


async def run_environment_test():
    """Run comprehensive environment test."""
    print("MCP vs RAG-MCP Environment Test")
    print("=" * 50)
    
    all_passed = True
    
    # Check Python version
    passed, message = check_python_version()
    print(f"\nPython Version: {message}")
    if not passed:
        all_passed = False
    
    # Check required modules
    print(f"\nRequired Modules:")
    for passed, message in check_required_modules():
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    # Check optional modules
    print(f"\nOptional Modules:")
    for passed, message in check_optional_modules():
        print(f"  {message}")
    
    # Check chat modules
    print(f"\nChat Modules:")
    for passed, message in check_chat_modules():
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    # Check test directory
    passed, message = check_test_directory()
    print(f"\nTest Directory: {message}")
    if not passed:
        all_passed = False
    
    # Check AWS configuration
    passed, message = check_aws_configuration()
    print(f"\nAWS Configuration: {message}")
    
    # Check ChatManager initialization
    print(f"\nChatManager Test:")
    passed, message = await check_chat_manager_initialization()
    print(f"  {message}")
    if not passed:
        all_passed = False
    
    # Check MCP connection (this might fail in some environments)
    print(f"\nMCP Connection Test:")
    passed, message = await check_mcp_connection()
    print(f"  {message}")
    if not passed:
        print("  Note: MCP connection failure is common and may not prevent testing")
    
    # Summary
    print(f"\n" + "=" * 50)
    if all_passed:
        print("✓ Environment test PASSED - Ready for MCP comparison testing!")
        print("\nNext steps:")
        print("1. Run quick test: python test/run_mcp_comparison.py --mode quick")
        print("2. Run full test: python test/run_mcp_comparison.py --mode full")
        print("3. Run token analysis: python test/token_analysis.py")
    else:
        print("✗ Environment test FAILED - Please fix the issues above")
        print("\nCommon solutions:")
        print("1. Install missing modules: pip install -r chat/requirements.txt")
        print("2. Check Python path and module imports")
        print("3. Verify AWS credentials and configuration")
    
    return all_passed


def main():
    """Main function."""
    try:
        result = asyncio.run(run_environment_test())
        return 0 if result else 1
    except Exception as e:
        print(f"Environment test failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 