"""
PROGRESSIVE TEST SUITE - From Simple to EXTREME

Test architecture escalates complexity progressively:
- Level 1: BASIC (simple atomic commands)
- Level 2: PREPROCESSING (variables, braces, arithmetic)
- Level 3: PIPELINE SIMPLE (pipes, &&, ||, ;)
- Level 4: PIPELINE COMPLEX (multi-stage, nesting, redirects)
- Level 5: MIXED (preprocessing + pipelines)
- Level 6: ACROBATIC (nested substitution, extreme patterns)

Strategy: test → fix bugs → retest → NEXT LEVEL

Usage:
    python test_progressive_levels.py [level]

    Examples:
        python test_progressive_levels.py 1     # Run level 1 only
        python test_progressive_levels.py       # Run all levels
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'bash_tool'))

from command_executor import CommandExecutor
import tempfile


class ProgressiveTestRunner:
    """Test runner with progressive levels"""

    def __init__(self):
        self.executor = CommandExecutor(
            working_dir=tempfile.gettempdir(),
            test_mode=True,
            test_capabilities={'bash': False}  # Force MANUAL to test AST walking
        )
        self.passed = 0
        self.failed = 0
        self.current_level = 0

    def test(self, command, description):
        """Run single test"""
        try:
            result = self.executor.execute(command)

            # Check for errors
            is_error = result.returncode != 0

            if is_error:
                print(f"  ✗ {description}")
                print(f"    Command: {command}")
                print(f"    Exit code: {result.returncode}")
                if result.stderr:
                    print(f"    Stderr: {result.stderr[:100]}")
                self.failed += 1
                return False
            else:
                print(f"  ✓ {description}")
                self.passed += 1
                return True

        except Exception as e:
            print(f"  ✗ {description}")
            print(f"    Command: {command}")
            print(f"    Exception: {str(e)[:150]}")
            self.failed += 1
            return False

    def level_header(self, level, name):
        """Print level header"""
        self.current_level = level
        print(f"\n{'='*80}")
        print(f"LEVEL {level}: {name}")
        print(f"{'='*80}")

    def level_summary(self):
        """Print level summary"""
        total = self.passed + self.failed
        if total == 0:
            return

        success_rate = (self.passed / total * 100)
        status = "✅ PASS" if success_rate == 100 else "⚠️ PARTIAL" if success_rate >= 80 else "❌ FAIL"

        print(f"\n{'-'*80}")
        print(f"Level {self.current_level} Results: {self.passed}/{total} tests passed ({success_rate:.1f}%) {status}")
        print(f"{'-'*80}")

        return success_rate == 100

    def final_summary(self):
        """Print final summary"""
        total = self.passed + self.failed
        if total == 0:
            return

        success_rate = (self.passed / total * 100)

        print(f"\n{'#'*80}")
        print(f"# FINAL RESULTS")
        print(f"{'#'*80}")
        print(f"Total tests:  {total}")
        print(f"Passed:       {self.passed}")
        print(f"Failed:       {self.failed}")
        print(f"Success rate: {success_rate:.1f}%")

        if success_rate == 100:
            print(f"\n🔥🔥🔥 ALL LEVELS PASSED - PRODUCTION READY 🔥🔥🔥")
        elif success_rate >= 90:
            print(f"\n✅ EXCELLENT - Minor issues remain")
        elif success_rate >= 70:
            print(f"\n⚠️ GOOD - Some work needed")
        else:
            print(f"\n❌ NEEDS WORK - Major issues found")


# ============================================================================
# LEVEL 1: BASIC - Simple atomic commands
# ============================================================================

def level_1_basic(runner):
    """Level 1: Basic atomic commands"""
    runner.level_header(1, "BASIC - Simple Atomic Commands")

    runner.test("echo hello", "Simple echo")
    runner.test("echo 'hello world'", "Echo with spaces")
    runner.test("echo foo", "Echo simple word")
    runner.test("true", "True command")
    runner.test("false || echo fallback", "False with fallback")

    return runner.level_summary()


# ============================================================================
# LEVEL 2: PREPROCESSING - Variable expansion, braces, arithmetic
# ============================================================================

def level_2_preprocessing(runner):
    """Level 2: Preprocessing (variables, braces, arithmetic)"""
    runner.level_header(2, "PREPROCESSING - Variables, Braces, Arithmetic")

    # Set test environment variables
    os.environ['TEST_VAR'] = 'test_value'
    os.environ['NUM'] = '42'
    os.environ['PATH_VAR'] = '/tmp/test'

    # Variable expansion
    runner.test("echo $TEST_VAR", "Simple variable expansion")
    runner.test("echo ${TEST_VAR}", "Braced variable expansion")
    runner.test("echo ${TEST_VAR:-default}", "Variable with default")

    # Arithmetic
    runner.test("echo $((5 + 3))", "Simple arithmetic")
    runner.test("echo $((NUM + 10))", "Arithmetic with variable")

    # Brace expansion
    runner.test("echo {1..5}", "Numeric brace expansion")
    runner.test("echo {a,b,c}", "List brace expansion")

    return runner.level_summary()


# ============================================================================
# LEVEL 3: PIPELINE SIMPLE - Basic pipes, &&, ||, ;
# ============================================================================

def level_3_pipeline_simple(runner):
    """Level 3: Simple pipelines and command chains"""
    runner.level_header(3, "PIPELINE SIMPLE - Pipes, &&, ||, ;")

    # Simple pipe
    runner.test("echo hello | grep hello", "Simple pipe")

    # AND chain
    runner.test("echo foo && echo bar", "AND chain")
    runner.test("true && echo success", "AND with true")

    # OR chain
    runner.test("false || echo fallback", "OR chain")

    # Sequence
    runner.test("echo first ; echo second", "Sequence with semicolon")
    runner.test("echo a ; echo b ; echo c", "Multiple sequences")

    return runner.level_summary()


# ============================================================================
# LEVEL 4: PIPELINE COMPLEX - Multi-stage, nesting, redirects
# ============================================================================

def level_4_pipeline_complex(runner):
    """Level 4: Complex pipelines"""
    runner.level_header(4, "PIPELINE COMPLEX - Multi-stage, Nesting")

    # Multi-stage pipes
    runner.test("echo abc | grep a | grep b", "Triple pipe")
    runner.test("echo test | grep test | grep test", "Pipeline with same command")

    # Mixed operators
    runner.test("echo test | grep test && echo success", "Pipe + AND")
    runner.test("true && echo a | grep a", "AND + pipe")
    runner.test("echo x | grep x || echo fallback", "Pipe + OR")

    # Sequence with pipes
    runner.test("echo a | grep a ; echo b | grep b", "Sequence of pipes")

    return runner.level_summary()


# ============================================================================
# LEVEL 5: MIXED - Preprocessing + Pipelines
# ============================================================================

def level_5_mixed(runner):
    """Level 5: Mixed preprocessing and pipelines"""
    runner.level_header(5, "MIXED - Preprocessing + Pipelines")

    os.environ['PATTERN'] = 'test'

    # Variables in pipelines
    runner.test("echo test | grep $PATTERN", "Variable in pipe")
    runner.test("echo $((5 + 5)) | grep 10", "Arithmetic in pipe")

    # Braces in pipelines
    runner.test("echo {1..3} | grep 2", "Brace expansion in pipe")

    # Mixed chains
    runner.test("echo $TEST_VAR && echo success", "Variable + AND")
    runner.test("echo $((NUM + 1)) ; echo done", "Arithmetic + sequence")

    return runner.level_summary()


# ============================================================================
# LEVEL 6: ACROBATIC - Nested substitution, extreme patterns
# ============================================================================

def level_6_acrobatic(runner):
    """Level 6: Acrobatic patterns (nested, extreme)"""
    runner.level_header(6, "ACROBATIC - Nested Substitution, Extreme Patterns")

    # Command substitution (will be preprocessed)
    runner.test("echo $(echo hello)", "Simple command substitution")
    runner.test("echo $(echo $(echo nested))", "Nested command substitution")

    # Complex variable operations
    runner.test("file=/path/to/file.txt; echo ${file##*/}", "Remove path prefix")
    runner.test("text=foo-bar-baz; echo ${text//-/_}", "String substitution")

    # Complex pipes
    runner.test("echo abc | grep a | grep b | grep c", "4-stage pipe")
    runner.test("echo test | grep t && echo ok | grep ok", "Pipe + AND + pipe")

    return runner.level_summary()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run progressive test suite"""

    # Parse command line arguments
    target_level = None
    if len(sys.argv) > 1:
        try:
            target_level = int(sys.argv[1])
        except ValueError:
            print(f"Invalid level: {sys.argv[1]}")
            print("Usage: python test_progressive_levels.py [level]")
            sys.exit(1)

    print("="*80)
    print("PROGRESSIVE TEST SUITE - Simple to EXTREME")
    print("="*80)
    print()

    if target_level:
        print(f"Running LEVEL {target_level} only")
    else:
        print("Running ALL LEVELS progressively")

    runner = ProgressiveTestRunner()

    levels = [
        (1, level_1_basic),
        (2, level_2_preprocessing),
        (3, level_3_pipeline_simple),
        (4, level_4_pipeline_complex),
        (5, level_5_mixed),
        (6, level_6_acrobatic),
    ]

    for level_num, level_func in levels:
        # Skip if target level specified and doesn't match
        if target_level and level_num != target_level:
            continue

        # Run level
        success = level_func(runner)

        # If running all levels and this level failed, stop
        if not target_level and not success:
            print(f"\n⚠️ Level {level_num} had failures. Fix before proceeding to next level.")
            print(f"To retest this level: python test_progressive_levels.py {level_num}")
            print(f"To continue: python test_progressive_levels.py {level_num + 1}")
            break

    # Final summary
    runner.final_summary()


if __name__ == '__main__':
    main()
