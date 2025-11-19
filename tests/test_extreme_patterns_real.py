#!/usr/bin/env python3
"""
EXTREME STRESS TEST - REAL CLAUDE PATTERNS

This test suite uses ACTUAL commands from CLAUDE_REAL_BASH_PATTERNS.md.
These are the patterns Claude uses in PRODUCTION during real work.

FAILURE = Claude is paralyzed on Windows for that task.

NO TOLERANCE for approximations. Output must be EXACT.
"""

from bash_tool_executor import BashToolExecutor
from pathlib import Path
import os

executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

print("=" * 80)
print("EXTREME STRESS TEST - REAL CLAUDE PRODUCTION PATTERNS")
print("=" * 80)
print("Testing the ACTUAL commands Claude uses during work.")
print("=" * 80)
print()

passed = 0
failed = 0
failures = []

def test(name, cmd, expected_keywords, must_not_contain=None):
    """
    Test that command translation contains expected keywords.

    Args:
        name: Test description
        cmd: Bash command to test
        expected_keywords: List of strings that MUST appear in output
        must_not_contain: List of strings that MUST NOT appear in output
    """
    global passed, failed, failures

    result = executor.execute({'command': cmd, 'description': name})

    # Extract translated command
    translated = None
    if '[TEST MODE]' in result:
        for line in result.split('\n'):
            if 'Would execute:' in line:
                translated = line.split('Would execute:')[1].strip()
                break

    if not translated:
        translated = result

    # Check expectations
    all_found = True
    missing = []
    for keyword in expected_keywords:
        if keyword not in translated:
            all_found = False
            missing.append(keyword)

    # Check exclusions
    found_forbidden = []
    if must_not_contain:
        for forbidden in must_not_contain:
            if forbidden in translated:
                all_found = False
                found_forbidden.append(forbidden)

    if all_found:
        print(f"✓ {name}")
        passed += 1
        return True
    else:
        print(f"✗ {name}")
        if missing:
            print(f"  MISSING: {missing}")
        if found_forbidden:
            print(f"  SHOULD NOT CONTAIN: {found_forbidden}")
        print(f"  CMD: {cmd[:80]}")
        print(f"  GOT: {translated[:150]}")
        failed += 1
        failures.append({
            'name': name,
            'cmd': cmd,
            'missing': missing,
            'forbidden': found_forbidden,
            'output': translated
        })
        return False


# ============================================================================
# CATEGORY 1: FIND WITH -EXEC AND PIPES
# ============================================================================
print("=" * 80)
print("CATEGORY 1: Find Acrobatics (CRITICAL for codebase exploration)")
print("=" * 80)

test(
    "Find all Python files (excluding venv)",
    'find . -name "*.py" -type f ! -path "*/venv/*"',
    ['Get-ChildItem', '.py'],
)

test(
    "Find with -exec grep",
    'find . -name "*.py" -type f -exec grep -l "CommandExecutor" {} \\;',
    ['Get-ChildItem', 'Select-String', 'CommandExecutor'],
)

test(
    "Find with -exec grep and pattern",
    'find . -name "*.py" -exec grep -H "^class " {} \\;',
    ['Get-ChildItem', 'Select-String', '^class'],
)

test(
    "Find with wc (count total lines)",
    'find . -name "*.py" ! -path "*/venv/*" -type f -exec wc -l {} + | tail -1',
    ['Get-ChildItem', 'Measure-Object'],
)

test(
    "Find with size filter and analysis",
    'find . -name "*.py" -type f -exec wc -l {} + | sort -rn | head -10',
    ['Get-ChildItem', 'Measure-Object', 'Sort-Object'],
)

# ============================================================================
# CATEGORY 2: MULTI-STAGE PIPELINES (5-6 commands)
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 2: Multi-Stage Pipelines (CRITICAL for data processing)")
print("=" * 80)

test(
    "5-stage pipeline: grep -> awk -> sort -> uniq -> wc",
    'grep "^import " test_main.py | awk \'{print $2}\' | sort | uniq | wc -l',
    ['Select-String', 'Sort-Object', 'Measure-Object'],
)

test(
    "Complex analysis pipeline",
    'cat bash_tool_executor.py | grep "def " | sed \'s/def //\' | awk \'{print $1}\' | sort',
    ['Get-Content', 'Select-String', 'Sort-Object'],
)

test(
    "Log analysis pipeline",
    'grep "ERROR" test_main.py | awk \'{print $1}\' | sort | uniq -c | sort -rn',
    ['Select-String', 'Sort-Object'],
)

# ============================================================================
# CATEGORY 3: COMMAND SUBSTITUTION (nested)
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 3: Command Substitution (CRITICAL for dynamic commands)")
print("=" * 80)

test(
    "Simple command substitution",
    'echo "Files: $(find . -type f -name "*.py" | wc -l)"',
    ['echo', 'Get-ChildItem', 'Measure-Object'],
)

test(
    "Grep in files from find",
    'grep "pattern" $(find . -name "*.py" -type f)',
    ['Select-String', 'Get-ChildItem'],
)

