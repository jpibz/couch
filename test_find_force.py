#!/usr/bin/env python3
"""Test find with force_translate"""

from bash_tool_executor import BashToolExecutor
from unix_translator import CommandTranslator
from path_translator import PathTranslator

path_translator = PathTranslator(claude_home_win='C:\\Users\\test', claude_home_unix='/home/test')
translator = CommandTranslator(path_translator)

# Test find translation with force_translate=True
test_cmds = [
    'find . -name "README.md"',
    'find . -name "README.md" | head -1',
    'find . -name "*.py" | wc -l',
]

for cmd in test_cmds:
    print(f"\nCMD: {cmd}")
    result, use_shell, method = translator.translate(cmd, force_translate=True)
    print(f"TRANSLATED: {result}")
    print(f"METHOD: {method}")
