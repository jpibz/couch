"""
Bash Tool Executor - Main orchestrator (thin layer)
"""
import logging
from pathlib import Path
from typing import Optional, Dict

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

    def __init__(self, working_dir: str, enabled: bool = False,
                 **kwargs):
        """
        Initialize BashToolExecutor
        
        Args:
            working_dir: Tool working directory (from ConfigurationManager)
            enabled: Tool enabled state
            
        """
        super().__init__('bash_tool', enabled)

        # TESTMODE flag for testing purposes
        TESTMODE = True  # Set to True for testing
        self.TESTMODE = TESTMODE

        self.working_dir = Path(working_dir)

        # Initialize components
        self.path_translator = PathTranslator()
        self.sandbox_validator = SandboxValidator(self.path_translator.workspace_root)

        # Create tool-specific scratch directory
        self.scratch_dir = self.path_translator.get_tool_scratch_directory('bash_tool')
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

        # Get claude home directory (needed for preprocessing)
        self.claude_home_unix = self.path_translator.get_claude_home_unix()

        # Initialize CommandExecutor (execution strategy layer)

        self.command_executor = CommandExecutor(
            claude_home_unix=self.claude_home_unix,
            logger=self.logger,
            test_mode=self.TESTMODE
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

        # Determine timeout
        timeout = self.python_timeout if 'python' in command.lower() else self.default_timeout

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
            result, translated_cmd, method = self.command_executor.execute(
                command=command_with_win_paths,
                timeout=timeout
            )

            # STEP 4: Format result (with path reverse translation)
            return self._format_result(result, command, translated_cmd, method)

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return f"Error: {str(e)}"
        finally:
            # Cleanup temp files
            self._cleanup_temp_files(temp_files)
    
    def _format_result(self, result, original_cmd: str, translated_cmd: str, method: str) -> str:
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
