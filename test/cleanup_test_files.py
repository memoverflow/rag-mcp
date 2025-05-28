#!/usr/bin/env python3
"""
Cleanup script for MCP test files
"""

import os
import glob
import argparse
from typing import List


def find_test_files() -> List[str]:
    """Find all test-generated files"""
    patterns = [
        'test_file_*.txt',
        'sample_*.txt',
        'backup_*.txt',
        'test_dir_*',
        'mcp_test_*.txt',
        'temp_*.txt'
    ]
    
    found_files = []
    for pattern in patterns:
        found_files.extend(glob.glob(pattern))
    
    return found_files


def find_test_directories() -> List[str]:
    """Find all test-generated directories"""
    patterns = [
        'test_dir_*',
        'temp_dir_*',
        'mcp_test_dir_*'
    ]
    
    found_dirs = []
    for pattern in patterns:
        found_dirs.extend(glob.glob(pattern))
    
    # Return only directories
    return [d for d in found_dirs if os.path.isdir(d)]


def cleanup_files(files: List[str], dry_run: bool = False) -> None:
    """Cleanup files"""
    if not files:
        print("No files found to cleanup")
        return
    
    print(f"Found {len(files)} test files:")
    for file in files:
        print(f"  - {file}")
    
    if dry_run:
        print("\n[DRY RUN] Above files will be deleted (use --execute to actually delete)")
        return
    
    deleted_count = 0
    for file in files:
        try:
            os.remove(file)
            print(f"✅ Deleted file: {file}")
            deleted_count += 1
        except Exception as e:
            print(f"❌ Failed to delete file {file}: {str(e)}")
    
    print(f"\nSuccessfully deleted {deleted_count}/{len(files)} files")


def cleanup_directories(directories: List[str], dry_run: bool = False) -> None:
    """Cleanup directories"""
    if not directories:
        print("No directories found to cleanup")
        return
    
    print(f"Found {len(directories)} test directories:")
    for directory in directories:
        print(f"  - {directory}/")
    
    if dry_run:
        print("\n[DRY RUN] Above directories will be deleted (use --execute to actually delete)")
        return
    
    deleted_count = 0
    for directory in directories:
        try:
            import shutil
            shutil.rmtree(directory)
            print(f"✅ Deleted directory: {directory}/")
            deleted_count += 1
        except Exception as e:
            print(f"❌ Failed to delete directory {directory}: {str(e)}")
    
    print(f"\nSuccessfully deleted {deleted_count}/{len(directories)} directories")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Cleanup MCP test-generated temporary files and directories')
    parser.add_argument('--execute', action='store_true', help='Actually execute deletion (default is preview mode)')
    parser.add_argument('--files-only', action='store_true', help='Only cleanup files, not directories')
    parser.add_argument('--dirs-only', action='store_true', help='Only cleanup directories, not files')
    
    args = parser.parse_args()
    
    print("🧹 MCP Test File Cleanup Tool")
    print("=" * 40)
    
    # Find test files and directories
    test_files = find_test_files()
    test_dirs = find_test_directories()
    
    if not test_files and not test_dirs:
        print("✨ No test files or directories found to cleanup")
        return
    
    # Decide what to cleanup based on arguments
    if args.dirs_only:
        cleanup_directories(test_dirs, dry_run=not args.execute)
    elif args.files_only:
        cleanup_files(test_files, dry_run=not args.execute)
    else:
        # Cleanup both files and directories
        if test_files:
            print("\n📄 Cleaning up test files:")
            cleanup_files(test_files, dry_run=not args.execute)
        
        if test_dirs:
            print("\n📁 Cleaning up test directories:")
            cleanup_directories(test_dirs, dry_run=not args.execute)
    
    if not args.execute:
        print(f"\n💡 Tip: Use --execute parameter to actually execute deletion")
        print(f"   Example: python test/cleanup_test_files.py --execute")


if __name__ == "__main__":
    main() 