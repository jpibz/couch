#!/usr/bin/env python3
"""Test variable assignment chains"""

from bash_tool_executor import BashToolExecutor
import os

# Clear any existing test variables
for key in list(os.environ.keys()):
    if key.startswith('file') or key.startswith('text'):
        del os.environ[key]

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

# Enable debug to see variable assignments
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

tests = [
    ('file="test.tar.gz"; echo ${file%.*}', 'echo test.tar'),
    ('file="test.tar.gz"; echo ${file%%.*}', 'echo test'),
    ('text="hello"; echo ${text^^}', 'echo HELLO'),
    ('x=5; y=10; echo $x $y', 'echo 5 10'),
]

print("=" * 60)
print("VARIABLE ASSIGNMENT CHAIN TESTS")
print("=" * 60)

for test_cmd, expected in tests:
    print(f"\nTest: {test_cmd}")
    print(f"Expected: {expected}")
    result = executor.execute({'command': test_cmd, 'description': 'test'})
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                output = line.split('Would execute:')[1].strip()
                print(f"Got: {output}")
                if expected in output:
                    print("  ✅ PASS")
                else:
                    print("  ❌ FAIL")
