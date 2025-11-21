#!/usr/bin/env python3
"""Test tilde expansion with Windows paths"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock Windows environment
original_environ = os.environ.copy()
os.environ['USERPROFILE'] = r'C:\Users\Giovanni'

from src.bash_tool.bash_command_preprocessor import BashCommandPreprocessor

prep = BashCommandPreprocessor()

print("=" * 80)
print("Testing tilde expansion with Windows paths")
print("=" * 80)

test_cases = [
    ("ls ~/Documents", "Should expand ~ at start"),
    ("cd ~/workspace && ls", "Should expand ~ in middle"),
    ("cat ~/file.txt | grep pattern", "Should expand ~ with pipe"),
    ("echo ~/path1 ~/path2", "Should expand multiple tildes"),
]

for cmd, desc in test_cases:
    print(f"\nTest: {desc}")
    print(f"Input:  {cmd}")
    try:
        result = prep.preprocess_always(cmd)
        print(f"Output: {result}")

        # Verify backslashes are present (Windows path)
        if '~' in result:
            print("❌ FAIL - Tilde not expanded!")
        elif r'C:\Users\Giovanni' in result or 'C:\\Users\\Giovanni' in result.replace('\\\\\\\\', '\\\\'):
            print("✅ PASS - Expanded correctly")
        else:
            print(f"⚠️  CHECK - Unexpected result")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

# Restore environment
os.environ = original_environ

print("\n" + "=" * 80)
