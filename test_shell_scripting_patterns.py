#!/usr/bin/env python3
"""
SHELL SCRIPTING PATTERNS TEST

Testing advanced shell scripting constructs:
- Variable assignments and scoping
- Function definitions
- Case statements
- Loop variations
- Read operations
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

executor = BashToolExecutor(working_dir='/home/user/couch')

print("=" * 80)
print("SHELL SCRIPTING PATTERNS TEST")
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

print("CATEGORY: Variable assignments")
print("-" * 80)

if test("Simple assignment",
    'x=5; echo $x'):
    passed += 1
else:
    failed += 1

if test("Assignment with spaces in value",
    'msg="hello world"; echo $msg'):
    passed += 1
else:
    failed += 1

if test("Assignment from command",
    'result=$(echo test); echo $result'):
    passed += 1
else:
    failed += 1

if test("Multiple assignments",
    'a=1; b=2; c=3; echo $a $b $c'):
    passed += 1
else:
    failed += 1

if test("Assignment with arithmetic",
    'x=$((5 + 3)); echo $x'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Read from input")
print("-" * 80)

if test("Read single line",
    'echo "test" | { read line; echo "Line: $line"; }'):
    passed += 1
else:
    failed += 1

if test("Read multiple variables",
    'echo "a b c" | { read x y z; echo "$x-$y-$z"; }'):
    passed += 1
else:
    failed += 1

if test("Read with while loop",
    'echo -e "a\\nb\\nc" | while read line; do echo ">> $line"; done'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Case statements")
print("-" * 80)

if test("Case with single pattern",
    'case "test" in test) echo "matched";; esac'):
    passed += 1
else:
    failed += 1

if test("Case with multiple patterns",
    'case "b" in a) echo "a";; b) echo "b";; *) echo "other";; esac'):
    passed += 1
else:
    failed += 1

if test("Case with wildcard",
    'case "hello" in h*) echo "starts with h";; esac'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: For loop variations")
print("-" * 80)

if test("For with list",
    'for i in a b c; do echo $i; done'):
    passed += 1
else:
    failed += 1

if test("For with range",
    'for i in {1..5}; do echo $i; done'):
    passed += 1
else:
    failed += 1

if test("For with command substitution",
    'for f in $(echo "a b c"); do echo $f; done'):
    passed += 1
else:
    failed += 1

if test("For with glob",
    'for f in *.py; do echo $f; done | head -3'):
    passed += 1
else:
    failed += 1

if test("C-style for loop",
    'for ((i=0; i<3; i++)); do echo $i; done'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: While loop variations")
print("-" * 80)

if test("While with counter",
    'i=0; while [ $i -lt 3 ]; do echo $i; i=$((i + 1)); done'):
    passed += 1
else:
    failed += 1

if test("While true with break",
    'i=0; while true; do echo $i; i=$((i + 1)); [ $i -ge 3 ] && break; done'):
    passed += 1
else:
    failed += 1

if test("While read with pipe",
    'echo -e "1\\n2\\n3" | while read n; do echo "Num: $n"; done'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Until loops")
print("-" * 80)

if test("Until basic",
    'i=0; until [ $i -ge 3 ]; do echo $i; i=$((i + 1)); done'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: If-then-else variations")
print("-" * 80)

if test("If with test command",
    'if test -f bash_tool_executor.py; then echo "exists"; fi'):
    passed += 1
else:
    failed += 1

if test("If-elif-else",
    'x=2; if [ $x -eq 1 ]; then echo "one"; elif [ $x -eq 2 ]; then echo "two"; else echo "other"; fi'):
    passed += 1
else:
    failed += 1

if test("If with command success",
    'if echo "test" > /dev/null; then echo "success"; fi'):
    passed += 1
else:
    failed += 1

if test("Nested if",
    'if true; then if [ 1 -eq 1 ]; then echo "nested true"; fi; fi'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Boolean operators")
print("-" * 80)

if test("AND operator in test",
    '[ 1 -eq 1 ] && [ 2 -eq 2 ] && echo "both true"'):
    passed += 1
else:
    failed += 1

if test("OR operator in test",
    '[ 1 -eq 2 ] || [ 2 -eq 2 ] && echo "one true"'):
    passed += 1
else:
    failed += 1

if test("NOT operator",
    '[ ! 1 -eq 2 ] && echo "not equal"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: String operations")
print("-" * 80)

if test("String length",
    'str="hello"; echo ${#str}'):
    passed += 1
else:
    failed += 1

if test("String concatenation",
    'a="hello"; b="world"; echo "$a $b"'):
    passed += 1
else:
    failed += 1

if test("String contains check",
    '[[ "hello world" == *world* ]] && echo "contains"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Array operations (basic)")
print("-" * 80)

if test("Array-like with for",
    'for item in "a" "b" "c"; do echo $item; done'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Export and environment")
print("-" * 80)

if test("Export variable",
    'export TEST_VAR=value; echo $TEST_VAR'):
    passed += 1
else:
    failed += 1

if test("Env variable access",
    'echo $PATH | head -c 10'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Command grouping and subshells")
print("-" * 80)

if test("Group with braces",
    '{ echo "line1"; echo "line2"; } | wc -l'):
    passed += 1
else:
    failed += 1

if test("Subshell preserves parent",
    'x=1; (x=2; echo $x); echo $x'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Special variables")
print("-" * 80)

if test("Exit status $?",
    'true; echo $?'):
    passed += 1
else:
    failed += 1

if test("Process ID $$",
    'echo $$ | grep -E "^[0-9]+$"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Command line arguments simulation")
print("-" * 80)

if test("Positional parameter simulation",
    'set -- a b c; echo $1 $2 $3'):
    passed += 1
else:
    failed += 1

if test("Argument count",
    'set -- a b c; echo $#'):
    passed += 1
else:
    failed += 1

print()
print("=" * 80)
print(f"RESULTS: {passed}/{passed+failed} passed ({(passed/(passed+failed)*100):.1f}%)")
print("=" * 80)

if failed == 0:
    print("🎉 ALL SHELL SCRIPTING PATTERNS PASSED!")
else:
    print(f"⚠️  {failed} tests failed - BUGS FOUND")
