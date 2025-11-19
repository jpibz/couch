"""
Pipeline Strategy - MACRO level pipeline analysis

ARCHITECTURE:
This is the MACRO LEVEL strategic analyzer for PIPELINES and COMMAND CHAINS.
Complementary to ExecuteUnixSingleCommand (MICRO level for single commands).

Position in hierarchy:
    CommandExecutor
       ↓
    ├── PipelineStrategy (MACRO: pipelines, chains, complex patterns) ← THIS CLASS
    │      ↓
    │   Creates: PipelineAnalysis + ExecutionStrategy
    │
    └── ExecuteUnixSingleCommand (MICRO: single atomic commands)

RESPONSIBILITIES:
1. Analyze entire pipeline/chain structure (pattern recognition)
2. Detect structural elements (pipes, chains, redirections, process substitution)
3. Pattern matching against known pipeline scenarios (140+ patterns)
4. Decide overall execution strategy (BASH_REQUIRED, BASH_PREFERRED, POWERSHELL, etc.)
5. Provide fallback strategies when primary strategy fails
6. Determine if pipeline can be split (future optimization)

NOT RESPONSIBLE FOR:
- Executing commands (done by ExecutionEngine)
- Translating syntax (done by CommandEmulator)
- Managing subprocess (done by ExecutionEngine)
- Path translation (done by PathTranslator)
- Single command execution (done by ExecuteUnixSingleCommand)

STRATEGY TYPES:
1. BASH_REQUIRED: Command MUST use bash.exe (no alternative)
   - Process substitution: <(...) or >(...)
   - Complex pipelines: find | xargs, awk with BEGIN/END, sed multi-expression
   - Stderr redirection: 2>, 2>&1, |&
   - Command chains: &&, ||, ; (for correct semantics)

2. BASH_PREFERRED: bash.exe is better but PowerShell can work
   - Multi-stage text processing: sort | uniq, grep | sort
   - head/tail in pipelines
   - Commands with subtle edge cases

3. POWERSHELL: PowerShell emulation is sufficient
   - Simple pipelines: echo | base64, cat | grep (simple)
   - Well-emulated commands

4. SINGLE: Not a pipeline, delegate to ExecuteUnixSingleCommand
   - No pipes, no chains, single atomic command

5. FAIL: Cannot execute (process substitution without bash.exe)

PATTERN MATCHING:
140+ regex patterns organized in priority categories:
- BASH_REQUIRED patterns (55+ patterns): find|grep, xargs, awk|*, sed|*, complex grep
- BASH_PREFERRED patterns (35+ patterns): sort|uniq, head|tail, grep|sort
- POWERSHELL_OK patterns (10+ patterns): echo|base64, cat|base64, ls|wc

Pattern format: regex → strategy_type
Example: r'find.*\|.*grep' → 'bash_exe_required'

ANALYSIS FLOW:
    analyze_pipeline(command) →
        1. Detect structural elements (pipes, chains, redirections)
        2. Extract command names from pipeline parts
        3. Pattern matching (140+ patterns)
        4. Determine complexity level (HIGH/MEDIUM/LOW)
        5. Return PipelineAnalysis

    decide_execution_strategy(analysis, command) →
        1. Check CRITICAL patterns (process subst, stderr redir, chains)
        2. Check matched pattern from analysis
        3. Determine if bash.exe available
        4. Return ExecutionStrategy with fallbacks

DESIGN PATTERN:
- Strategy Pattern: Different execution strategies based on pipeline characteristics
- Pattern Matching: Regex-based pattern recognition
- Factory Pattern: Creates ExecutionStrategy objects based on analysis
- Fallback Chain: Primary strategy with optional fallback strategy

DATA FLOW:
    analyze_pipeline("find . -name '*.py' | xargs grep TODO") →
        PipelineAnalysis(
            has_pipeline=True,
            command_count=2,
            command_names=['find', 'xargs'],
            matched_pattern=r'find.*\|.*xargs',
            complexity_level='HIGH'
        )
        ↓
    decide_execution_strategy(analysis, command) →
        ExecutionStrategy(
            strategy_type='BASH_REQUIRED',
            reason='Pipeline pattern requires bash.exe: find.*\|.*xargs'
        )

USAGE PATTERN:
    strategy = PipelineStrategy(
        git_bash_available=True,
        native_bins={'grep': 'C:\\Tools\\grep.exe'},
        logger=logger,
        test_mode=False
    )

    analysis = strategy.analyze_pipeline("find . | grep TODO")
    execution_strategy = strategy.decide_execution_strategy(analysis, "find . | grep TODO")

    if execution_strategy.strategy_type == 'BASH_REQUIRED':
        # Use bash.exe
        pass
    elif execution_strategy.has_fallback():
        # Try primary, fallback to execution_strategy.fallback_strategy
        pass

KEY CONCEPTS:
- MACRO vs MICRO: This handles complex patterns, ExecuteUnixSingleCommand handles atomic commands
- PATTERN PRIORITY: BASH_REQUIRED > BASH_PREFERRED > POWERSHELL_OK > DEFAULT
- CRITICAL PATTERNS: Process substitution, stderr redirection, command chains REQUIRE bash
- COMPLEXITY LEVELS:
  - HIGH: Process substitution OR 3+ commands in pipeline
  - MEDIUM: Pipeline OR chain
  - LOW: Single command
- GITBASH_PASSTHROUGH: Commands in constants.py that should ALWAYS use bash.exe
  (find, awk, sed, grep, diff, tar, sort, uniq, split, join, comm, paste, xargs, cut, tr, tee)

STRATEGIC DECISIONS:
1. Performance: Native binary > Quick script > Bash > Heavy script
2. Correctness: If bash.exe not available for REQUIRED pattern → warn and try PowerShell (may fail)
3. Safety: Default to bash.exe for unrecognized complex patterns (safety net)
4. Fallbacks: BASH_PREFERRED includes fallback_strategy pointing to POWERSHELL

FUTURE OPTIMIZATION:
- can_split_pipeline(): Intelligent pipeline splitting for hybrid execution
  (e.g., "find . -name '*.py' | grep TODO | wc -l" could split at | boundaries)
  Currently returns False (execute as whole)
"""
import re
import logging
from typing import Dict, List, Optional, Tuple

