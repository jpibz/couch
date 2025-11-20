"""
TEST SUITE ESTREMA - Preprocessing Pipeline Flow

OBIETTIVO: Vedere ESATTAMENTE cosa arriva a valle del sistema!

Test Categories:
1. Variable Expansion (10 tests)
2. Brace Expansion (6 tests)
3. Command Substitution (4 tests)
4. Mixed Acrobatic (6 tests)
5. Aliases (2 tests)
6. Test Commands (2 tests)

Total: 30 EXTREME tests

Each test shows:
- Original command
- After pipeline preprocessing
- After comando preprocessing (cat 1)
- After comando preprocessing (cat 2 if emulated)
- What arrives at ExecutionEngine (BASH/POWERSHELL/NATIVE)
"""
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(message)s'
)

# Import system
sys.path.insert(0, '/home/claude')
from command_executor_light import CommandExecutor


class TestRunner:
    """Test runner with detailed output"""
    
    def __init__(self):
        self.executor = CommandExecutor(test_mode=True)
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name, command, expected_pattern=None):
        """
        Run a single test
        
        Args:
            name: Test name
            command: Command to test
            expected_pattern: Optional pattern to check in output
        """
        print(f"\n{'='*70}")
        print(f"TEST: {name}")
        print(f"{'='*70}")
        print(f"INPUT: {command}")
        
        try:
            result = self.executor.execute(command)
            
            print(f"\nOUTPUT:")
            print(result.stdout)
            
            if expected_pattern:
                if expected_pattern in result.stdout:
                    print(f"\n✅ PASS - Found expected pattern: {expected_pattern}")
                    self.passed += 1
                else:
                    print(f"\n❌ FAIL - Expected pattern not found: {expected_pattern}")
                    self.failed += 1
            else:
                print(f"\n✅ PASS - Executed successfully")
                self.passed += 1
        
        except Exception as e:
            print(f"\n❌ FAIL - Exception: {e}")
            self.failed += 1
        
        self.tests.append(name)
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{'#'*70}")
        print(f"# TEST SUMMARY")
        print(f"{'#'*70}")
        print(f"Total tests:  {total}")
        print(f"Passed:       {self.passed}")
        print(f"Failed:       {self.failed}")
        print(f"Pass rate:    {pass_rate:.1f}%")
        print(f"\nStatus: {'🔥🔥🔥 PRODUCTION READY' if pass_rate == 100 else '⚠️ NEEDS WORK'}")


