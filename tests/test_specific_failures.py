#!/usr/bin/env python3
"""Test specific failing patterns"""

from bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

tests = [
    "grep -B 2 -A 2 'def execute' bash_tool_executor.py",
    "cat README.md",
    "echo test | xargs grep def",
]

for cmd in tests:
    print(f"\n{'='*70}")
    print(f"Command: {cmd}")
    print(f"{'='*70}")
    result = executor.execute({'command': cmd, 'description': 'test'})
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                output = line.split('Would execute:')[1].strip()
                print(f"Output:\n  {output}")
                break
