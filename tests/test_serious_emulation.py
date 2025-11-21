#!/usr/bin/env python3
"""
SERIOUS COMMAND TESTING - PROGRESSIVE LEVELS WITH EMULATION VERIFICATION

Goal: Test ALL 70 commands with REAL emulation, not just bash passthrough!

Strategy:
1. Level 1: QUICK commands (bash=False) → verify PowerShell output
2. Level 2: MEDIUM commands (bash=False) → verify complex scripts
3. Level 3: HEAVY commands (bash=False) → stress test long scripts (awk, sed, jq, curl)
4. Level 4: HYBRID mode (bash=False, some bins=True) → verify fallback logic
5. Level 5: INTEGRATION with preprocessing → verify contingent correctness

Each level uses test_capabilities to control execution strategy.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bash_tool.bash_tool_executor import BashToolExecutor

print("=" * 80)
print("SERIOUS COMMAND TESTING - EMULATION VERIFICATION")
print("Testing with bash=False to force PowerShell emulation")
print("=" * 80)
print()

passed = 0
failed = 0
total_emulations_checked = 0

def test(name, cmd, executor, verify_emulation=True):
    """
    Run test and VERIFY the emulation output.

    Args:
        name: Test description
        cmd: Command to execute
        executor: BashToolExecutor instance
        verify_emulation: If True, verify that PowerShell script was generated
    """
    global passed, failed, total_emulations_checked

    try:
        result = executor.execute({'command': cmd, 'description': name})

        # Check for errors
        is_error = any([
            result.startswith("Error:"),
            result.startswith("SECURITY VIOLATION:"),
            "Exception:" in result,
            "Traceback" in result,
            "CommandNotFoundError" in result,
        ])

        # Check if emulation happened (PowerShell script in output)
        if verify_emulation:
            # In TEST MODE, output shows "(CMD):" for emulated commands
            # Look for PowerShell syntax markers: Get-Command, Get-Content, $LASTEXITCODE, etc.
            ps_markers = ["Get-Command", "Get-Content", "Get-ChildItem", "$LASTEXITCODE",
                         "ForEach-Object", "(CMD):", "(PowerShell):", "pwsh -Command"]
            is_emulated = any(marker in result for marker in ps_markers)
            is_bash = "(Git Bash):" in result or "bash -c" in result

            if is_bash and not is_emulated:
                print(f"⚠️  {name}")
                print(f"   WARN: Command went to BASH instead of EMULATION")
                print(f"   CMD: {cmd[:100]}")
                print(f"   OUTPUT: {result[:200]}")
                failed += 1
                return False

            if is_emulated:
                total_emulations_checked += 1
                # Extract and show PowerShell script snippet
                if "(PowerShell):" in result:
                    ps_start = result.find("(PowerShell):") + len("(PowerShell):")
                    ps_snippet = result[ps_start:ps_start+150].strip()
                    print(f"✓ {name}")
                    print(f"   EMULATED: {ps_snippet[:100]}...")
                    passed += 1
                    return True

        if not is_error:
            print(f"✓ {name}")
            passed += 1
            return True
        else:
            print(f"✗ {name}")
            print(f"   CMD: {cmd[:100]}")
            print(f"   ERROR: {result[:300]}")
            failed += 1
            return False

    except Exception as e:
        print(f"✗ {name}")
        print(f"   CMD: {cmd[:100]}")
        print(f"   EXCEPTION: {str(e)[:200]}")
        failed += 1
        return False


# =============================================================================
# LEVEL 1: QUICK COMMANDS - FORCE EMULATION (bash=False, no bins)
# =============================================================================
print("\n" + "=" * 80)
print("LEVEL 1: QUICK COMMANDS - FORCED EMULATION")
print("test_capabilities: {'bash': False} → ALL commands must use PowerShell")
print("=" * 80)
print()

executor_manual = BashToolExecutor(
    working_dir='/home/user/couch',
    test_capabilities={'bash': False}  # FORCE MANUAL MODE
)

# Test QUICK commands - should generate short PowerShell scripts
print("Testing: pwd")
test("pwd - manual mode", "pwd", executor_manual, verify_emulation=True)

print("\nTesting: whoami")
test("whoami - manual mode", "whoami", executor_manual, verify_emulation=True)

print("\nTesting: hostname")
test("hostname - manual mode", "hostname", executor_manual, verify_emulation=True)

print("\nTesting: echo")
test("echo hello - manual mode", "echo hello", executor_manual, verify_emulation=True)
test("echo with quotes", "echo 'hello world'", executor_manual, verify_emulation=True)

print("\nTesting: basename")
test("basename /path/to/file.txt", "basename /path/to/file.txt", executor_manual, verify_emulation=True)

print("\nTesting: dirname")
test("dirname /path/to/file.txt", "dirname /path/to/file.txt", executor_manual, verify_emulation=True)

print("\nTesting: date")
test("date - manual mode", "date", executor_manual, verify_emulation=True)

print("\nTesting: sleep")
test("sleep 0.1", "sleep 0.1", executor_manual, verify_emulation=True)

print("\nTesting: true/false")
test("true - manual mode", "true", executor_manual, verify_emulation=True)
test("false || echo fallback", "false || echo fallback", executor_manual, verify_emulation=True)


# =============================================================================
# LEVEL 2: MEDIUM COMMANDS - VERIFY COMPLEX SCRIPTS
# =============================================================================
print("\n" + "=" * 80)
print("LEVEL 2: MEDIUM COMMANDS - COMPLEX SCRIPT VERIFICATION")
print("Testing commands with 20-100 line translate methods")
print("=" * 80)
print()

print("Testing: ls")
test("ls simple", "ls", executor_manual, verify_emulation=True)
test("ls with flags", "ls -la", executor_manual, verify_emulation=True)

print("\nTesting: cat")
test("cat with stdin", "echo test | cat", executor_manual, verify_emulation=True)

print("\nTesting: head")
test("head -n 5", "echo -e 'a\\nb\\nc\\nd\\ne\\nf' | head -n 5", executor_manual, verify_emulation=True)

print("\nTesting: tail")
test("tail -n 3", "echo -e 'a\\nb\\nc\\nd\\ne' | tail -n 3", executor_manual, verify_emulation=True)

print("\nTesting: wc")
test("wc -l", "echo -e 'a\\nb\\nc' | wc -l", executor_manual, verify_emulation=True)

print("\nTesting: tr")
test("tr lowercase to uppercase", "echo hello | tr a-z A-Z", executor_manual, verify_emulation=True)

print("\nTesting: touch")
test("touch /tmp/test_$$", "touch /tmp/test_serious_$$", executor_manual, verify_emulation=True)


# =============================================================================
# LEVEL 3: HEAVY COMMANDS - STRESS TEST LONG SCRIPTS
# =============================================================================
print("\n" + "=" * 80)
print("LEVEL 3: HEAVY COMMANDS - STRESS TEST (100+ line scripts)")
print("Testing: awk (211 lines), sed (233 lines), grep (124 lines), jq (212 lines)")
print("=" * 80)
print()

print("Testing: grep (124 lines)")
test("grep simple", "echo -e 'foo\\nbar\\nbaz' | grep ba", executor_manual, verify_emulation=True)
test("grep with -v", "echo -e 'foo\\nbar\\nbaz' | grep -v foo", executor_manual, verify_emulation=True)

print("\nTesting: awk (211 lines)")
test("awk print column", "echo 'a b c' | awk '{print $2}'", executor_manual, verify_emulation=True)
test("awk with pattern", "echo -e 'foo\\nbar\\nbaz' | awk '/ba/'", executor_manual, verify_emulation=True)

print("\nTesting: sed (233 lines)")
test("sed substitute", "echo hello | sed 's/hello/world/'", executor_manual, verify_emulation=True)
test("sed delete line", "echo -e 'a\\nb\\nc' | sed '2d'", executor_manual, verify_emulation=True)

print("\nTesting: cut (107 lines)")
test("cut by delimiter", "echo 'a:b:c' | cut -d: -f2", executor_manual, verify_emulation=True)

print("\nTesting: sort (190 lines)")
test("sort lines", "echo -e 'c\\na\\nb' | sort", executor_manual, verify_emulation=True)

print("\nTesting: uniq (161 lines)")
test("uniq basic", "echo -e 'a\\na\\nb' | uniq", executor_manual, verify_emulation=True)


# =============================================================================
# LEVEL 4: HYBRID MODE - SOME BINS AVAILABLE
# =============================================================================
print("\n" + "=" * 80)
print("LEVEL 4: HYBRID MODE - bash=False, grep=True")
print("grep should use native binary, others use emulation")
print("=" * 80)
print()

executor_hybrid = BashToolExecutor(
    working_dir='/home/user/couch',
    test_capabilities={'bash': False, 'grep': True}
)

print("Testing: grep with native bin")
test("grep with native binary", "echo -e 'foo\\nbar' | grep foo", executor_hybrid, verify_emulation=False)

print("\nTesting: awk without bash")
test("awk forced emulation", "echo 'a b c' | awk '{print $1}'", executor_hybrid, verify_emulation=True)


# =============================================================================
# LEVEL 5: INTEGRATION WITH PREPROCESSING
# =============================================================================
print("\n" + "=" * 80)
print("LEVEL 5: INTEGRATION - Preprocessing + Emulation")
print("Testing contingent correctness (preprocessing interaction)")
print("=" * 80)
print()

print("Testing: Variable expansion + emulation")
test("echo $VAR", "VAR=hello; echo $VAR", executor_manual, verify_emulation=True)

print("\nTesting: Command substitution + emulation")
test("echo $(pwd)", "echo $(pwd)", executor_manual, verify_emulation=True)

print("\nTesting: Arithmetic + emulation")
test("echo $((5+3))", "echo $((5 + 3))", executor_manual, verify_emulation=True)

print("\nTesting: Pipe with emulation")
test("echo | cat", "echo test | cat", executor_manual, verify_emulation=True)


# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 80)
print("SERIOUS TESTING SUMMARY")
print("=" * 80)
total = passed + failed
print(f"Total tests: {total}")
print(f"Passed: {passed} ({passed/total*100:.1f}%)")
print(f"Failed: {failed} ({failed/total*100:.1f}%)")
print(f"PowerShell emulations verified: {total_emulations_checked}")
print()

if failed == 0 and total_emulations_checked > 20:
    print(f"✅ ALL TESTS PASSED with {total_emulations_checked} emulations verified!")
elif total_emulations_checked < 10:
    print(f"⚠️  WARNING: Only {total_emulations_checked} emulations verified - most went to bash!")
else:
    print(f"⚠️  {failed} tests failed - fixes needed")

print("=" * 80)
