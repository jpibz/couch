"""
Bash Tool Executor - Main orchestrator (thin layer)

ARCHITECTURE:
This is the TOP-LEVEL ENTRY POINT for bash command execution on Windows.
It is a THIN ORCHESTRATOR that delegates almost all work to specialized components.

Position in hierarchy:
    USER/API
       ↓
    BashToolExecutor (this class) ← ORCHESTRATOR
       ↓
    ├── PathTranslator ← Unix/Windows path conversion
    ├── SandboxValidator ← Security checks
    └── CommandExecutor ← Command execution strategy + preprocessing

RESPONSIBILITIES:
1. Tool registration and initialization (inherits from ToolExecutor ABC)
2. Path translation orchestration (Unix → Windows before execution, Windows → Unix in results)
3. Security orchestration (sandbox validation)
4. Result formatting (matches bash_tool API contract)
5. Timeout management (different timeouts for python vs other commands)
6. Temp file cleanup

NOT RESPONSIBLE FOR:
- Command translation (delegated to CommandEmulator via CommandExecutor)
- Execution strategy decisions (delegated to PipelineStrategy/ExecuteUnixSingleCommand)
- Subprocess management (delegated to ExecutionEngine)
- Bash pattern preprocessing (delegated to CommandExecutor)
- Path translation logic (delegated to PathTranslator)
- Security validation logic (delegated to SandboxValidator)

DESIGN PATTERN:
- Facade Pattern: Provides simple interface hiding complex subsystem
- Delegation Pattern: Delegates almost all work to specialized components
- Template Method: execute() method follows fixed orchestration template

DATA FLOW:
    execute(tool_input) →
        1. PathTranslator.translate_paths_in_string(command, 'to_windows')
        2. SandboxValidator.validate_command(command)
        3. CommandExecutor.execute(command) → (result, translated_cmd, method)
        4. PathTranslator.translate_paths_in_string(result, 'to_unix')
        5. _format_result(result) → formatted_string

USAGE PATTERN:
    executor = BashToolExecutor(working_dir="/home/claude/workspace")
    result = executor.execute({"command": "ls -la /home/claude"})
    # Returns: "Exit code: 0\\n\\nfile1.txt\\nfile2.txt"

CONFIGURATION:
- TESTMODE flag: Set to True to skip path translation and sandbox validation (for testing)
- working_dir: Tool working directory (from ConfigurationManager)
- scratch_dir: Tool-specific scratch directory (for temporary files)

API CONTRACT:
The execute() method returns a string formatted as:
    Exit code: N [\\n\\n stdout] [\\n\\n--- stderr ---\\n stderr]
"""
import logging
from pathlib import Path
from typing import Optional, Dict
import subprocess
from .tool_executor import ToolExecutor
from .sandbox_validator import SandboxValidator
from .command_executor import CommandExecutor
from .path_translator import PathTranslator

