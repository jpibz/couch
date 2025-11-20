"""
Execute Unix Single Command - MICRO level single command execution strategy

ARCHITECTURE:
This is the MICRO LEVEL execution strategy for SINGLE ATOMIC Unix commands.
Complementary to PipelineStrategy (MACRO level for pipelines/chains).

Position in hierarchy:
    CommandExecutor
       ↓
    ├── PipelineStrategy (MACRO: pipelines, chains, complex patterns)
    └── ExecuteUnixSingleCommand (MICRO: single atomic commands) ← THIS CLASS
           ↓
        ├── ExecutionEngine (subprocess management)
        └── CommandEmulator (Unix→PowerShell translation)

RESPONSIBILITIES:
1. Execute ONE ATOMIC Unix command (no pipes, no chains, no command substitution)
2. Choose optimal execution strategy for single command:
   - PRIORITY 1: Native Binary (grep.exe, awk.exe) → Best performance, zero translation
   - PRIORITY 2: Quick Script (< 20 lines PowerShell) → Fast inline emulation
   - PRIORITY 3: Bash Git (if available) → POSIX compatibility
   - PRIORITY 4: Heavy Script (> 20 lines PowerShell) → Full emulation
3. Simple, focused decision logic (no complex fallbacks)
4. Command name extraction from full command string

NOT RESPONSIBLE FOR:
- Analyzing pipelines/chains (that's PipelineStrategy's job at MACRO level)
- Managing subprocess (that's ExecutionEngine's job)
- Path translation (already done by PathTranslator before this point)
- Security validation (already done by SandboxValidator before this point)
- Bash pattern preprocessing (already done by CommandExecutor before this point)

STRATEGY DECISION TREE:
    execute_single(command) →
        Parse command → extract cmd_name
           ↓
        1. Is native binary available? (grep.exe, awk.exe, etc.)
           YES → ExecutionEngine.execute_native() → DONE
           NO → Continue
           ↓
        2. Is "quick" command? (< 20 lines PowerShell) AND not in GITBASH_PASSTHROUGH?
           YES → CommandEmulator.emulate_command() → ExecutionEngine.execute_powershell()
           NO → Continue
           ↓
        3. Is Git Bash available? AND command supported?
           YES → ExecutionEngine.execute_bash() → DONE (or fallback to #4 if fails)
           NO → Continue
           ↓
        4. CommandEmulator.emulate_command() → ExecutionEngine.execute_powershell()

DESIGN PATTERN:
- Strategy Pattern: Different execution strategies for different command types
- Chain of Responsibility: Try strategies in priority order until one succeeds
- Adapter Pattern: CommandEmulator adapts Unix commands to PowerShell

DATA FLOW:
    execute_single("grep -r pattern .") →
        1. Parse → cmd_name = "grep"
        2. Check native: is_available("grep") → YES → execute_native("grep", ["-r", "pattern", "."])
        3. Return CompletedProcess

USAGE PATTERN:
    executor = ExecuteUnixSingleCommand(logger=logger, test_mode=False)
    result = executor.execute_single("grep -r TODO src/")
    # result: subprocess.CompletedProcess(returncode=0, stdout="...", stderr="")

KEY CONCEPTS:
- ATOMIC: Command must be single, no pipes/chains
- COMMAND NAME: First word of command used to determine strategy
- QUICK vs HEAVY: CommandEmulator distinguishes quick (< 20 lines) vs heavy (> 20 lines) scripts
- GITBASH_PASSTHROUGH: Commands better handled by Git Bash than PowerShell emulation
  (find, awk, sed, grep with complex patterns)

STRATEGY RATIONALE:
1. Native binaries: Best performance (no translation, direct execution)
2. Quick scripts: Fast (inline PowerShell, no bash.exe overhead)
3. Bash Git: POSIX compatibility (complex commands work correctly)
4. Heavy scripts: Full emulation (fallback when nothing else works)
"""
import subprocess
import logging
import shlex
from typing import Optional

from constants import BASH_GIT_UNSUPPORTED_COMMANDS, GITBASH_PASSTHROUGH_COMMANDS
from execution_engine import ExecutionEngine
from command_emulator import CommandEmulator


