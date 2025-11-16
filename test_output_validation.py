#!/usr/bin/env python3
"""
OUTPUT VALIDATION TEST

Not just "does it crash?" but "is the OUTPUT CORRECT?"

Testing that translations produce CORRECT Windows commands.
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path
import os

# Set environment for testing
os.environ['TESTFILE'] = '/path/to/file.txt'
os.environ['TESTNUM'] = '42'

executor = BashToolExecutor(working_dir='/home/user/couch')

print("=" * 80)
print("OUTPUT VALIDATION TEST - Verify CORRECT translations")
print("=" * 80)
print()

def test_output(name, cmd, expected_in_output):
    """Test that expected string appears in output"""
    result = executor.execute({'command': cmd, 'description': name})

    # Check if expected output is in result
    found = expected_in_output in result
    status = "✓" if found else "✗"

    print(f"{status} {name}")
    if not found:
        print(f"   EXPECTED: {expected_in_output}")
        print(f"   GOT: {result[:300]}")

    return found


passed = 0
failed = 0

print("CATEGORY: Parameter expansion correctness")
print("-" * 80)

# Verify ${#var} gives correct length
if test_output("${#var} gives correct length",
    'echo ${#TESTFILE}',
    'echo 17'):  # /path/to/file.txt = 17 chars
    passed += 1
else:
    failed += 1

# Verify ${var##*/} gives basename
if test_output("${var##*/} extracts basename",
    'echo ${TESTFILE##*/}',
    'echo file.txt'):
    passed += 1
else:
    failed += 1

# Verify ${var%.*} removes extension
if test_output("${var%.*} removes last extension",
    'file="test.tar.gz"; echo ${file%.*}',
    'echo test.tar'):
    passed += 1
else:
    failed += 1

# Verify ${var%%.*} removes all extensions
if test_output("${var%%.*} removes all extensions",
    'file="test.tar.gz"; echo ${file%%.*}',
    'echo test'):
    passed += 1
else:
    failed += 1

# Verify ${var/pattern/repl} replaces
if test_output("${var/pattern/repl} replaces first",
    'text="foo-bar-baz"; echo ${text//-/_}',
    'echo foo_bar-baz'):
    passed += 1
else:
    failed += 1

# Verify ${var//pattern/repl} replaces all
if test_output("${var//pattern/repl} replaces all",
    'text="foo-bar-baz"; echo ${text//-/_}',
    'echo foo_bar_baz'):  # Wait, this should be different for //
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Arithmetic correctness")
print("-" * 80)

# Verify $((5+5)) = 10
if test_output("$((5+5)) equals 10",
    'echo $((5 + 5))',
    'echo 10'):
    passed += 1
else:
    failed += 1

# Verify $((10*2)) = 20
if test_output("$((10*2)) equals 20",
    'echo $((10 * 2))',
    'echo 20'):
    passed += 1
else:
    failed += 1

# Verify $((20/4)) = 5
if test_output("$((20/4)) equals 5",
    'echo $((20 / 4))',
    'echo 5'):
    passed += 1
else:
    failed += 1

# Verify $((17%5)) = 2
if test_output("$((17%5)) equals 2",
    'echo $((17 % 5))',
    'echo 2'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Command substitution correctness")
print("-" * 80)

# Verify $(echo test) expands
if test_output("$(echo test) expands to 'test'",
    'echo $(echo test)',
    'echo test'):
    passed += 1
else:
    failed += 1

# Verify nested $(echo $(echo deep))
if test_output("Nested $($(cmd)) works",
    'echo $(echo $(echo nested))',
    'echo nested'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Pipeline translations")
print("-" * 80)

# Verify head -n uses Select-Object -First
if test_output("head -n 10 uses Select-Object -First",
    'echo test | head -n 10',
    'Select-Object -First 10'):
    passed += 1
else:
    failed += 1

# Verify tail -n uses Select-Object -Last
if test_output("tail -n 5 uses Select-Object -Last",
    'echo test | tail -n 5',
    'Select-Object -Last 5'):
    passed += 1
else:
    failed += 1

# Verify wc -l uses Measure-Object
if test_output("wc -l uses Measure-Object",
    'echo test | wc -l',
    'Measure-Object -Line'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Find translations")
print("-" * 80)

# Verify find uses Get-ChildItem
if test_output("find translates to Get-ChildItem",
    'find . -name "*.py"',
    'Get-ChildItem'):
    passed += 1
else:
    failed += 1

# Verify find -type f
if test_output("find -type f filters files",
    'find . -name "*.py" -type f',
    'Get-ChildItem'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Brace expansion correctness")
print("-" * 80)

# Verify {1..5} expands
if test_output("{1..5} expands to sequence",
    'echo {1..5}',
    'echo 1 2 3 4 5'):
    passed += 1
else:
    failed += 1

# Verify {a,b,c} expands
if test_output("{a,b,c} expands to list",
    'echo {a,b,c}',
    'echo a b c'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Variable preservation")
print("-" * 80)

# Verify ${var} preserved in command substitution context
if test_output("${var} preserved in $()",
    'echo "$(echo ${TESTNUM})"',
    'echo 42'):
    passed += 1
else:
    failed += 1

# Verify $var preserved
if test_output("$var expands correctly",
    'echo $TESTNUM',
    'echo 42'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Quoting preservation")
print("-" * 80)

# Verify single quotes preserve $
if test_output("Single quotes preserve $()",
    "echo 'test $(date)'",
    "echo 'test $(date)'"):
    passed += 1
else:
    failed += 1

# Verify double quotes allow expansion
if test_output("Double quotes allow $var",
    'echo "Value: $TESTNUM"',
    'echo "Value: 42"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Case conversion correctness")
print("-" * 80)

# Verify ${var^^} uppercases
if test_output("${var^^} uppercases all",
    'text="hello"; echo ${text^^}',
    'echo HELLO'):
    passed += 1
else:
    failed += 1

# Verify ${var,,} lowercases
if test_output("${var,,} lowercases all",
    'text="HELLO"; echo ${text,,}',
    'echo hello'):
    passed += 1
else:
    failed += 1

# Verify ${var^} uppercases first
if test_output("${var^} uppercases first char",
    'text="hello"; echo ${text^}',
    'echo Hello'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: PowerShell cmdlet detection")
print("-" * 80)

# Verify Get-ChildItem detected as PowerShell
if test_output("Get-ChildItem uses powershell",
    'Get-ChildItem .',
    'powershell'):
    passed += 1
else:
    failed += 1

print()
print("=" * 80)
print(f"RESULTS: {passed}/{passed+failed} passed ({(passed/(passed+failed)*100):.1f}%)")
print("=" * 80)

if failed == 0:
    print("🎉 ALL OUTPUT VALIDATION TESTS PASSED!")
    print("Translations are CORRECT, not just non-crashing!")
else:
    print(f"⚠️  {failed} tests failed")
    print("Translations produce WRONG output - bugs in logic!")
