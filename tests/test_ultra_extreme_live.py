#!/usr/bin/env python3
"""
ULTRA EXTREME LIVE TEST - Vedere TUTTO il flusso di esecuzione

Test con:
- Pipeline lunghissime (10+ stadi)
- Heredocs complessi
- Redirect multipli
- Preprocessing estremo
- Command substitution annidati
- Process substitution
- Tutto combinato insieme

OBIETTIVO: Vedere output LUNGHISSIMI con ogni passaggio tracciato
"""
import sys
import logging
from pathlib import Path

# Setup logging dettagliato
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(name)-25s] %(levelname)-8s: %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.bash_tool.bash_tool_executor import BashToolExecutor

print("=" * 100)
print("🔥 ULTRA EXTREME LIVE TEST - Full Pipeline Flow Tracing 🔥")
print("=" * 100)
print()

# Initialize executor in test mode per vedere TUTTO
executor = BashToolExecutor(
    working_dir=Path('/home/user/couch'),
    test_mode=True
)

def run_extreme_test(name, cmd):
    """Run test e mostra TUTTO il flusso"""
    print("\n" + "█" * 100)
    print(f"TEST: {name}")
    print("█" * 100)
    print(f"COMMAND: {cmd}")
    print("-" * 100)

    try:
        result = executor.execute({'command': cmd, 'description': name})
        print(f"\n✅ COMPLETED")
        print(f"OUTPUT LENGTH: {len(result)} chars")
        if len(result) > 0:
            print(f"OUTPUT PREVIEW:\n{result[:500]}")
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

    print("\n")

# ============================================================================
# TEST 1: Pipeline LUNGHISSIMA (10+ stadi)
# ============================================================================
run_extreme_test(
    "Pipeline 10-stage con grep multipli, sort, uniq, wc",
    'find . -name "*.py" | '
    'grep -v __pycache__ | '
    'grep -v ".pyc" | '
    'head -100 | '
    'xargs -I {} basename {} | '
    'sort | '
    'uniq | '
    'grep "test" | '
    'wc -l | '
    'xargs echo "Total test files:"'
)

# ============================================================================
# TEST 2: Command substitution PROFONDAMENTE annidato (4+ livelli)
# ============================================================================
run_extreme_test(
    "Quad-nested command substitution",
    'echo "Level1: $(echo "Level2: $(echo "Level3: $(echo "Level4: $(echo deep)")")")"'
)

# ============================================================================
# TEST 3: Parameter expansion ESTREMO con tutto
# ============================================================================
run_extreme_test(
    "Mega parameter expansion chain",
    'file="/home/user/workspace/projects/myapp/src/components/Button.tsx"; '
    'dir=${file%/*}; '
    'base=${file##*/}; '
    'name=${base%%.*}; '
    'ext=${base#*.}; '
    'upper=${name^^}; '
    'echo "Dir: $dir | Base: $base | Name: $name | Ext: $ext | Upper: $upper"'
)

# ============================================================================
# TEST 4: Brace expansion PAZZESCO con nested multipli
# ============================================================================
run_extreme_test(
    "Triple nested brace expansion",
    'echo {prod,staging{1,2{a,b,c}}}/{api{1..3},worker{x,y}}/{config,secrets}{.json,.yaml,.xml}'
)

# ============================================================================
# TEST 5: Find con condizioni COMPLESSE e exec
# ============================================================================
run_extreme_test(
    "Find complex conditions with exec",
    'find . \\( -name "*.py" -o -name "*.sh" \\) '
    '-type f '
    '! -path "*__pycache__*" '
    '! -path "*.git*" '
    '-size +1k '
    '-exec echo "Found: {}" \\; | '
    'head -10'
)

# ============================================================================
# TEST 6: Heredoc COMPLESSO con variable expansion dentro
# ============================================================================
run_extreme_test(
    "Heredoc with variable expansion",
    '''cat <<EOF
Title: Test Report
Date: $(date +%Y-%m-%d)
User: $USER
Path: $(pwd)
Files: $(ls *.py 2>/dev/null | wc -l)
---
This is a multi-line heredoc
with variable expansion
and command substitution
---
EOF
'''
)

# ============================================================================
# TEST 7: Redirect MULTIPLI e complessi
# ============================================================================
run_extreme_test(
    "Complex redirections (stdout, stderr, append)",
    'find /nonexistent 2>&1 | grep -i "no such" | tee /tmp/errors.log | wc -l'
)

# ============================================================================
# TEST 8: While loop con pipeline e command subst
# ============================================================================
run_extreme_test(
    "While loop reading from pipeline",
    'find . -name "test_*.py" -type f | head -5 | while read f; do '
    'echo "File: ${f##*/} - Lines: $(wc -l < "$f" 2>/dev/null || echo 0)"; '
    'done'
)

# ============================================================================
# TEST 9: Process substitution con diff
# ============================================================================
run_extreme_test(
    "Process substitution with diff",
    'diff <(ls *.py | sort) <(find . -name "*.py" -type f -exec basename {} \\; | sort) | head -10'
)

