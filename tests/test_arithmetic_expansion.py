#!/usr/bin/env python3
"""
Test arithmetic expansion in isolation
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path
import re

# Setup
WORKSPACE = Path("/home/user/couch")
executor = BashToolExecutor(working_dir=str(WORKSPACE))

print("=" * 80)
print("TESTING ARITHMETIC EXPANSION")
print("=" * 80)
print()

# Test 1: Direct _expand_variables test
test_commands = [
    'echo $((5 + 3))',
    'head -n $((5 + 5)) file.txt',
    'echo $((10 * 2))',
    'count=$((5 + 3)); echo $count',
]

print("Testing _expand_variables() directly:")
print("-" * 80)
for cmd in test_commands:
    expanded = executor._expand_variables(cmd)
    print(f"Original: {cmd}")
    print(f"Expanded: {expanded}")
    print()

# Test 2: Full execution with detailed logging
print("=" * 80)
print("Testing full execution:")
print("=" * 80)
print()

# Enable debug logging
import logging
executor.logger.setLevel(logging.DEBUG)

result = executor.execute({'command': 'head -n $((5 + 5)) file.txt', 'description': 'test'})
print("Result:")
print(result)