class BashToolExecutor(ToolExecutor):
    """
    Bash command executor for Windows - PRODUCTION VERSION.

    RESPONSIBILITIES:
    - Entry point for bash tool execution
    - Path translation (Unix <-> Windows)
    - Security validation (sandbox)
    - Preprocessing (heredocs, substitution, expansions)
    - Delegation to CommandExecutor for execution

    ARCHITECTURE:
    This is a THIN COORDINATOR that delegates to specialized components:
    - PathTranslator: Unix/Windows path conversion
    - SandboxValidator: Security checks
    - CommandExecutor: Command execution strategy
    """

    def __init__(self, working_dir: Path, enabled: bool = False,
                 test_capabilities: dict = None,
                 **kwargs):
        """
        Initialize BashToolExecutor

        Args:
            working_dir: Tool working directory (from ConfigurationManager)
            enabled: Tool enabled state
            test_capabilities: Dict to override capability detection in test mode
                Example: {'bash': False, 'grep': True} forces manual emulation

        """
        super().__init__('bash_tool', enabled)

        # TESTMODE flag for testing purposes
        # TRUE = Test mode (for development/testing - simulates bash execution)
        # FALSE = Production mode (for real Claude agent - executes real bash)
        TESTMODE = True
        self.TESTMODE = TESTMODE
        self.test_capabilities = test_capabilities

        self.working_dir = working_dir

        # Initialize components
        self.path_translator = PathTranslator()
        self.sandbox_validator = SandboxValidator(self.working_dir)

        # Create tool-specific scratch directory
        self.scratch_dir = self.path_translator.get_tool_scratch_directory('bash_tool')
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

        # Get claude home directory (needed for preprocessing)
        self.claude_home_unix = self.path_translator.get_claude_home_unix()

        # Initialize CommandExecutor (execution strategy layer)
        self.command_executor = CommandExecutor(
            working_dir=self.working_dir,
            logger=self.logger,
            test_mode=self.TESTMODE,
            test_capabilities=self.test_capabilities  # PROPAGATE test_capabilities!
        )

        self.logger.info(
            "BashToolExecutor initialized"
        )
    
    def execute(self, tool_input: dict) -> str:
        """
        Execute bash command - SIMPLIFIED ORCHESTRATOR

        RESPONSIBILITIES:
        1. Translate Unix paths -> Windows paths
        2. Delegate to CommandTranslator.execute_command() (preprocessing + translation + execution)
        3. Translate Windows paths -> Unix paths in results
        4. Return formatted result
        """
        command = tool_input.get('command', '')

        if not command:
            return "Error: command parameter is required"

        self.logger.info(f"Executing: {command[:100]}")

        temp_files = []

        try:
            # STEP 1: Translate Unix paths -> Windows paths
            if not self.TESTMODE:
                command_with_win_paths = self.path_translator.translate_paths_in_string(command, 'to_windows')
            else:
                # TEST MODE: Skip path translation
                command_with_win_paths = command
                self.logger.debug("TEST MODE: Skipping path translation")

            # STEP 2: Security validation
            if not self.TESTMODE:
                is_safe, reason = self.sandbox_validator.validate_command(command_with_win_paths)
                if not is_safe:
                    return f"Error: Security - {reason}"
            else:
                self.logger.debug("TEST MODE: Skipping sandbox validation")

            # STEP 3: Execute via CommandExecutor (preprocessing + translation + execution)
            result = self.command_executor.execute(
                command=command_with_win_paths
            )

            # STEP 4: Format result (with path reverse translation)
            return self._format_result(result, command)

        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    def _format_result(self, result, original_cmd: str) -> str:
        """Format result matching bash_tool API"""
        lines = []
        
        # Exit code
        if result.returncode == 0:
            lines.append(f"Exit code: {result.returncode}")
        else:
            lines.append(f"Exit code: {result.returncode} (error)")
        
        # Stdout - translate Windows paths back to Unix
        if result.stdout:
            lines.append("")
            if not self.TESTMODE:
                stdout_unix = self.path_translator.translate_paths_in_string(result.stdout, 'to_unix')
            else:
                # TEST MODE: No path translation
                stdout_unix = result.stdout
            lines.append(stdout_unix.rstrip())

        # Stderr - translate Windows paths back to Unix
        if result.stderr:
            lines.append("")
            if result.stdout:
                lines.append("--- stderr ---")
            if self.path_translator:
                stderr_unix = self.path_translator.translate_paths_in_string(result.stderr, 'to_unix')
            else:
                # TEST MODE: No path translation
                stderr_unix = result.stderr
            lines.append(stderr_unix.rstrip())
        
        return '\n'.join(lines)
    
    def get_definition(self) -> dict:
        """Return bash_tool definition for API"""
        return {
            "name": "bash_tool",
            "description": "Run a bash command in the container",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to run in container"
                    },
                    "description": {
                        "type": "string",
                        "description": "Why I'm running this command"
                    }
                },
                "required": ["command", "description"]
            }
        }
