#!/usr/bin/env python3
"""
Debug the execution flow
"""

from bash_tool_executor_REFACTORED import BashToolExecutor
from pathlib import Path

# Monkey-patch to add logging
original_expand = BashToolExecutor._expand_variables
def logged_expand(self, command):
    result = original_expand(self, command)
    print(f"[EXPAND_VARIABLES]")
    print(f"  Input:  {command}")
    print(f"  Output: {result}")
    return result

original_process_cmd_sub = BashToolExecutor._process_command_substitution_recursive
def logged_process_cmd_sub(self, command):
    print(f"[PROCESS_CMD_SUBSTITUTION]")
    print(f"  Input: {command}")
    result = original_process_cmd_sub(self, command)
    print(f"  Output: {result}")
    return result

BashToolExecutor._expand_variables = logged_expand
BashToolExecutor._process_command_substitution_recursive = logged_process_cmd_sub

# Now run test
executor = BashToolExecutor(working_dir='/home/user/couch')
result = executor.execute({'command': 'head -n $((5 + 5)) file.txt', 'description': 'test'})

print("\n" + "=" * 80)
print("FINAL RESULT:")
print(result)
