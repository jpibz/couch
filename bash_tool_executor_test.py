"""
CommandExecutorTest - Test version with faked subprocess calls

This class is a TEST DOUBLE of CommandExecutor that fakes all subprocess.run calls
to return the command that WOULD have been executed, allowing us to verify
command translation without actually executing anything.
"""

import os
import re
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock

# Import the real CommandExecutor to inherit from
from bash_tool_executor_REFACTORED import CommandExecutor


# ============================================================================
# FAKE SUBPROCESS RESULT FOR TEST MODE
# ============================================================================

class FakeSubprocessResult:
    """Fake subprocess.CompletedProcess result"""
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.args = []


class CommandExecutorTest(CommandExecutor):
    """
    Test version of CommandExecutor with faked subprocess calls.

    All subprocess.run() calls are intercepted and return fake results
    showing what command WOULD have been executed.

    For complex emulations with multiple subprocess calls, intermediate
    results are faked to simulate successful execution.
    """

    def __init__(self, command_translator=None,
                 git_bash_exe=None, claude_home_unix="/home/testuser", logger=None):
        """Initialize test executor with subprocess mocking"""
        self.logger = logger or logging.getLogger('CommandExecutorTest')
        self.subprocess_calls = []  # Track all subprocess calls for debugging

        # Patch subprocess.run BEFORE calling super().__init__
        # This ensures all subprocess calls in parent init are also faked
        self._patch_subprocess()

        # Now call parent init which will use our patched subprocess
        super().__init__(command_translator, git_bash_exe, claude_home_unix, logger)

    def _patch_subprocess(self):
        """Monkey-patch subprocess.run to use our fake version"""
        import bash_tool_executor_REFACTORED as executor_module
        import subprocess

        # Save original
        self._original_subprocess_run = subprocess.run

        # Replace with our fake
        subprocess.run = self._fake_subprocess_run
        executor_module.subprocess.run = self._fake_subprocess_run

    def _unpatch_subprocess(self):
        """Restore original subprocess.run"""
        import bash_tool_executor_REFACTORED as executor_module
        import subprocess

        if hasattr(self, '_original_subprocess_run'):
            subprocess.run = self._original_subprocess_run
            executor_module.subprocess.run = self._original_subprocess_run

    def _fake_subprocess_run(self, args, capture_output=False, text=False,
                            timeout=None, cwd=None, env=None, errors=None,
                            encoding=None, **kwargs) -> FakeSubprocessResult:
        """
        Fake subprocess.run() - returns what WOULD be executed.

        Args:
            args: Command args (list or string)
            **kwargs: subprocess.run kwargs (analyzed for smart faking)

        Returns:
            FakeSubprocessResult with command as stdout
        """
        # Convert args to string for output
        if isinstance(args, list):
            cmd_str = ' '.join(str(arg) for arg in args)
        else:
            cmd_str = str(args)

        # Track the call
        self.subprocess_calls.append({
            'args': args,
            'kwargs': kwargs,
            'command': cmd_str,
            'cwd': cwd
        })

        # Log what we're faking
        self.logger.info(f"[FAKE SUBPROCESS] {cmd_str}")

        # Smart fake outputs based on command
        fake_stdout = self._generate_fake_output(args, cmd_str)

        # Return fake successful result
        return FakeSubprocessResult(
            returncode=0,
            stdout=fake_stdout,
            stderr=""
        )

    def _generate_fake_output(self, args, cmd_str):
        """
        Generate smart fake output based on command.

        For multi-step emulations, this simulates intermediate results.
        """
        # Default: show what would be executed
        output = f"[TEST MODE] Would execute: {cmd_str}\n"

        # Special cases for specific commands

        # 'where' command (binary detection)
        if isinstance(args, list) and len(args) >= 2 and args[0] == 'where':
            binary_name = args[1]
            output = f"C:\\Program Files\\Git\\usr\\bin\\{binary_name}\n"

        # bash.exe -c "..." command execution
        if isinstance(args, list) and len(args) >= 3:
            if 'bash' in str(args[0]).lower() and args[1] == '-c':
                bash_cmd = args[2]
                output = f"[BASH.EXE] {bash_cmd}\n"

                # If it's a cat heredoc expansion, simulate expansion
                if 'cat <<EXPAND_DELIMITER' in bash_cmd:
                    # Extract content between delimiters
                    content_match = re.search(r'<<EXPAND_DELIMITER\n(.*?)\nEXPAND_DELIMITER', bash_cmd, re.DOTALL)
                    if content_match:
                        content = content_match.group(1)
                        # Simulate variable expansion
                        expanded = content.replace('$HOME', '/home/testuser')
                        expanded = expanded.replace('$USER', 'testuser')
                        expanded = expanded.replace('$PATH', '/usr/bin:/bin')
                        output = expanded + "\n"

        # PowerShell commands
        if isinstance(args, list) and len(args) >= 3:
            if 'powershell' in str(args[0]).lower() or args[0] == 'powershell':
                ps_cmd = ' '.join(args[1:])
                output = f"[POWERSHELL] {ps_cmd}\n"

        # awk.exe / gawk.exe detection
        if 'awk' in cmd_str.lower() and 'where' not in cmd_str.lower():
            if 'Get-Command' in cmd_str or '-ErrorAction' in cmd_str:
                # PowerShell checking for awk
                output = "C:\\Program Files\\Git\\usr\\bin\\awk.exe\n"

        return output

    def get_subprocess_calls(self) -> List[Dict]:
        """Get all subprocess calls made during testing"""
        return self.subprocess_calls

    def clear_subprocess_calls(self):
        """Clear subprocess call history"""
        self.subprocess_calls = []

    def print_subprocess_calls(self):
        """Print all subprocess calls for debugging"""
        print("\n" + "="*80)
        print("SUBPROCESS CALLS MADE:")
        print("="*80)
        for i, call in enumerate(self.subprocess_calls, 1):
            print(f"\n[{i}] Command: {call['command']}")
            if call.get('cwd'):
                print(f"    CWD: {call['cwd']}")
        print("="*80 + "\n")

    def __del__(self):
        """Cleanup: unpatch subprocess on destruction"""
        try:
            self._unpatch_subprocess()
        except:
            pass
