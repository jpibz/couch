#!/usr/bin/env python3
"""
EXTREME ACROBATIC PATTERNS TEST

Testing the MOST COMPLEX patterns that Claude actually uses in real work:
- Multi-level nesting
- Complex combinations
- Edge cases that break systems
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

executor = BashToolExecutor(working_dir='/home/user/couch')

print("=" * 80)
print("EXTREME ACROBATIC PATTERNS TEST")
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
            print(f"   CMD: {cmd[:100]}")
            print(f"   ERROR: {result[:300]}")
        return not is_error
    except Exception as e:
        print(f"✗ {name}")
        print(f"   CMD: {cmd[:100]}")
        print(f"   EXCEPTION: {str(e)[:200]}")
        return False


passed = 0
failed = 0

print("CATEGORY: Multi-level command substitution nesting")
print("-" * 80)

# Test deeply nested command substitution
if test("Triple nested $($($(cmd)))",
    'echo "Result: $(echo "Level2: $(echo "Level3: $(echo deep)")")"'):
    passed += 1
else:
    failed += 1

# Test command substitution with pipeline inside
if test("Command subst with pipeline",
    'echo "Count: $(find . -name "*.py" | grep -v __pycache__ | wc -l)"'):
    passed += 1
else:
    failed += 1

# Test command substitution with arithmetic
if test("Command subst with arithmetic inside",
    'echo "Result: $(echo $((10 + $(echo 5))))"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Complex parameter expansion combinations")
print("-" * 80)

# Test chained parameter operations
if test("Multiple param expansions in sequence",
    'file="/path/to/archive.tar.gz"; base=${file##*/}; name=${base%%.*}; echo $name'):
    passed += 1
else:
    failed += 1

# Test param expansion in command substitution
if test("Param expansion inside $()",
    'path="/home/user/file.txt"; echo "Dir: $(echo ${path%/*})"'):
    passed += 1
else:
    failed += 1

# Test complex substitution pattern
if test("Complex string substitution",
    'text="foo-bar-baz"; echo ${text//-/_}'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Pipeline extremes")
print("-" * 80)

# Test 5-stage pipeline
if test("5-stage pipeline",
    'find . -name "*.py" | grep -v test | head -10 | sort | wc -l'):
    passed += 1
else:
    failed += 1

# Test pipeline with multiple greps
if test("Multiple grep filters in pipeline",
    'cat bash_tool_executor.py | grep def | grep -v "^#" | grep -v "__" | head -5'):
    passed += 1
else:
    failed += 1

# Test pipeline with arithmetic in middle
if test("Pipeline with arithmetic",
    'seq 1 100 | head -n $((20 + 10)) | tail -n 10 | wc -l'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Find with complex conditions")
print("-" * 80)

# Test find with multiple -name patterns
if test("Find with OR conditions",
    'find . \\( -name "*.py" -o -name "*.md" \\) -type f | head -5'):
    passed += 1
else:
    failed += 1

# Test find with AND conditions
if test("Find with AND conditions",
    'find . -name "*.py" -type f -size +1k | head -5'):
    passed += 1
else:
    failed += 1

# Test find with negation
if test("Find with negation",
    'find . -name "*.py" ! -path "*__pycache__*" -type f | head -10'):
    passed += 1
else:
    failed += 1

# Test find with exec and substitution
if test("Find exec with command substitution",
    'find . -name "test_*.py" -exec echo "Found: {}" \\;| head -3'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Sed/awk complexity")
print("-" * 80)

# Test sed with multiple substitutions
if test("Sed multiple operations",
    'echo "hello world" | sed "s/hello/hi/; s/world/universe/"'):
    passed += 1
else:
    failed += 1

# Test awk with multiple conditions
if test("Awk with complex pattern",
    'echo -e "1 a\\n2 b\\n3 c" | awk \'$1 > 1 {print $2}\''):
    passed += 1
else:
    failed += 1

# Test awk with BEGIN/END
if test("Awk with BEGIN and END",
    'echo -e "1\\n2\\n3" | awk \'BEGIN {sum=0} {sum+=$1} END {print sum}\''):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Quoting nightmares")
print("-" * 80)

# Test nested quotes
if test("Nested double and single quotes",
    """echo "He said 'hello world' today" """):
    passed += 1
else:
    failed += 1

# Test escaped quotes in command substitution
if test("Escaped quotes in $()",
    'echo "Result: $(echo \\"quoted\\")"'):
    passed += 1
else:
    failed += 1

# Test single quotes preserving everything
if test("Single quotes preserve $() and $var",
    "echo 'Literal: $(date) and $HOME'"):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Redirection complexity")
print("-" * 80)

# Test stderr and stdout merge
if test("Merge stderr to stdout",
    'grep "pattern" nonexistent.txt 2>&1 | head -1'):
    passed += 1
else:
    failed += 1

# Test redirect stderr to null
if test("Stderr to /dev/null",
    'ls nonexistent 2>/dev/null || echo "failed"'):
    passed += 1
else:
    failed += 1

# Test append redirection
if test("Append redirection",
    'echo "test" >> /tmp/test.log 2>&1'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Conditionals with complex tests")
print("-" * 80)

# Test file existence with AND
if test("File test with AND",
    '[ -f bash_tool_executor.py ] && [ -s bash_tool_executor.py ] && echo "exists and non-empty"'):
    passed += 1
else:
    failed += 1

# Test string comparison in pipeline
if test("String test in conditional",
    'if [ "$(echo test)" = "test" ]; then echo "match"; fi'):
    passed += 1
else:
    failed += 1

# Test numeric comparison with arithmetic
if test("Numeric test with arithmetic",
    '[ $((5 + 5)) -eq 10 ] && echo "correct"'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Background jobs and job control")
print("-" * 80)

# Test simple background (simulation)
if test("Background job simulation",
    'echo "Job started" # Simulated: sleep 1 &'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Alias and function expansion")
print("-" * 80)

# Test common alias
if test("ll alias",
    'll'):
    passed += 1
else:
    failed += 1

# Test la alias
if test("la alias",
    'la'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Wildcard and glob patterns")
print("-" * 80)

# Test multiple wildcards
if test("Multiple wildcards",
    'ls test_*.py | head -5'):
    passed += 1
else:
    failed += 1

# Test character class
if test("Character class glob",
    'ls test_[a-z]*.py 2>/dev/null | head -3'):
    passed += 1
else:
    failed += 1

# Test negation in glob
if test("Negation in glob",
    'ls *.py | grep -v test | head -5'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Process substitution extremes")
print("-" * 80)

# Test process subst with pipeline
if test("Process subst with pipeline",
    'diff <(cat file1 | sort) <(cat file2 | sort)'):
    passed += 1
else:
    failed += 1

# Test process subst with command substitution
if test("Process subst with command subst",
    'cat <(echo "$(date)")'):
    passed += 1
else:
    failed += 1

print()
print("CATEGORY: Everything combined (nightmare mode)")
print("-" * 80)

# Test mega-pipeline with everything
if test("Mega complex pipeline",
    'find . -name "*.py" -type f ! -path "*__pycache__*" -exec grep -l "def " {} \\; | head -n $((5 + 5)) | while read f; do echo "File: ${f##*/}"; done'):
    passed += 1
else:
    failed += 1

# Test nested everything
if test("Nested command subst + param expansion + pipeline",
    'file="$(find . -name "*.py" | head -1)"; echo "Base: ${file##*/}" | sed "s/\\.py//"'):
    passed += 1
else:
    failed += 1

# Test complex conditional with everything
if test("Complex conditional chain",
    '[ -f "$(echo bash_tool_executor.py)" ] && echo "Count: $(wc -l < bash_tool_executor.py | head -1)" || echo "not found"'):
    passed += 1
else:
    failed += 1

print()
print("=" * 80)
print(f"RESULTS: {passed}/{passed+failed} passed ({(passed/(passed+failed)*100):.1f}%)")
print("=" * 80)

if failed == 0:
    print("🎉 ALL EXTREME ACROBATIC TESTS PASSED!")
else:
    print(f"⚠️  {failed} tests failed - MORE BUGS FOUND")
    print("Continue fixing...")
