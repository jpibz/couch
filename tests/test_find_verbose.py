#!/usr/bin/env python3
"""Verbose find test"""

from bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

cmd = 'find . -name "*.py" ! -path "*/venv/*"'
result = executor.execute({'command': cmd, 'description': 'test'})

print(f"Command: {cmd}")
print(f"\nResult:")
for line in result.split('\n'):
    if 'Would execute:' in line:
        output = line.split('Would execute:')[1].strip()
        print(output)
