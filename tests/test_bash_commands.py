#!/usr/bin/env python3
"""
Test harness for BashToolExecutor - Verify all acrobatic bash commands work

This script tests ALL bash command patterns used during development to ensure
nothing breaks when users try complex Unix operations.

TESTMODE must be enabled in bash_tool_executor_REFACTORED.py for this to work.
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger('BashTest')

# Import BashToolExecutor (will use TESTMODE)
try:
    from bash_tool_executor_REFACTORED import BashToolExecutor
except ImportError as e:
    logger.error(f"Failed to import BashToolExecutor: {e}")
    sys.exit(1)


# ============================================================================
# TEST COMMAND COLLECTION
# ============================================================================

ACROBATIC_COMMANDS = [
    # ========== GREP PATTERNS ==========
    {
        'name': 'grep with -E (extended regex)',
        'command': 'grep -E "def.*execute" bash_tool_executor.py',
        'description': 'Extended regex pattern matching'
    },
    {
        'name': 'grep with -C (context lines)',
        'command': 'grep -C 5 "class CommandExecutor" bash_tool_executor.py',
        'description': 'Show 5 lines of context around matches'
    },
    {
        'name': 'grep with -i (case insensitive)',
        'command': 'grep -i "error" logfile.txt',
        'description': 'Case-insensitive search'
    },
    {
        'name': 'grep with -v (invert match)',
        'command': 'grep -v "^#" config.txt',
        'description': 'Show lines NOT matching pattern'
    },
    {
        'name': 'grep with -n (line numbers)',
        'command': 'grep -n "TODO" source.py',
        'description': 'Show line numbers with matches'
    },

    # ========== AWK PATTERNS ==========
    {
        'name': 'awk field extraction',
        'command': '''awk '/def/ {print $1}' file.py''',
        'description': 'Extract first field from lines with "def"'
    },
    {
        'name': 'awk with custom delimiter',
        'command': '''awk -F ':' '{print $2}' /etc/passwd''',
        'description': 'Use : as field separator'
    },
    {
        'name': 'awk with NR (line number)',
        'command': '''awk 'NR > 10 {print}' file.txt''',
        'description': 'Print lines after line 10'
    },

    # ========== HEAD/TAIL/WC ==========
    {
        'name': 'head with -N shorthand',
        'command': 'head -10 file.txt',
        'description': 'First 10 lines (shorthand syntax)'
    },
    {
        'name': 'head with -n flag',
        'command': 'head -n 20 file.txt',
        'description': 'First 20 lines (long syntax)'
    },
    {
        'name': 'tail with -N shorthand',
        'command': 'tail -50 logfile.log',
        'description': 'Last 50 lines'
    },
    {
        'name': 'wc -l (line count)',
        'command': 'wc -l file.txt',
        'description': 'Count lines in file'
    },
    {
        'name': 'wc with glob pattern',
        'command': 'wc -l *.py',
        'description': 'Count lines in all Python files'
    },

    # ========== CAT WITH HEREDOC ==========
    {
        'name': 'cat with quoted heredoc (no expansion)',
        'command': '''cat <<'EOF'
This is text with $VAR that should NOT expand
EOF''',
        'description': 'Heredoc with quoted delimiter (literal)'
    },
    {
        'name': 'cat with unquoted heredoc (expansion)',
        'command': '''cat <<EOF
HOME is: $HOME
USER is: $USER
EOF''',
        'description': 'Heredoc with unquoted delimiter (expands variables)'
    },

    # ========== PIPELINES ==========
    {
        'name': 'git log | head',
        'command': 'git log --oneline | head -10',
        'description': 'Pipeline: git log into head'
    },
    {
        'name': 'grep | wc',
        'command': 'grep "ERROR" logfile.txt | wc -l',
        'description': 'Pipeline: grep into wc for counting'
    },
    {
        'name': 'cat | grep | wc',
        'command': 'cat file.txt | grep "pattern" | wc -l',
        'description': 'Multi-stage pipeline'
    },
    {
        'name': 'ls | grep',
        'command': 'ls -la | grep ".py"',
        'description': 'List files and filter'
    },

    # ========== VARIABLE EXPANSION ==========
    {
        'name': 'Simple $VAR expansion',
        'command': 'echo $HOME',
        'description': 'Expand $HOME environment variable'
    },
    {
        'name': '${VAR} expansion',
        'command': 'echo ${PATH}',
        'description': 'Expand ${PATH} with braces'
    },
    {
        'name': '${VAR:-default} expansion',
        'command': 'echo ${MISSING_VAR:-/default/path}',
        'description': 'Variable with default value'
    },
    {
        'name': 'Tilde expansion',
        'command': 'ls ~/Documents',
        'description': 'Expand ~ to home directory'
    },

    # ========== COMMAND SUBSTITUTION ==========
    {
        'name': 'Simple $(command)',
        'command': 'echo "Date is $(date)"',
        'description': 'Command substitution with $()'
    },
    {
        'name': 'Nested $($(...))',
        'command': 'echo $(echo $(whoami))',
        'description': 'Nested command substitution'
    },
    {
        'name': '$(cat file)',
        'command': 'echo $(cat version.txt)',
        'description': 'Substitute file contents'
    },

    # ========== COMMAND CHAINS ==========
    {
        'name': 'Command chain with &&',
        'command': 'mkdir test_dir && cd test_dir && pwd',
        'description': 'Chain with AND operator'
    },
    {
        'name': 'Command chain with ||',
        'command': 'test -f missing.txt || echo "File not found"',
        'description': 'Chain with OR operator'
    },
    {
        'name': 'Command chain with ;',
        'command': 'echo "First"; echo "Second"; echo "Third"',
        'description': 'Sequential commands'
    },

    # ========== FILE OPERATIONS ==========
    {
        'name': 'ls with flags',
        'command': 'ls -la /tmp',
        'description': 'List files with all details'
    },
    {
        'name': 'cd to directory',
        'command': 'cd /tmp',
        'description': 'Change directory'
    },
    {
        'name': 'pwd (print working directory)',
        'command': 'pwd',
        'description': 'Get current directory'
    },
    {
        'name': 'mkdir (create directory)',
        'command': 'mkdir -p /tmp/test/nested',
        'description': 'Create nested directories'
    },
    {
        'name': 'rm with flags',
        'command': 'rm -rf /tmp/test',
        'description': 'Remove directory recursively'
    },
    {
        'name': 'cp (copy)',
        'command': 'cp file1.txt file2.txt',
        'description': 'Copy file'
    },
    {
        'name': 'mv (move)',
        'command': 'mv oldname.txt newname.txt',
        'description': 'Rename/move file'
    },

    # ========== STDERR REDIRECTION ==========
    {
        'name': 'STDERR to file',
        'command': 'command 2> errors.log',
        'description': 'Redirect stderr to file'
    },
    {
        'name': 'STDERR to STDOUT',
        'command': 'command 2>&1',
        'description': 'Merge stderr into stdout'
    },
    {
        'name': 'Pipeline with stderr',
        'command': 'command 2>&1 | grep ERROR',
        'description': 'Pipe both stdout and stderr'
    },

    # ========== COMPLEX PATTERNS ==========
    {
        'name': 'find with -exec',
        'command': 'find . -name "*.py" -exec grep "TODO" {} \\;',
        'description': 'Find files and execute command on each'
    },
    {
        'name': 'Complex pipeline with awk',
        'command': 'ps aux | grep python | awk \'{print $2}\'',
        'description': 'Process list → filter → extract PID'
    },
    {
        'name': 'sed substitution',
        'command': 's/old/new/g',
        'description': 'Global string replacement'
    },
    {
        'name': 'tar create archive',
        'command': 'tar -czf archive.tar.gz directory/',
        'description': 'Create compressed tar archive'
    },
    {
        'name': 'tar extract archive',
        'command': 'tar -xzf archive.tar.gz',
        'description': 'Extract compressed tar archive'
    },
]


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_test(executor, test_case):
    """Run a single test command"""
    name = test_case['name']
    command = test_case['command']
    description = test_case['description']

    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"DESC: {description}")
    print(f"CMD:  {command}")
    print(f"{'-'*80}")

    try:
        # Execute command
        result = executor.execute({'command': command, 'description': description})

        # Show result
        print(f"RESULT:\n{result}")

        # Show subprocess calls if in test mode
        if hasattr(executor, 'TESTMODE') and executor.TESTMODE:
            if hasattr(executor.command_executor, 'get_subprocess_calls'):
                calls = executor.command_executor.get_subprocess_calls()
                if calls:
                    print(f"\nSUBPROCESS CALLS ({len(calls)}):")
                    for i, call in enumerate(calls, 1):
                        print(f"  [{i}] {call['command'][:100]}")
                executor.command_executor.clear_subprocess_calls()

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all test commands"""
    print("="*80)
    print("BASH TOOL EXECUTOR - ACROBATIC COMMAND TEST SUITE")
    print("="*80)

    # Initialize BashToolExecutor
    print("\nInitializing BashToolExecutor...")
    try:
        executor = BashToolExecutor(
            working_dir="/tmp/bash_test",
            enabled=True,
            use_git_bash=True  # Enable git bash for maximum compatibility
        )
        print(f"✓ BashToolExecutor initialized")
        print(f"  TESTMODE: {executor.TESTMODE}")
        print(f"  Git Bash: {executor.git_bash_exe}")

    except Exception as e:
        print(f"✗ Failed to initialize BashToolExecutor: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Run tests
    passed = 0
    failed = 0

    for test_case in ACROBATIC_COMMANDS:
        success = run_test(executor, test_case)
        if success:
            passed += 1
        else:
            failed += 1

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {len(ACROBATIC_COMMANDS)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {100 * passed / len(ACROBATIC_COMMANDS):.1f}%")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
