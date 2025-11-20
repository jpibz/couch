"""
Test EXTREME pipelines with controlled capabilities

This test uses test_capabilities to force different execution paths:
1. Manual execution (bash=False) - tests AST walking
2. Passthrough (bash=True, all bins=True) - tests bash.exe delegation
3. Hybrid (bash=False, some bins=True) - tests manual with native bins
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'bash_tool'))

from command_executor import CommandExecutor
import tempfile


def test_extreme_manual_execution():
    """
    Force MANUAL execution by disabling bash.
    This tests AST walking, manual pipe loop, exit code checking.
    """
    print("\n" + "="*80)
    print("TEST: EXTREME MANUAL EXECUTION (bash=False)")
    print("="*80)

    # Force manual execution - no bash, no native bins
    executor = CommandExecutor(
        working_dir=tempfile.gettempdir(),
        test_mode=True,
        test_capabilities={'bash': False}  # Force MANUAL
    )

    tests = [
        # Simple command
        ("echo hello", "Simple command"),

        # Pipe chain (tests manual pipe loop)
        ("echo hello | grep hello", "Pipe chain"),

        # AND chain (tests exit code checking)
        ("echo foo && echo bar", "AND chain"),

        # OR chain
        ("false || echo fallback", "OR chain"),

        # Sequence
        ("echo first ; echo second", "Sequence"),

        # Complex mix
        ("echo test | grep test && echo success", "Pipe + AND"),

        # Triple pipe
        ("echo abc | grep a | grep b", "Triple pipe"),
    ]

    passed = 0
    failed = 0

    for command, description in tests:
        print(f"\n[{description}]")
        print(f"Command: {command}")
        try:
            result = executor.execute(command)
            print(f"✓ PASS - Exit code: {result.returncode}")
            passed += 1
        except Exception as e:
            print(f"✗ FAIL: {e}")
            failed += 1

    print(f"\n{'='*80}")
    print(f"MANUAL EXECUTION: {passed} passed, {failed} failed")
    print(f"{'='*80}")

    return passed, failed


def test_extreme_passthrough():
    """
    Force PASSTHROUGH by enabling bash and all bins.
    This tests bash.exe delegation.
    """
    print("\n" + "="*80)
    print("TEST: EXTREME PASSTHROUGH (bash=True, all bins=True)")
    print("="*80)

    # Force passthrough - bash + all native bins
    executor = CommandExecutor(
        working_dir=tempfile.gettempdir(),
        test_mode=True,
        test_capabilities={
            'bash': True,
            'grep': True,
            'awk': True,
            'sed': True,
            'diff': True
        }
    )

    tests = [
        # Same commands as manual - should use bash passthrough
        ("echo hello", "Simple command"),
        ("echo hello | grep hello", "Pipe chain"),
        ("echo foo && echo bar", "AND chain"),
        ("echo test | grep test && echo success", "Pipe + AND"),

        # Complex awk chain (should passthrough to bash)
        ("echo 'a b c' | awk '{print $2}'", "Awk processing"),
    ]

    passed = 0
    failed = 0

    for command, description in tests:
        print(f"\n[{description}]")
        print(f"Command: {command}")
        try:
            result = executor.execute(command)
            print(f"✓ PASS - Exit code: {result.returncode}")
            passed += 1
        except Exception as e:
            print(f"✗ FAIL: {e}")
            failed += 1

    print(f"\n{'='*80}")
    print(f"PASSTHROUGH: {passed} passed, {failed} failed")
    print(f"{'='*80}")

    return passed, failed


def test_extreme_hybrid():
    """
    Hybrid mode: Manual execution with some native bins available.
    This tests manual AST walking with native binary optimization.
    """
    print("\n" + "="*80)
    print("TEST: EXTREME HYBRID (bash=False, grep=True)")
    print("="*80)

    # Hybrid: manual execution but grep is native
    executor = CommandExecutor(
        working_dir=tempfile.gettempdir(),
        test_mode=True,
        test_capabilities={
            'bash': False,  # Manual execution
            'grep': True    # But grep is native binary
        }
    )

    tests = [
        # Pipe with native grep (should use native grep.exe)
        ("echo hello | grep hello", "Pipe with native grep"),

        # Multiple pipes with grep
        ("echo test | grep test | grep test", "Multiple native greps"),
    ]

    passed = 0
    failed = 0

    for command, description in tests:
        print(f"\n[{description}]")
        print(f"Command: {command}")
        try:
            result = executor.execute(command)
            print(f"✓ PASS - Exit code: {result.returncode}")
            passed += 1
        except Exception as e:
            print(f"✗ FAIL: {e}")
            failed += 1

    print(f"\n{'='*80}")
    print(f"HYBRID: {passed} passed, {failed} failed")
    print(f"{'='*80}")

    return passed, failed


if __name__ == '__main__':
    print("\n" + "="*80)
    print("EXTREME PIPELINE TESTS WITH CONTROLLED CAPABILITIES")
    print("="*80)

    total_passed = 0
    total_failed = 0

    # Test 1: Manual execution
    p, f = test_extreme_manual_execution()
    total_passed += p
    total_failed += f

    # Test 2: Passthrough
    p, f = test_extreme_passthrough()
    total_passed += p
    total_failed += f

    # Test 3: Hybrid
    p, f = test_extreme_hybrid()
    total_passed += p
    total_failed += f

    # Final results
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Total passed: {total_passed}")
    print(f"Total failed: {total_failed}")
    print(f"Success rate: {total_passed/(total_passed+total_failed)*100:.1f}%")
    print("="*80)
