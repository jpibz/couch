#!/usr/bin/env python3
"""
Test per simmetria BIDIREZIONALE traduzione path in PathTranslator

PROBLEMA:
- Unix → Windows: /tmp/file.txt → workspace/claude/tmp/file.txt ✓
- Windows → Unix: workspace/claude/tmp/file.txt → /home/claude/tmp/file.txt ❌

DOVREBBE ESSERE:
- Windows → Unix: workspace/claude/tmp/file.txt → /tmp/file.txt ✓

TESTA:
- Simmetria bidirezionale: Unix → Windows → Unix deve tornare uguale
- Path relativi tradotti correttamente in ENTRAMBE le direzioni
"""
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from bash_tool.path_translator import PathTranslator

def test_bidirectional_symmetry():
    """Test simmetria bidirezionale traduzione path"""
    print("\n" + "="*80)
    print("TEST: PathTranslator - Bidirectional Symmetry")
    print("="*80)

    translator = PathTranslator()

    # Test cases: (original_unix_path, description)
    test_cases = [
        ("/tmp/file.txt", "Relative path: /tmp/file.txt"),
        ("/var/log/app.log", "Relative path: /var/log/app.log"),
        ("/etc/config.ini", "Relative path: /etc/config.ini"),
        ("/home/claude/myfile.py", "Known path: /home/claude/myfile.py"),
        ("/mnt/user-data/uploads/data.csv", "Known path: /mnt/user-data/uploads/data.csv"),
    ]

    print("\n[BIDIRECTIONAL SYMMETRY TEST]")
    print("Unix → Windows → Unix (should return to original)")
    print("-"*80)

    for original_unix, description in test_cases:
        print(f"\n{description}")
        print(f"  Original (Unix):  {original_unix}")

        # Step 1: Unix → Windows
        text_unix = f"cat {original_unix}"
        text_windows = translator.translate_paths_in_string(text_unix, 'to_windows')
        print(f"  After Unix→Win:   {text_windows}")

        # Step 2: Windows → Unix (REVERSE)
        text_unix_reversed = translator.translate_paths_in_string(text_windows, 'to_unix')
        print(f"  After Win→Unix:   {text_unix_reversed}")

        # Extract path from "cat <path>"
        reversed_path = text_unix_reversed.replace("cat ", "").strip()

        # Verify symmetry
        if reversed_path == original_unix:
            print(f"  ✅ PASS: Symmetry maintained!")
        else:
            print(f"  ❌ FAIL: Expected '{original_unix}', got '{reversed_path}'")
            raise AssertionError(f"Symmetry broken for {original_unix}")

    # SPECIFIC TEST: /tmp path
    print("\n" + "-"*80)
    print("[SPECIFIC TEST] /tmp path bidirectional")
    print("-"*80)

    original = "cat /tmp/myfile.txt"
    print(f"Original:       {original}")

    # Unix → Windows
    windows = translator.translate_paths_in_string(original, 'to_windows')
    print(f"Unix→Windows:   {windows}")

    # Windows → Unix (should return to original)
    unix_reversed = translator.translate_paths_in_string(windows, 'to_unix')
    print(f"Windows→Unix:   {unix_reversed}")

    if unix_reversed == original:
        print("✅ PASS: Perfect symmetry!")
    else:
        print(f"❌ FAIL: Expected '{original}', got '{unix_reversed}'")
        raise AssertionError("Bidirectional symmetry broken!")

    # TEST: Windows → Unix translation directly
    print("\n" + "-"*80)
    print("[DIRECT TEST] Windows → Unix translation")
    print("-"*80)

    workspace = translator.workspace_root
    windows_path = f"{workspace}/claude/tmp/file.txt"
    print(f"Windows path: {windows_path}")

    unix_result = translator.translate_paths_in_string(windows_path, 'to_unix')
    print(f"Unix result:  {unix_result}")

    if "/tmp/file.txt" in unix_result:
        print("✅ PASS: /tmp correctly recovered from Windows path!")
    else:
        print(f"❌ FAIL: Expected '/tmp/file.txt' but got: {unix_result}")
        raise AssertionError("Windows→Unix translation failed")

    print("\n" + "="*80)
    print("ALL TESTS PASSED! ✅")
    print("Bidirectional path translation maintains perfect symmetry")
    print("="*80)


if __name__ == '__main__':
    try:
        test_bidirectional_symmetry()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