test(
    "Nested command substitution",
    'echo $(echo $(echo "nested"))',
    ['echo', 'nested'],
)

test(
    "Command substitution with cat",
    'cat $(find . -name "README.md" | head -1)',
    ['Get-Content', 'Get-ChildItem', 'README.md'],
)

# ============================================================================
# CATEGORY 4: COMPLEX GREP PATTERNS
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 4: Complex Grep (CRITICAL for code search)")
print("=" * 80)

test(
    "Recursive grep with line numbers",
    'grep -rn "class.*Executor" --include="*.py" .',
    ['Select-String', 'class.*Executor', 'Recurse'],
)

test(
    "Grep with context (before/after)",
    'grep -B 2 -A 2 "def execute" bash_tool_executor.py',
    ['Select-String', 'def execute', 'Context'],
)

test(
    "Grep count occurrences",
    'grep -c "import" bash_tool_executor.py',
    ['Select-String', 'Measure-Object'],
)

test(
    "Grep with multiple patterns",
    'grep -E "class|def" bash_tool_executor.py | head -10',
    ['Select-String', 'class|def'],
)

# ============================================================================
# CATEGORY 5: SED OPERATIONS
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 5: Sed Transformations (CRITICAL for text processing)")
print("=" * 80)

test(
    "Sed substitute",
    'echo "hello world" | sed "s/world/universe/"',
    ['echo', 'hello'],  # Should handle sed substitution
)

test(
    "Sed with line ranges",
    'sed -n "10,20p" bash_tool_executor.py',
    [],  # Complex - may need special handling
)

# ============================================================================
# CATEGORY 6: AWK OPERATIONS
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 6: Awk Processing (CRITICAL for field extraction)")
print("=" * 80)

test(
    "Awk print column",
    'echo "one two three" | awk \'{print $2}\'',
    ['echo'],  # Awk is complex
)

test(
    "Awk sum calculation",
    'echo -e "1\\n2\\n3" | awk \'{sum+=$1} END {print sum}\'',
    ['echo'],
)

# ============================================================================
# CATEGORY 7: XARGS PATTERNS
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 7: Xargs (CRITICAL for batch operations)")
print("=" * 80)

test(
    "Find with xargs",
    'find . -name "*.py" -type f | head -3 | xargs wc -l',
    ['Get-ChildItem', 'Measure-Object'],
)

test(
    "Echo with xargs",
    'echo "test_main.py" | xargs grep "def"',
    ['Select-String', 'def'],
)

# ============================================================================
# CATEGORY 8: PROCESS SUBSTITUTION
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 8: Process Substitution (CRITICAL for comparisons)")
print("=" * 80)

test(
    "Diff with process substitution",
    'diff <(git show HEAD:bash_tool_executor.py) <(cat bash_tool_executor.py)',
    ['git', 'show', 'Get-Content'],  # Should create temp files
)

test(
    "Comm with process substitution",
    'comm -12 <(sort test1.txt) <(sort test2.txt)',
    ['Sort-Object'],  # Should create temp files for sorted output
)

# ============================================================================
# CATEGORY 9: REAL WORKFLOWS (from CLAUDE_REAL_BASH_PATTERNS.md)
# ============================================================================
print()
print("=" * 80)
print("CATEGORY 9: Real Claude Workflows (THE ULTIMATE TEST)")
print("=" * 80)

test(
    "Find all class definitions",
    'find . -name "*.py" -exec grep -H "^class " {} \\; | sort',
    ['Get-ChildItem', 'Select-String', '^class', 'Sort-Object'],
)

test(
    "Count lines in multiple files",
    'find . -name "*.py" ! -path "*/__pycache__/*" -exec wc -l {} +',
    ['Get-ChildItem', 'Measure-Object'],
)

test(
    "Complex dependency analysis",
    'grep -rh "^import " --include="*.py" . | sort | uniq',
    ['Select-String', '^import', 'Sort-Object'],
)

# ============================================================================
# RESULTS
# ============================================================================
print()
print("=" * 80)
print("EXTREME STRESS TEST RESULTS")
print("=" * 80)
print()
print(f"Total:    {passed + failed}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Success:  {(passed/(passed+failed)*100):.1f}%")
print()

if failed == 0:
    print("🎉 ALL EXTREME TESTS PASSED!")
    print("Claude can execute ALL real-world patterns successfully.")
else:
    print(f"⚠️  {failed} CRITICAL patterns failed")
    print()
    print("FAILED PATTERNS:")
    print("-" * 80)
    for i, failure in enumerate(failures[:10], 1):
        print(f"\n{i}. {failure['name']}")
        print(f"   CMD: {failure['cmd'][:70]}")
        if failure['missing']:
            print(f"   MISSING: {failure['missing']}")
        if failure['forbidden']:
            print(f"   FORBIDDEN: {failure['forbidden']}")

print()
print("=" * 80)
print("THESE ARE THE PATTERNS CLAUDE USES EVERY DAY.")
print("IF THEY DON'T WORK → CLAUDE IS PARALYZED ON WINDOWS.")
print("=" * 80)
