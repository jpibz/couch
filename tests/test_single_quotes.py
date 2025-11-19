#!/usr/bin/env python3
"""Test single quote preservation"""

from bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

tests = [
    "echo 'test $(date)'",
    'echo "test $(date)"',
    "echo 'literal text'",
]

for test in tests:
    print(f"\n{'='*60}")
    print(f"Test: {test}")
    result = executor.execute({'command': test, 'description': 'test'})
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                print(f"Output: {line.split('Would execute:')[1].strip()}")
    print(f"{'='*60}")
