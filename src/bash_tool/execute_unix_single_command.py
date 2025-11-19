"""
Execute Unix Single Command - MICRO level single command execution strategy
"""
import subprocess
import logging
import shlex
from typing import Optional

from .constants import BASH_GIT_UNSUPPORTED_COMMANDS
from .execution_engine import ExecutionEngine
from .command_emulator import CommandEmulator

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

    def __init__(self,
                 logger: logging.Logger = None,
                 test_mode: bool = False):
        """
        Initialize ExecuteUnixSingleCommand.

        Args:
            execution_engine: ExecutionEngine instance (for is_available checks)
            command_emulator: CommandEmulator instance (for translation)
            git_bash_exe: Path to bash.exe (None if not available)
            git_bash_converter: Function to convert command to bash format
            logger: Logger instance
            test_mode: If True, log decisions without executing
        """
        self.logger = logger or logging.getLogger('ExecuteUnixSingleCommand')
        self.test_mode = test_mode
        self.engine = ExecutionEngine( self.logger, self.test_mode)
        self.emulator = CommandEmulator()

    def execute_single(self, command: str, test_mode_stdout=None) -> subprocess.CompletedProcess:
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

        Returns:
            Tuple[str, bool]: (executable_command, use_powershell)
                             use_powershell=True → PowerShell script
                             use_powershell=False → Native binary or bash.exe
        """
        # ================================================================
        # INTERNAL PARSING - Extract cmd_name to choose strategy
        # ================================================================
        import shlex
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
            return self.engine.execute_native(cmd_name, parts[1:], test_mode_stdout)

        # ================================================================
        # PRIORITY 2: CommandEmulator Quick (FAST INLINE)
        # ================================================================
        if self.emulator.is_quick_command(cmd_name) and cmd_name not in GITBASH_PASSTHROUGH_COMMANDS:
            self.logger.debug(f"Strategy: Quick PowerShell script ({cmd_name})")
            translated = self.emulator.emulate_command(command)
            if self._needs_powershell(translated):
                return self.engine.execute_powershell(translated, test_mode_stdout)
            else:
                return self.engine.execute_cmd(translated, test_mode_stdout)

        # ================================================================
        # PRIORITY 3: Bash Git (if supported) + FALLBACK TO SCRIPT
        # ================================================================
        if cmd_name not in BASH_GIT_UNSUPPORTED_COMMANDS and self.engine.capabilities['bash']:
            try:
                self.logger.debug(f"Strategy: Bash Git ({cmd_name})")
                return self.engine.execute_bash(command, test_mode_stdout)
            except Exception:
                # Fallback to script if bash conversion fails
                self.logger.debug(f"Strategy: Bash conversion failed, fallback to script ({cmd_name})")
                translated = self.emulator.emulate_command(command)
                if self._needs_powershell(translated):
                    return self.engine.execute_powershell(translated, test_mode_stdout)
                else:
                    return self.engine.execute_cmd(translated, test_mode_stdout)

        # ================================================================
        # PRIORITY 4: CommandEmulator Script (HEAVY EMULATION)
        # ================================================================
        self.logger.debug(f"Strategy: Heavy PowerShell script ({cmd_name})")
        translated = self.emulator.emulate_command(command)
        return self.engine.execute_powershell(translated, test_mode_stdout)


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