from .pipeline_analysis import PipelineAnalysis
from .execution_strategy import ExecutionStrategy

class PipelineStrategy:
    """
    Pipeline strategic analyzer - MACRO level strategy.

    RESPONSIBILITIES:
    - Analyze entire pipeline structure
    - Pattern match against known pipeline scenarios
    - Decide overall execution strategy
    - Determine if pipeline should be split
    - Provide fallback strategies

    NOT responsible for:
    - Executing commands
    - Translating syntax
    - Managing subprocess
    - Path translation
    """

    # ========================================================================
    # STRATEGY CONFIGURATION - Pattern Cache
    # ========================================================================

    # Commands that MUST use bash.exe (no good alternative)
    BASH_EXE_REQUIRED = {
        'complex_awk',      # awk with BEGIN/END/functions
        'complex_sed',      # sed multi-expression
        'process_subst',    # <(...) process substitution
    }

    # Commands PREFERRED for bash.exe (best compatibility)
    BASH_EXE_PREFERRED = {
        'find', 'awk', 'sed', 'grep',  # Pattern matching
        'diff', 'tar',                  # Format-sensitive
        'sort', 'uniq', 'split',        # Edge cases
        'join', 'comm', 'paste',        # Perfect behavior
        'xargs',                        # Argument building (CRITICAL for pipelines)
        'cut',                          # Field extraction (subtle behaviors)
        'tr',                           # Character translation (locale-dependent)
        'tee',                          # Output splitting (buffering matters)
    }

    # Pipeline strategies - Pattern matching for command chains
    # Format: regex pattern -> strategy type
    PIPELINE_STRATEGIES = {
        # ===== BASH.EXE REQUIRED (Complex, no alternative) =====

        # find combinations (complex logic, -exec, tests)
        r'find.*\|.*grep': 'bash_exe_required',
        r'find.*\|.*wc': 'bash_exe_required',
        r'find.*\|.*xargs': 'bash_exe_required',
        r'find.*\|.*awk': 'bash_exe_required',
        r'find.*\|.*sed': 'bash_exe_required',
        r'find.*\|.*cut': 'bash_exe_required',
        r'find.*\|.*sort': 'bash_exe_required',

        # xargs (process substitution, argument building)
        r'xargs': 'bash_exe_required',

        # awk in pipeline (field processing, BEGIN/END blocks)
        r'awk.*\|': 'bash_exe_required',
        r'\|.*awk': 'bash_exe_required',

        # sed in pipeline (multi-line, hold space, complex patterns)
        r'sed.*\|': 'bash_exe_required',
        r'\|.*sed': 'bash_exe_required',

        # grep with pipeline (regex complexity, -v, -o flags)
        r'grep.*\|.*awk': 'bash_exe_required',
        r'grep.*\|.*sed': 'bash_exe_required',
        r'grep.*\|.*xargs': 'bash_exe_required',
        r'grep.*\|.*cut': 'bash_exe_required',

        # cut in pipeline (field extraction precision)
        r'cut.*\|': 'bash_exe_required',
        r'\|.*cut': 'bash_exe_required',

        # tar/compression with pipeline
        r'tar.*\|': 'bash_exe_required',
        r'\|.*tar': 'bash_exe_required',
        r'gzip.*\|': 'bash_exe_required',
        r'\|.*gzip': 'bash_exe_required',

        # diff with pipeline
        r'diff.*\|': 'bash_exe_required',
        r'\|.*diff': 'bash_exe_required',

        # ===== BASH.EXE PREFERRED (Can emulate but bash better) =====

        # Multi-stage text processing
        r'cat.*\|.*sort.*\|.*uniq': 'bash_exe_preferred',
        r'grep.*\|.*sort.*\|.*uniq': 'bash_exe_preferred',
        r'sort.*\|.*uniq': 'bash_exe_preferred',
        r'grep.*\|.*sort': 'bash_exe_preferred',
        r'cat.*\|.*grep.*\|': 'bash_exe_preferred',

        # head/tail with pipeline
        r'head.*\|': 'bash_exe_preferred',
        r'tail.*\|': 'bash_exe_preferred',
        r'\|.*head': 'bash_exe_preferred',
        r'\|.*tail': 'bash_exe_preferred',

        # sort/uniq alone
        r'sort.*\|': 'bash_exe_preferred',
        r'\|.*sort': 'bash_exe_preferred',
        r'uniq.*\|': 'bash_exe_preferred',
        r'\|.*uniq': 'bash_exe_preferred',

        # wc with complex input
        r'grep.*\|.*wc': 'bash_exe_preferred',
        r'find.*\|.*wc': 'bash_exe_preferred',

        # ===== POWERSHELL OK (Simple, well emulated) =====

        # Simple text display
        r'echo.*\|.*base64': 'powershell_ok',
        r'cat.*\|.*base64': 'powershell_ok',

        # Simple listing
        r'ls\s+[^|]*\|.*wc': 'powershell_ok',  # ls | wc (simple count)
        r'dir\s+[^|]*\|.*wc': 'powershell_ok',

        # Simple grep (single file, simple pattern)
        r'cat\s+\S+\s*\|\s*grep\s+[^|]+$': 'powershell_ok',  # cat file | grep pattern (end)
    }

    def __init__(self, git_bash_available: bool, native_bins: Dict[str, str],
                 logger: logging.Logger = None, test_mode: bool = False):
        """
        Initialize PipelineStrategy.

        Args:
            git_bash_available: Whether Git Bash is available
            native_bins: Dict of available native binaries {cmd: path}
            logger: Logger instance
            test_mode: If True, log strategic decisions without executing
        """
        self.git_bash_available = git_bash_available
        self.native_bins = native_bins
        self.logger = logger or logging.getLogger('PipelineStrategy')
        self.test_mode = test_mode

    def analyze_pipeline(self, command: str) -> PipelineAnalysis:
        """
        Analyze pipeline structure and complexity.

        Args:
            command: Full command string

        Returns:
            PipelineAnalysis with all structural information
        """
        analysis = PipelineAnalysis()

        # Detect structural elements
        analysis.has_pipeline = '|' in command
        analysis.has_chain = '&&' in command or '||' in command or ';' in command
        analysis.has_redirection = '>' in command or '<' in command
        analysis.has_stderr_redir = '2>' in command or '|&' in command or re.search(r'2>&1', command)
        analysis.has_process_subst = '<(' in command or '>(' in command

        # Extract command names
        if analysis.has_pipeline:
            # Split by pipe and extract first word of each part
            parts = command.split('|')
            analysis.command_count = len(parts)
            for part in parts:
                cmd_parts = part.strip().split()
                if cmd_parts:
                    analysis.command_names.append(cmd_parts[0])
        else:
            # Single command or chain
            cmd_parts = command.split()[0] if command.split() else ""
            if cmd_parts:
                analysis.command_names.append(cmd_parts)

        # Pattern matching
        for pattern, strategy_type in self.PIPELINE_STRATEGIES.items():
            if re.search(pattern, command):
                analysis.matched_pattern = pattern
                break

        # Determine complexity level
        if analysis.has_process_subst:
            analysis.complexity_level = 'HIGH'
        elif analysis.has_pipeline and analysis.command_count > 2:
            analysis.complexity_level = 'HIGH'
        elif analysis.has_pipeline or analysis.has_chain:
            analysis.complexity_level = 'MEDIUM'
        else:
            analysis.complexity_level = 'LOW'

        if self.test_mode:
            self.logger.info(f"[TEST-PIPELINE-ANALYSIS] {analysis}")

        return analysis

    def decide_execution_strategy(self, analysis: PipelineAnalysis, command: str) -> ExecutionStrategy:
        """
        Decide optimal execution strategy based on analysis.

        Args:
            analysis: PipelineAnalysis from analyze_pipeline()
            command: Original command string

        Returns:
            ExecutionStrategy with decision and fallbacks
        """
        # CRITICAL: Process substitution REQUIRES bash
        if analysis.has_process_subst:
            if self.git_bash_available:
                return ExecutionStrategy(
                    strategy_type='BASH_REQUIRED',
                    reason='Process substitution requires bash.exe'
                )
            else:
                # FATAL: Cannot execute without bash
                return ExecutionStrategy(
                    strategy_type='FAIL',
                    reason='Process substitution requires bash.exe (not available)'
                )

        # CRITICAL: Stderr redirection should use bash
        if analysis.has_stderr_redir:
            if self.git_bash_available:
                return ExecutionStrategy(
                    strategy_type='BASH_REQUIRED',
                    reason='Stderr redirection (2>, 2>&1, |&) requires bash.exe'
                )
            else:
                # Can try PowerShell but warn
                self.logger.warning("Stderr redirection without bash.exe - semantics may differ")
                return ExecutionStrategy(
                    strategy_type='POWERSHELL',
                    reason='Stderr redirection emulation (bash.exe not available)'
                )

        # CRITICAL: Command chains need bash for correct semantics
        if analysis.has_chain:
            if self.git_bash_available:
                return ExecutionStrategy(
                    strategy_type='BASH_REQUIRED',
                    reason='Command chain (&&, ||, ;) requires bash.exe for correct semantics'
                )
            else:
                self.logger.error("Command chain without bash.exe - may behave incorrectly")
                return ExecutionStrategy(
                    strategy_type='POWERSHELL',
                    reason='Command chain emulation (bash.exe not available - may fail)'
                )

        # Pipeline pattern matching
        if analysis.matched_pattern:
            strategy_from_pattern = None
            for pattern, strategy_name in self.PIPELINE_STRATEGIES.items():
                if pattern == analysis.matched_pattern:
                    strategy_from_pattern = strategy_name
                    break

            if strategy_from_pattern == 'bash_exe_required':
                if self.git_bash_available:
                    return ExecutionStrategy(
                        strategy_type='BASH_REQUIRED',
                        reason=f'Pipeline pattern requires bash.exe: {analysis.matched_pattern}'
                    )
                else:
                    self.logger.error(f"Pipeline requires bash.exe but not available: {command[:100]}")
                    return ExecutionStrategy(
                        strategy_type='POWERSHELL',
                        reason='Pipeline emulation (bash.exe not available - may produce wrong results)'
                    )

            elif strategy_from_pattern == 'bash_exe_preferred':
                if self.git_bash_available:
                    return ExecutionStrategy(
                        strategy_type='BASH_PREFERRED',
                        reason=f'Pipeline pattern prefers bash.exe: {analysis.matched_pattern}',
                        fallback_strategy=ExecutionStrategy(
                            strategy_type='POWERSHELL',
                            reason='PowerShell emulation fallback'
                        )
                    )
                else:
                    self.logger.debug("bash.exe preferred but not available, using emulation")
                    return ExecutionStrategy(
                        strategy_type='POWERSHELL',
                        reason='Pipeline emulation (bash.exe preferred but not available)'
                    )

            elif strategy_from_pattern == 'powershell_ok':
                return ExecutionStrategy(
                    strategy_type='POWERSHELL',
                    reason='Pipeline can be emulated in PowerShell'
                )

        # DEFAULT: Pipeline detected but no pattern matched
        if analysis.has_pipeline:
            # Check if contains complex commands
            contains_complex = any(cmd in self.BASH_EXE_PREFERRED for cmd in analysis.command_names)

            if contains_complex:
                if self.git_bash_available:
                    return ExecutionStrategy(
                        strategy_type='BASH_PREFERRED',
                        reason='Pipeline with complex commands (safety net)',
                        fallback_strategy=ExecutionStrategy(
                            strategy_type='POWERSHELL',
                            reason='PowerShell emulation fallback'
                        )
                    )
                else:
                    self.logger.error(f"Complex pipeline without bash.exe: {command[:100]}")
                    return ExecutionStrategy(
                        strategy_type='POWERSHELL',
                        reason='Complex pipeline emulation (bash.exe not available - may fail)'
                    )
            else:
                # Simple pipeline, can try emulation
                return ExecutionStrategy(
                    strategy_type='POWERSHELL',
                    reason='Simple pipeline, PowerShell emulation'
                )

        # NO PIPELINE: Single command
        return ExecutionStrategy(
            strategy_type='SINGLE',
            reason='Single command (no pipeline or chain)'
        )

    def can_split_pipeline(self, command: str, analysis: PipelineAnalysis) -> Tuple[bool, List[int]]:
        """
        Determine if pipeline can be split into parts for hybrid execution.

        This is for FUTURE optimization - not implemented in first iteration.

        Args:
            command: Command string
            analysis: PipelineAnalysis

        Returns:
            (can_split, split_points)
        """
        # TODO: Implement intelligent pipeline splitting
        # For now, always return False (execute as whole)
        return False, []


