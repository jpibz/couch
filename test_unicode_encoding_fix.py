#!/usr/bin/env python3
"""
Test UTF-8 encoding fix in ExecutionEngine

PROBLEMA:
- grep output con caratteri Unicode (═, │, etc.)
- subprocess.run() senza encoding='utf-8' usa cp1252 su Windows
- cp1252 non supporta caratteri Unicode → UnicodeDecodeError

SOLUZIONE:
- Aggiunto encoding='utf-8', errors='replace' a tutti subprocess.run()

TESTA:
- Creazione file con caratteri Unicode
- grep con pattern Unicode
- Verifica che NON crashia con UnicodeDecodeError
"""
import sys
import subprocess
import tempfile
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from bash_tool.execution_engine import ExecutionEngine

def test_unicode_encoding():
    """Test che ExecutionEngine gestisce caratteri Unicode"""
    print("\n" + "="*80)
    print("TEST: UTF-8 Encoding in ExecutionEngine")
    print("="*80)

    # Create temp file with Unicode characters (box drawing)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
        f.write("═══ Header Line 1 ═══\n")
        f.write("│ Content line 1 │\n")
        f.write("═══ Header Line 2 ═══\n")
        f.write("│ Content line 2 │\n")
        f.write("═══ Header Line 3 ═══\n")
        temp_file = Path(f.name)

    print(f"\n[SETUP] Created temp file: {temp_file}")
    print(f"[SETUP] Content:")
    with open(temp_file, 'r', encoding='utf-8') as f:
        print(f.read())

    try:
        # Initialize ExecutionEngine
        engine = ExecutionEngine(
            working_dir=Path.cwd(),
            logger=None,
            test_mode=False
        )

        # Test 1: grep with Unicode pattern (native binary)
        if engine.is_available('grep'):
            print("\n[TEST 1] grep with Unicode pattern (native binary)")
            try:
                result = engine.execute_native(
                    'grep',
                    ['-n', '^═══', str(temp_file)]
                )
                print(f"  Exit code: {result.returncode}")
                print(f"  Stdout length: {len(result.stdout)} chars")
                print(f"  Output preview:")
                for line in result.stdout.split('\n')[:5]:
                    print(f"    {line}")
                print("  ✅ PASS: No UnicodeDecodeError!")
            except UnicodeDecodeError as e:
                print(f"  ❌ FAIL: UnicodeDecodeError: {e}")
                raise
        else:
            print("\n[TEST 1] SKIP: grep not available")

        # Test 2: bash with Unicode (if available)
        if engine.bash_available:
            print("\n[TEST 2] bash with Unicode command")
            try:
                result = engine.execute_bash(
                    f'grep -n "^═══" "{temp_file}"'
                )
                print(f"  Exit code: {result.returncode}")
                print(f"  Stdout length: {len(result.stdout)} chars")
                print(f"  Output preview:")
                for line in result.stdout.split('\n')[:5]:
                    print(f"    {line}")
                print("  ✅ PASS: No UnicodeDecodeError!")
            except UnicodeDecodeError as e:
                print(f"  ❌ FAIL: UnicodeDecodeError: {e}")
                raise
        else:
            print("\n[TEST 2] SKIP: bash not available")

        # Test 3: cmd with type (Windows command)
        print("\n[TEST 3] cmd with type (Windows)")
        try:
            result = engine.execute_cmd(f'type "{temp_file}"')
            print(f"  Exit code: {result.returncode}")
            print(f"  Stdout length: {len(result.stdout)} chars")
            # On Windows, 'type' might replace Unicode with '?' but no decode error
            print(f"  Output preview:")
            for line in result.stdout.split('\n')[:5]:
                print(f"    {line}")
            print("  ✅ PASS: No UnicodeDecodeError!")
        except UnicodeDecodeError as e:
            print(f"  ❌ FAIL: UnicodeDecodeError: {e}")
            raise

        print("\n" + "="*80)
        print("ALL TESTS PASSED! ✅")
        print("UTF-8 encoding fix works correctly")
        print("="*80)

    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
            print(f"\n[CLEANUP] Removed temp file: {temp_file}")


if __name__ == '__main__':
    try:
        test_unicode_encoding()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
