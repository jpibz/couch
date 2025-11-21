#!/usr/bin/env python3
"""Debug REAL preprocessor with patched logging"""
import sys
import re
sys.path.insert(0, '/home/user/couch/src')

from bash_tool.bash_command_preprocessor import BashCommandPreprocessor

# Patch the _expand_braces method to add logging
original_expand = BashCommandPreprocessor._expand_braces

def logged_expand(self, command):
    """Patched version with logging"""
    print(f"\n{'='*80}")
    print(f"_expand_braces INPUT: {command}")
    print(f"{'='*80}")

    # Call original with step tracing
    # We'll monkey-patch expand_word_with_braces too
    original_expand_word = None

    def find_innermost_brace(text):
        """Find innermost brace - LOGGED"""
        depth = 0
        brace_info = []
        stack = []

        for i, char in enumerate(text):
            if char == '{' and (i == 0 or text[i-1] != '$'):
                stack.append((i, depth))
                depth += 1
            elif char == '}' and stack:
                start_pos, brace_depth = stack.pop()
                depth -= 1
                content = text[start_pos+1:i]
                brace_info.append((start_pos, i+1, content, brace_depth))

        deepest = None
        max_depth = -1

        for start, end, content, brace_depth in brace_info:
            if '{' not in content and '}' not in content:
                if brace_depth > max_depth:
                    max_depth = brace_depth
                    deepest = (start, end, content)

        if deepest:
            print(f"  Found innermost: {text[deepest[0]:deepest[1]]} at pos {deepest[0]}")
        else:
            print(f"  No innermost brace found")

        return deepest

    # Manually implement Pass 1 with logging
    print("\n--- PASS 1: Nested braces ---")
    max_nested_iter = 20
    for iteration in range(max_nested_iter):
        innermost = find_innermost_brace(command)
        if innermost is None:
            print(f"  Iteration {iteration}: No more innermost braces")
            break

        start, end, content = innermost
        print(f"  Iteration {iteration}: Expanding {{{content}}}")

        # Check for numeric range
        m = re.match(r'^(\d+)\.\.(\d+)$', content)
        if m:
            s = int(m.group(1))
            e = int(m.group(2))
            items = [str(i) for i in range(s, e + 1)]
        elif ',' in content:
            items = [item.strip() for item in content.split(',')]
        else:
            print(f"    Can't expand - breaking")
            break

        print(f"    Items: {items}")

        # Find prefix
        prefix_start = start - 1
        while prefix_start >= 0 and command[prefix_start] not in ',{ \t\n;|&':
            prefix_start -= 1

        if prefix_start < 0 or command[prefix_start] in ' \t\n;|&{':
            print(f"    Top-level brace - leaving for Pass 2")
            break
        else:
            prefix_start += 1
            prefix = command[prefix_start:start]
            print(f"    Nested brace with prefix '{prefix}'")

            expanded_items = [prefix + item for item in items]
            replacement = ','.join(expanded_items)

            command = command[:prefix_start] + replacement + command[end:]
            print(f"    After expansion: {command}")

    print(f"\nAfter Pass 1: {command}")

    # Pass 2
    print("\n--- PASS 2: Token-based expansion ---")
    max_iter = 10
    prev = None

    for iteration in range(max_iter):
        if command == prev:
            print(f"  Iteration {iteration}: No change - done")
            break
        prev = command

        print(f"  Iteration {iteration}:")
        tokens = re.split(r'([ \t\n;|&])', command)
        print(f"    Tokens: {tokens}")

        result_tokens = []

        for token in tokens:
            if token in [' ', '\t', '\n', ';', '|', '&', '']:
                result_tokens.append(token)
                continue

            if not re.search(r'(?<!\$)\{[^{}]+\}', token):
                result_tokens.append(token)
                continue

            print(f"    Token '{token}' has braces")

            # Use REAL expand_word_with_braces from preprocessor
            # But we inline it here to see what happens
            brace_pattern = r'(?<!\$)\{([^{}]+)\}'
            matches = list(re.finditer(brace_pattern, token))

            print(f"      Found {len(matches)} brace patterns:")
            for idx, match in enumerate(matches):
                print(f"        {idx+1}. {{{match.group(1)}}}")

            # Now the REAL expansion happens
            # Call original method
            expanded = original_expand(self, f'dummy {token}').replace('dummy ', '').split()
            print(f"      Expanded to {len(expanded)} items: {expanded}")

            result_tokens.append(' '.join(expanded))

        command = ''.join(result_tokens)
        print(f"    After iteration {iteration}: {command}")

    print(f"\n{'='*80}")
    print(f"FINAL: {command}")
    print(f"{'='*80}\n")

    return command

# Patch it
BashCommandPreprocessor._expand_braces = logged_expand

# Test
prep = BashCommandPreprocessor()
result = prep._expand_braces('echo {prod,staging1}/{api{1..3},workerx}')

# Count
words = result.replace('echo ', '').split()
print(f"\nTotal words: {len(words)}")

from collections import Counter
counts = Counter(words)
for word, count in sorted(counts.items()):
    marker = " ❌ DUPLICATE!" if count > 1 else ""
    print(f"  {word}: {count}{marker}")