class ExecuteUnixSingleCommand:
    """
    Single Unix command executor - MICRO level strategy.

    RESPONSIBILITIES:
    - Execute ONE ATOMIC Unix command (no pipelines/chains)
    - Choose optimal strategy: Native Bin → Quick Script → Bash Git → Heavy Script
    - Simple, focused decision logic

    NOT responsible for:
    - Analyzing pipelines/chains (that's PipelineStrategy's job)
    - Managing subprocess (that's ExecutionEngine's job)
    - Complex fallbacks (keep it simple!)
    """

    def __init__(self, command_preprocessor,
                 working_dir,
                 logger: logging.Logger = None,
                 test_mode: bool = False,
                 test_capabilities: Optional[dict] = None):
        """
        Initialize ExecuteUnixSingleCommand.

        Args:
            execution_engine: ExecutionEngine instance (for is_available checks)
            command_emulator: CommandEmulator instance (for translation)
            git_bash_exe: Path to bash.exe (None if not available)
            git_bash_converter: Function to convert command to bash format
            logger: Logger instance
            test_mode: If True, log decisions without executing
            test_capabilities: Dict for TEST MODE ONLY - control availability
        """
        self.logger = logger or logging.getLogger('ExecuteUnixSingleCommand')
        self.test_mode = test_mode
        self.working_dir = working_dir
        self.engine = ExecutionEngine(working_dir, test_mode=test_mode, logger=logger, test_capabilities=test_capabilities)
        self.emulator = CommandEmulator()
        self.command_preprocessor = command_preprocessor

    def execute(self, command: str, stdin: str = None, test_mode_stdout=None) -> subprocess.CompletedProcess:
        """
        Execute single ATOMIC Unix command with optimal strategy.

        DESIGN:
        - Accepts FULL command string (e.g., "grep -r pattern .")
        - Parses INTERNALLY to extract cmd_name
        - Uses cmd_name ONLY to choose strategy
        - Returns executable command

        STRATEGY (SIMPLE & CLEAR):
        1. Native Binary (grep.exe, awk.exe) → Best performance
        2. CommandEmulator Quick (< 20 lines) → Fast inline scripts
        3. Bash Git (if supported) + fallback → POSIX compatibility
        4. CommandEmulator Script → Heavy PowerShell emulation

        Args:
            command: Full command string (e.g., "grep -r pattern .")
            stdin: Optional stdin data to pass to command

        Returns:
            Tuple[str, bool]: (executable_command, use_powershell)
                             use_powershell=True → PowerShell script
                             use_powershell=False → Native binary or bash.exe
        """
        # ================================================================
        # INTERNAL PARSING - Extract cmd_name to choose strategy
        # ================================================================

        try:
            parts = shlex.split(command) if ' ' in command else [command]
        except ValueError:
            # Quote parsing error, fallback to simple split
            parts = command.split()

        if not parts:
            # Empty command
            return subprocess.CompletedProcess(
                returncode=-1,
                stderr="Empty command"
            )

        cmd_name = parts[0]

        if self.test_mode:
            self.logger.info(f"[SINGLE-EXEC] {cmd_name}: {command}")

        # ================================================================
        # PRIORITY 1: Native Binary (BEST PERFORMANCE)
        # ================================================================
        if self.engine.is_available(cmd_name):
            self.logger.debug(f"Strategy: Native binary ({cmd_name}.exe)")
            return self.engine.execute_native(cmd_name, parts[1:], stdin=stdin, test_mode_stdout=test_mode_stdout)

        # ================================================================
        # PRIORITY 2: Quick PowerShell (FAST INLINE for simple commands)
        # ================================================================
        if self.emulator.is_quick_command(cmd_name) and cmd_name not in GITBASH_PASSTHROUGH_COMMANDS:
            self.logger.debug(f"Strategy: Quick PowerShell inline ({cmd_name})")
            cmd_preprocessed = self.command_preprocessor.preprocess_for_emulation(command)
            translated = self.emulator.emulate_command(cmd_preprocessed)
            if self._needs_powershell(translated):
                return self.engine.execute_powershell(translated, stdin=stdin, test_mode_stdout=test_mode_stdout)
            else:
                return self.engine.execute_cmd(translated, stdin=stdin, test_mode_stdout=test_mode_stdout)

        # ================================================================
        # PRIORITY 3: Bash Git (POSIX compatibility for complex commands)
        # ================================================================
        if cmd_name not in BASH_GIT_UNSUPPORTED_COMMANDS and self.engine.capabilities['bash']:
            self.logger.debug(f"Strategy: Bash Git ({cmd_name})")
            return self.engine.execute_bash(command, stdin=stdin, test_mode_stdout=test_mode_stdout)

        # ================================================================
        # PRIORITY 4: Heavy PowerShell (FALLBACK for heavy emulation)
        # ================================================================
        self.logger.debug(f"Strategy: Heavy PowerShell emulation ({cmd_name})")
        cmd_preprocessed = self.command_preprocessor.preprocess_for_emulation(command)
        translated = self.emulator.emulate_command(cmd_preprocessed)
        if self._needs_powershell(translated):
            return self.engine.execute_powershell(translated, stdin=stdin, test_mode_stdout=test_mode_stdout)
        else:
            return self.engine.execute_cmd(translated, stdin=stdin, test_mode_stdout=test_mode_stdout)


    def _needs_powershell(self, command: str) -> bool:
        """
        Detect if command needs PowerShell instead of cmd.exe.
        
        PowerShell required for:
        - Command substitution: $(...)
        - Backticks: `...`
        - Process substitution: <(...)
        - Complex variable expansion
        
        Returns:
            True if PowerShell required, False if cmd.exe sufficient
        """
        # Command substitution patterns
        if '$(' in command:
            return True
        
        # Backtick command substitution
        if '`' in command:
            # Check it's not just in a string
            # Simple heuristic: backticks outside of quotes
            in_quotes = False
            quote_char = None
            for i, char in enumerate(command):
                if char in ('"', "'") and (i == 0 or command[i-1] != '\\'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                elif char == '`' and not in_quotes:
                    return True
        
        # Process substitution
        if '<(' in command or '>(' in command:
            return True
        
        return False

    def _adapt_for_powershell(self, command: str) -> str:
        """
        Adapt Unix command for PowerShell execution.
        
        Translations:
        - Backticks `cmd` → $(...) PowerShell syntax
        - Preserve pipes, redirects, logical operators
        - Path translations already done by PathTranslator
        
        Args:
            command: Unix command with Windows paths already translated
            
        Returns:
            Command adapted for PowerShell
        """
        adapted = command
        
        # Convert backticks to PowerShell command substitution
        # Pattern: `command` → $(command)
        # Handle escaped backticks (don't convert)
        import re
        
        # Find all backtick pairs (not escaped)
        # This is a simple implementation - may need refinement for complex cases
        backtick_pattern = r'(?<!\\)`([^`]+)`'
        adapted = re.sub(backtick_pattern, r'$(\1)', adapted)
        
        # PowerShell uses different redirection for null
        # /dev/null → $null
        adapted = adapted.replace('/dev/null', '$null')
        
        # Note: Most other Unix patterns (pipes, redirects, &&, ||) work in PowerShell
        
        return adapted

# ============================================================================
# COMMAND EXECUTOR - Main orchestrator
# ============================================================================

