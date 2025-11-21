#!/usr/bin/env python3
"""Test nested quotes in command substitution"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bash_tool.bash_tool_executor import BashToolExecutor

executor = BashToolExecutor(
    working_dir=Path('/home/user/couch'),
    test_mode=True
)

# Simple nested test
cmd1 = 'echo "Level1: $(echo "Level2")"'
print("="*80)
print(f"TEST 1: {cmd1}")
result1 = executor.execute({'command': cmd1, 'description': 'test1'})
print(f"OUTPUT: {result1}")
print("="*80)

# Double nested
cmd2 = 'echo "Level1: $(echo "Level2: $(echo "Level3")")"'
print("\n" + "="*80)
print(f"TEST 2: {cmd2}")
result2 = executor.execute({'command': cmd2, 'description': 'test2'})
print(f"OUTPUT: {result2}")
print("="*80)

# Compare with real bash
import subprocess
real1 = subprocess.run(['bash', '-c', cmd1], capture_output=True, text=True).stdout.strip()
real2 = subprocess.run(['bash', '-c', cmd2], capture_output=True, text=True).stdout.strip()

print("\n" + "="*80)
print("COMPARISON:")
print("="*80)
print(f"Test 1 - Our: {result1}")
print(f"Test 1 - Bash: {real1}")
print(f"Match: {result1.strip() == real1}")

print(f"\nTest 2 - Our: {result2}")
print(f"Test 2 - Bash: {real2}")
print(f"Match: {result2.strip() == real2}")