def test_variable_expansion():
    """Test all variable expansion forms"""
    print("\n" + "="*70)
    print("CATEGORY 1: VARIABLE EXPANSION (10 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    # Setup test env vars
    os.environ['TEST_VAR'] = 'hello'
    os.environ['NUM'] = '42'
    os.environ['PATH_VAR'] = '/usr/bin:/bin'
    
    runner.test(
        "1.1 Simple $VAR",
        "echo $TEST_VAR",
        "hello"
    )
    
    runner.test(
        "1.2 Simple ${VAR}",
        "echo ${TEST_VAR}",
        "hello"
    )
    
    runner.test(
        "1.3 Default ${VAR:-default}",
        "echo ${NONEXIST:-default_value}",
        "default_value"
    )
    
    runner.test(
        "1.4 Length ${#VAR}",
        "echo ${#TEST_VAR}",
        "5"
    )
    
    runner.test(
        "1.5 Remove prefix ${VAR#pattern}",
        "echo ${PATH_VAR#/usr}",
        "/bin:/bin"
    )
    
    runner.test(
        "1.6 Substitution ${VAR/old/new}",
        "echo ${TEST_VAR/hello/goodbye}",
        "goodbye"
    )
    
    runner.test(
        "1.7 Uppercase ${VAR^^}",
        "echo ${TEST_VAR^^}",
        "HELLO"
    )
    
    runner.test(
        "1.8 Lowercase ${VAR,,}",
        "echo ${TEST_VAR,,}",
        "hello"
    )
    
    runner.test(
        "1.9 Arithmetic $((expr))",
        "echo $((5 + 3))",
        "8"
    )
    
    runner.test(
        "1.10 Tilde expansion ~/",
        "ls ~/test",
        None
    )
    
    return runner


def test_brace_expansion():
    """Test brace expansion"""
    print("\n" + "="*70)
    print("CATEGORY 2: BRACE EXPANSION (6 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    runner.test(
        "2.1 Numeric range {1..5}",
        "echo file{1..3}.txt",
        "file1.txt file2.txt file3.txt"
    )
    
    runner.test(
        "2.2 Zero-padded {01..10}",
        "echo num{01..03}",
        "num01 num02 num03"
    )
    
    runner.test(
        "2.3 Alpha range {a..c}",
        "echo {a..c}",
        "a b c"
    )
    
    runner.test(
        "2.4 List {a,b,c}",
        "echo {hello,world}",
        "hello world"
    )
    
    runner.test(
        "2.5 Nested {a,b{1,2}}",
        "echo {a,b{1,2}}",
        "a b1 b2"
    )
    
    runner.test(
        "2.6 Multiple {a,b}{1,2}",
        "echo {a,b}{1,2}",
        "a1 a2 b1 b2"
    )
    
    return runner


def test_command_substitution():
    """Test command substitution"""
    print("\n" + "="*70)
    print("CATEGORY 3: COMMAND SUBSTITUTION (4 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    runner.test(
        "3.1 Simple $(cmd)",
        "echo result=$(echo test)",
        "result="
    )
    
    runner.test(
        "3.2 Nested $($(...))",
        "echo $(echo $(echo nested))",
        None
    )
    
    runner.test(
        "3.3 Multiple substitutions",
        "echo $(echo a) $(echo b)",
        None
    )
    
    runner.test(
        "3.4 Command subst with pipe",
        "echo $(cat file.txt | grep pattern)",
        None
    )
    
    return runner


def test_mixed_acrobatic():
    """Test extreme mixed cases"""
    print("\n" + "="*70)
    print("CATEGORY 4: MIXED ACROBATIC (6 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    os.environ['VAR'] = 'test'
    
    runner.test(
        "4.1 Variables + Braces",
        "echo $VAR{1..3}.txt",
        "test1.txt test2.txt test3.txt"
    )
    
    runner.test(
        "4.2 Command subst + Variable",
        "echo $(echo $TEST_VAR)",
        None
    )
    
    runner.test(
        "4.3 Brace + Command subst",
        "echo file{1..2}_$(echo test).txt",
        None
    )
    
    runner.test(
        "4.4 ALL COMBINED (EXTREME!)",
        "echo ~/dir/${VAR}{1..2}_$(echo test).txt",
        None
    )
    
    runner.test(
        "4.5 Tilde + Variable + Brace",
        "ls ~/$TEST_VAR{1..2}",
        None
    )
    
    runner.test(
        "4.6 Arithmetic + Variable + Brace",
        "echo $((NUM + 5))_{1..2}",
        "47_1 47_2"
    )
    
    return runner


def test_aliases():
    """Test alias expansion"""
    print("\n" + "="*70)
    print("CATEGORY 5: ALIASES (2 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    runner.test(
        "5.1 ll → ls -la",
        "ll",
        "ls -la"
    )
    
    runner.test(
        "5.2 la → ls -A",
        "la",
        "ls -A"
    )
    
    return runner


def test_test_commands():
    """Test command translation"""
    print("\n" + "="*70)
    print("CATEGORY 6: TEST COMMANDS (2 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    runner.test(
        "6.1 [ -f file ] → test -f file",
        "[ -f file.txt ]",
        "test -f file.txt"
    )
    
    runner.test(
        "6.2 [[ expr ]] → test expr",
        "[[ -d /tmp ]]",
        "test -d /tmp"
    )
    
    return runner


def test_extreme_acrobatic_madness():
    """Test EXTREME cases that Claude might actually use in production"""
    print("\n" + "="*70)
    print("CATEGORY 7: EXTREME ACROBATIC MADNESS 🎪 (8 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    # Setup complex env
    os.environ['PROJECT'] = 'myapp'
    os.environ['ENV'] = 'prod'
    
    runner.test(
        "7.1 Multi-level nested with prefix/suffix",
        "echo file_{a,b{1,2{x,y}}}.txt",
        None  # Just test it doesn't crash
    )
    
    runner.test(
        "7.2 Cartesian product x3",
        "echo {a,b}{1,2}{x,y}",
        None
    )
    
    runner.test(
        "7.3 Variables + Nested braces + Arithmetic",
        "echo $PROJECT/{api,web{$((NUM-40)),$(( NUM - 41 ))}}/config.txt",
        None
    )
    
    runner.test(
        "7.4 Tilde + Variables + Multiple braces",
        "ls ~/$PROJECT/{src,test}/{backend{1,2},frontend}.js",
        None
    )
    
    runner.test(
        "7.5 Range + List + Nested",
        "echo {1..3}_{a,b{x,y}}.log",
        None
    )
    
    runner.test(
        "7.6 Zero-padded + Nested + Suffix",
        "touch file_{01..03}_{a,b{1,2}}.tmp",
        None
    )
    
    runner.test(
        "7.7 Alpha range + Cartesian + Variable",
        "echo $ENV/{a..c}{1..2}_$PROJECT.conf",
        None
    )
    
    runner.test(
        "7.8 THE ULTIMATE: Everything combined",
        "echo ~/$PROJECT/{api{1..2},worker}/{$ENV,test}/{config,secrets}{.json,.yaml}",
        None
    )
    
    return runner


def test_claude_sotto_cocaina():
    """Test ULTRA EXTREME cases - Claude's craziest possible pipelines"""
    print("\n" + "="*70)
    print("CATEGORY 8: CLAUDE SOTTO COCAINA 🤪💊 (10 tests)")
    print("="*70)
    
    runner = TestRunner()
    
    # Setup ultra complex env
    os.environ['APP'] = 'system'
    os.environ['STAGE'] = 'staging'
    os.environ['REGION'] = 'eu-west'
    
    runner.test(
        "8.1 Triple nested braces",
        "echo {a,b{1,2{x,y,z}}}",
        None
    )
    
    runner.test(
        "8.2 Quad nested with ranges",
        "echo {a,b{1..2{x,y{i,ii}}}}",
        None
    )
    
    runner.test(
        "8.3 Multiple cartesian x4",
        "echo {a,b}{1,2}{x,y}{i,ii}",
        None
    )
    
    runner.test(
        "8.4 Ranges + nested + variables + arithmetic",
        "echo $APP/{api{1..3},worker{$((NUM-40))..$(( NUM -38 ))}}/{$STAGE,prod}.conf",
        None
    )
    
    runner.test(
        "8.5 Complex path with everything",
        "ls ~/$APP/{src{1..2},test}/{backend{a,b{1,2}},frontend{x,y}}/config{.dev,.prod}.{json,yaml}",
        None
    )
    
    runner.test(
        "8.6 Zero-padded + nested x3",
        "touch file_{01..03}_{a,b{1,2{x,y}}}.tmp",
        None
    )
    
    runner.test(
        "8.7 Alpha ranges + nested + cartesian",
        "echo {a..c}_{1..3}_{x,y{i,ii}}.log",
        None
    )
    
    runner.test(
        "8.8 Variables everywhere",
        "echo $APP/$REGION/{$STAGE,test}/{api{1..2},worker}/{config,secrets{_$APP,}}.json",
        None
    )
    
    runner.test(
        "8.9 THE MEGA EXTREME",
        "echo ~/$APP/{api{1..3{a,b}},worker{x,y}}/{$STAGE,dev}/{db{1..2},cache}/{config{.json,.yaml},secrets{_prod,_dev,}}",
        None
    )
    
    runner.test(
        "8.10 THE ULTIMATE MADNESS",
        "find ~/$APP/{src{1..2{a,b{i,ii}}},test}/{backend{api{1..2},worker},frontend{react,vue{2,3}}}/{config,secrets}{.dev{1..2},.prod}.{json,yaml,xml}",
        None
    )
    
    return runner


def run_all_extreme_tests():
    """Run ALL extreme tests"""
    print("\n" + "#"*70)
    print("# 🔥 PREPROCESSING EXTREME - FULL PIPELINE FLOW TEST 🔥")
    print("#"*70)
    
    # Run all categories
    runners = []
    
    runners.append(test_variable_expansion())
    runners.append(test_brace_expansion())
    runners.append(test_command_substitution())
    runners.append(test_mixed_acrobatic())
    runners.append(test_aliases())
    runners.append(test_test_commands())
    runners.append(test_extreme_acrobatic_madness())
    runners.append(test_claude_sotto_cocaina())  # NEW!
    
    # Combined summary
    total_passed = sum(r.passed for r in runners)
    total_failed = sum(r.failed for r in runners)
    total_tests = total_passed + total_failed
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "#"*70)
    print("# 🎯 FINAL SUMMARY - ALL CATEGORIES")
    print("#"*70)
    print(f"Total tests:  {total_tests}")
    print(f"Passed:       {total_passed}")
    print(f"Failed:       {total_failed}")
    print(f"Pass rate:    {pass_rate:.1f}%")
    print(f"\nStatus: {'🔥🔥🔥 PRODUCTION READY - Ship it!' if pass_rate == 100 else '⚠️ NEEDS WORK - Iterate!'}")
    
    if pass_rate == 100:
        print("\n" + "="*70)
        print("🚀 ALL TESTS PASSED! SYSTEM READY FOR INTEGRATION! 🚀")
        print("="*70)
    else:
        print("\n" + "="*70)
        print(f"⚠️ {total_failed} tests failed - debugging needed!")
        print("="*70)


if __name__ == '__main__':
    run_all_extreme_tests()
