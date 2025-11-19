#!/usr/bin/env python3
"""
Test FIX #7: Advanced parameter expansion - CORRECTED
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path
import os

# Setup test environment variables
os.environ['TESTFILE'] = '/path/to/file.txt'
os.environ['TESTARCHIVE'] = 'archive.tar.gz'
os.environ['TESTTEXT'] = 'hello world'
os.environ['TESTDUP'] = 'aa bb aa'
os.environ['TESTUPPER'] = 'HELLO'
os.environ['TESTLOWER'] = 'hello'
os.environ['TESTLEN'] = 'hello'

executor = BashToolExecutor(working_dir='/home/user/couch')

print("=" * 80)
print("FIX #7: ADVANCED PARAMETER EXPANSION TEST")
print("=" * 80)
print()

def test(name, cmd, expected_in_result):
    """Run a test and check if expected string is in result"""
    result = executor.execute({'command': cmd, 'description': name})

    success = expected_in_result in result
    status = "✓" if success else "✗"

    print(f"{status} {name}")
    if not success:
        print(f"   CMD:      {cmd}")
        print(f"   EXPECTED: {expected_in_result}")
        print(f"   RESULT:   {result[:200]}")
    print()

    return success


passed = 0
failed = 0

# Test ${#var} - string length
if test("String length ${#var}",
        'echo ${#TESTLEN}',
        'echo 5'):
    passed += 1
else:
    failed += 1

# Test ${var#pattern} - remove shortest prefix
if test("Remove shortest prefix ${var#*/}",
        'echo ${TESTFILE#*/}',
        'echo path/to/file.txt'):
    passed += 1
else:
    failed += 1

# Test ${var##pattern} - remove longest prefix
if test("Remove longest prefix ${var##*/}",
        'echo ${TESTFILE##*/}',
        'echo file.txt'):
    passed += 1
else:
    failed += 1

# Test ${var%pattern} - remove shortest suffix
if test("Remove shortest suffix ${var%.*}",
        'echo ${TESTARCHIVE%.*}',
        'echo archive.tar'):
    passed += 1
else:
    failed += 1

# Test ${var%%pattern} - remove longest suffix
if test("Remove longest suffix ${var%%.*}",
        'echo ${TESTARCHIVE%%.*}',
        'echo archive'):
    passed += 1
else:
    failed += 1

# Test ${var/pattern/string} - replace first
if test("Replace first ${var/pattern/repl}",
        'echo ${TESTTEXT/world/universe}',
        'echo hello universe'):
    passed += 1
else:
    failed += 1

# Test ${var//pattern/string} - replace all
if test("Replace all ${var//pattern/repl}",
        'echo ${TESTDUP//aa/XX}',
        'echo XX bb XX'):
    passed += 1
else:
    failed += 1

# Test ${var^^} - uppercase all
if test("Uppercase all ${var^^}",
        'echo ${TESTLOWER^^}',
        'echo HELLO'):
    passed += 1
else:
    failed += 1

# Test ${var,,} - lowercase all
if test("Lowercase all ${var,,}",
        'echo ${TESTUPPER,,}',
        'echo hello'):
    passed += 1
else:
    failed += 1

# Test ${var^} - uppercase first
if test("Uppercase first ${var^}",
        'echo ${TESTLOWER^}',
        'echo Hello'):
    passed += 1
else:
    failed += 1

print("=" * 80)
print(f"RESULTS: {passed}/{passed+failed} passed ({(passed/(passed+failed)*100):.1f}%)")
print("=" * 80)

if failed == 0:
    print("🎉 ALL PARAMETER EXPANSION TESTS PASSED!")
else:
    print(f"⚠️  {failed} tests failed")
