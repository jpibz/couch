#!/usr/bin/env python3
"""
Manual pipeline testing - Find bugs by running real complex commands
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bash_tool.bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(
    working_dir=Path('/home/user/couch'),
    test_mode=True
)

def test_cmd(name, cmd):
    """Test command and show all preprocessing stages"""
    print("\n" + "█" * 100)
    print(f"TEST: {name}")
    print("█" * 100)
    print(f"INPUT: {cmd}")
    print("-" * 100)

    try:
        result = executor.execute({'command': cmd, 'description': name})
        print(f"\n✅ Completed")

        # Check for issues
        if "Error:" in result or "Exception:" in result:
            print(f"⚠️  ERROR in output: {result[:200]}")
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")


# TEST 1: Complex find with nested conditions
test_cmd(
    "Find with complex nested conditions",
    'find . \\( -name "*.py" -o \\( -name "*.sh" -a ! -path "*test*" \\) \\) -type f | head -10'
)

# TEST 2: Sed with multiple patterns and delimiters
test_cmd(
    "Sed with complex patterns",
    'echo "foo/bar/baz" | sed "s/\\//-/g; s/foo/FOO/; s/baz/BAZ/"'
)

# TEST 3: Awk with variables and arithmetic
test_cmd(
    "Awk with variables",
    'echo -e "1\\n2\\n3" | awk \'BEGIN{sum=0; count=0} {sum+=$1; count++} END{print "Avg:", sum/count}\''
)

# TEST 4: While loop with command substitution
test_cmd(
    "While with command subst",
    'find . -name "*.py" -type f | head -3 | while read f; do echo "File: $f Size: $(wc -l < "$f" || echo 0)"; done'
)

# TEST 5: For loop with brace expansion and nested command
test_cmd(
    "For with braces and command subst",
    'for f in file{1..3}.txt; do echo "Creating $f with $(date)"; touch "$f"; done'
)

# TEST 6: Case statement
test_cmd(
    "Case statement",
    'var="test"; case "$var" in test) echo "matched";; *) echo "not matched";; esac'
)

# TEST 7: Function definition and call
test_cmd(
    "Function definition",
    'myfunc() { echo "Args: $@"; }; myfunc one two three'
)

# TEST 8: Array operations
test_cmd(
    "Array operations",
    'arr=(one two three); echo "${arr[0]}"; echo "${arr[@]}"; echo "${#arr[@]}"'
)

# TEST 9: Process substitution with multiple files
test_cmd(
    "Process subst multiple",
    'diff <(sort file1.txt) <(sort file2.txt) | head -5'
)

# TEST 10: Complex redirect chain
test_cmd(
    "Complex redirects",
    'command 2>&1 > /tmp/out.log | tee /tmp/err.log | grep ERROR'
)

# TEST 11: Conditional with pattern matching
test_cmd(
    "Pattern matching conditional",
    '[[ "hello world" =~ ^hello ]] && echo "matched" || echo "not matched"'
)

# TEST 12: Arithmetic in various contexts
test_cmd(
    "Complex arithmetic",
    'a=5; b=3; echo $((a + b)); echo $((a * b)); echo $((a ** 2)); c=$((a > b ? a : b)); echo $c'
)

# TEST 13: String manipulation extreme
test_cmd(
    "String manipulation",
    'str="  hello world  "; echo "${str##* }"; echo "${str%% *}"; echo "${str//o/O}"; echo "${str^^}"'
)

# TEST 14: Subshell with exports
test_cmd(
    "Subshell with exports",
    '(export VAR=value; echo "In subshell: $VAR"; bash -c "echo Nested: $VAR")'
)

# TEST 15: Background jobs with wait
test_cmd(
    "Background jobs",
    'sleep 0.1 & pid1=$!; sleep 0.1 & pid2=$!; wait $pid1 $pid2; echo "Done"'
)

# TEST 16: Here-string
test_cmd(
    "Here-string",
    'grep "pattern" <<< "this is a pattern test"'
)

# TEST 17: Command grouping with braces
test_cmd(
    "Command grouping",
    '{ echo "Line 1"; echo "Line 2"; echo "Line 3"; } | grep "2"'
)

# TEST 18: Nested quotes extreme
test_cmd(
    "Nested quotes extreme",
    """echo "She said \\"It's $(echo "a 'test'") today\\""  """
)

# TEST 19: Pipeline with stderr merge in middle
test_cmd(
    "Pipeline stderr merge",
    'find /nonexistent 2>&1 | grep -i error | wc -l'
)

# TEST 20: Xargs with complex options
test_cmd(
    "Xargs complex",
    'echo -e "file1\\nfile2\\nfile3" | xargs -I {} -P 3 bash -c \'echo "Processing: {}"; sleep 0.1\''
)

print("\n" + "=" * 100)
print("MANUAL PIPELINE TESTING COMPLETED")
print("=" * 100)
