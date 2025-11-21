#!/usr/bin/env python3
"""
BUG FINDER - Analisi sistemat

ica output test
"""
import subprocess
import re

def run_test_and_find_bugs():
    """Run tests and find all bugs"""

    bugs_found = []

    # Run tests
    result = subprocess.run(
        ['python', 'tests/test_ultra_extreme_live.py'],
        capture_output=True,
        text=True,
        timeout=120
    )

    output = result.stdout + result.stderr

    # BUG 1: Brace expansion duplicates
    if 'staging2c/api3/config.json' in output:
        count = output.count('staging2c/api3/config.json')
        if count > 1:
            bugs_found.append(f"BUG: Brace expansion duplicates - staging2c/api3/config.json appears {count} times")

    # BUG 2: Quote handling in command substitution
    if '"Level2: "Level3:' in output:
        bugs_found.append("BUG: Command substitution doesn't remove inner quotes")

    # BUG 3: Check for ERROR lines
    errors = re.findall(r'ERROR.*: (.*)', output)
    for error in errors:
        bugs_found.append(f"ERROR: {error}")

    # BUG 4: Check for exceptions
    if 'Traceback' in output:
        bugs_found.append("BUG: Exception raised during execution")

    # BUG 5: Check parameter expansion not working
    if 'dir=; base=; name=; ext=;' in output:
        bugs_found.append("BUG: Parameter expansion removed instead of preserved")

    # BUG 6: AST parsing errors
    if 'Expected WORD, got' in output:
        bugs_found.append("BUG: AST parser error")

    return bugs_found

if __name__ == '__main__':
    print("=" * 80)
    print("BUG FINDER - Systematic Analysis")
    print("=" * 80)
    print()

    bugs = run_test_and_find_bugs()

    if bugs:
        print(f"Found {len(bugs)} bugs:")
        for i, bug in enumerate(bugs, 1):
            print(f"{i}. {bug}")
    else:
        print("No bugs found!")

    print()
    print("=" * 80)
