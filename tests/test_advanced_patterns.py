#!/usr/bin/env python3
"""
ADVANCED PATTERNS TEST - Iteration 2

Testing additional complex bash patterns that Claude uses
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

# Setup
WORKSPACE = Path("/home/user/couch")
executor = BashToolExecutor(working_dir=str(WORKSPACE))

print("=" * 80)
print("ADVANCED PATTERNS TEST - Iteration 2")
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
            print(f"✗ FAILED\n{result[:800]}\n")
            return False
        else:
            print(f"✓ PASSED")
            # Show key translation info
            if "[TEST MODE]" in result:
                for line in result.split('\n'):
                    if any(x in line for x in ["Would execute:", "Strategy:", "Translation:"]):
                        print(f"  {line.strip()}")
            print()
            return True
    except Exception as e:
        print(f"✗ EXCEPTION: {e}\n")
        import traceback
        traceback.print_exc()
        return False


passed = 0
failed = 0
tests = []

# ============================================================================
# CATEGORY 1: HEREDOC with variable expansion
# ============================================================================
print("=" * 80)
print("CATEGORY 1: Heredoc with variable expansion")
print("=" * 80)
print()

tests.append(("Heredoc with expansion", """cat <<EOF
Current dir: $(pwd)
Date: $(date)
EOF"""))

tests.append(("Heredoc without expansion", """cat <<'EOF'
Literal: $(pwd)
Not expanded: $HOME
EOF"""))

tests.append(("Heredoc in pipeline", """cat <<EOF | grep Current
Current dir: $(pwd)
Date: $(date)
EOF"""))


# ============================================================================
# CATEGORY 2: Find -exec with shell
# ============================================================================
print("=" * 80)
print("CATEGORY 2: Find -exec with shell commands")
print("=" * 80)
print()

tests.append(("Find -exec sh -c", 'find . -name "*.py" -exec sh -c \'echo "File: $1"\' _ {} \\;'))

tests.append(("Find -exec with pipe", 'find . -name "*.py" -exec sh -c \'cat {} | head -5\' \\;'))


# ============================================================================
# CATEGORY 3: Arithmetic expansion
# ============================================================================
print("=" * 80)
print("CATEGORY 3: Arithmetic expansion")
print("=" * 80)
print()

tests.append(("Simple arithmetic", 'echo $((5 + 3))'))

tests.append(("Arithmetic with variables", 'count=10; echo $((count * 2))'))

tests.append(("Arithmetic in command", 'head -n $((5 + 5)) file.txt'))


# ============================================================================
# CATEGORY 4: Brace expansion
# ============================================================================
print("=" * 80)
print("CATEGORY 4: Brace expansion")
print("=" * 80)
print()

tests.append(("Numeric brace expansion", 'echo {1..5}'))

tests.append(("String brace expansion", 'echo file.{txt,md,py}'))

tests.append(("Brace in find", 'find . -name "*.{py,js,ts}"'))


# ============================================================================
# CATEGORY 5: Parameter expansion
# ============================================================================
print("=" * 80)
print("CATEGORY 5: Parameter expansion")
print("=" * 80)
print()

tests.append(("Remove prefix pattern", 'file="/path/to/file.txt"; echo ${file#*/}'))

tests.append(("Remove suffix pattern", 'file="document.tar.gz"; echo ${file%.gz}'))

tests.append(("Default value", 'echo ${UNDEFINED:-default_value}'))

tests.append(("String length", 'text="hello"; echo ${#text}'))


# ============================================================================
# CATEGORY 6: Complex redirections
# ============================================================================
print("=" * 80)
print("CATEGORY 6: Complex redirections")
print("=" * 80)
print()

tests.append(("Stderr to stdout", 'grep "error" file.txt 2>&1'))

tests.append(("Both to file", 'command &>output.txt'))

tests.append(("Pipe stderr", 'command 2>&1 | grep -i error'))


# ============================================================================
# CATEGORY 7: Test constructs
# ============================================================================
print("=" * 80)
print("CATEGORY 7: Test constructs and conditionals")
print("=" * 80)
print()

tests.append(("File test", '[ -f "bash_tool_executor.py" ] && echo "exists"'))

tests.append(("String test", '[ "$USER" = "claude" ] || echo "not claude"'))

tests.append(("Numeric test", '[ 5 -gt 3 ] && echo "yes"'))

tests.append(("Double bracket test", '[[ -f "*.py" ]] && echo "has py files"'))


# ============================================================================
# CATEGORY 8: Command grouping
# ============================================================================
print("=" * 80)
print("CATEGORY 8: Command grouping")
print("=" * 80)
print()

tests.append(("Subshell grouping", '(cd /tmp && pwd)'))

tests.append(("Brace grouping", '{ echo "line1"; echo "line2"; }'))

tests.append(("Pipeline grouping", '(echo "a"; echo "b") | sort'))


# ============================================================================
# CATEGORY 9: While/For loops
# ============================================================================
print("=" * 80)
print("CATEGORY 9: Loops")
print("=" * 80)
print()

tests.append(("For loop simple", 'for i in 1 2 3; do echo $i; done'))

tests.append(("For loop with command", 'for file in $(find . -name "*.py" | head -3); do echo $file; done'))

tests.append(("While read loop", 'echo -e "line1\\nline2" | while read line; do echo ">> $line"; done'))


# ============================================================================
# CATEGORY 10: Grep advanced
# ============================================================================
print("=" * 80)
print("CATEGORY 10: Grep advanced patterns")
print("=" * 80)
print()

tests.append(("Grep only-matching", 'echo "test123abc" | grep -o "[0-9]+"'))

tests.append(("Grep with context", 'grep -A 2 -B 1 "def " bash_tool_executor.py | head -20'))

tests.append(("Grep count", 'grep -c "class" bash_tool_executor.py'))

tests.append(("Grep invert match", 'grep -v "^#" bash_tool_executor.py | head -10'))


# ============================================================================
# RUN ALL TESTS
# ============================================================================
print("\n" + "=" * 80)
print("RUNNING ALL TESTS")
print("=" * 80)
print()

for name, cmd in tests:
    if test(name, cmd):
        passed += 1
    else:
        failed += 1


# ============================================================================
# RESULTS
# ============================================================================
print()
print("=" * 80)
print("ADVANCED PATTERNS TEST RESULTS")
print("=" * 80)
print()
print(f"Total:    {passed + failed}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Success:  {(passed/(passed+failed)*100):.1f}%")
print()

if failed == 0:
    print("🎉 ALL ADVANCED TESTS PASSED!")
else:
    print(f"⚠️  {failed} tests failed - identifying bugs...")
    print()
    print("Failed tests require fixes. Running detailed analysis...")

print("=" * 80)
