#!/usr/bin/env python3
"""Test command substitution"""

from bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

test_cases = [
    ('cat $(find . -name "README.md" | head -1)', 'should show Get-Content with proper find'),
    ('echo "Files: $(find . -name "*.py" | wc -l)"', 'should count py files'),
]

for cmd, desc in test_cases:
    print(f"\n{'='*70}")
    print(f"Test: {desc}")
    print(f"CMD:  {cmd}")
    print(f"{'='*70}")
    result = executor.execute({'command': cmd, 'description': 'test'})
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                output = line.split('Would execute:')[1].strip()
                print(f"GOT:  {output}")
                break
    else:
        print(f"RESULT: {result[:200]}")
