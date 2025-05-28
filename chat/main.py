#!/usr/bin/env python3
"""
Main entry point for the chat application.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat.cli import chat

if __name__ == "__main__":
    chat() 