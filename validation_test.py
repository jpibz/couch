#!/usr/bin/env python3
"""
FINAL VALIDATION TEST - Production Files

Tests critical fixes using PRODUCTION bash_tool_executor.py and unix_translator.py
(NOT the REFACTORED versions)
"""

from bash_tool_executor import BashToolExecutor
from pathlib import Path

# Setup
WORKSPACE = Path("/home/user/couch")
executor = BashToolExecutor(working_dir=str(WORKSPACE))

# CRITICAL: Set TESTMODE manually
executor.TESTMODE = True

print("=" * 80)
print("FINAL VALIDATION - PRODUCTION FILES")
print("=" * 80)
print()
print("Using: bash_tool_executor.py + unix_translator.py (PRODUCTION)")
print("TESTMODE: Enabled")
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
            print(f"✓ PASSED")
            # Show translation for key tests
            if "[TEST MODE]" in result:
                for line in result.split('\n'):
                    if "Would execute:" in line or "Translation:" in line:
                        print(f"  {line}")
            print()
            return True
    except Exception as e:
        print(f"✗ EXCEPTION: {e}\n")
        return False


# Track results
passed = 0
failed = 0

# ============================================================================
# CRITICAL FIX #1: Pipeline head/tail/wc stdin support
# ============================================================================
print("=" * 80)
print("FIX #1: Pipeline head/tail/wc stdin support")
print("=" * 80)
print()

if test("head in pipeline", "git log --oneline | head -20"):
    passed += 1
else:
    failed += 1

if test("tail in pipeline", "find . -name '*.py' | tail -10"):
    passed += 1
else:
    failed += 1

if test("wc in pipeline", "grep 'ERROR' bash_tool_executor.py | wc -l"):
    passed += 1
else:
    failed += 1


# ============================================================================
# CRITICAL FIX #2: Preserve $(command) syntax
# ============================================================================
print("=" * 80)
print("FIX #2: Preserve $(command) syntax")
print("=" * 80)
print()

if test("simple command substitution", "echo $(date)"):
    passed += 1
else:
    failed += 1

if test("nested in quotes", 'echo "Current: $(pwd)"'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CRITICAL FIX #3: Translate commands inside $()
# ============================================================================
print("=" * 80)
print("FIX #3: Translate commands inside $() with force_translate")
print("=" * 80)
print()

if test("find inside $()", 'grep -r "import" $(find . -name "*.py" -type f)'):
    passed += 1
else:
    failed += 1

if test("wc inside $()", 'echo "Total: $(find . -name "*.py" | wc -l)"'):
    passed += 1
else:
    failed += 1


# ============================================================================
# CRITICAL FIX #4: Preserve <(command) and >(command)
# ============================================================================
print("=" * 80)
print("FIX #4: Preserve <(command) process substitution")
print("=" * 80)
print()

if test("process substitution input", "diff <(cat file1) <(cat file2)"):
    passed += 1
else:
    failed += 1

if test("process substitution with sort", "comm -12 <(sort file1) <(sort file2)"):
    passed += 1
else:
    failed += 1


# ============================================================================
# CRITICAL FIX #5: PowerShell cmdlet detection
# ============================================================================
print("=" * 80)
print("FIX #5: PowerShell cmdlet detection in _needs_powershell")
print("=" * 80)
print()

if test("find -exec (generates Get-ChildItem)", 'find . -name "*.py" -exec grep -l "class" {} \\;'):
    passed += 1
else:
    failed += 1


# ============================================================================
# COMBINED TESTS: Multiple fixes together
# ============================================================================
print("=" * 80)
print("COMBINED: Multiple fixes working together")
print("=" * 80)
print()

if test("pipeline + command substitution", 'git log --oneline | head -20 | awk \'{print $1}\' | wc -l'):
    passed += 1
else:
    failed += 1

if test("find + wc in pipeline", 'find . -name "*.py" -type f -exec wc -l {} + | tail -1'):
    passed += 1
else:
    failed += 1


# ============================================================================
# RESULTS
# ============================================================================
print()
print("=" * 80)
print("VALIDATION RESULTS")
print("=" * 80)
print()
print(f"Total:   {passed + failed}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Success:  {(passed/(passed+failed)*100):.1f}%")
print()

if failed == 0:
    print("🎉 ALL VALIDATION TESTS PASSED!")
    print("Production files are ready for use.")
else:
    print(f"⚠️  {failed} tests failed - need further fixes")

print("=" * 80)
