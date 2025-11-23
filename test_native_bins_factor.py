#!/usr/bin/env python3
"""
Test per il fattore decisionale NATIVE BINS in PipelineAnalyzer

SCENARIO:
- Pipeline con bins nativi (grep.exe, awk.exe, etc.)
- Dovrebbe preferire MANUAL execution invece di BASH_FULL
- Replica logica di ExecuteUnixSingleCommand: Native > Bash
"""
import sys
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from bash_tool.bash_pipeline_parser import parse_bash_command, Pipeline, SimpleCommand
from bash_tool.execution_engine import ExecutionEngine
from bash_tool.pipeline_analyzer import PipelineAnalyzer, CommandInfo

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TEST')


def test_native_bins_preference():
    """
    Test che bins nativi causano preferenza per MANUAL execution
    """
    print("\n" + "="*80)
    print("TEST: Native Bins Preference in Pipeline")
    print("="*80)

    # Mock engine with native bins available
    class MockEngine:
        def __init__(self, native_bins):
            self.bash_available = True
            self.native_bins = native_bins

        def is_available(self, cmd_name):
            return cmd_name in self.native_bins

    # Test 1: Pipeline with NATIVE bin (grep.exe)
    print("\n[TEST 1] Pipeline with NATIVE bin: cat file | grep pattern")
    engine = MockEngine(native_bins={'grep', 'cat'})
    analyzer = PipelineAnalyzer(engine=engine, logger=logger)

    # Create simple AST
    ast = parse_bash_command("cat file | grep pattern")

    # Analyze
    result = analyzer.analyze(ast)

    print(f"  Commands: {[c.name for c in result.commands]}")
    print(f"  Native bins: {[c.name for c in result.commands if c.is_native]}")
    print(f"  Strategy: {result.strategy}")
    print(f"  Reason: {result.reason}")

    # EXPECTED: manual (prefer native execution)
    assert result.strategy == 'manual', f"Expected 'manual' but got '{result.strategy}'"
    assert 'native' in result.reason.lower(), f"Expected 'native' in reason but got: {result.reason}"
    print("  ✅ PASS: Prefers MANUAL for native bins")

    # Test 2: Pipeline with ONLY builtins (no native)
    print("\n[TEST 2] Pipeline with ONLY builtins: echo hello | cd /tmp")
    engine2 = MockEngine(native_bins={})  # No native bins
    analyzer2 = PipelineAnalyzer(engine=engine2, logger=logger)

    ast2 = parse_bash_command("echo hello | cd /tmp")
    result2 = analyzer2.analyze(ast2)

    print(f"  Commands: {[c.name for c in result2.commands]}")
    print(f"  Native bins: {[c.name for c in result2.commands if c.is_native]}")
    print(f"  Strategy: {result2.strategy}")
    print(f"  Reason: {result2.reason}")

    # EXPECTED: bash_full (passthrough for builtins)
    assert result2.strategy == 'bash_full', f"Expected 'bash_full' but got '{result2.strategy}'"
    assert 'builtin' in result2.reason.lower(), f"Expected 'builtin' in reason but got: {result2.reason}"
    print("  ✅ PASS: Uses BASH_FULL for builtins only")

    # Test 3: Complex pipeline with mix
    print("\n[TEST 3] Complex pipeline: find . | grep .py | wc -l")
    engine3 = MockEngine(native_bins={'grep'})  # Only grep is native
    analyzer3 = PipelineAnalyzer(engine=engine3, logger=logger)

    ast3 = parse_bash_command("find . | grep .py | wc -l")
    result3 = analyzer3.analyze(ast3)

    print(f"  Commands: {[c.name for c in result3.commands]}")
    print(f"  Native bins: {[c.name for c in result3.commands if c.is_native]}")
    print(f"  Builtins: {[c.name for c in result3.commands if c.is_builtin]}")
    print(f"  Strategy: {result3.strategy}")
    print(f"  Reason: {result3.reason}")

    # EXPECTED: manual (has native bin)
    assert result3.strategy == 'manual', f"Expected 'manual' but got '{result3.strategy}'"
    print("  ✅ PASS: Uses MANUAL when has native bins")

    print("\n" + "="*80)
    print("ALL TESTS PASSED! ✅")
    print("="*80)


if __name__ == '__main__':
    try:
        test_native_bins_preference()
    except Exception as e:
        logger.error(f"TEST FAILED: {e}", exc_info=True)
        sys.exit(1)
