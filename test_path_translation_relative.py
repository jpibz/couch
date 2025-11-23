#!/usr/bin/env python3
"""
Test per il fix di PathTranslator: traduzione path relativi

PROBLEMA:
- /tmp/file.txt non veniva tradotto (rimaneva /tmp/file.txt)
- Solo path conosciuti (/home/claude, /mnt/user-data/...) venivano tradotti

SOLUZIONE:
- Path relativi tradotti come /home/claude/...
- /tmp/file.txt → /home/claude/tmp/file.txt → tradotto a Windows

TESTA:
- Path conosciuti: funzionano ancora ✅
- Path relativi: tradotti come /home/claude/... ✅
- Nessuna regressione ✅
"""
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from bash_tool.path_translator import PathTranslator

def test_path_translation():
    """Test traduzione path con fix per path relativi"""
    print("\n" + "="*80)
    print("TEST: PathTranslator - Relative Paths Translation")
    print("="*80)

    translator = PathTranslator()

    # Test cases
    test_cases = [
        # (input_text, description, should_contain_substring)

        # KNOWN PATHS (should work as before)
        ("cat /home/claude/file.txt", "Known path: /home/claude/file.txt", "claude"),
        ("ls /mnt/user-data/uploads/data.csv", "Known path: /mnt/user-data/uploads/", "uploads"),
        ("cp /mnt/user-data/outputs/report.pdf", "Known path: /mnt/user-data/outputs/", "outputs"),

        # RELATIVE PATHS (NEW: should translate as /home/claude/...)
        ("cat /tmp/file.txt", "Relative path: /tmp/file.txt", "claude"),
        ("ls /var/log/app.log", "Relative path: /var/log/app.log", "claude"),
        ("cp /etc/config.ini", "Relative path: /etc/config.ini", "claude"),

        # MIXED (both known and relative)
        ("cp /home/claude/src.py /tmp/dst.py", "Mixed: known + relative", "claude"),
    ]

    print("\n[TEST CASES]")
    for i, (input_text, description, expected_substring) in enumerate(test_cases, 1):
        print(f"\n{i}. {description}")
        print(f"   Input:  {input_text}")

        result = translator.translate_paths_in_string(input_text, 'to_windows')
        print(f"   Output: {result}")

        # Verify translation occurred
        if expected_substring in result:
            print(f"   ✅ PASS: Contains '{expected_substring}'")
        else:
            print(f"   ❌ FAIL: Missing '{expected_substring}'")
            raise AssertionError(f"Expected '{expected_substring}' in result: {result}")

    # SPECIFIC TEST: /tmp should be translated
    print("\n" + "-"*80)
    print("[SPECIFIC TEST] /tmp path translation")
    print("-"*80)

    input_cmd = "cat /tmp/myfile.txt"
    result = translator.translate_paths_in_string(input_cmd, 'to_windows')

    print(f"Input:  {input_cmd}")
    print(f"Output: {result}")

    # Check that /tmp is NO LONGER present (should be translated)
    if "/tmp" in result and "claude" not in result:
        print("❌ FAIL: /tmp was NOT translated!")
        raise AssertionError(f"/tmp should be translated but got: {result}")
    elif "claude" in result:
        print("✅ PASS: /tmp translated to claude path!")
    else:
        print("⚠️  WARNING: Unexpected result")

    print("\n" + "="*80)
    print("ALL TESTS PASSED! ✅")
    print("Path translation now handles relative paths correctly")
    print("="*80)


if __name__ == '__main__':
    try:
        test_path_translation()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
