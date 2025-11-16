#!/usr/bin/env python3
"""Debug command substitution processing"""

from bash_tool_executor import BashToolExecutor

# Monkey-patch to add logging
original_translate_sub = BashToolExecutor._translate_substitution_content

def debug_translate_sub(self, content):
    print(f"\n[DEBUG] _translate_substitution_content called")
    print(f"[DEBUG] INPUT content: {repr(content)}")
    result = original_translate_sub(self, content)
    print(f"[DEBUG] OUTPUT result: {repr(result)}")
    return result

BashToolExecutor._translate_substitution_content = debug_translate_sub

# Now run test
executor = BashToolExecutor(working_dir='/home/user/couch')
executor.testmode = True

cmd = 'cat $(find . -name "README.md" | head -1)'
print(f"MAIN CMD: {cmd}\n")
result = executor.execute({'command': cmd, 'description': 'test'})

for line in result.split('\n'):
    if 'Would execute:' in line:
        print(f"\nFINAL RESULT: {line.split('Would execute:')[1].strip()}")
        break
