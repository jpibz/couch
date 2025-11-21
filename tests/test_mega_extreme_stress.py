#!/usr/bin/env python3
"""
MEGA EXTREME STRESS TEST - Real-world Claude patterns
NO AUTO-VALIDATION - Just show raw output for manual inspection
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.bash_tool.bash_tool_executor import BashToolExecutor

print("=" * 120)
print("MEGA EXTREME STRESS TEST - Real Claude Usage Patterns")
print("=" * 120)
print()

# Use REAL workspace that EXISTS on this system!
workspace = Path('/home/user/couch')  # Linux system path
# NO test_mode - TESTMODE is hardcoded in BashToolExecutor!
executor = BashToolExecutor(working_dir=workspace)

def test(name, cmd):
    """Run test and show OUTPUT"""
    print("\n" + "=" * 120)
    print(f"TEST: {name}")
    print("=" * 120)
    print(f"CMD: {cmd}")
    print("-" * 120)

    try:
        result = executor.execute({'command': cmd, 'description': name})
        print(result)
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# REAL PATTERN 1: Git operations with complex grep/sed chains
# ============================================================================
test(
    "Git log with grep/sed/awk pipeline",
    """git log --oneline --all | grep -E "(feat|fix|refactor)" | sed 's/^[a-f0-9]\\{7\\}/[&]/' | awk '{print NR". "$0}' | head -20"""
)

# ============================================================================
# REAL PATTERN 2: Find with complex exec and multiple conditions
# ============================================================================
test(
    "Find files with size/time/name conditions + exec",
    """find C:\\Users\\Test\\workspace -type f \\( -name "*.py" -o -name "*.sh" \\) ! -path "*__pycache__*" ! -path "*.git*" -mtime -7 -size +1k -exec sh -c 'echo "File: {} - Lines: $(wc -l < "{}")"' \\;"""
)

# ============================================================================
# REAL PATTERN 3: Heredoc with extensive variable expansion
# ============================================================================
test(
    "Heredoc with variables, command subst, and multiline",
    '''cat <<REPORT
═══════════════════════════════════════
    System Report - $(date +"%Y-%m-%d %H:%M:%S")
═══════════════════════════════════════

Current User: $USER
Working Directory: $(pwd)
Python Version: $(python --version 2>&1)
Git Branch: $(git branch --show-current 2>/dev/null || echo "not a git repo")

Files Statistics:
- Total Python files: $(find C:\\Users\\Test\\workspace -name "*.py" | wc -l)
- Total Lines of Code: $(find C:\\Users\\Test\\workspace -name "*.py" -exec wc -l {} \\; | awk '{sum+=$1} END {print sum}')
- Modified in last 24h: $(find C:\\Users\\Test\\workspace -name "*.py" -mtime -1 | wc -l)

Recent Commits:
$(git log --oneline -5 2>/dev/null | sed 's/^/  - /')

═══════════════════════════════════════
REPORT
'''
)

# ============================================================================
# REAL PATTERN 4: While loop reading from complex pipeline
# ============================================================================
test(
    "While loop with IFS, read, complex processing",
    '''find C:\\Users\\Test\\workspace -name "*.py" -type f | head -5 | while IFS= read -r file; do
  lines=$(wc -l < "$file" 2>/dev/null || echo 0)
  funcs=$(grep -c "^def " "$file" 2>/dev/null || echo 0)
  classes=$(grep -c "^class " "$file" 2>/dev/null || echo 0)
  echo "${file##*/}: $lines lines, $funcs functions, $classes classes"
done'''
)

# ============================================================================
# REAL PATTERN 5: Process substitution with diff comparison
# ============================================================================
test(
    "Process subst comparing two command outputs",
    '''diff <(find C:\\Users\\Test\\workspace\\src -name "*.py" | sort) <(git ls-files C:\\Users\\Test\\workspace\\src | grep "\\.py$" | sort) | head -20'''
)

# ============================================================================
# REAL PATTERN 6: Here-string with grep and pipeline
# ============================================================================
test(
    "Here-string feeding grep with multi-stage pipeline",
    """grep -o "[A-Z][a-z]*" <<< "TestCamelCaseString WithMultipleWords" | tr '\\n' ' ' | sed 's/ $/\\n/'"""
)

# ============================================================================
# REAL PATTERN 7: Nested command substitution with arithmetic
# ============================================================================
test(
    "Triple-nested command subst with arithmetic",
    '''total_lines=$(find C:\\Users\\Test\\workspace -name "*.py" -exec sh -c 'echo $(($(wc -l < "$1") + $(grep -c "^#" "$1"))' _ {} \\; | awk '{sum+=$1} END {print sum}'); echo "Total: $total_lines"'''
)

# ============================================================================
# REAL PATTERN 8: Complex brace expansion for batch operations
# ============================================================================
test(
    "Brace expansion creating directory structure",
    '''echo mkdir -p {src,tests,docs}/{utils,core,api}/{models,views,controllers}/{v{1..3},legacy}'''
)

# ============================================================================
# REAL PATTERN 9: Xargs with complex shell execution
# ============================================================================
test(
    "Xargs with inline shell script",
    """find C:\\Users\\Test\\workspace -name "test_*.py" | head -5 | xargs -I {} sh -c 'echo "=== {} ==="; head -10 "{}" | grep -E "(def|class)" | nl'"""
)

# ============================================================================
# REAL PATTERN 10: Awk with complex BEGIN/END and variables
# ============================================================================
test(
    "Awk processing with BEGIN/END blocks",
    """find C:\\Users\\Test\\workspace -name "*.py" -exec wc -l {} \\; | awk 'BEGIN{total=0; count=0; max=0; min=999999} {total+=$1; count++; if($1>max) max=$1; if($1<min) min=$1} END{print "Total:"total" Avg:"int(total/count)" Max:"max" Min:"min}'"""
)

# ============================================================================
# REAL PATTERN 11: Grep with complex regex and context
# ============================================================================
test(
    "Grep with lookahead/behind simulation using multiple greps",
    '''grep -r "def " C:\\Users\\Test\\workspace\\src/ | grep -v "__" | grep -E "def [a-z_]+\\(" | sed "s/.*def //" | cut -d"(" -f1 | sort | uniq -c | sort -rn | head -10'''
)

# ============================================================================
# REAL PATTERN 12: Sed with multiple transformations and addressing
# ============================================================================
test(
    "Sed with hold space and multi-line patterns",
    """echo -e "line1\\nline2\\nline3\\nline4" | sed -e '1,2s/line/LINE/' -e '3,$s/line/row/' -e 's/[0-9]/[&]/g' """
)

# ============================================================================
# REAL PATTERN 13: For loop with nested braces and command subst
# ============================================================================
test(
    "Nested for loops with brace expansion",
    '''for env in {dev,staging,prod}; do for svc in {api,worker}{1..2}; do echo "Deploy $env/$svc to $(echo ${env^^})-${svc}"; done; done'''
)

# ============================================================================
# REAL PATTERN 14: Complex redirection chains
# ============================================================================
test(
    "Multiple redirects with stderr and stdout",
    '''(echo "stdout message"; echo "stderr message" >&2) 2>&1 | tee /tmp/combined.log | grep -E "(stdout|stderr)"'''
)

# ============================================================================
# REAL PATTERN 15: Tee with multiple outputs
# ============================================================================
test(
    "Tee writing to multiple files in pipeline",
    '''echo -e "data1\\ndata2\\ndata3" | tee >(grep "data1" > /tmp/out1.txt) >(grep "data2" > /tmp/out2.txt) | wc -l'''
)

# ============================================================================
# REAL PATTERN 16: Case statement with pattern matching
# ============================================================================
test(
    "Case with multiple patterns and fallthrough",
    '''for file in test_*.py README.md setup.py; do
  case "$file" in
    test_*) echo "Test file: $file";;
    *.md) echo "Docs file: $file";;
    *) echo "Other: $file";;
  esac
done'''
)

# ============================================================================
# REAL PATTERN 17: Parameter expansion extreme
# ============================================================================
test(
    "All parameter expansion types combined",
    '''file="/path/to/project/src/module/component.py";
dir=${file%/*}; base=${file##*/}; name=${base%.*}; ext=${file##*.};
parent=${dir%/*}; upper=${name^^}; lower=${name,,};
echo "Dir:$dir Base:$base Name:$name Ext:$ext Parent:$parent Upper:$upper Lower:$lower"'''
)

# ============================================================================
# REAL PATTERN 18: Background jobs with wait
# ============================================================================
test(
    "Parallel background jobs with wait and status check",
    '''(sleep 0.1; echo "Job 1 done") & pid1=$!;
(sleep 0.2; echo "Job 2 done") & pid2=$!;
(sleep 0.15; echo "Job 3 done") & pid3=$!;
wait $pid1 $pid2 $pid3;
echo "All jobs completed"'''
)

# ============================================================================
# REAL PATTERN 19: Array operations (if supported)
# ============================================================================
test(
    "Array declaration and manipulation",
    '''files=(test_*.py); echo "Found: ${#files[@]} files"; for f in "${files[@]:0:3}"; do echo "- $f"; done'''
)

# ============================================================================
# REAL PATTERN 20: THE ULTIMATE - Everything combined
# ============================================================================
test(
    "ULTIMATE: All features in one mega command",
    '''for env in {prod,staging}; do
  echo "=== Environment: ${env^^} ==="
  find C:\\Users\\Test\\workspace -name "*.py" -type f ! -path "*test*" | head -3 | while read f; do
    lines=$(wc -l < "$f" || echo 0)
    funcs=$(grep -c "^def " "$f" || echo 0)
    echo "  ${f##*/}: $lines lines, $funcs functions" | tee -a /tmp/${env}_report.log
  done
  echo "Report saved to /tmp/${env}_report.log"
done | tee >(wc -l > /tmp/total_lines.txt)'''
)
