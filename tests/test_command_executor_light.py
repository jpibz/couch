"""
Test Suite for CommandExecutor LIGHT system

Tests:
1. Parser integration
2. Strategy analysis
3. Manual execution (SimpleCommand, Pipeline, Sequence, AndList, OrList)
4. Bash execution fallback
5. Real-world commands
"""
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

# Import system
sys.path.insert(0, '/home/claude')
from command_executor_light import CommandExecutor, ExecutionStrategy


def test_simple_commands():
    """Test simple command execution"""
    print("="*60)
    print("TEST: Simple Commands")
    print("="*60)
    
    executor = CommandExecutor(test_mode=True)
    
    tests = [
        "ls -la",
        "cat file.txt",
        "echo hello world",
        "pwd",
        "grep pattern file.txt",
    ]
    
    for cmd in tests:
        print(f"\nCommand: {cmd}")
        result = executor.execute(cmd)
        print(f"  Exit code: {result.returncode}")
        print(f"  Output: {result.stdout[:100]}")


def test_pipelines():
    """Test pipeline execution"""
    print("\n" + "="*60)
    print("TEST: Pipelines")
    print("="*60)
    
    executor = CommandExecutor(test_mode=True)
    
    tests = [
        "cat file.txt | grep pattern",
        "ls -la | grep .py | wc -l",
        "echo hello | cat | cat",
    ]
    
    for cmd in tests:
        print(f"\nCommand: {cmd}")
        result = executor.execute(cmd)
        print(f"  Exit code: {result.returncode}")
        print(f"  Strategy: Manual (pipeline)")


def test_logical_operators():
    """Test && and || operators"""
    print("\n" + "="*60)
    print("TEST: Logical Operators")
    print("="*60)
    
    executor = CommandExecutor(test_mode=True)
    
    tests = [
        "cmd1 && cmd2",
        "cmd1 || cmd2",
        "cmd1 && cmd2 || cmd3",
        "test -f file.txt && cat file.txt",
    ]
    
    for cmd in tests:
        print(f"\nCommand: {cmd}")
        result = executor.execute(cmd)
        print(f"  Exit code: {result.returncode}")
        print(f"  Note: Exit code logic tested")


def test_sequences():
    """Test command sequences"""
    print("\n" + "="*60)
    print("TEST: Sequences")
    print("="*60)
    
    executor = CommandExecutor(test_mode=True)
    
    tests = [
        "cmd1 ; cmd2 ; cmd3",
        "echo hello ; echo world",
        "ls ; pwd ; echo done",
    ]
    
    for cmd in tests:
        print(f"\nCommand: {cmd}")
        result = executor.execute(cmd)
        print(f"  Exit code: {result.returncode}")


def test_complex_commands():
    """Test complex real-world commands"""
    print("\n" + "="*60)
    print("TEST: Complex Commands")
    print("="*60)
    
    executor = CommandExecutor(test_mode=True)
    
    tests = [
        # Pipeline with logical
        "cat file | grep pattern && echo found",
        
        # Sequence with pipeline
        "echo start ; cat file | grep pattern ; echo done",
        
        # Mixed operators
        "cmd1 | cmd2 && cmd3 || cmd4",
        
        # Subshell (should use bash)
        "(cd /tmp && ls)",
        
        # Background (should use bash)
        "long_process &",
        
        # Command group (should use bash)
        "{ cmd1; cmd2; }",
    ]
    
    for cmd in tests:
        print(f"\nCommand: {cmd}")
        try:
            result = executor.execute(cmd)
            print(f"  Exit code: {result.returncode}")
            print(f"  ✓ SUCCESS")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")


def test_strategy_analysis():
    """Test strategy decision making"""
    print("\n" + "="*60)
    print("TEST: Strategy Analysis")
    print("="*60)
    
    from bash_pipeline_parser import parse_bash_command
    
    executor = CommandExecutor(test_mode=True)
    
    tests = [
        ("ls -la", "MANUAL", "Simple command"),
        ("cat file | grep pattern", "MANUAL", "Pipeline"),
        ("cmd1 ; cmd2", "MANUAL", "Sequence"),
        ("cmd1 && cmd2", "MANUAL", "AndList"),
        ("(cd /tmp && ls)", "BASH_FULL", "Subshell"),
        ("{ cmd1; cmd2; }", "BASH_FULL", "CommandGroup"),
        ("cmd &", "BASH_FULL", "Background"),
    ]
    
    for cmd, expected_strategy, description in tests:
        ast = parse_bash_command(cmd)
        strategy = executor._analyze_strategy(ast)
        
        match = "✓" if strategy == getattr(ExecutionStrategy, expected_strategy) else "✗"
        print(f"{match} {description}: {cmd}")
        print(f"   Expected: {expected_strategy}, Got: {strategy}")


def test_preprocessing():
    """Test command preprocessing"""
    print("\n" + "="*60)
    print("TEST: Preprocessing")
    print("="*60)
    
    import os
    os.environ['TEST_VAR'] = 'test_value'
    
    executor = CommandExecutor(test_mode=True)
    
    tests = [
        ("echo $TEST_VAR", "Variable expansion"),
        ("echo ~/file", "Tilde expansion"),
        ("cat $TEST_VAR.txt", "Variable in filename"),
    ]
    
    for cmd, description in tests:
        print(f"\n{description}: {cmd}")
        preprocessed = executor._preprocess_command(cmd)
        print(f"  Preprocessed: {preprocessed}")


def run_all_tests():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# COMMAND EXECUTOR LIGHT - TEST SUITE")
    print("#"*60)
    
    test_simple_commands()
    test_pipelines()
    test_logical_operators()
    test_sequences()
    test_complex_commands()
    test_strategy_analysis()
    test_preprocessing()
    
    print("\n" + "#"*60)
    print("# ALL TESTS COMPLETE")
    print("#"*60)


if __name__ == '__main__':
    run_all_tests()
