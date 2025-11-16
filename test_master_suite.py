#!/usr/bin/env python3
"""
MASTER TEST SUITE - All fixes validation

Combines all critical patterns to ensure all fixes work together
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

# Setup
WORKSPACE = Path("/home/user/couch")
executor = BashToolExecutor(working_dir=str(WORKSPACE))

print("=" * 80)
print("MASTER TEST SUITE - ALL FIXES VALIDATION")
print("=" * 80)
print()

def test(name, cmd):
    """Run a single test"""
    try:
        result = executor.execute({'command': cmd, 'description': name})
        is_error = any([
            result.startswith("Error:"),
            result.startswith("SECURITY VIOLATION:"),
            "Exception:" in result,
            "Traceback" in result,
        ])
        return not is_error
    except Exception as e:
        return False


passed = 0
failed = 0
tests = []

# ============================================================================
# NIGHTMARE MODE: Multiple fixes combined
# ============================================================================
print("Testing extreme combinations of all fixes...")
print("-" * 80)

tests.append(("FIX #1+#2+#3: Pipeline + cmd subst + translation",
    'git log --oneline | head -20 | grep "$(echo commit)" | wc -l'))

tests.append(("FIX #1+#6: Pipeline with arithmetic",
    'seq 1 100 | head -n $((10 + 5))'))

tests.append(("FIX #2+#3+#6: Command subst with arithmetic",
    'echo "Files: $(find . -name "*.py" | head -n $((5 + 5)) | wc -l)"'))

tests.append(("FIX #4+#6: Process subst with arithmetic",
    'diff <(seq 1 $((5 + 5))) <(seq 1 10)'))

tests.append(("FIX #1+#2+#3+#5: Complex pipeline with PowerShell",
    'find . -name "*.py" -exec grep -l "class" {} \\; | head -n 20 | wc -l'))

tests.append(("FIX #2+#3+#6 nested: Nested cmd subst with arithmetic",
    'echo "Result: $(echo "Count: $(ls *.py | wc -l)")"'))

tests.append(("FIX #1+#2+#3+#4+#6: Everything together",
    'diff <(find . -name "*.py" | head -n $((10 + 5))) <(ls *.py | head -20) | wc -l'))

tests.append(("FIX #3+#5+#6: Find with arithmetic in command subst",
    'grep -r "def" $(find . -name "*.py" | head -n $((3 + 2)))'))

tests.append(("FIX #1+#6: Multiple arithmetic in pipeline",
    'seq 1 $((10 * 10)) | head -n $((20 + 5)) | tail -n $((5 + 5))'))

tests.append(("FIX #2+#3+#6: Arithmetic in command subst nested",
    'echo $((5 + $(echo 3)))'))

# ============================================================================
# STRESS TEST: Real Claude patterns
# ============================================================================
print()
print("Testing real Claude usage patterns...")
print("-" * 80)

tests.append(("Real pattern: File search with count",
    'find . -type f -name "*.py" -exec grep -l "BashToolExecutor" {} \\; | wc -l'))

tests.append(("Real pattern: Git log analysis",
    'git log --oneline | head -20 | awk \'{print $1}\' | wc -l'))

tests.append(("Real pattern: Complex grep pipeline",
    'grep -r "def " bash_tool_executor.py | grep -v "^#" | head -10 | wc -l'))

tests.append(("Real pattern: Arithmetic in head",
    'cat bash_tool_executor.py | head -n $((100 + 50)) | tail -20'))

tests.append(("Real pattern: Find with multiple filters",
    'find . -name "*.py" -type f | grep -v "__pycache__" | head -10'))

# ============================================================================
# RUN ALL TESTS
# ============================================================================
for name, cmd in tests:
    if test(name, cmd):
        passed += 1
        print(f"✓ {name}")
    else:
        failed += 1
        print(f"✗ {name}")
        print(f"   CMD: {cmd}")

# ============================================================================
# RESULTS
# ============================================================================
print()
print("=" * 80)
print("MASTER TEST SUITE RESULTS")
print("=" * 80)
print()
print(f"Total:    {passed + failed}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Success:  {(passed/(passed+failed)*100):.1f}%")
print()

if failed == 0:
    print("🎉 ALL MASTER TESTS PASSED!")
    print("All fixes working correctly together.")
else:
    print(f"⚠️  {failed} tests failed")
    print("Need further investigation...")

print("=" * 80)
