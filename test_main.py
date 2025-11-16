#!/usr/bin/env python3
"""
TEST MAIN - Istanzia BashToolExecutor con TESTMODE=True ed esegue comandi bash

IMPORTANTE: Prima di eseguire, impostare TESTMODE=True in bash_tool_executor_REFACTORED.py
"""

import sys
import logging

# Setup logging dettagliato
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s - %(name)-20s - %(message)s'
)

logger = logging.getLogger('TestMain')

# Importa BashToolExecutor
try:
    from bash_tool_executor_REFACTORED import BashToolExecutor
    logger.info("✓ BashToolExecutor imported")
except ImportError as e:
    logger.error(f"✗ Failed to import BashToolExecutor: {e}")
    sys.exit(1)


def print_separator(char='=', length=80):
    """Print separator line"""
    print(char * length)


def test_command(executor, cmd, description):
    """Test a single bash command"""
    print_separator('=')
    print(f"TEST: {description}")
    print(f"CMD:  {cmd}")
    print_separator('-')

    try:
        result = executor.execute({
            'command': cmd,
            'description': description
        })

        print("RESULT:")
        print(result)

        # Show subprocess calls if available
        if hasattr(executor, 'TESTMODE') and executor.TESTMODE:
            if hasattr(executor.command_executor, 'get_subprocess_calls'):
                calls = executor.command_executor.get_subprocess_calls()
                if calls:
                    print(f"\n[DEBUG] Subprocess calls made: {len(calls)}")
                    for i, call in enumerate(calls, 1):
                        print(f"  [{i}] {call['command'][:80]}")
                executor.command_executor.clear_subprocess_calls()

        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print_separator('=')
    print("BASH TOOL EXECUTOR - TEST MAIN")
    print_separator('=')

    # Istanzia BashToolExecutor
    logger.info("Initializing BashToolExecutor...")
    try:
        executor = BashToolExecutor(
            working_dir="/tmp/bash_test",
            enabled=True,
            use_git_bash=True
        )
        logger.info(f"✓ BashToolExecutor initialized")
        logger.info(f"  TESTMODE: {executor.TESTMODE}")
        logger.info(f"  Git Bash: {executor.git_bash_exe}")
        logger.info(f"  Claude Home: {executor.claude_home_unix}")

        if not executor.TESTMODE:
            logger.error("✗ TESTMODE is FALSE! Set TESTMODE=True in bash_tool_executor_REFACTORED.py")
            return 1

    except Exception as e:
        logger.error(f"✗ Failed to initialize BashToolExecutor: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()

    # Test commands
    test_cases = [
        # ===== GREP =====
        ("grep -E 'def.*execute' file.py", "grep with extended regex"),
        ("grep -C 5 'class' file.py", "grep with context lines"),

        # ===== AWK =====
        ("awk '/def/ {print $1}' file.py", "awk field extraction"),
        ("awk -F ':' '{print $2}' /etc/passwd", "awk with delimiter"),

        # ===== HEAD/TAIL =====
        ("head -10 file.txt", "head shorthand syntax"),
        ("tail -20 logfile.log", "tail shorthand syntax"),

        # ===== WC =====
        ("wc -l file.txt", "wc line count"),
        ("wc -l *.py", "wc with glob pattern"),

        # ===== CAT HEREDOC =====
        ("""cat <<'EOF'
Text with $VAR that should NOT expand
EOF""", "cat heredoc quoted (no expansion)"),

        ("""cat <<EOF
HOME is: $HOME
USER is: $USER
EOF""", "cat heredoc unquoted (with expansion)"),

        # ===== PIPELINES =====
        ("ls -la | grep '.py'", "pipeline: ls | grep"),
        ("grep 'ERROR' log.txt | wc -l", "pipeline: grep | wc"),

        # ===== VARIABLE EXPANSION =====
        ("echo $HOME", "simple $VAR expansion"),
        ("echo ${PATH}", "braced ${VAR} expansion"),
        ("ls ~/Documents", "tilde expansion"),

        # ===== COMMAND SUBSTITUTION =====
        ("echo $(date)", "command substitution $(date)"),
        ("echo $(cat version.txt)", "command substitution $(cat)"),

        # ===== COMMAND CHAINS =====
        ("mkdir test && cd test && pwd", "command chain with &&"),
        ("test -f missing.txt || echo 'Not found'", "command chain with ||"),

        # ===== FILE OPERATIONS =====
        ("ls -la /tmp", "ls with flags"),
        ("pwd", "print working directory"),
        ("mkdir -p /tmp/test/nested", "mkdir nested"),

        # ===== STDERR REDIRECTION =====
        ("command 2> errors.log", "stderr to file"),
        ("command 2>&1", "stderr to stdout"),
        ("command 2>&1 | grep ERROR", "stderr in pipeline"),

        # ===== COMPLEX =====
        ("find . -name '*.py' -exec grep 'TODO' {} \\;", "find with -exec"),
        ("tar -czf archive.tar.gz dir/", "tar create archive"),
        ("sed 's/old/new/g' file.txt", "sed substitution"),
    ]

    passed = 0
    failed = 0

    for cmd, desc in test_cases:
        success = test_command(executor, cmd, desc)
        if success:
            passed += 1
        else:
            failed += 1
        print()  # Empty line between tests

    # Summary
    print_separator('=')
    print("TEST SUMMARY")
    print_separator('=')
    print(f"Total tests: {len(test_cases)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {100 * passed / len(test_cases):.1f}%")
    print_separator('=')

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
