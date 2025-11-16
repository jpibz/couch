#!/usr/bin/env python3
"""Debug command substitution processing"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

executor = BashToolExecutor(working_dir='/tmp/test')

# Test simple command substitution
test_cases = [
    'echo $(date)',
    'echo $(find . -name "*.txt")',
    'grep "pattern" $(find . -name "*.py")',
]

for cmd in test_cases:
    print("=" * 80)
    print(f"COMMAND: {cmd}")
    print("-" * 80)

    result = executor.execute({'command': cmd, 'description': 'debug'})

    # Extract what would be executed
    if "[TEST MODE]" in result:
        for line in result.split('\n'):
            if "Would execute:" in line:
                print(f"TRANSLATED: {line}")

    print()
