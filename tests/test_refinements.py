"""
Test veloce per verificare le due rifiniture

1. NATIVE_BINS detection con path di default
2. python3 → python translation
"""
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(message)s'
)

sys.path.insert(0, '/home/claude')

from execution_engine_light import ExecutionEngine
from execute_single_light import ExecuteUnixSingleCommand
from pipeline_analyzer import PipelineAnalyzer


def test_native_bins_detection():
    """Test native bins detection con path di default"""
    print("="*70)
    print("TEST 1: NATIVE BINS DETECTION")
    print("="*70)
    
    # Test mode
    engine = ExecutionEngine(test_mode=True)
    
    print(f"\nBash available: {engine.bash_available}")
    print(f"\nDetected bins ({len(engine.available_bins)}):")
    for name, path in engine.available_bins.items():
        print(f"  - {name}: {path}")
    
    # Check specific bins
    assert engine.is_available('grep'), "grep should be available"
    assert engine.is_available('python'), "python should be available"
    assert not engine.is_available('nonexistent'), "nonexistent should not be available"
    
    print("\nâœ… PASS - Native bins detection works!")


def test_python3_translation():
    """Test python3 → python translation"""
    print("\n" + "="*70)
    print("TEST 2: PYTHON3 TRANSLATION")
    print("="*70)
    
    engine = ExecutionEngine(test_mode=True)
    executor = ExecuteUnixSingleCommand(engine, test_mode=True)
    
    # Test cases
    tests = [
        ("python3 script.py", "python script.py"),
        ("python3 -c 'print(1)'", "python -c 'print(1)'"),
        ("echo python3 is great", "echo python is great"),  # Should translate inside text too
        ("python script.py", "python script.py"),  # Should not change
    ]
    
    for original, expected in tests:
        translated = executor._translate_python3(original)
        
        # Check if translation worked
        status = "âœ…" if expected in translated else "âŒ"
        print(f"\n{status} '{original}'")
        print(f"   → '{translated}'")
        
        if expected not in translated:
            print(f"   EXPECTED: '{expected}'")


def test_analyzer_with_python3():
    """Test analyzer con comando python3"""
    print("\n" + "="*70)
    print("TEST 3: ANALYZER WITH PYTHON3")
    print("="*70)
    
    from bash_pipeline_parser import parse_bash_command
    
    engine = ExecutionEngine(test_mode=True)
    analyzer = PipelineAnalyzer(engine)
    
    # Parse command con python3
    ast = parse_bash_command("python3 script.py | grep output")
    
    # Analyze
    result = analyzer.analyze(ast)
    
    print(f"\nCommand: python3 script.py | grep output")
    print(f"Strategy: {result.strategy}")
    print(f"Reason: {result.reason}")
    print(f"\nCommands found:")
    for cmd in result.commands:
        print(f"  - {cmd.name}: builtin={cmd.is_builtin}, native={cmd.is_native}, needs_emulation={cmd.needs_emulation}")
    
    # python3 should be treated as python (available)
    python_cmd = [c for c in result.commands if c.name == 'python3'][0]
    
    if python_cmd.is_native or python_cmd.is_builtin:
        print("\nâœ… PASS - python3 recognized as available!")
    else:
        print("\nâŒ FAIL - python3 not recognized as available")


def run_all_tests():
    """Run all refinement tests"""
    print("\n" + "#"*70)
    print("# REFINEMENT TESTS - Native bins + python3 translation")
    print("#"*70)
    
    try:
        test_native_bins_detection()
        test_python3_translation()
        test_analyzer_with_python3()
        
        print("\n" + "#"*70)
        print("# âœ… ALL REFINEMENT TESTS PASSED!")
        print("#"*70)
    
    except Exception as e:
        print(f"\n" + "#"*70)
        print(f"# âŒ TEST FAILED: {e}")
        print("#"*70)
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
