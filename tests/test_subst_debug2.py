#!/usr/bin/env python3
"""Debug command substitution - full pipeline"""

from bash_tool_executor import BashToolExecutor

# Patch multiple methods
original_process_subst = BashToolExecutor._process_command_substitution_recursive
original_translate_cmd = None

def debug_process_subst(self, command):
    print(f"\n[1] BEFORE _process_command_substitution_recursive:")
    print(f"    {repr(command[:150])}")
    result = original_process_subst(self, command)
    print(f"[1] AFTER _process_command_substitution_recursive:")
    print(f"    {repr(result[:150])}")
    return result

BashToolExecutor._process_command_substitution_recursive = debug_process_subst

# Patch execute to see steps
original_execute = BashToolExecutor.execute

def debug_execute(self, params):
    cmd = params['command']
    print(f"\n[EXEC] Original command: {repr(cmd[:100])}")

    # Call original but intercept at key points
    result = original_execute(self, params)

    return result

BashToolExecutor.execute = debug_execute

# Run test
executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

cmd = 'cat $(find . -name "README.md" | head -1)'
print(f"MAIN CMD: {cmd}")
result = executor.execute({'command': cmd, 'description': 'test'})

for line in result.split('\n'):
    if 'Would execute:' in line:
        print(f"\n[FINAL] {line.split('Would execute:')[1].strip()}")
        break
