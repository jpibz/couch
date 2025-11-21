#!/usr/bin/env python3
"""Debug brace expansion step by step"""
import sys
sys.path.insert(0, '/home/user/couch/src')

from bash_tool.bash_command_preprocessor import BashCommandPreprocessor

prep = BashCommandPreprocessor()

# Test the exact failing case
cmd = 'echo {prod,staging1}/{api{1..3},workerx}'

print("=" * 80)
print(f"Input: {cmd}")
print("=" * 80)

# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

result = prep._expand_braces(cmd)

print("\n" + "=" * 80)
print(f"Output: {result}")
print("=" * 80)

# Parse result
words = result.replace('echo ', '').split()
print(f"\nTotal words: {len(words)}")
print(f"Words: {words}")

# Count occurrences
from collections import Counter
counts = Counter(words)

print("\nOccurrence counts:")
for word, count in sorted(counts.items()):
    marker = " ❌ DUPLICATE!" if count > 1 else ""
    print(f"  {word}: {count}{marker}")

# Expected
expected = [
    'prod/api1', 'prod/api2', 'prod/api3', 'prod/workerx',
    'staging1/api1', 'staging1/api2', 'staging1/api3', 'staging1/workerx'
]
print(f"\nExpected {len(expected)} words: {expected}")

if len(words) != len(expected):
    print(f"\n❌ FAIL: Got {len(words)} words instead of {len(expected)}")
else:
    print(f"\n✅ PASS: Correct number of words")
