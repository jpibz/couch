#!/usr/bin/env python3
"""Debug grep -r translation"""

from unix_translator import CommandTranslator

translator = CommandTranslator()

# Test grep -r
cmd = 'grep -rn "class.*Executor" --include="*.py" .'
parts = cmd.split()

print(f"Command: {cmd}")
print(f"Parts: {parts}")

translated, use_shell = translator._translate_grep(cmd, parts)

print(f"\nTranslated: {translated}")
print(f"Use shell: {use_shell}")

# Check if -Recurse is in output
if '-Recurse' in translated:
    print("✓ -Recurse found")
else:
    print("✗ -Recurse NOT found")
