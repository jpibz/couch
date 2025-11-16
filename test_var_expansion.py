#!/usr/bin/env python3
"""Test variable expansion"""

from bash_tool_executor import BashToolExecutor
import os

# Set test environment variables
os.environ['TESTNUM'] = '42'
os.environ['TESTFILE'] = '/path/to/file.txt'

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

tests = [
    'echo $TESTNUM',
    'echo ${TESTNUM}',
    'echo "Value: $TESTNUM"',
    'echo ${TESTFILE}',
]

for test in tests:
    print(f"\nTest: {test}")
    result = executor.execute({'command': test, 'description': 'test'})
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                output = line.split('Would execute:')[1].strip()
                print(f"Output: {output}")
                # Check if variable was expanded
                if '$' in output and 'TEST' in output:
                    print("  ❌ Variable NOT expanded")
                elif '42' in output or '/path/to/file.txt' in output:
                    print("  ✅ Variable expanded correctly")
