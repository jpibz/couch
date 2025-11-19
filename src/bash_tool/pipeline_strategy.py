"""
Pipeline Strategy - MACRO level pipeline analysis
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


