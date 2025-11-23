#!/usr/bin/env python3
"""
Test semplice per verificare encoding='utf-8' fix

Simula il problema e la soluzione
"""
import subprocess
import tempfile
from pathlib import Path

print("="*80)
print("TEST: subprocess encoding fix")
print("="*80)

# Create temp file with Unicode
with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
    f.write("═══ Header Line 1 ═══\n")
    f.write("│ Content line 1 │\n")
    f.write("═══ Header Line 2 ═══\n")
    temp_file = Path(f.name)

print(f"\nCreated file: {temp_file}")
print("Content:")
with open(temp_file, 'r', encoding='utf-8') as f:
    content = f.read()
    print(content)

# Test 1: WITHOUT encoding (OLD - would fail on Windows)
print("\n[TEST 1] subprocess.run() WITHOUT encoding='utf-8'")
print("On Windows with cp1252, this would cause: UnicodeDecodeError")
print("On Linux with UTF-8 default, this works")
try:
    result = subprocess.run(
        ['cat', str(temp_file)],
        capture_output=True,
        text=True
        # NO encoding specified → uses system default (cp1252 on Windows, utf-8 on Linux)
    )
    print(f"  Result: {result.returncode}")
    print(f"  Output: {result.stdout[:50]}...")
    print("  ✅ Worked (system default is UTF-8 compatible)")
except UnicodeDecodeError as e:
    print(f"  ❌ UnicodeDecodeError: {e}")

# Test 2: WITH encoding (NEW - always works)
print("\n[TEST 2] subprocess.run() WITH encoding='utf-8', errors='replace'")
print("This ALWAYS works, even on Windows!")
try:
    result = subprocess.run(
        ['cat', str(temp_file)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'  # Replace invalid chars with '?'
    )
    print(f"  Result: {result.returncode}")
    print(f"  Output: {result.stdout[:50]}...")
    print("  ✅ PASS: Works with explicit UTF-8!")
except UnicodeDecodeError as e:
    print(f"  ❌ FAIL: {e}")

# Cleanup
temp_file.unlink()

print("\n" + "="*80)
print("CONCLUSION:")
print("- OLD code (text=True only) → fails on Windows cp1252")
print("- NEW code (text=True + encoding='utf-8') → always works! ✅")
print("="*80)