# ============================================================================
# TEST 10: Arithmetic COMPLESSA con nested
# ============================================================================
run_extreme_test(
    "Complex arithmetic with nested operations",
    'x=10; y=20; z=$((x * y + $(echo 5) - $((3 + 2)))); echo "Result: $z"'
)

# ============================================================================
# TEST 11: Sed/Awk ACROBATICO
# ============================================================================
run_extreme_test(
    "Sed and Awk extreme pipeline",
    'echo -e "line1\\nline2\\nline3" | '
    'sed "s/line/LINE/g; s/1/ONE/; s/2/TWO/" | '
    'awk \'BEGIN {count=0} {count++; print count ": " $0} END {print "Total: " count}\''
)

# ============================================================================
# TEST 12: Grep con REGEX complessa e context
# ============================================================================
run_extreme_test(
    "Grep with complex regex and context lines",
    'grep -r -A 2 -B 1 "def.*execute" src/ 2>/dev/null | head -50'
)

# ============================================================================
# TEST 13: TUTTO INSIEME - THE ULTIMATE NIGHTMARE
# ============================================================================
run_extreme_test(
    "THE ULTIMATE NIGHTMARE - Everything combined",
    'for env in prod staging dev; do '
    'echo "Environment: ${env^^}"; '
    'find . -name "*.py" -type f ! -path "*__pycache__*" 2>/dev/null | '
    'head -5 | '
    'while read f; do '
    'base=${f##*/}; '
    'name=${base%%.*}; '
    'lines=$(wc -l < "$f" 2>/dev/null || echo 0); '
    'echo "  - $name: $lines lines"; '
    'done; '
    'done'
)

# ============================================================================
# TEST 14: Array operations e loops annidati
# ============================================================================
run_extreme_test(
    "Nested loops with arrays",
    'for i in {1..3}; do '
    'for j in {a..c}; do '
    'for k in {x,y}; do '
    'echo "file_${i}_${j}_${k}.txt"; '
    'done; '
    'done; '
    'done | head -10'
)

# ============================================================================
# TEST 15: Quoting NIGHTMARE con escaped characters
# ============================================================================
run_extreme_test(
    "Quoting nightmare with escapes",
    '''echo "He said \\"Hello $(echo 'world')!\\" and she replied: '$(date)'"'''
)

# ============================================================================
# TEST 16: Git-like pipeline (real world)
# ============================================================================
run_extreme_test(
    "Git-like real-world pipeline",
    'find src/ -name "*.py" -type f -exec grep -l "class.*Executor" {} \\; | '
    'xargs -I {} sh -c \'echo "File: {}"; grep -n "class.*Executor" "{}"\' | '
    'head -20'
)

# ============================================================================
# TEST 17: JSON processing simulation
# ============================================================================
run_extreme_test(
    "JSON-like processing pipeline",
    'echo \'{"name": "test", "value": 42}\' | '
    'grep -o \'"name":[^,}]*\' | '
    'sed \'s/"name"://; s/"//g\''
)

# ============================================================================
# TEST 18: Multi-file operations con xargs
# ============================================================================
run_extreme_test(
    "Multi-file xargs operations",
    'find . -name "test_*.py" -type f | '
    'head -5 | '
    'xargs -I {} sh -c \'echo "=== {} ==="; head -3 "{}"\''
)

# ============================================================================
# TEST 19: Background job simulation con output merge
# ============================================================================
run_extreme_test(
    "Background job simulation",
    '(echo "Job 1 output" && sleep 0.1 && echo "Job 1 done") & '
    '(echo "Job 2 output" && sleep 0.1 && echo "Job 2 done") & '
    'wait; '
    'echo "All jobs completed"'
)

# ============================================================================
# TEST 20: MEGA EXTREME - All preprocessing + pipeline + redirects
# ============================================================================
run_extreme_test(
    "MEGA EXTREME - All techniques combined",
    'PROJECT=myapp; '
    'ENV=prod; '
    'for dir in {api{1..2},worker}/{config,secrets}; do '
    'path=~/$PROJECT/$ENV/$dir; '
    'echo "Checking: ${path}"; '
    'find "${path}" -name "*.{json,yaml}" 2>/dev/null | '
    'while read f; do '
    'base=${f##*/}; '
    'size=$(wc -c < "$f" 2>/dev/null || echo 0); '
    'echo "  ${base}: ${size} bytes"; '
    'done; '
    'done | head -30'
)

print("\n" + "=" * 100)
print("🎯 ULTRA EXTREME TESTS COMPLETED")
print("=" * 100)
print("\nCheck the output above to see the FULL PIPELINE FLOW for each test!")
print("Look for:")
print("  - Preprocessing stages (variable expansion, brace expansion, etc)")
print("  - Pipeline detection and splitting")
print("  - Command emulation decisions")
print("  - Execution engine calls")
print("=" * 100)
