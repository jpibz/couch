#!/usr/bin/env python3
"""Debug brace expansion step by step with FULL tracing"""
import sys
import re
from itertools import product

sys.path.insert(0, '/home/user/couch/src')

# Inline the brace expansion logic with DEBUG prints
def expand_items(content):
    """Generate items from single brace content"""
    # Numeric range
    m = re.match(r'^(\d+)\.\.(\d+)$', content)
    if m:
        start = int(m.group(1))
        end = int(m.group(2))
        padding = len(m.group(1)) if m.group(1).startswith('0') else 0

        if start <= end:
            result = [str(i).zfill(padding) if padding else str(i)
                   for i in range(start, end + 1)]
        else:
            result = [str(i).zfill(padding) if padding else str(i)
                   for i in range(start, end - 1, -1)]
        print(f"    expand_items('{content}') → {result}")
        return result

    # List (may contain spaces from previous expansion!)
    if ',' in content:
        result = [item.strip() for item in content.split(',')]
        print(f"    expand_items('{content}') → {result}")
        return result

    print(f"    expand_items('{content}') → None (can't expand)")
    return None


def expand_word_with_braces(word):
    """Expand a single word containing one or more brace patterns"""
    print(f"  expand_word_with_braces('{word}')")

    brace_pattern = r'(?<!\$)\{([^{}]+)\}'
    matches = list(re.finditer(brace_pattern, word))

    if not matches:
        print(f"    No braces found → ['{word}']")
        return [word]

    print(f"    Found {len(matches)} brace patterns")

    # Extract all brace contents and expand to items
    expanded_lists = []
    for i, match in enumerate(matches):
        content = match.group(1)
        print(f"    Brace {i+1}: {{{{content}}}} = {{{content}}}")
        items = expand_items(content)
        if items is None:
            items = ['{' + content + '}']
        expanded_lists.append(items)

    # Cartesian product
    cartesian = list(product(*expanded_lists))
    print(f"    Cartesian product of {len(expanded_lists)} lists: {len(cartesian)} combinations")

    # Reconstruct word for each combination
    results = []
    for combo in cartesian:
        result = word
        for match, item in zip(reversed(matches), reversed(combo)):
            result = result[:match.start()] + item + result[match.end():]
        results.append(result)

    print(f"    Results: {results}")
    return results


# Test the failing case
command = 'echo {prod,staging1}/{api{1..3},workerx}'

print("=" * 100)
print(f"INPUT: {command}")
print("=" * 100)

# PASS 1: Nested expansion (simplified - only do one level)
print("\n--- PASS 1: Innermost nested braces ---")
# Find {1..3} inside api{1..3}
print("Looking for innermost braces...")
# In this case: {1..3} is innermost
# Prefix is 'api'
# Expansion: api{1..3} → api1,api2,api3
# Result: {prod,staging1}/{api1,api2,api3,workerx}
command_after_pass1 = 'echo {prod,staging1}/{api1,api2,api3,workerx}'
print(f"After Pass 1: {command_after_pass1}")

# PASS 2: Token-based expansion
print("\n--- PASS 2: Token-based expansion ---")
tokens = re.split(r'([ \t\n;|&])', command_after_pass1)
print(f"Tokens: {tokens}")

result_tokens = []
for token in tokens:
    if token in [' ', '\t', '\n', ';', '|', '&', '']:
        result_tokens.append(token)
        continue

    if not re.search(r'(?<!\$)\{[^{}]+\}', token):
        print(f"\nToken '{token}' has no braces")
        result_tokens.append(token)
        continue

    print(f"\nToken '{token}' HAS BRACES - expanding...")
    expanded = expand_word_with_braces(token)
    result_tokens.append(' '.join(expanded))

final = ''.join(result_tokens)
print("\n" + "=" * 100)
print(f"FINAL: {final}")
print("=" * 100)

# Parse result
words = final.replace('echo ', '').split()
print(f"\nTotal words: {len(words)}")

from collections import Counter
counts = Counter(words)
print("\nOccurrence counts:")
for word, count in sorted(counts.items()):
    marker = " ❌ DUPLICATE!" if count > 1 else ""
    print(f"  {word}: {count}{marker}")
