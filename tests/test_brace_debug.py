#!/usr/bin/env python3
"""Debug brace expansion"""

import re

def expand_braces(command: str) -> str:
    """Expand brace patterns"""

    def expand_single_brace(match):
        """Expand a single brace expression"""
        content = match.group(1)
        print(f"  Matched content: '{content}'")

        # Check for range pattern (numeric or alpha)
        range_match = re.match(r'^(\d+)\.\.(\d+)$', content)
        if range_match:
            # Numeric range
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            padding = len(range_match.group(1)) if range_match.group(1).startswith('0') else 0

            if start <= end:
                items = [str(i).zfill(padding) if padding else str(i) for i in range(start, end + 1)]
            else:
                items = [str(i).zfill(padding) if padding else str(i) for i in range(start, end - 1, -1)]

            result = ' '.join(items)
            print(f"  Expanded to: '{result}'")
            return result

        # Alpha range
        alpha_match = re.match(r'^([a-zA-Z])\.\.([a-zA-Z])$', content)
        if alpha_match:
            start_char = alpha_match.group(1)
            end_char = alpha_match.group(2)

            if start_char <= end_char:
                items = [chr(c) for c in range(ord(start_char), ord(end_char) + 1)]
            else:
                items = [chr(c) for c in range(ord(start_char), ord(end_char) - 1, -1)]

            result = ' '.join(items)
            print(f"  Expanded to: '{result}'")
            return result

        # Comma-separated list
        if ',' in content:
            items = [item.strip() for item in content.split(',')]
            result = ' '.join(items)
            print(f"  Expanded to: '{result}'")
            return result

        # No expansion needed
        print(f"  No expansion needed")
        return match.group(0)

    # Expand braces - may need multiple passes for nested
    max_iterations = 10
    for i in range(max_iterations):
        # Pattern: {content} but NOT ${var...}
        pattern = r'(?<!\$)\{([^{}]+)\}'
        print(f"Iteration {i+1}: '{command}'")
        new_command = re.sub(pattern, expand_single_brace, command)

        if new_command == command:
            # No more expansions
            print(f"No more expansions")
            break
        command = new_command

    return command


# Test cases
test_cases = [
    'echo {1..5}',
    'echo {a,b,c}',
    'echo ${var}',  # Should NOT expand
    'echo {1..10}',
]

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"Test: {test}")
    print(f"{'='*60}")
    result = expand_braces(test)
    print(f"Result: {result}\n")
