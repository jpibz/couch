#!/usr/bin/env python3
"""Test translator directly"""

import sys
sys.path.insert(0, '/home/user/couch')

from unix_translator import CommandTranslator, PathTranslator

path_trans = PathTranslator()
trans = CommandTranslator(path_trans)

# Test the problematic command
cmd = 'find . -name "README.md" | head -1'
print(f"CMD: {cmd}")
print(f"\nWith force_translate=True:")
result, use_shell, method = trans.translate(cmd, force_translate=True)
print(f"RESULT: {result}")
print(f"METHOD: {method}")
