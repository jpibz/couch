#!/usr/bin/env python3
"""
EDGE CASES V2 - Extreme corner cases

Testing patterns that typically break bash emulators:
- Backticks vs $()
- Input redirection
- Empty strings
- Special characters
- Malformed commands
- Boundary conditions
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

executor = BashToolExecutor(working_dir='/home/user/couch')

print("=" * 80)
print("EDGE CASES V2 TEST")
print("=" * 80)
print()

def test(name, cmd):
    """Run test and check for errors"""
    try:
        result = executor.execute({'command': cmd, 'description': name})
        is_error = any([
            result.startswith("Error:"),
            result.startswith("SECURITY VIOLATION:"),
            "Exception:" in result,
            "Traceback" in result,
        ])
        status = "✓" if not is_error else "✗"
        print(f"{status} {name}")
        if is_error:
            print(f"   ERROR: {result[:200]}")
        return not is_error
    except Exception as e:
        print(f"✗ {name}")
        print(f"   EXCEPTION: {str(e)[:200]}")
        return False


passed = 0
failed = 0

print("CATEGORY: Backticks (legacy command substitution)")
print("-" * 80)

# Backticks should work like $()
if test("Simple backticks",
    'echo `date`'):
    passed += 1
else:
    failed += 1

if test("Nested backticks",
    'echo `echo \`date\``'):
    passed += 1
else:
    failed += 1

if test("Backticks in string",
    'echo "Today: `date`"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Input redirection")
print("-" * 80)

if test("Input redirect from file",
    'wc -l < bash_tool_executor.py'):
    passed += 1
else:
    failed += 1

if test("Input redirect with pipeline",
    'cat < bash_tool_executor.py | head -5'):
    passed += 1
else:
    failed += 1

if test("Here-string simple",
    'wc -w <<< "hello world test"'):
    passed += 1
else:
    failed += 1

if test("Here-string with variable",
    'text="hello world"; wc -w <<< "$text"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Empty and whitespace")
print("-" * 80)

if test("Empty string echo",
    'echo ""'):
    passed += 1
else:
    failed += 1

if test("Multiple spaces",
    'echo "a    b    c"'):
    passed += 1
else:
    failed += 1

if test("Tab characters",
    'echo "a\tb\tc"'):
    passed += 1
else:
    failed += 1

if test("Newline in string",
    'echo -e "line1\\nline2"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Special characters in filenames")
print("-" * 80)

if test("Spaces in filename (quoted)",
    'echo "file name with spaces.txt"'):
    passed += 1
else:
    failed += 1

if test("Dash in filename",
    'ls bash_tool_executor.py'):
    passed += 1
else:
    failed += 1

if test("Underscore in filename",
    'ls test_extreme_acrobatics.py'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Command chaining edge cases")
print("-" * 80)

if test("Empty command in chain",
    'true && echo "success"'):
    passed += 1
else:
    failed += 1

if test("False in OR chain",
    'false || echo "fallback"'):
    passed += 1
else:
    failed += 1

if test("Multiple semicolons",
    'echo "a"; echo "b"; echo "c"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Arithmetic edge cases")
print("-" * 80)

if test("Arithmetic with zero",
    'echo $((0 + 0))'):
    passed += 1
else:
    failed += 1

if test("Arithmetic with negative",
    'echo $((-5 + 10))'):
    passed += 1
else:
    failed += 1

if test("Arithmetic with spaces",
    'echo $(( 5 + 3 ))'):
    passed += 1
else:
    failed += 1

if test("Arithmetic division by 1",
    'echo $((10 / 1))'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Parameter expansion edge cases")
print("-" * 80)

if test("Empty variable expansion",
    'unset VAR; echo ${VAR:-default}'):
    passed += 1
else:
    failed += 1

if test("Variable with underscores",
    'MY_VAR=test; echo $MY_VAR'):
    passed += 1
else:
    failed += 1

if test("Variable with numbers",
    'VAR123=test; echo $VAR123'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Pipe edge cases")
print("-" * 80)

if test("Pipe to cat (no-op)",
    'echo "test" | cat'):
    passed += 1
else:
    failed += 1

if test("Empty pipe input",
    'echo "" | wc -l'):
    passed += 1
else:
    failed += 1

if test("Pipe with no output",
    'echo "" | grep nonexistent || echo "not found"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Subshell edge cases")
print("-" * 80)

if test("Empty subshell",
    '(true)'):
    passed += 1
else:
    failed += 1

if test("Subshell with variable",
    '(x=5; echo $x)'):
    passed += 1
else:
    failed += 1

if test("Nested subshells",
    '((echo "nested"))'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Glob pattern edge cases")
print("-" * 80)

if test("Glob with no matches",
    'ls *.nonexistent 2>/dev/null || echo "none"'):
    passed += 1
else:
    failed += 1

if test("Glob with single char",
    'ls ?.py 2>/dev/null || echo "none"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Find edge cases")
print("-" * 80)

if test("Find with maxdepth",
    'find . -maxdepth 1 -name "*.py" | head -5'):
    passed += 1
else:
    failed += 1

if test("Find with mindepth",
    'find . -mindepth 1 -name "*.py" | head -5'):
    passed += 1
else:
    failed += 1

if test("Find empty name pattern",
    'find . -name "" 2>/dev/null || echo "invalid"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Grep edge cases")
print("-" * 80)

if test("Grep empty pattern",
    'echo "test" | grep ""'):
    passed += 1
else:
    failed += 1

if test("Grep with line number 0",
    'grep -n "def" bash_tool_executor.py | head -1'):
    passed += 1
else:
    failed += 1

if test("Grep case insensitive empty",
    'echo "TEST" | grep -i "test"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Sed edge cases")
print("-" * 80)

if test("Sed with empty replacement",
    'echo "hello world" | sed "s/world//"'):
    passed += 1
else:
    failed += 1

if test("Sed with no match",
    'echo "hello" | sed "s/xyz/abc/"'):
    passed += 1
else:
    failed += 1

if test("Sed delete all lines",
    'echo -e "a\\nb\\nc" | sed "d"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Awk edge cases")
print("-" * 80)

if test("Awk print nothing",
    'echo "test" | awk \'0\''):
    passed += 1
else:
    failed += 1

if test("Awk with empty input",
    'echo "" | awk \'{print NF}\''):
    passed += 1
else:
    failed += 1

if test("Awk field beyond bounds",
    'echo "a b" | awk \'{print $10}\''):
    passed += 1
else:
    failed += 1

print()
print("=" * 80)
print(f"RESULTS: {passed}/{passed+failed} passed ({(passed/(passed+failed)*100):.1f}%)")
print("=" * 80)

if failed == 0:
    print("🎉 ALL EDGE CASES V2 PASSED!")
else:
    print(f"⚠️  {failed} tests failed - MORE BUGS FOUND")
