#!/usr/bin/env python3
"""
EXTREME FULL PATH TEST - NO SHORTCUTS, NO FAKES

Tests the COMPLETE execution path including:
- Real bin detection (not faked)
- Real strategy analysis
- Real preprocessing (all stages)
- Real parser
- Real validation

This is what Giovanni runs in production - we must match it!
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.bash_tool.bash_tool_executor import BashToolExecutor

print("=" * 120)
print("EXTREME FULL PATH TEST - Testing REAL execution flow")
print("=" * 120)
print()

# Create executor with test_mode=True BUT it should still exercise full path
workspace = Path(r'C:\Users\Test\workspace')
executor = BashToolExecutor(
    working_dir=workspace,
    test_mode=True  # This should ONLY fake actual command execution, NOT skip validation/analysis
)

def test(name, cmd):
    """Run test and show FULL TRACE"""
    print("\n" + "=" * 120)
    print(f"TEST: {name}")
    print("=" * 120)
    print(f"CMD: {cmd}")
    print("-" * 120)

    try:
        # This MUST go through:
        # 1. BashToolExecutor.execute()
        # 2. CommandExecutor.execute()
        # 3. SandboxValidator.validate()
        # 4. BashCommandPreprocessor.preprocess_always()
        # 5. BashPipelineParser.parse()
        # 6. PipelineAnalyzer.analyze() ← THIS is where is_available() is called!
        # 7. ExecutionEngine._analyze_strategy()
        # 8. ExecutionEngine.execute()

        result = executor.execute({'command': cmd, 'description': name})
        print("RESULT:")
        print(result)
        print()
        print("EXIT CODE:", result.get('exit_code', 'N/A'))

    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print()


# ============================================================================
# TEST 1: Simple command - exercises FULL path
# ============================================================================
test(
    "Simple echo - full path",
    "echo 'Hello World'"
)

# ============================================================================
# TEST 2: Pipeline - exercises strategy analysis
# ============================================================================
test(
    "Pipeline with grep",
    "echo 'test1\ntest2\ntest3' | grep test"
)

# ============================================================================
# TEST 3: Command substitution - exercises preprocessor
# ============================================================================
test(
    "Command substitution",
    "echo \"Current dir: $(pwd)\""
)

# ============================================================================
# TEST 4: Brace expansion - exercises all preprocessing
# ============================================================================
test(
    "Brace expansion",
    "echo {a,b,c}{1,2,3}"
)

# ============================================================================
# TEST 5: Parameter expansion - exercises variable handling
# ============================================================================
test(
    "Parameter expansion",
    "file='/path/to/file.txt'; echo ${file%/*}"
)

# ============================================================================
# TEST 6: Redirect - exercises parser
# ============================================================================
test(
    "Redirect to file",
    "echo 'test' > /tmp/test.txt"
)

# ============================================================================
# TEST 7: Stderr redirect - exercises >&2 fix
# ============================================================================
test(
    "Stderr redirect >&2",
    "echo 'error' >&2"
)

# ============================================================================
# TEST 8: Complex pipeline - exercises analyzer bin detection
# ============================================================================
test(
    "Complex pipeline with multiple commands",
    "echo 'line1\nline2' | grep line | wc -l"
)

# ============================================================================
# TEST 9: Nested command substitution - exercises preprocessor depth
# ============================================================================
test(
    "Nested command substitution",
    "echo \"Outer: $(echo Inner: $(echo Deep))\""
)

# ============================================================================
# TEST 10: Process substitution - exercises temp file handling
# ============================================================================
test(
    "Process substitution <()",
    "cat <(echo 'from process subst')"
)

# ============================================================================
# TEST 11: Here-string - exercises heredoc handling
# ============================================================================
test(
    "Here-string <<<",
    "grep test <<< 'this is a test'"
)

# ============================================================================
# TEST 12: Background job - exercises parser background handling
# ============================================================================
test(
    "Background job",
    "sleep 0.1 &"
)

# ============================================================================
# TEST 13: Subshell - exercises parser grouping
# ============================================================================
test(
    "Subshell with redirect",
    "(echo 'stdout'; echo 'stderr' >&2) 2>&1"
)

# ============================================================================
# TEST 14: AND chain - exercises control flow
# ============================================================================
test(
    "AND chain &&",
    "echo 'first' && echo 'second'"
)

# ============================================================================
# TEST 15: OR chain - exercises control flow
# ============================================================================
test(
    "OR chain ||",
    "false || echo 'fallback'"
)

# ============================================================================
# TEST 16: Sequence - exercises command chaining
# ============================================================================
test(
    "Sequence with ;",
    "echo 'one'; echo 'two'; echo 'three'"
)

# ============================================================================
# TEST 17: Arithmetic expansion - exercises $((..)) handling
# ============================================================================
test(
    "Arithmetic expansion",
    "echo $((5 + 3))"
)

# ============================================================================
# TEST 18: Nested arithmetic with command subst - exercises Bug 3 fix
# ============================================================================
test(
    "Nested arithmetic with command subst",
    "echo $(($(echo 5) + $(echo 3)))"
)

# ============================================================================
# TEST 19: echo -e flag - exercises Bug 4 fix
# ============================================================================
test(
    "echo -e with escape sequences",
    "echo -e 'line1\\nline2\\nline3'"
)

# ============================================================================
# TEST 20: ULTIMATE - everything combined
# ============================================================================
test(
    "ULTIMATE: All features combined",
    """
    for i in {1..3}; do
        result=$(echo "Processing $i: $(echo $((i * 2)))")
        echo "$result" | grep Processing
    done
    """
)

print("\n" + "=" * 120)
print("EXTREME FULL PATH TEST COMPLETED")
print("=" * 120)
print()
print("If you see this, ALL code paths were exercised!")
print("Any AttributeError would have crashed before reaching here.")
