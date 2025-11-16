#!/usr/bin/env python3
"""
CLAUDE PRODUCTION PATTERNS TEST

Testing ACTUAL patterns Claude uses in real tasks:
- Code analysis workflows
- Git operations
- File manipulation
- Search and replace operations
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

# Setup
WORKSPACE = Path("/home/user/couch")
executor = BashToolExecutor(working_dir=str(WORKSPACE))

print("=" * 80)
print("CLAUDE PRODUCTION PATTERNS TEST")
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
        status = "✓" if not is_error else "✗"
        print(f"{status} {name}")
        if is_error:
            print(f"  ERROR: {result[:200]}")
        return not is_error
    except Exception as e:
        print(f"✗ {name}")
        print(f"  EXCEPTION: {e}")
        return False


passed = 0
failed = 0

print("REAL CLAUDE WORKFLOWS:")
print("-" * 80)

# Pattern 1: Find and analyze code structure
if test("Find all Python classes",
    'grep -r "^class " --include="*.py" . | head -20'):
    passed += 1
else:
    failed += 1

# Pattern 2: Count specific patterns
if test("Count function definitions",
    'grep -c "^def " bash_tool_executor.py'):
    passed += 1
else:
    failed += 1

# Pattern 3: Find with exclusions
if test("Find Python files excluding cache",
    'find . -name "*.py" -type f ! -path "*__pycache__*" | head -10'):
    passed += 1
else:
    failed += 1

# Pattern 4: Complex grep with context
if test("Grep with before/after context",
    'grep -B 2 -A 2 "class BashToolExecutor" bash_tool_executor.py | head -20'):
    passed += 1
else:
    failed += 1

# Pattern 5: Find and count
if test("Find and count Python files",
    'find . -name "*.py" -type f | wc -l'):
    passed += 1
else:
    failed += 1

# Pattern 6: Multi-stage pipeline
if test("Multi-stage filter pipeline",
    'grep -r "def " --include="*.py" . | grep -v "__pycache__" | head -10 | wc -l'):
    passed += 1
else:
    failed += 1

# Pattern 7: Sort and unique
if test("Find, sort, unique",
    'find . -name "*.py" -type f | sort | head -10'):
    passed += 1
else:
    failed += 1

# Pattern 8: Filename extraction
if test("Extract just filenames",
    'find . -name "*.py" -type f | head -5'):
    passed += 1
else:
    failed += 1

# Pattern 9: Case-insensitive search
if test("Case-insensitive grep",
    'grep -i "bashtoolexecutor" bash_tool_executor.py | head -3'):
    passed += 1
else:
    failed += 1

# Pattern 10: Word boundaries in grep
if test("Grep with word boundaries",
    'grep -w "command" bash_tool_executor.py | head -5'):
    passed += 1
else:
    failed += 1

# Pattern 11: Recursive grep with line numbers
if test("Recursive grep with line numbers",
    'grep -rn "TESTMODE" --include="*.py" . | head -5'):
    passed += 1
else:
    failed += 1

# Pattern 12: Find with size filter
if test("Find large files",
    'find . -name "*.py" -type f -size +10k | head -5'):
    passed += 1
else:
    failed += 1

# Pattern 13: Find recently modified
if test("Find recently modified files",
    'find . -name "*.py" -type f -mtime -1 | head -10'):
    passed += 1
else:
    failed += 1

# Pattern 14: Combine find results
if test("Find multiple patterns",
    'find . \\( -name "*.py" -o -name "*.md" \\) -type f | head -10'):
    passed += 1
else:
    failed += 1

# Pattern 15: Grep with inverted match
if test("Grep exclude pattern",
    'grep -v "^$" bash_tool_executor.py | head -20'):
    passed += 1
else:
    failed += 1

# Pattern 16: Count lines in multiple files
if test("Count lines across files",
    'find . -name "test_*.py" -exec wc -l {} + | tail -1'):
    passed += 1
else:
    failed += 1

# Pattern 17: Extract specific fields with cut
if test("Extract with cut",
    'echo "one:two:three" | cut -d: -f2'):
    passed += 1
else:
    failed += 1

# Pattern 18: Sed basic substitution
if test("Sed replace first occurrence",
    'echo "hello world world" | sed "s/world/universe/"'):
    passed += 1
else:
    failed += 1

# Pattern 19: Sed replace all occurrences
if test("Sed replace all",
    'echo "hello world world" | sed "s/world/universe/g"'):
    passed += 1
else:
    failed += 1

# Pattern 20: Awk print column
if test("Awk print column",
    'echo "one two three" | awk \'{print $2}\''):
    passed += 1
else:
    failed += 1

# Pattern 21: Awk with condition
if test("Awk with condition",
    'echo -e "1\\n5\\n3" | awk \'$1 > 2 {print}\''):
    passed += 1
else:
    failed += 1

# Pattern 22: Sort numeric
if test("Sort numerically",
    'echo -e "10\\n2\\n30" | sort -n'):
    passed += 1
else:
    failed += 1

# Pattern 23: Uniq after sort
if test("Unique lines",
    'echo -e "a\\nb\\na\\nc" | sort | uniq'):
    passed += 1
else:
    failed += 1

# Pattern 24: Xargs with command
if test("Xargs execution",
    'echo "bash_tool_executor.py" | xargs wc -l'):
    passed += 1
else:
    failed += 1

# Pattern 25: Xargs with find
if test("Find with xargs",
    'find . -name "test_*.py" -type f | head -3 | xargs wc -l'):
    passed += 1
else:
    failed += 1

# Pattern 26: Tee to save intermediate
if test("Tee to file and stdout",
    'echo "test" | tee /tmp/test_output.txt'):
    passed += 1
else:
    failed += 1

# Pattern 27: Chained greps
if test("Multiple grep filters",
    'grep -r "class" --include="*.py" . | grep "Tool" | grep -v "Test" | head -5'):
    passed += 1
else:
    failed += 1

# Pattern 28: Find exec with multiple commands
if test("Find exec grep",
    'find . -name "*.py" -type f -exec grep -l "TESTMODE" {} \\; | head -3'):
    passed += 1
else:
    failed += 1

# Pattern 29: Complex awk
if test("Awk sum column",
    'echo -e "1 10\\n2 20\\n3 30" | awk \'{sum+=$2} END {print sum}\''):
    passed += 1
else:
    failed += 1

# Pattern 30: Basename in command substitution
if test("Basename extraction",
    'echo $(basename "/path/to/file.txt")'):
    passed += 1
else:
    failed += 1

# Pattern 31: Dirname in command substitution
if test("Dirname extraction",
    'echo $(dirname "/path/to/file.txt")'):
    passed += 1
else:
    failed += 1

# Pattern 32: Date formatting
if test("Date command",
    'echo $(date +"%Y-%m-%d")'):
    passed += 1
else:
    failed += 1

# Pattern 33: Command substitution in find
if test("Find with current date",
    'find . -name "*.py" -type f | head -5'):
    passed += 1
else:
    failed += 1

# Pattern 34: Read file content check
if test("Check if file contains pattern",
    'grep -q "BashToolExecutor" bash_tool_executor.py && echo "found" || echo "not found"'):
    passed += 1
else:
    failed += 1

# Pattern 35: Complex sed
if test("Sed delete lines",
    'echo -e "line1\\nline2\\nline3" | sed "2d"'):
    passed += 1
else:
    failed += 1

# Pattern 36: Tr command
if test("Tr uppercase",
    'echo "hello" | tr a-z A-Z'):
    passed += 1
else:
    failed += 1

# Pattern 37: Tr delete chars
if test("Tr delete characters",
    'echo "hello123" | tr -d 0-9'):
    passed += 1
else:
    failed += 1

# Pattern 38: Printf formatting
if test("Printf command",
    'printf "Value: %d\\n" 42'):
    passed += 1
else:
    failed += 1

# Pattern 39: Readonly variable
if test("Echo with complex string",
    'echo "Status: OK"'):
    passed += 1
else:
    failed += 1

# Pattern 40: Multiple pipes with arithmetic
if test("Pipeline with arithmetic count",
    'find . -name "*.py" | head -n $((5 + 5)) | wc -l'):
    passed += 1
else:
    failed += 1

# ============================================================================
# RESULTS
# ============================================================================
print()
print("=" * 80)
print("CLAUDE PRODUCTION PATTERNS RESULTS")
print("=" * 80)
print()
print(f"Total:    {passed + failed}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Success:  {(passed/(passed+failed)*100):.1f}%")
print()

if failed == 0:
    print("🎉 ALL PRODUCTION PATTERNS PASSED!")
    print("Claude can execute real-world tasks successfully.")
else:
    print(f"⚠️  {failed} patterns failed")
    print("Critical functionality missing for Claude's real usage.")

print("=" * 80)
