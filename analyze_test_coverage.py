#!/usr/bin/env python3
"""
Analyze test coverage for all 68 commands in CommandEmulator.
"""
import re
import os
from collections import defaultdict

# 68 commands from command_map
COMMANDS = [
    'awk', 'base64', 'basename', 'cat', 'cd', 'chmod', 'chown', 'column',
    'comm', 'cp', 'curl', 'cut', 'date', 'df', 'diff', 'dirname', 'du',
    'echo', 'env', 'export', 'false', 'file', 'find', 'grep', 'gunzip',
    'gzip', 'head', 'hexdump', 'hostname', 'join', 'jq', 'kill', 'ln',
    'ls', 'md5sum', 'mkdir', 'mv', 'paste', 'printenv', 'ps', 'pwd',
    'readlink', 'realpath', 'rm', 'sed', 'seq', 'sha1sum', 'sha256sum',
    'sleep', 'sort', 'split', 'stat', 'strings', 'tail', 'tar', 'tee',
    'test', 'timeout', 'touch', 'tr', 'true', 'uniq', 'unzip', 'watch',
    'wc', 'wget', 'which', 'whoami', 'yes', 'zip'
]

def extract_commands_from_string(cmd_string):
    """
    Extract all command names from a command string.
    Handles pipes, &&, ||, ;, etc.
    """
    # Split by common operators
    parts = re.split(r'[|;&]+', cmd_string)

    commands = []
    for part in parts:
        # Remove leading/trailing whitespace
        part = part.strip()
        if not part:
            continue

        # Get first word (the command)
        # Handle command substitution $(...)
        part = re.sub(r'\$\([^)]+\)', '', part)

        # Split on spaces and get first token
        tokens = part.split()
        if tokens:
            cmd = tokens[0]
            # Remove variable assignments (VAR=value command)
            if '=' not in cmd:
                commands.append(cmd)
            elif len(tokens) > 1:
                commands.append(tokens[1])

    return commands

def analyze_test_files():
    """Analyze all test files for command coverage."""
    test_dir = '/home/user/couch/tests'
    command_counts = defaultdict(int)
    command_examples = defaultdict(list)

    # Find all test files
    test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]

    for test_file in test_files:
        filepath = os.path.join(test_dir, test_file)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extract test commands - multiple patterns:
        # 1. runner.test("command", "description")
        # 2. test("description", "command") - second param is command
        # 3. if test(..., 'command'):
        # 4. Direct command strings in triple quotes

        # Pattern 1: runner.test("command", ...)
        pattern1 = r'runner\.test\(["\']([^"\']+)["\']'

        # Pattern 2: test("description", "command") or test('desc', 'command')
        pattern2 = r'test\(["\'][^"\']*["\'],\s*["\']([^"\']+)["\']'

        # Pattern 3: if test(..., 'command'):
        pattern3 = r'if\s+test\(["\'][^"\']*["\'],\s*["\']([^"\']+)["\']'

        # Pattern 4: executor.execute("command")
        pattern4 = r'executor\.execute\(["\']([^"\']+)["\']'

        matches = (re.findall(pattern1, content) +
                   re.findall(pattern2, content) +
                   re.findall(pattern3, content) +
                   re.findall(pattern4, content))

        for cmd_string in matches:
            # Extract all commands from the string
            cmds = extract_commands_from_string(cmd_string)

            for cmd in cmds:
                if cmd in COMMANDS:
                    command_counts[cmd] += 1
                    # Save first 3 examples
                    if len(command_examples[cmd]) < 3:
                        command_examples[cmd].append((cmd_string, test_file))

    return command_counts, command_examples

def main():
    print("Analyzing test coverage for 68 commands...")
    print("="*80)

    counts, examples = analyze_test_files()

    # Separate into categories
    well_covered = []  # 10+ tests
    some_coverage = []  # 1-9 tests
    no_coverage = []   # 0 tests

    for cmd in sorted(COMMANDS):
        count = counts[cmd]
        if count >= 10:
            well_covered.append((cmd, count))
        elif count >= 1:
            some_coverage.append((cmd, count))
        else:
            no_coverage.append((cmd, count))

    # Print results
    print(f"\n{'='*80}")
    print(f"WELL COVERED (10+ tests): {len(well_covered)} commands")
    print(f"{'='*80}")
    for cmd, count in sorted(well_covered, key=lambda x: x[1], reverse=True):
        print(f"  {cmd:15} {count:3} tests")
        for ex, file in examples[cmd][:2]:
            print(f"      → {ex[:60]}")

    print(f"\n{'='*80}")
    print(f"SOME COVERAGE (1-9 tests): {len(some_coverage)} commands")
    print(f"{'='*80}")
    for cmd, count in sorted(some_coverage, key=lambda x: x[1], reverse=True):
        print(f"  {cmd:15} {count:3} tests")
        for ex, file in examples[cmd][:1]:
            print(f"      → {ex[:60]}")

    print(f"\n{'='*80}")
    print(f"NO COVERAGE (0 tests): {len(no_coverage)} commands")
    print(f"{'='*80}")
    print(f"  {', '.join([cmd for cmd, _ in no_coverage])}")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total commands:      {len(COMMANDS)}")
    print(f"Tested:              {len(well_covered) + len(some_coverage)} ({(len(well_covered) + len(some_coverage))/len(COMMANDS)*100:.1f}%)")
    print(f"Not tested:          {len(no_coverage)} ({len(no_coverage)/len(COMMANDS)*100:.1f}%)")
    print(f"Well covered (10+):  {len(well_covered)} ({len(well_covered)/len(COMMANDS)*100:.1f}%)")

if __name__ == '__main__':
    main()
