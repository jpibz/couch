#!/usr/bin/env python3
"""
REAL VERIFICATION - Print and READ full scripts
No shortcuts - must see ENTIRE PowerShell/CMD scripts generated
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bash_tool.bash_tool_executor import BashToolExecutor

print("=" * 80)
print("SCRIPT VERIFICATION - FULL OUTPUT")
print("=" * 80)
print()

# Force emulation
executor = BashToolExecutor(
    working_dir='/home/user/couch',
    test_capabilities={'bash': False}
)

def show_full_script(cmd_name, cmd):
    """Show COMPLETE script generated - no shortcuts"""
    print(f"\n{'='*80}")
    print(f"TESTING: {cmd_name}")
    print(f"INPUT: {cmd}")
    print(f"{'='*80}")

    result = executor.execute({'command': cmd, 'description': f'test {cmd_name}'})

    # Print EVERYTHING
    print(result)
    print(f"{'='*80}\n")


# Test representative commands from each category
print("\n### SIMPLE COMMANDS ###")
show_full_script('pwd', 'pwd')
show_full_script('whoami', 'whoami')
show_full_script('echo', 'echo hello world')
show_full_script('true', 'true')
show_full_script('basename', 'basename /path/to/file.txt')

print("\n### MEDIUM COMMANDS ###")
show_full_script('ls', 'ls -la')
show_full_script('cat', 'echo test | cat')
show_full_script('head', 'echo -e "a\\nb\\nc\\nd\\ne" | head -n 3')
show_full_script('wc', 'echo -e "a\\nb\\nc" | wc -l')
show_full_script('tr', 'echo hello | tr a-z A-Z')

print("\n### COMPLEX COMMANDS ###")
show_full_script('grep', 'echo -e "foo\\nbar\\nbaz" | grep ba')
show_full_script('awk', 'echo "a b c" | awk \'{print $2}\'')
show_full_script('sed', 'echo hello | sed "s/hello/world/"')
show_full_script('sort', 'echo -e "c\\na\\nb" | sort')
show_full_script('cut', 'echo "a:b:c" | cut -d: -f2')

print("\n" + "=" * 80)
print("READ EACH SCRIPT ABOVE - VERIFY SYNTAX AND LOGIC")
print("=" * 80)
