#!/usr/bin/env python3
"""Test brace expansion duplicates bug"""
import sys
sys.path.insert(0, '/home/user/couch/src')

from bash_tool.bash_command_preprocessor import BashCommandPreprocessor

prep = BashCommandPreprocessor()

# Test case: simple nested braces
test_cases = [
    ('{a,b}{1,2}', ['a1', 'a2', 'b1', 'b2']),  # 4 items
    ('{a,b{1,2}}', ['a', 'b1', 'b2']),  # 3 items
    ('{prod,staging{1,2{a,b}}}', ['prod', 'staging1', 'staging2a', 'staging2b']),  # 4 items
    ('{prod,staging1}/{api{1..3},workerx}', ['prod/api1', 'prod/api2', 'prod/api3', 'prod/workerx',
                                               'staging1/api1', 'staging1/api2', 'staging1/api3', 'staging1/workerx']),  # 8 items
]

for input_cmd, expected in test_cases:
    result = prep._expand_braces(f'echo {input_cmd}')
    result_words = result.replace('echo ', '').split()

    print(f"\nInput: {input_cmd}")
    print(f"Expected: {len(expected)} items: {expected}")
    print(f"Got: {len(result_words)} items")

    # Count duplicates
    from collections import Counter
    counts = Counter(result_words)
    duplicates = {word: count for word, count in counts.items() if count > 1}

    if duplicates:
        print(f"❌ DUPLICATES FOUND: {duplicates}")
    else:
        print("✅ No duplicates")

    # Check if result matches expected
    if set(result_words) == set(expected) and len(result_words) == len(expected):
        print("✅ Correct expansion")
    else:
        print("❌ WRONG expansion")
        print(f"   Missing: {set(expected) - set(result_words)}")
        print(f"   Extra: {set(result_words) - set(expected)}")
