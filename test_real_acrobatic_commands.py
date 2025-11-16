"""
REAL ACROBATIC BASH COMMANDS TEST SUITE

This test suite contains THE ACTUAL commands that Claude uses in production.
Not toy examples. REAL, COMPLEX, ACROBATIC bash commands.

The kind of commands that if they fail, the entire task collapses.
"""

import sys
from pathlib import Path
from bash_tool_executor import BashToolExecutor

# Setup test environment
WORKSPACE = Path("/home/user/couch")
executor = BashToolExecutor(working_dir=str(WORKSPACE), testmode=True)

def test_command(description, command, category=""):
    """Test a single bash command"""
    print("=" * 80)
    if category:
        print(f"CATEGORY: {category}")
    print(f"TEST: {description}")
    print(f"CMD:  {command}")
    print("-" * 80)

    try:
        result = executor.execute(command)
        print(f"RESULT: Exit code {result.returncode}")
        if result.returncode == 0:
            print("✓ PASSED")
        else:
            print("✗ FAILED")
            if result.stderr:
                print(f"STDERR: {result.stderr[:500]}")
        return result.returncode == 0
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        return False


# Track results
passed = 0
failed = 0
tests = []


def run_test(category, description, command):
    global passed, failed, tests
    result = test_command(description, command, category)
    tests.append((category, description, result))
    if result:
        passed += 1
    else:
        failed += 1
    return result


print("=" * 80)
print("REAL ACROBATIC BASH COMMANDS - EXTREME END USER TEST SUITE")
print("=" * 80)
print()
print("This is what Claude ACTUALLY uses. Not toy examples.")
print()


# ============================================================================
# CATEGORY 1: COMPLEX FIND WITH -EXEC
# ============================================================================

run_test(
    "FIND ACROBATICS",
    "Find all Python files excluding venv, search for pattern",
    'find . -name "*.py" -type f ! -path "*/venv/*" -exec grep -l "class" {} \\;'
)

run_test(
    "FIND ACROBATICS",
    "Find recent files, count lines, sort by size",
    'find . -type f -name "*.py" -mtime -30 -exec wc -l {} + | sort -rn | head -10'
)

run_test(
    "FIND ACROBATICS",
    "Find and delete with confirmation pattern",
    'find /tmp -name "*.tmp" -type f -mtime +7 -exec rm {} \\;'
)

run_test(
    "FIND ACROBATICS",
    "Find files larger than 1MB and show details",
    'find . -type f -size +1M -exec ls -lh {} \\; | awk \'{print $9, $5}\''
)


# ============================================================================
# CATEGORY 2: MULTI-STAGE PIPELINES (5+ COMMANDS)
# ============================================================================

run_test(
    "PIPELINE EXTREMES",
    "5-stage pipeline: grep, sed, sort, uniq, count",
    'cat bash_tool_executor.py | grep "def " | sed \'s/^[[:space:]]*//\' | sort | uniq -c | awk \'{sum+=$1} END {print sum}\''
)

run_test(
    "PIPELINE EXTREMES",
    "Git log analysis with multi-stage processing",
    'git log --oneline | head -20 | awk \'{print $1}\' | wc -l'
)

run_test(
    "PIPELINE EXTREMES",
    "Process list filtering and formatting",
    'ps aux | grep -v "grep" | awk \'{print $2, $11}\' | sort -k2'
)

run_test(
    "PIPELINE EXTREMES",
    "File analysis with multiple transforms",
    'ls -la | grep "^-" | awk \'{sum+=$5} END {print "Total:", sum}\''
)


# ============================================================================
# CATEGORY 3: NESTED COMMAND SUBSTITUTION
# ============================================================================

run_test(
    "COMMAND SUBSTITUTION",
    "Grep in dynamically found files",
    'grep -r "import" $(find . -name "*.py" -type f ! -path "*/test/*")'
)

run_test(
    "COMMAND SUBSTITUTION",
    "Count lines in all found Python files",
    'wc -l $(find . -name "*.py" -type f) | tail -1'
)

run_test(
    "COMMAND SUBSTITUTION",
    "Nested find and cat",
    'cat $(find . -name "README.md" -type f | head -1)'
)

run_test(
    "COMMAND SUBSTITUTION",
    "Echo with complex nested substitution",
    'echo "Files: $(find . -type f -name "*.py" | wc -l)"'
)


# ============================================================================
# CATEGORY 4: PROCESS SUBSTITUTION (ADVANCED)
# ============================================================================

run_test(
    "PROCESS SUBSTITUTION",
    "Diff between git HEAD and current file",
    'diff <(git show HEAD:bash_tool_executor.py) <(cat bash_tool_executor.py)'
)

run_test(
    "PROCESS SUBSTITUTION",
    "Compare sorted file contents",
    'comm -12 <(sort unix_translator.py) <(sort bash_tool_executor.py)'
)

run_test(
    "PROCESS SUBSTITUTION",
    "Diff with command output",
    'diff <(ls -1 *.py | sort) <(git ls-files "*.py" | sort)'
)


# ============================================================================
# CATEGORY 5: SED/AWK ACROBATICS
# ============================================================================

run_test(
    "SED/AWK MASTERS",
    "Extract specific line range and transform",
    'sed -n "100,200p" bash_tool_executor.py | sed \'s/def /function /g\' | grep -c "function"'
)

run_test(
    "SED/AWK MASTERS",
    "AWK field sum calculation",
    'ls -l *.py | awk \'{sum+=$5} END {print "Total bytes:", sum}\''
)

run_test(
    "SED/AWK MASTERS",
    "Sed multi-pattern replacement",
    'echo "hello world" | sed -e \'s/hello/hi/\' -e \'s/world/universe/\''
)

