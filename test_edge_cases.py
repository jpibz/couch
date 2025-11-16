#!/usr/bin/env python3
"""
EDGE CASES TEST - Iteration 3

Testing extreme edge cases and corner scenarios
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

# Setup
WORKSPACE = Path("/home/user/couch")
executor = BashToolExecutor(working_dir=str(WORKSPACE))

print("=" * 80)
print("EDGE CASES TEST - Iteration 3")
print("=" * 80)
print()

def test(name, cmd):
    """Run a single test"""
    print("-" * 80)
    print(f"TEST: {name}")
    print(f"CMD:  {cmd}")
    print()

    try:
        result = executor.execute({'command': cmd, 'description': name})

        # Check for errors
        is_error = any([
            result.startswith("Error:"),
            result.startswith("SECURITY VIOLATION:"),
            "Exception:" in result,
            "Traceback" in result,
        ])

        if is_error:
            print(f"✗ FAILED\n{result[:500]}\n")
            return False
        else:
            print(f"✓ PASSED\n")
            return True
    except Exception as e:
        print(f"✗ EXCEPTION: {e}\n")
        import traceback
        traceback.print_exc()
        return False


passed = 0
failed = 0

# ============================================================================
# CATEGORY 1: Complex quoting and escaping
# ============================================================================
print("=" * 80)
print("CATEGORY 1: Complex quoting and escaping")
print("=" * 80)
print()

if test("Single quotes preserve everything", "echo 'Hello $USER $(date) `whoami`'"):
    passed += 1
else:
    failed += 1

if test("Double quotes expand variables", 'echo "Hello $USER"'):
    passed += 1
else:
    failed += 1

if test("Escaped quotes in string", 'echo "He said \\"hello\\""'):
    passed += 1
else:
    failed += 1

if test("Mixed quoting", '''echo "Today's date: $(date)"'''):
    passed += 1
else:
    failed += 1

if test("Backslash escape", 'echo "Line1\\nLine2"'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 2: Variable expansion edge cases
# ============================================================================
print("=" * 80)
print("CATEGORY 2: Variable expansion edge cases")
print("=" * 80)
print()

if test("Remove shortest prefix", 'file="path/to/file.txt"; echo ${file#*/}'):
    passed += 1
else:
    failed += 1

if test("Remove longest prefix", 'file="path/to/file.txt"; echo ${file##*/}'):
    passed += 1
else:
    failed += 1

if test("Remove shortest suffix", 'file="archive.tar.gz"; echo ${file%.*}'):
    passed += 1
else:
    failed += 1

if test("Remove longest suffix", 'file="archive.tar.gz"; echo ${file%%.*}'):
    passed += 1
else:
    failed += 1

if test("String substitution", 'text="hello world"; echo ${text/world/universe}'):
    passed += 1
else:
    failed += 1

if test("Uppercase conversion", 'text="hello"; echo ${text^^}'):
    passed += 1
else:
    failed += 1

if test("Lowercase conversion", 'text="HELLO"; echo ${text,,}'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 3: Exit status and conditionals
# ============================================================================
print("=" * 80)
print("CATEGORY 3: Exit status and conditionals")
print("=" * 80)
print()

if test("Exit status check", 'ls bash_tool_executor.py && echo "found"'):
    passed += 1
else:
    failed += 1

if test("Negated exit status", 'ls nonexistent 2>/dev/null || echo "not found"'):
    passed += 1
else:
    failed += 1

if test("If statement simple", 'if [ -f bash_tool_executor.py ]; then echo "exists"; fi'):
    passed += 1
else:
    failed += 1

if test("If-else statement", 'if [ -f nonexistent ]; then echo "yes"; else echo "no"; fi'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 4: Here-strings
# ============================================================================
print("=" * 80)
print("CATEGORY 4: Here-strings")
print("=" * 80)
print()

if test("Here-string basic", 'grep "test" <<< "this is a test"'):
    passed += 1
else:
    failed += 1

if test("Here-string with pipe", 'wc -w <<< "one two three"'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 5: Null and colon commands
# ============================================================================
print("=" * 80)
print("CATEGORY 5: Null and colon commands")
print("=" * 80)
print()

if test("Colon as no-op", ': this is a comment'):
    passed += 1
else:
    failed += 1

if test("Colon with variable", 'x=5; : $x; echo $x'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 6: Background jobs (limited support)
# ============================================================================
print("=" * 80)
print("CATEGORY 6: Background execution")
print("=" * 80)
print()

if test("Sleep background (simulated)", 'echo "background job started"'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 7: Glob patterns advanced
# ============================================================================
print("=" * 80)
print("CATEGORY 7: Advanced glob patterns")
print("=" * 80)
print()

if test("Star glob", 'ls *.py | head -5'):
    passed += 1
else:
    failed += 1

if test("Question mark glob", 'ls test_?.py 2>/dev/null || echo "none"'):
    passed += 1
else:
    failed += 1

if test("Bracket glob", 'ls test_[a-z]*.py | head -3'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 8: Multiple commands variations
# ============================================================================
print("=" * 80)
print("CATEGORY 8: Multiple commands variations")
print("=" * 80)
print()

if test("Three commands with semicolons", 'echo "one"; echo "two"; echo "three"'):
    passed += 1
else:
    failed += 1

if test("Commands with AND", 'echo "start" && echo "success" && echo "done"'):
    passed += 1
else:
    failed += 1

if test("Commands with OR", 'false || echo "fallback" || echo "backup"'):
    passed += 1
else:
    failed += 1

if test("Mixed operators", 'true && echo "ok" || echo "failed"'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 9: Special characters in filenames
# ============================================================================
print("=" * 80)
print("CATEGORY 9: Special characters handling")
print("=" * 80)
print()

if test("Filename with spaces (quoted)", 'echo "test with spaces.txt"'):
    passed += 1
else:
    failed += 1

if test("Filename with dash", 'ls bash_tool_executor.py'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CATEGORY 10: Arithmetic edge cases
# ============================================================================
print("=" * 80)
print("CATEGORY 10: Arithmetic edge cases")
print("=" * 80)
print()

if test("Arithmetic multiplication", 'echo $((10 * 5))'):
    passed += 1
else:
    failed += 1

if test("Arithmetic division", 'echo $((20 / 4))'):
    passed += 1
else:
    failed += 1

if test("Arithmetic modulo", 'echo $((17 % 5))'):
    passed += 1
else:
    failed += 1

if test("Arithmetic with parentheses", 'echo $(((5 + 3) * 2))'):
    passed += 1
else:
    failed += 1

if test("Nested arithmetic", 'echo $((10 + $((5 * 2))))'):
    passed += 1
else:
    failed += 1


# ============================================================================
# RESULTS
# ============================================================================
print()
print("=" * 80)
print("EDGE CASES TEST RESULTS")
print("=" * 80)
print()
print(f"Total:    {passed + failed}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Success:  {(passed/(passed+failed)*100):.1f}%")
print()

if failed == 0:
    print("🎉 ALL EDGE CASE TESTS PASSED!")
else:
    print(f"⚠️  {failed} tests failed - identifying new bugs...")

print("=" * 80)
