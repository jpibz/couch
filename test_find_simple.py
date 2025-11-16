#!/usr/bin/env python3
"""Test find translation"""

from bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

tests = [
    ('find . -name "*.py"', 'Get-ChildItem'),
    ('find . -name "*.py" -type f', 'Get-ChildItem'),
    ('find . -name "*.py" ! -path "*/venv/*"', 'Where-Object'),
]

for cmd, expected in tests:
    result = executor.execute({'command': cmd, 'description': 'test'})
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                output = line.split('Would execute:')[1].strip()
                has_expected = expected in output
                status = "✓" if has_expected else "✗"
                print(f"{status} {cmd[:50]}")
                if not has_expected:
                    print(f"   Expected: {expected}")
                    print(f"   Got: {output[:150]}")
                break
