#!/usr/bin/env python3
"""Quick test for recent fixes"""

from bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

tests = [
    ("cat simple", 'cat bash_tool_executor.py', 'Get-Content'),
    ("grep -r recursive", 'grep -rn "class.*Executor" --include="*.py" .', 'Recurse'),
    ("sort in pipeline", 'echo -e "3\\n1\\n2" | sort', 'Sort-Object'),
    ("uniq in pipeline", 'echo -e "a\\na\\nb" | sort | uniq', 'Get-Unique'),
]

for name, cmd, expected in tests:
    result = executor.execute({'command': cmd, 'description': name})
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                output = line.split('Would execute:')[1].strip()
                has_expected = expected in output
                status = "✓" if has_expected else "✗"
                print(f"{status} {name}")
                if not has_expected:
                    print(f"   Expected: {expected}")
                    print(f"   Got: {output[:100]}")
                break