run_test(
    "SED/AWK MASTERS",
    "AWK with pattern matching and field extraction",
    'awk \'/^def / {print $2}\' bash_tool_executor.py | head -10'
)


# ============================================================================
# CATEGORY 6: HEREDOCS IN COMPLEX CONTEXTS
# ============================================================================

run_test(
    "HEREDOC GYMNASTICS",
    "Heredoc with variable expansion in pipeline",
    '''cat <<EOF | grep "HOME"
HOME is: $HOME
USER is: $USER
PATH is: $PATH
EOF'''
)

run_test(
    "HEREDOC GYMNASTICS",
    "Heredoc quoted (no expansion) with special chars",
    '''cat <<'EOF'
$VAR should not expand
$(command) should not execute
\$escaped should stay escaped
EOF'''
)

run_test(
    "HEREDOC GYMNASTICS",
    "Heredoc in command substitution",
    '''echo "Lines: $(cat <<EOF | wc -l
line 1
line 2
line 3
EOF
)"'''
)


# ============================================================================
# CATEGORY 7: COMBINATION NIGHTMARES (The Real Deal)
# ============================================================================

run_test(
    "NIGHTMARE MODE",
    "Find logs with errors, show last 20 lines of each",
    'find . -name "*.log" -type f -exec grep -l "ERROR" {} \\; | head -3 | xargs -I {} sh -c \'echo "=== {} ==="; tail -5 {}\''
)

run_test(
    "NIGHTMARE MODE",
    "Complex git analysis with multiple substitutions",
    'for commit in $(git log --oneline | head -5 | awk \'{print $1}\'); do echo "$commit: $(git show --stat $commit | grep -c "files changed")"; done'
)

run_test(
    "NIGHTMARE MODE",
    "File comparison with inline transformations",
    'diff <(grep "^class" bash_tool_executor.py | sort) <(grep "^class" unix_translator.py | sort)'
)

run_test(
    "NIGHTMARE MODE",
    "Multi-level command substitution with pipes",
    'echo "Total methods: $(grep -o "def [a-z_]*" bash_tool_executor.py | wc -l)"'
)


# ============================================================================
# CATEGORY 8: REAL CLAUDE WORKFLOWS
# ============================================================================

run_test(
    "CLAUDE REAL USAGE",
    "Find all classes in Python files",
    'find . -name "*.py" -type f -exec grep -H "^class " {} \\; | sed \'s/:class /: /\' | sort'
)

run_test(
    "CLAUDE REAL USAGE",
    "Count total lines of Python code",
    'find . -name "*.py" ! -path "*/venv/*" ! -path "*/__pycache__/*" -type f -exec wc -l {} + | tail -1'
)

run_test(
    "CLAUDE REAL USAGE",
    "Search for TODO comments with context",
    'grep -r -n "TODO\\|FIXME\\|XXX" --include="*.py" . | head -20'
)

run_test(
    "CLAUDE REAL USAGE",
    "Find duplicate function definitions",
    'grep -r "^def " --include="*.py" . | awk -F: \'{print $2}\' | sort | uniq -d'
)

run_test(
    "CLAUDE REAL USAGE",
    "Analyze import statements",
    'grep -h "^import \\|^from " *.py | sort | uniq -c | sort -rn | head -10'
)


# ============================================================================
# CATEGORY 9: EDGE CASES THAT BREAK THINGS
# ============================================================================

run_test(
    "EDGE CASES",
    "Files with spaces in names",
    'find . -name "* *.py" -type f -exec echo {} \\;'
)

run_test(
    "EDGE CASES",
    "Special characters in grep patterns",
    'grep -E "\\$\\{.*\\}" bash_tool_executor.py | head -5'
)

run_test(
    "EDGE CASES",
    "Pipes within quotes",
    'echo "This | is | not | a | pipe" | wc -w'
)

run_test(
    "EDGE CASES",
    "Backticks (legacy command substitution)",
    'echo `date` `pwd`'
)


# ============================================================================
# CATEGORY 10: PERFORMANCE CRITICAL
# ============================================================================

run_test(
    "PERFORMANCE",
    "Large file processing with head optimization",
    'find . -name "*.py" -type f | xargs cat | head -1000 | wc -l'
)

run_test(
    "PERFORMANCE",
    "Parallel-style processing with xargs",
    'find . -name "*.py" -type f -print0 | xargs -0 -n 1 wc -l | awk \'{sum+=$1} END {print sum}\''
)


# ============================================================================
# RESULTS SUMMARY
# ============================================================================

print()
print("=" * 80)
print("TEST RESULTS SUMMARY")
print("=" * 80)
print()
print(f"Total tests: {passed + failed}")
print(f"✓ Passed:    {passed}")
print(f"✗ Failed:    {failed}")
print(f"Success rate: {(passed/(passed+failed)*100):.1f}%")
print()

# Breakdown by category
print("BREAKDOWN BY CATEGORY:")
print("-" * 80)
categories = {}
for cat, desc, result in tests:
    if cat not in categories:
        categories[cat] = {"passed": 0, "failed": 0}
    if result:
        categories[cat]["passed"] += 1
    else:
        categories[cat]["failed"] += 1

for cat in sorted(categories.keys()):
    stats = categories[cat]
    total = stats["passed"] + stats["failed"]
    rate = (stats["passed"] / total * 100) if total > 0 else 0
    print(f"{cat:25s} {stats['passed']:3d}/{total:3d} ({rate:5.1f}%)")

print("=" * 80)

# Exit with error code if any tests failed
sys.exit(0 if failed == 0 else 1)
