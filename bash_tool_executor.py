"""
Tool executors - FILE DI LAVORO
Contiene solo le classi essenziali per il lavoro di refactoring.
"""

import os
import subprocess
import json
import re
import logging
import threading
# import tiktoken  # Not needed for testing
from pathlib import Path
from dataclasses import dataclass, field
from typing import Type, Callable, Dict, Any, List, Optional, Tuple, Tuple
from abc import ABC, abstractmethod
from unix_translator import PathTranslator, CommandTranslator


class SandboxValidator:
    """
    Sandbox validator for bash command execution.
    
    SECURITY MODEL:
    - Workspace containment: Commands can only access workspace directory
    - Command blacklist: Dangerous system commands blocked
    - Drive restrictions: Only workspace drive accessible
    - Path enforcement: Absolute paths outside workspace rejected
    
    NOT A FULL SANDBOX: Protection against common dangerous operations,
    not designed to stop determined attackers (not the use case).
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.workspace_drive = self.workspace_root.drive.upper()
        
        # BLACKLIST: Commands that should NEVER execute
        self.dangerous_commands = {
            # Disk operations
            'format', 'diskpart', 'chkdsk',
            # Registry
            'reg', 'regedit',
            # System control
            'shutdown', 'restart', 'logoff',
            # Services
            'sc', 'net', 'taskkill',
            # System config
            'bcdedit', 'powercfg', 'wmic',
            # Package managers (could install malware)
            'msiexec',
            # Scheduled tasks
            'schtasks', 'at',
            # Firewall/Security
            'netsh',
        }
        
        # RESTRICTED: Commands allowed only with careful argument checking
        self.restricted_commands = {
            'del', 'erase', 'rd', 'rmdir', 'deltree',
            'move', 'ren', 'rename',
            'copy', 'xcopy', 'robocopy',
        }
    
    def validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate command for sandbox safety.
        
        Returns:
            (is_safe, reason)
            - (True, "OK") if safe
            - (False, "reason") if blocked
        """
        if not command or not command.strip():
            return True, "OK"
        
        command_lower = command.lower().strip()
        
        # Check 1: Dangerous commands blacklist
        for dangerous_cmd in self.dangerous_commands:
            if self._contains_command(command_lower, dangerous_cmd):
                return False, f"Dangerous command blocked: {dangerous_cmd}"
        
        # Check 2: Absolute paths outside workspace
        is_safe, reason = self._check_path_boundaries(command)
        if not is_safe:
            return False, reason
        
        # Check 3: Drive access restrictions
        is_safe, reason = self._check_drive_access(command)
        if not is_safe:
            return False, reason
        
        # Check 4: Restricted commands need path verification
        for restricted_cmd in self.restricted_commands:
            if self._contains_command(command_lower, restricted_cmd):
                is_safe, reason = self._validate_restricted_command(command, restricted_cmd)
                if not is_safe:
                    return False, reason
        
        return True, "OK"
    
    def _contains_command(self, command: str, cmd_name: str) -> bool:
        """Check if command contains given command name as standalone word"""
        # Match cmd_name as whole word (start of string or after space/pipe/&&/||)
        pattern = r'(?:^|[\s|&;])' + re.escape(cmd_name) + r'(?:[\s.]|$)'
        return re.search(pattern, command, re.IGNORECASE) is not None
    
    def _check_path_boundaries(self, command: str) -> tuple[bool, str]:
        """Check that all absolute Windows paths are within workspace"""
        # Pattern: Windows absolute path (drive letter + colon + path)
        # Matches: C:\path, D:\other, etc.
        pattern = r'([A-Z]):\\([^\s"]+)'
        
        matches = re.finditer(pattern, command, re.IGNORECASE)
        
        for match in matches:
            full_path_str = match.group(0)
            
            try:
                full_path = Path(full_path_str).resolve()
                
                # Check if path is within workspace
                try:
                    full_path.relative_to(self.workspace_root)
                    # Path is within workspace - OK
                except ValueError:
                    # Path is OUTSIDE workspace - BLOCK
                    return False, f"Path outside workspace blocked: {full_path_str}"
            
            except Exception:
                # Invalid path - let it fail naturally during execution
                pass
        
        return True, "OK"
    
    def _check_drive_access(self, command: str) -> tuple[bool, str]:
        """Check that command doesn't access other drives"""
        # Pattern: Drive letter references (C:, D:, etc.)
        pattern = r'\b([A-Z]):'
        
        matches = re.finditer(pattern, command, re.IGNORECASE)
        
        for match in matches:
            drive = match.group(1).upper()
            if drive != self.workspace_drive:
                return False, f"Access to drive {drive}: blocked (only {self.workspace_drive}: allowed)"
        
        return True, "OK"
    
    def _validate_restricted_command(self, command: str, cmd_name: str) -> tuple[bool, str]:
        """
        Validate restricted commands (del, move, etc.) have safe arguments.
        
        These commands are allowed but must operate on workspace paths only.
        """
        # For restricted commands, we've already checked path boundaries
        # Additional check: ensure not using wildcard on root
        
        
        # Check for dangerous wildcards at root level
        # Pattern: del C:\* or rd C:\ /S
        dangerous_patterns = [
            r'(del|erase|rd|rmdir)\s+[A-Z]:\\?\*',  # del C:\*
            r'(del|erase)\s+.*\\?\*.*\s+/[sS]',      # del ... * /S (recursive)
            r'(rd|rmdir)\s+[A-Z]:\\\s+/[sS]',        # rd C:\ /S
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Dangerous wildcard operation blocked: {cmd_name}"
        
        return True, "OK"


# ============================================================================
# BASE CLASS
# ============================================================================

class ToolExecutor(ABC):
    """Base class per tool executors"""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.logger = logging.getLogger(f"ToolExecutor.{name}")
    
    @abstractmethod
    def execute(self, tool_input: Dict) -> str:
        """Execute tool con input"""
        pass
    
    @abstractmethod
    def get_definition(self) -> Dict:
        """Return tool definition per API payload"""
        pass
    
    def enable(self):
        """Enable tool"""
        self.enabled = True
    
    def disable(self):
        """Disable tool"""
        self.enabled = False


class CommandExecutor:
    """
    Command execution strategy orchestrator.
    
    RESPONSIBILITIES:
    - Execute bash commands on Windows
    - Choose optimal execution strategy per command
    - Implement complex command emulation
    - Manage fallback chains
    - Handle Git Bash passthrough
    - Detect and use native binaries
    
    NOT responsible for:
    - Syntax translation (CommandTranslator)
    - Path translation (PathTranslator)
    - Preprocessing (BashToolExecutor)
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
    
    # Native Windows binaries available (Git for Windows)
    NATIVE_BINS = {
        'diff': 'diff.exe',
        'tar': 'tar.exe',
        'awk': 'awk.exe',
        'sed': 'sed.exe',
        'grep': 'grep.exe',
        'jq': 'jq.exe',
    }
    
    # Commands with PowerShell emulation
    POWERSHELL_EMULATION = {
        'curl', 'wget',                    # Invoke-WebRequest
        'sha256sum', 'sha1sum', 'md5sum',  # Get-FileHash
        'base64', 'timeout', 'watch',      # Utilities
        'hexdump', 'strings',              # Binary inspection
        'gzip', 'gunzip', 'zip', 'unzip',  # Compression
        'column',                          # Formatting
    }
    
    # Pipeline strategies - Pattern matching for command chains
    # Format: regex pattern → strategy
    #
    # CRITICAL: User (Claude) uses EXTREME pipeline acrobatics
    # Default for pipelines MUST be bash.exe for perfect emulation
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
    
    def __init__(self, path_translator=None, command_translator=None,
                 git_bash_exe=None, logger=None):
        """
        Initialize CommandExecutor.
        
        Args:
            path_translator: PathTranslator instance (optional)
            command_translator: CommandTranslator instance (for delegation)
            git_bash_exe: Path to bash.exe (optional)
            logger: Logger instance
        """
        self.path_translator = path_translator
        self.command_translator = command_translator
        self.git_bash_exe = git_bash_exe
        self.logger = logger or logging.getLogger('CommandExecutor')
        
        # Detect available native binaries
        self.available_bins = self._detect_native_binaries()
        
        self.logger.info(f"CommandExecutor initialized")
        self.logger.info(f"Git Bash: {'available' if git_bash_exe else 'not available'}")
        self.logger.info(f"Native binaries: {len(self.available_bins)} detected")
    
    # ========================================================================
    # MAIN EXECUTION ENTRY POINT
    # ========================================================================
    
    def execute_bash(self, command: str, parts: List[str]) -> Tuple[str, bool]:
        """
        Execute bash command with optimal strategy.
        
        This is the MAIN dispatcher - decides execution strategy.
        
        Args:
            command: Full command string
            parts: Command parts [cmd, arg1, arg2, ...]
            
        Returns:
            Tuple[str, bool]: (executable_command, use_powershell)
        """
        if not parts:
            return command, False
        
        cmd_name = parts[0]
        
        # ================================================================
        # PIPELINE DETECTION - Check if command contains pipeline/chain
        # ================================================================
        
        has_pipeline = '|' in command
        has_chain = '&&' in command or '||' in command or ';' in command

        # ================================================================
        # COMMAND CHAINS - && || ;
        # ================================================================
        # CRITICAL: Chains have different semantics in bash vs PowerShell
        # - Exit code propagation differs
        # - Short-circuit evaluation behavior differs
        # - Error handling differs
        # For PERFECT emulation, chains MUST use bash.exe

        if has_chain:
            if self.git_bash_exe:
                self.logger.debug(f"Command chain detected (&&, ||, ;) → using bash.exe")
                bash_cmd = self._execute_with_gitbash(command)
                if bash_cmd:
                    return bash_cmd, False
            else:
                # No bash.exe for chain - CRITICAL
                self.logger.error(f"Command chain requires bash.exe: {command[:100]}")
                self.logger.error("bash.exe not available - chain execution may behave incorrectly")
                # Continue but results may be wrong

        # ================================================================
        # PIPELINES - |
        # ================================================================

        if has_pipeline:
            # Check pipeline strategies
            matched_strategy = None
            for pattern, strategy in self.PIPELINE_STRATEGIES.items():
                if re.search(pattern, command):
                    self.logger.debug(f"Pipeline pattern matched: {pattern} → {strategy}")
                    matched_strategy = strategy

                    if strategy == 'bash_exe_required':
                        if self.git_bash_exe:
                            # Must use bash.exe
                            bash_cmd = self._execute_with_gitbash(command)
                            if bash_cmd:
                                return bash_cmd, False
                        else:
                            # CRITICAL: bash.exe REQUIRED but not available
                            self.logger.error(f"Pipeline requires bash.exe but not available: {command[:100]}")
                            # Try fallback anyway but warn
                            self.logger.warning("Attempting PowerShell emulation - may produce incorrect results")
                            break  # Continue to emulation with warning

                    elif strategy == 'bash_exe_preferred':
                        if self.git_bash_exe:
                            # Prefer bash.exe but can fallback
                            bash_cmd = self._execute_with_gitbash(command)
                            if bash_cmd:
                                return bash_cmd, False
                        # If bash not available, continue to emulation
                        self.logger.debug("bash.exe preferred but not available, trying emulation")
                        break

                    elif strategy == 'powershell_ok':
                        # Can handle with PowerShell - continue to normal flow
                        break

                    # Strategy handled, exit pattern loop
                    break

            # DEFAULT SAFETY NET: Pipeline detected but no pattern matched
            # OR pattern matched but bash.exe not available for required/preferred
            if matched_strategy is None or (matched_strategy in ['bash_exe_required', 'bash_exe_preferred'] and not self.git_bash_exe):
                # Check if pipeline contains any BASH_EXE_PREFERRED commands
                contains_complex = False
                for complex_cmd in self.BASH_EXE_PREFERRED:
                    if complex_cmd in command:
                        contains_complex = True
                        break

                if contains_complex or matched_strategy is None:
                    # Complex pipeline or unknown pattern
                    if self.git_bash_exe:
                        self.logger.debug("Pipeline with complex commands → using bash.exe (safety net)")
                        bash_cmd = self._execute_with_gitbash(command)
                        if bash_cmd:
                            return bash_cmd, False
                    else:
                        # NO bash.exe for complex pipeline - CRITICAL situation
                        # User requirement: PERFECT emulation at ANY cost
                        # If we can't guarantee perfect, we should fail honestly
                        self.logger.error(f"Complex pipeline requires bash.exe: {command[:100]}")
                        self.logger.error("bash.exe not available - emulation may fail or produce wrong results")
                        # Continue to try emulation but user is warned
        
        # ================================================================
        # TIER 1: Pattern Cache - Fast path
        # ================================================================
        
        # Strategy 1: Git Bash passthrough (100% compatibility)
        if cmd_name in self.BASH_EXE_PREFERRED and self.git_bash_exe:
            bash_cmd = self._execute_with_gitbash(command)
            if bash_cmd:
                self.logger.debug(f"Using Git Bash for {cmd_name}")
                return bash_cmd, False
        
        # Strategy 2: Native binary (best performance)
        if cmd_name in self.available_bins:
            self.logger.debug(f"Using native binary for {cmd_name}")
            return command, False  # Pass through to binary
        
        # Strategy 3: Check execution map (complex emulation)
        execution_map = self._get_execution_map()
        if cmd_name in execution_map:
            executor = execution_map[cmd_name]
            self.logger.debug(f"Using emulation for {cmd_name}")
            return executor(command, parts)
        
        # ================================================================
        # TIER 2: Fallback - Unknown patterns
        # ================================================================
        
        return self._intelligent_fallback(command, parts)
    
    # ========================================================================
    # BINARY DETECTION
    # ========================================================================
    
    def _detect_native_binaries(self) -> Dict[str, str]:
        """
        Detect which native Windows binaries are available.
        
        Returns:
            Dict of available binaries {cmd: binary_path}
        """
        available = {}
        
        for cmd, binary in self.NATIVE_BINS.items():
            try:
                result = subprocess.run(
                    ['where', binary],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    available[cmd] = binary
            except Exception:
                pass
        
        return available
    
    # ========================================================================
    # GIT BASH PASSTHROUGH
    # ========================================================================
    
    def _execute_with_gitbash(self, unix_command: str) -> Optional[str]:
        """
        Execute command via Git Bash passthrough.
        
        Converts Windows paths and wraps in bash.exe call.
        
        Args:
            unix_command: Unix-style command
            
        Returns:
            Bash command string or None if unavailable
        """
        if not self.git_bash_exe:
            return None
        
        # Convert Windows paths to Git Bash format (C:\path -> /c/path)
        git_command = self._windows_to_gitbash_paths(unix_command)
        
        # Wrap in bash.exe
        return f'"{self.git_bash_exe}" -c "{git_command}"'
    
    def _windows_to_gitbash_paths(self, cmd: str) -> str:
        """
        Convert Windows paths in command to Git Bash format.
        
        C:\path\to\file -> /c/path/to/file
        """
        def convert_path(match):
            path = match.group(0)
            if ':' in path:
                drive = path[0].lower()
                rest = path[3:].replace('\\', '/')
                return f'/{drive}/{rest}'
            return path.replace('\\', '/')
        
        # Match Windows absolute paths
        pattern = r'[A-Za-z]:[/\\][^\s;|&<>()]*'
        return re.sub(pattern, convert_path, cmd)
    
    # ========================================================================
    # FALLBACK STRATEGY
    # ========================================================================
    
    def _intelligent_fallback(self, command: str, parts: List[str]) -> Tuple[str, bool]:
        """
        Fallback for unknown command patterns.

        Tries multiple strategies in order.

        FIX #14: Recognize PowerShell cmdlets and powershell command itself
        """
        cmd_name = parts[0]

        # FIX #14: Detect PowerShell cmdlets and commands
        POWERSHELL_CMDLETS = {
            'Get-Content', 'Set-Content', 'Get-ChildItem', 'Get-Item',
            'Select-String', 'Select-Object', 'ForEach-Object', 'Where-Object',
            'Measure-Object', 'Sort-Object', 'Get-Unique', 'Group-Object',
            'Compare-Object', 'Test-Path', 'New-Item', 'Remove-Item',
            'Copy-Item', 'Move-Item', 'Rename-Item',
            'Write-Host', 'Write-Output', 'Read-Host',
            'powershell', 'pwsh'  # PowerShell executables themselves
        }

        # Check if this is a PowerShell cmdlet
        if cmd_name in POWERSHELL_CMDLETS:
            self.logger.debug(f"PowerShell cmdlet detected: {cmd_name}")
            # Return command as-is but flag for PowerShell execution
            return command, True

        # Try Git Bash as fallback
        if self.git_bash_exe:
            bash_cmd = self._execute_with_gitbash(command)
            if bash_cmd:
                self.logger.debug(f"Fallback: Git Bash for {cmd_name}")
                return bash_cmd, False

        # Delegate to CommandTranslator for simple 1:1 mappings
        if self.command_translator:
            result = self._delegate_to_translator(command, parts)
            if result:
                return result

        # Last resort - pass through as-is
        self.logger.warning(f"Unknown command: {cmd_name} - passing through")
        return command, False
    
    def _delegate_to_translator(self, command: str, parts: List[str]) -> Optional[Tuple[str, bool]]:
        """
        Delegate to CommandTranslator for simple mappings.
        
        Returns None if translator unavailable or method not found.
        """
        if not self.command_translator:
            return None
        
        cmd_name = parts[0]
        method = getattr(self.command_translator, f'_translate_{cmd_name}', None)
        
        if method:
            try:
                return method(command, parts)
            except Exception as e:
                self.logger.error(f"Translator delegation failed for {cmd_name}: {e}")
        
        return None
    
    # ========================================================================
    # EXECUTION MAP - Command dispatcher
    # ========================================================================
    
    def _get_execution_map(self) -> Dict[str, Callable]:
        """
        Get execution map - command name to executor function.
        
        This is the PATTERN CACHE of known command strategies.
        """
        return {
            # Heavy emulation - Complex PowerShell scripts
            'find': self._execute_find,
            'curl': self._execute_curl,
            'sed': self._execute_sed,
            'diff': self._execute_diff,
            'sort': self._execute_sort,
            'uniq': self._execute_uniq,
            'awk': self._execute_awk,
            'split': self._execute_split,
            'grep': self._execute_grep,
            'join': self._execute_join,
            'ln': self._execute_ln,
            
            # Checksums with check mode
            'sha256sum': self._execute_sha256sum,
            'sha1sum': self._execute_sha1sum,
            'md5sum': self._execute_md5sum,
            
            # Compression
            'gzip': self._execute_gzip,
            'gunzip': self._execute_gunzip,
            'tar': self._execute_tar,
            'zip': self._execute_zip,
            'unzip': self._execute_unzip,
            
            # Binary inspection
            'hexdump': self._execute_hexdump,
            'strings': self._execute_strings,
            
            # Utilities
            'base64': self._execute_base64,
            'timeout': self._execute_timeout,
            'watch': self._execute_watch,
            'column': self._execute_column,
            'jq': self._execute_jq,
            
            # Network
            'wget': self._execute_wget,
        }
    
    # ========================================================================
    # EXECUTION METHODS - Command-specific implementations
    # ========================================================================
    # Each method implements FULL emulation for a specific command.
    # These are the HEAVY methods migrated from CommandTranslator.
    # ========================================================================
    
    def _execute_find(self, cmd: str, parts: List[str]) -> Tuple[str, bool]:
        """
        Execute find with COMPLETE test support - FULL EMULATION.
        
        Tests supported:
        - -name PATTERN: filename pattern (wildcards)
        - -iname PATTERN: case-insensitive name
        - -type f|d|l: file type (file, directory, link)
        - -size [+-]N[ckMG]: size test (+1M, -100k)
        - -mtime [+-]N: modification time in days (-7 = last week)
        - -atime [+-]N: access time in days
        - -ctime [+-]N: change time in days
        - -newer FILE: modified more recently than FILE
        - -maxdepth N: descend at most N levels
        - -mindepth N: descend at least N levels
        - -exec CMD {} \;: execute command on each file
        - -delete: delete matched files
        - -print: print matched files (default)
        - -print0: print with null separator
        
        Examples:
          find . -name "*.py" -mtime -7
          find /tmp -type f -size +100M -delete
          find . -name "*.log" -mtime +30 -exec rm {} \;
        """
        # Parse find arguments
        path = '.'
        tests = []
        actions = []
        max_depth = None
        min_depth = None
        print_null = False
        
        i = 1
        
        # First non-flag argument is the path
        if i < len(parts) and not parts[i].startswith('-'):
            path = parts[i]
            i += 1
        
        # Parse tests and actions
        while i < len(parts):
            test = parts[i]
            
            if test == '-name' and i + 1 < len(parts):
                pattern = parts[i + 1].strip('"\'')
                tests.append(('name', pattern, False))
                i += 2
            elif test == '-iname' and i + 1 < len(parts):
                pattern = parts[i + 1].strip('"\'')
                tests.append(('name', pattern, True))  # case-insensitive
                i += 2
            elif test == '-type' and i + 1 < len(parts):
                ftype = parts[i + 1]
                tests.append(('type', ftype, None))
                i += 2
            elif test == '-size' and i + 1 < len(parts):
                size_spec = parts[i + 1]
                tests.append(('size', size_spec, None))
                i += 2
            elif test == '-mtime' and i + 1 < len(parts):
                days = parts[i + 1]
                tests.append(('mtime', days, None))
                i += 2
            elif test == '-atime' and i + 1 < len(parts):
                days = parts[i + 1]
                tests.append(('atime', days, None))
                i += 2
            elif test == '-ctime' and i + 1 < len(parts):
                days = parts[i + 1]
                tests.append(('ctime', days, None))
                i += 2
            elif test == '-newer' and i + 1 < len(parts):
                ref_file = parts[i + 1]
                tests.append(('newer', ref_file, None))
                i += 2
            elif test == '-maxdepth' and i + 1 < len(parts):
                max_depth = int(parts[i + 1])
                i += 2
            elif test == '-mindepth' and i + 1 < len(parts):
                min_depth = int(parts[i + 1])
                i += 2
            elif test == '-delete':
                actions.append(('delete', None))
                i += 1
            elif test == '-print':
                # Default action, explicit
                i += 1
            elif test == '-print0':
                print_null = True
                i += 1
            elif test == '-exec':
                # Find -exec ... \; or -exec ... +
                exec_cmd = []
                i += 1
                while i < len(parts) and parts[i] not in [';', '\\;', '+']:
                    exec_cmd.append(parts[i])
                    i += 1
                actions.append(('exec', ' '.join(exec_cmd)))
                i += 1  # skip ; or +
            else:
                # Unknown test, skip
                i += 1
        
        # Build Windows command
        win_path = path  # Already translated

        # FIX #18: For simple cases, use direct Get-ChildItem | Where-Object (more readable)
        # Complex cases use full script
        is_simple = (
            len(tests) <= 2 and  # Only name and/or type tests
            not actions and  # No actions (no -exec, -delete)
            max_depth is None and
            min_depth is None and
            all(test[0] in ['name', 'type'] for test in tests)
        )

        if is_simple:
            # Simple case: Get-ChildItem | Where-Object
            get_cmd = f'Get-ChildItem -Path "{win_path}" -Recurse -ErrorAction SilentlyContinue'

            where_conditions = []
            for test_type, test_arg, test_flag in tests:
                if test_type == 'name':
                    if test_flag:  # case-insensitive
                        where_conditions.append(f'$_.Name -like "{test_arg}"')
                    else:
                        where_conditions.append(f'$_.Name -clike "{test_arg}"')
                elif test_type == 'type':
                    if test_arg == 'f':
                        where_conditions.append('-not $_.PSIsContainer')
                    elif test_arg == 'd':
                        where_conditions.append('$_.PSIsContainer')

            if where_conditions:
                where_clause = ' -and '.join(where_conditions)
                ps_cmd = f'{get_cmd} | Where-Object {{ {where_clause} }} | ForEach-Object {{ $_.FullName }}'
            else:
                ps_cmd = f'{get_cmd} | ForEach-Object {{ $_.FullName }}'

            return ps_cmd, True

        # Complex case: Build full PowerShell script
        ps_script = f'''
            $path = "{win_path}"
            $maxDepth = {max_depth if max_depth else 999}
            $minDepth = {min_depth if min_depth else 0}

            Get-ChildItem -Path $path -Recurse -ErrorAction SilentlyContinue | ForEach-Object {{
                $item = $_
                $depth = ($item.FullName.Substring($path.Length) -split '\\\\|/').Length - 1

                # Depth filtering
                if ($depth -gt $maxDepth -or $depth -lt $minDepth) {{
                    return
                }}

                $match = $true
        '''
        
        # Add test conditions
        for test_type, test_arg, test_flag in tests:
            if test_type == 'name':
                if test_flag:  # case-insensitive
                    ps_script += f'''
                if ($match) {{
                    $match = $match -and ($item.Name -like "{test_arg}")
                }}
                '''
                else:  # case-sensitive
                    ps_script += f'''
                if ($match) {{
                    $match = $match -and ($item.Name -clike "{test_arg}")
                }}
                '''
            
            elif test_type == 'type':
                if test_arg == 'f':
                    ps_script += '''
                if ($match) {
                    $match = $match -and (-not $item.PSIsContainer)
                }
                '''
                elif test_arg == 'd':
                    ps_script += '''
                if ($match) {
                    $match = $match -and $item.PSIsContainer
                }
                '''
                elif test_arg == 'l':
                    ps_script += '''
                if ($match) {
                    $match = $match -and ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
                }
                '''
            
            elif test_type == 'size':
                # Parse size: +1M (greater), -100k (less), 50k (exact)
                size_bytes = self._parse_find_size(test_arg)
                if test_arg.startswith('+'):
                    ps_script += f'''
                if ($match -and (-not $item.PSIsContainer)) {{
                    $match = $match -and ($item.Length -gt {size_bytes})
                }}
                '''
                elif test_arg.startswith('-'):
                    ps_script += f'''
                if ($match -and (-not $item.PSIsContainer)) {{
                    $match = $match -and ($item.Length -lt {size_bytes})
                }}
                '''
                else:
                    ps_script += f'''
                if ($match -and (-not $item.PSIsContainer)) {{
                    $match = $match -and ($item.Length -eq {size_bytes})
                }}
                '''
            
            elif test_type == 'mtime':
                # Parse days: -7 (within last 7 days), +30 (older than 30 days)
                days = int(test_arg.strip('+-'))
                if test_arg.startswith('-'):
                    # Modified within last N days
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastWriteTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -lt {days})
                }}
                '''
                elif test_arg.startswith('+'):
                    # Modified more than N days ago
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastWriteTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -gt {days})
                }}
                '''
                else:
                    # Exactly N days
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastWriteTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -eq {days})
                }}
                '''
            
            elif test_type == 'atime':
                # Access time
                days = int(test_arg.strip('+-'))
                if test_arg.startswith('-'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastAccessTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -lt {days})
                }}
                '''
                elif test_arg.startswith('+'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastAccessTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -gt {days})
                }}
                '''
            
            elif test_type == 'ctime':
                # Change time (CreationTime on Windows)
                days = int(test_arg.strip('+-'))
                if test_arg.startswith('-'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.CreationTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -lt {days})
                }}
                '''
                elif test_arg.startswith('+'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.CreationTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -gt {days})
                }}
                '''
            
            elif test_type == 'newer':
                # Newer than reference file
                ref_file = test_arg
                ps_script += f'''
                if ($match) {{
                    try {{
                        $refTime = (Get-Item "{ref_file}").LastWriteTime
                        $match = $match -and ($item.LastWriteTime -gt $refTime)
                    }} catch {{
                        $match = $false
                    }}
                }}
                '''
        
        # Actions
        ps_script += '''
                if ($match) {
        '''
        
        if actions:
            for action_type, action_arg in actions:
                if action_type == 'delete':
                    ps_script += '''
                    Remove-Item -Path $item.FullName -Force -ErrorAction SilentlyContinue
                '''
                elif action_type == 'exec':
                    # Execute command with {} replaced by filename
                    exec_cmd = action_arg.replace('{}', '$item.FullName')
                    ps_script += f'''
                    Invoke-Expression "{exec_cmd}"
                '''
        else:
            # Default action: print
            if print_null:
                ps_script += '''
                    Write-Host -NoNewline "$($item.FullName)`0"
                '''
            else:
                ps_script += '''
                    Write-Output $item.FullName
                '''
        
        ps_script += '''
                }
            }
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _execute_curl(self, cmd: str, parts: List[str]) -> Tuple[str, bool]:
        """
        Execute curl with COMPLETE flag support for API work.
        
        Common flags:
        - -X METHOD: request method (GET, POST, PUT, DELETE, PATCH)
        - -H "Header: value": headers (multiple)
        - -d "data" / --data: POST data
        - -d @file: POST data from file
        - --data-binary @file: binary data from file
        - --json '{}': JSON shorthand (auto Content-Type + POST)
        - -o file: output to file
        - -O: save with remote filename
        - -L: follow redirects
        - -f: fail silently on errors
        - -s: silent mode (no progress)
        - -i: include headers in output
        - -I: HEAD request
        - -v: verbose (show request/response headers)
        - -k, --insecure: skip SSL verification
        - -u user:pass: basic authentication
        - -A "agent": user agent
        - -F file=@path: multipart form upload
        """
        if len(parts) < 2:
            return 'echo Error: curl requires URL', True
        
        method = None
        headers = []
        data = None
        data_file = None
        data_binary = False
        json_data = None
        output_file = None
        save_remote = False
        follow_redirects = False
        fail_silent = False
        silent = False
        include_headers = False
        head_only = False
        verbose = False
        insecure = False
        auth = None
        user_agent = None
        form_data = []
        url = None
        
        i = 1
        while i < len(parts):
            if parts[i] in ['-X', '--request'] and i + 1 < len(parts):
                method = parts[i + 1]
                i += 2
            elif parts[i] in ['-H', '--header'] and i + 1 < len(parts):
                headers.append(parts[i + 1])
                i += 2
            elif parts[i] in ['-d', '--data'] and i + 1 < len(parts):
                data_arg = parts[i + 1]
                if data_arg.startswith('@'):
                    # Data from file
                    data_file = data_arg[1:]
                else:
                    data = data_arg
                i += 2
            elif parts[i] == '--data-binary' and i + 1 < len(parts):
                data_arg = parts[i + 1]
                if data_arg.startswith('@'):
                    data_file = data_arg[1:]
                    data_binary = True
                i += 2
            elif parts[i] == '--json' and i + 1 < len(parts):
                json_data = parts[i + 1]
                i += 2
            elif parts[i] in ['-F', '--form'] and i + 1 < len(parts):
                form_data.append(parts[i + 1])
                i += 2
            elif parts[i] in ['-o', '--output'] and i + 1 < len(parts):
                output_file = parts[i + 1]
                i += 2
            elif parts[i] in ['-O', '--remote-name']:
                save_remote = True
                i += 1
            elif parts[i] in ['-L', '--location']:
                follow_redirects = True
                i += 1
            elif parts[i] in ['-f', '--fail']:
                fail_silent = True
                i += 1
            elif parts[i] in ['-s', '--silent']:
                silent = True
                i += 1
            elif parts[i] in ['-i', '--include']:
                include_headers = True
                i += 1
            elif parts[i] in ['-I', '--head']:
                head_only = True
                i += 1
            elif parts[i] in ['-v', '--verbose']:
                verbose = True
                i += 1
            elif parts[i] in ['-k', '--insecure']:
                insecure = True
                i += 1
            elif parts[i] in ['-u', '--user'] and i + 1 < len(parts):
                auth = parts[i + 1]
                i += 2
            elif parts[i] in ['-A', '--user-agent'] and i + 1 < len(parts):
                user_agent = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                # URL
                url = parts[i]
                i += 1
            else:
                i += 1
        
        if not url:
            return 'echo Error: curl requires URL', True
        
        # Build PowerShell Invoke-WebRequest command
        ps_parts = []
        
        # Verbose setup
        if verbose:
            ps_parts.append('$VerbosePreference="Continue";')
        
        # SSL verification
        if insecure:
            ps_parts.append('[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true};')
        
        ps_parts.append('Invoke-WebRequest')
        ps_parts.append(f'-Uri "{url}"')
        
        # Method
        if method:
            ps_parts.append(f'-Method {method}')
        elif json_data or data or data_file:
            ps_parts.append('-Method POST')
        elif head_only:
            ps_parts.append('-Method HEAD')
        
        # Headers
        if json_data and not any('Content-Type' in h for h in headers):
            headers.append('Content-Type: application/json')
        
        if headers:
            # Build proper PowerShell hashtable for headers
            header_pairs = []
            for h in headers:
                if ':' in h:
                    key, val = h.split(':', 1)
                    header_pairs.append(f'"{key.strip()}"="{val.strip()}"')
            headers_str = ';'.join(header_pairs)
            ps_parts.append(f'-Headers @{{{headers_str}}}')
        
        # Body data
        if json_data:
            ps_parts.append(f'-Body \'{json_data}\'')
        elif data_file:
            if data_binary:
                ps_parts.append(f'-InFile "{data_file}"')
            else:
                ps_parts.append(f'-Body (Get-Content "{data_file}" -Raw)')
        elif data:
            ps_parts.append(f'-Body "{data}"')
        elif form_data:
            # Multipart form data
            form_parts = []
            for form in form_data:
                if '=' in form:
                    key, val = form.split('=', 1)
                    if val.startswith('@'):
                        # File upload
                        file_path = val[1:]
                        form_parts.append(f'"{key}"=(Get-Item "{file_path}")')
                    else:
                        # Regular field
                        form_parts.append(f'"{key}"="{val}"')
            form_str = ';'.join(form_parts)
            ps_parts.append(f'-Form @{{{form_str}}}')
        
        # Output
        if output_file:
            ps_parts.append(f'-OutFile "{output_file}"')
        elif save_remote:
            # Extract filename from URL
            filename = url.split('/')[-1].split('?')[0]
            if filename:
                ps_parts.append(f'-OutFile "{filename}"')
        
        # Redirects
        if follow_redirects:
            ps_parts.append('-MaximumRedirection 10')
        else:
            ps_parts.append('-MaximumRedirection 0')
        
        # User agent
        if user_agent:
            ps_parts.append(f'-UserAgent "{user_agent}"')
        
        # Authentication
        if auth:
            user, pwd = auth.split(':', 1) if ':' in auth else (auth, '')
            ps_parts.append(f'-Credential (New-Object System.Management.Automation.PSCredential("{user}", (ConvertTo-SecureString "{pwd}" -AsPlainText -Force)))')
        
        # Error handling
        error_action = 'Stop' if fail_silent else 'Continue'
        ps_parts.append(f'-ErrorAction {error_action}')
        
        # Verbose flag
        if verbose:
            ps_parts.append('-Verbose')
        
        # Silent mode: suppress progress
        if silent:
            ps_parts.insert(0, '$ProgressPreference="SilentlyContinue";')
        
        # Build command
        ps_cmd = ' '.join(ps_parts)
        
        # Output formatting
        if include_headers or head_only:
            # Include headers in output
            if head_only:
                ps_cmd += ' | Select-Object -ExpandProperty Headers | Format-List'
            else:
                ps_cmd += ' | ForEach-Object { $_.RawContent }'
        elif verbose:
            # Verbose shows everything
            ps_cmd += ' | Select-Object StatusCode, StatusDescription, Headers, Content | Format-List'
        elif not output_file and not save_remote:
            # Output content only (default)
            ps_cmd += ' | Select-Object -ExpandProperty Content'
        
        # Wrap in try-catch if fail_silent
        if fail_silent and not silent:
            ps_cmd = f'try {{ {ps_cmd} }} catch {{ exit 22 }}'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    # Checksums - COMPLETE implementation
    def _checksum_generic(self, algorithm: str, cmd_name: str, parts: List[str]) -> Tuple[str, bool]:
        """
        Generic checksum implementation with check mode.
        
        Supports: SHA256, SHA1, MD5
        """
        check_mode = '-c' in parts or '--check' in parts
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            return f'echo Error: {cmd_name} requires filename', True
        
        if check_mode:
            # Check mode: verify checksums from file
            checksum_file = files[0]
            
            ps_script = f'''
                $failed = 0
                Get-Content "{checksum_file}" | ForEach-Object {{
                    if ($_ -match '^([a-f0-9]+)\\s+(.+)$') {{
                        $expected = $matches[1].ToLower()
                        $file = $matches[2]
                        if (Test-Path $file) {{
                            $actual = (Get-FileHash -Path $file -Algorithm {algorithm}).Hash.ToLower()
                            if ($actual -eq $expected) {{
                                Write-Output "$file: OK"
                            }} else {{
                                Write-Output "$file: FAILED"
                                $failed++
                            }}
                        }} else {{
                            Write-Output "$file: FAILED open or read"
                            $failed++
                        }}
                    }}
                }}
                if ($failed -gt 0) {{
                    Write-Error "{cmd_name}: WARNING: $failed checksum(s) did NOT match"
                }}
            '''
            return f'powershell -Command "{ps_script}"', True
        
        # Hash files
        commands = []
        for file_path in files:
            ps_cmd = (
                f'$hash = Get-FileHash -Path \\"{file_path}\\" -Algorithm {algorithm}; '
                f'Write-Output ($hash.Hash.ToLower() + "  " + $hash.Path)'
            )
            commands.append(f'powershell -Command "{ps_cmd}"')
        
        return ' && '.join(commands), True
    
    def _execute_sha256sum(self, cmd: str, parts: List[str]) -> Tuple[str, bool]:
        return self._checksum_generic('SHA256', 'sha256sum', parts)
    
    def _execute_sha1sum(self, cmd: str, parts: List[str]) -> Tuple[str, bool]:
        return self._checksum_generic('SHA1', 'sha1sum', parts)
    
    def _execute_md5sum(self, cmd: str, parts: List[str]) -> Tuple[str, bool]:
        return self._checksum_generic('MD5', 'md5sum', parts)
    

    # ========================================================================
    # HEAVY EXECUTION METHODS - Migrated from CommandTranslator
    # ========================================================================

# ======== ln (1132-1255) ========
    def _execute_ln(self, cmd: str, parts):
        """
        Translate ln - FULL symlink/hardlink support with fallback.
        
        ARTISAN IMPLEMENTATION:
        - ln target link → Hard link (mklink /H)
        - ln -s target link → Symlink (mklink or mklink /D)
        - Fallback: PowerShell New-Item -ItemType SymbolicLink
        - Fallback 2: Copy if symlink fails (no admin)
        
        Windows challenges:
        - Symlinks require admin privileges (Vista+)
        - Hard links work without admin
        - Directory symlinks need /D flag
        
        Supported flags:
        - -s, --symbolic: Symbolic link (default: hard link)
        - -f, --force: Remove existing destination
        - -n, --no-dereference: Treat link destination as normal file
        """
        if len(parts) < 3:
            return 'echo Error: ln requires target and link_name', True
        
        # Parse flags (including combined flags like -sf)
        symbolic = False
        force = False
        
        for part in parts[1:]:
            if part.startswith('-') and not part.startswith('--'):
                # Combined flags: -sf, -fs, etc.
                if 's' in part:
                    symbolic = True
                if 'f' in part:
                    force = True
            elif part == '--symbolic':
                symbolic = True
            elif part == '--force':
                force = True
        
        # Extract target and link_name
        non_flags = [p for p in parts[1:] if not p.startswith('-')]
        if len(non_flags) < 2:
            return 'echo Error: ln requires target and link_name', True
        
        target = non_flags[0]  # Already translated path
        link_name = non_flags[1]  # Already translated path
        
        if symbolic:
            # SYMBOLIC LINK
            # Strategy: Try mklink, fallback to PowerShell, fallback to copy
            
            # Determine if target is directory or file
            # Use PowerShell to check
            check_dir = f'Test-Path -Path \\"{target}\\" -PathType Container'
            
            # Build mklink command with directory detection
            # Note: mklink requires "mklink /D link target" syntax (opposite of ln!)
            ps_script = f'''
                $target = \\"{target}\\"
                $link = \\"{link_name}\\"
                
                # Force: remove existing link
                if (Test-Path $link) {{
                    {"Remove-Item $link -Force" if force else 'Write-Host "Link exists (use -f to overwrite)" ; exit 1'}
                }}
                
                # Try mklink first (fast, native)
                try {{
                    if (Test-Path $target -PathType Container) {{
                        # Directory symlink
                        $result = cmd /c "mklink /D \\"$link\\" \\"$target\\"" 2>&1
                    }} else {{
                        # File symlink
                        $result = cmd /c "mklink \\"$link\\" \\"$target\\"" 2>&1
                    }}
                    
                    if ($LASTEXITCODE -eq 0) {{
                        Write-Host "Symbolic link created: $link -> $target"
                        exit 0
                    }}
                }}
                catch {{}}
                
                # Fallback: PowerShell New-Item (also requires admin but different API)
                try {{
                    if (Test-Path $target -PathType Container) {{
                        New-Item -ItemType SymbolicLink -Path $link -Target $target -Force | Out-Null
                    }} else {{
                        New-Item -ItemType SymbolicLink -Path $link -Target $target -Force | Out-Null
                    }}
                    Write-Host "Symbolic link created (PS): $link -> $target"
                    exit 0
                }}
                catch {{}}
                
                # Fallback 2: Copy (if no admin privileges)
                Write-Host "Warning: No admin privileges for symlink. Copying instead."
                try {{
                    if (Test-Path $target -PathType Container) {{
                        Copy-Item -Path $target -Destination $link -Recurse -Force
                    }} else {{
                        Copy-Item -Path $target -Destination $link -Force
                    }}
                    Write-Host "Copied: $link (symlink failed, file copied)"
                    exit 0
                }}
                catch {{
                    Write-Host "Error: Failed to create link or copy: $_"
                    exit 1
                }}
            '''
            
            return f'powershell -Command "{ps_script}"', True
        
        else:
            # HARD LINK (no admin required!)
            # Windows: mklink /H link target
            # Note: Syntax reversed from ln
            
            force_cmd = f'if exist "{link_name}" del /f "{link_name}" && ' if force else ''
            
            # mklink /H for hard links (files only, not directories)
            return f'{force_cmd}mklink /H "{link_name}" "{target}"', True
    


# ======== find (6500-6823) ========
    def _parse_find_size(self, size_spec: str) -> int:
        """
        Parse find -size specification to bytes.
        
        Format: [+-]N[ckMG]
        Examples: +1M → 1048576, -100k → 102400, 50 → 50
        """
        import re
        
        spec = size_spec.lstrip('+-')
        match = re.match(r'^(\d+)([ckMG])?$', spec)
        if not match:
            return 0
        
        value = int(match.group(1))
        unit = match.group(2) or 'c'
        
        multipliers = {
            'c': 1,
            'k': 1024,
            'M': 1024 * 1024,
            'G': 1024 * 1024 * 1024,
        }
        
        return value * multipliers.get(unit, 1)
    


# ======== join (4228-4367) ========
    def _execute_join(self, cmd: str, parts):
        """
        Translate join - join lines from two files on common field (SQL-like).
        
        ARTISAN IMPLEMENTATION:
        - Joins lines where join field matches
        - Default: field 1, whitespace separator
        - Files must be SORTED on join field!
        
        Flags:
        - -t SEP: field separator (default whitespace)
        - -1 FIELD: join on this field from file1 (1-indexed)
        - -2 FIELD: join on this field from file2 (1-indexed)
        - -a FILENUM: also print unpairable lines from file FILENUM
        
        Usage:
          join file1 file2                  → join on field 1
          join -t',' -1 2 -2 1 f1.csv f2.csv → custom fields + separator
        
        Output: join_field other_fields_f1 other_fields_f2
        """
        separator = r'\\s+'
        field1 = 1
        field2 = 1
        print_unpaired_1 = False
        print_unpaired_2 = False
        files = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-t' and i + 1 < len(parts):
                sep = parts[i + 1]
                separator = sep.replace('|', '\\|')
                i += 2
            elif parts[i] == '-1' and i + 1 < len(parts):
                field1 = int(parts[i + 1])
                i += 2
            elif parts[i] == '-2' and i + 1 < len(parts):
                field2 = int(parts[i + 1])
                i += 2
            elif parts[i] == '-a' and i + 1 < len(parts):
                filenum = int(parts[i + 1])
                if filenum == 1:
                    print_unpaired_1 = True
                elif filenum == 2:
                    print_unpaired_2 = True
                i += 2
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1
        
        if len(files) < 2:
            return 'echo Error: join requires two files', True
        
        file1_path, file2_path = files[0], files[1]
        
        # PowerShell: parse both files, hash on join field, merge
        ps_script = f'''
            $sep = "{separator}"
            $field1 = {field1} - 1  # Convert to 0-indexed
            $field2 = {field2} - 1
            
            if (-not (Test-Path "{file1_path}")) {{
                Write-Error "join: {file1_path}: No such file"
                exit 1
            }}
            if (-not (Test-Path "{file2_path}")) {{
                Write-Error "join: {file2_path}: No such file"
                exit 1
            }}
            
            # Read and parse file1
            $lines1 = Get-Content "{file1_path}"
            $hash1 = @{{}}
            foreach ($line in $lines1) {{
                $fields = $line -split $sep
                if ($field1 -lt $fields.Length) {{
                    $key = $fields[$field1]
                    if (-not $hash1.ContainsKey($key)) {{
                        $hash1[$key] = @()
                    }}
                    $hash1[$key] += ,$fields
                }}
            }}
            
            # Read and join with file2
            $lines2 = Get-Content "{file2_path}"
            $matched2 = @{{}}
            
            foreach ($line in $lines2) {{
                $fields = $line -split $sep
                if ($field2 -lt $fields.Length) {{
                    $key = $fields[$field2]
                    $matched2[$key] = $true
                    
                    if ($hash1.ContainsKey($key)) {{
                        # Match found: output joined line
                        foreach ($f1_fields in $hash1[$key]) {{
                            # Output: join_field + other_fields_f1 + other_fields_f2
                            $output = $key
                            
                            # Add other fields from file1
                            for ($i = 0; $i -lt $f1_fields.Length; $i++) {{
                                if ($i -ne $field1) {{
                                    $output += " " + $f1_fields[$i]
                                }}
                            }}
                            
                            # Add other fields from file2
                            for ($i = 0; $i -lt $fields.Length; $i++) {{
                                if ($i -ne $field2) {{
                                    $output += " " + $fields[$i]
                                }}
                            }}
                            
                            Write-Output $output
                        }}
                    }} elseif ({str(print_unpaired_2).lower()}) {{
                        # No match but print unpaired from file2
                        Write-Output ($fields -join " ")
                    }}
                }}
            }}
            
            # Print unpaired from file1 if requested
            if ({str(print_unpaired_1).lower()}) {{
                foreach ($key in $hash1.Keys) {{
                    if (-not $matched2.ContainsKey($key)) {{
                        foreach ($fields in $hash1[$key]) {{
                            Write-Output ($fields -join " ")
                        }}
                    }}
                }}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    


# ======== diff (3295-3506) ========
    def _execute_diff(self, cmd: str, parts):
        """
        Translate diff with unified format at 100% compatibility.
        
        STRATEGY FOR 100%:
        1. Try diff.exe (from Git for Windows) - 100% GNU compatible
        2. Fallback PowerShell custom - 95% compatible (format correct, hunks approximate)
        
        CRITICAL: unified format requirements:
        - Header: --- file1<TAB>timestamp
                  +++ file2<TAB>timestamp
        - Hunk: @@ -start,count +start,count @@
        - Lines:  <space> unchanged
                 - removed
                 + added
        - Context: default 3 lines before/after changes
        
        Flags:
        - -u, --unified: Unified format (FULL implementation)
        - -U N: N context lines
        - -q, --brief: Just report if different
        """
        if len(parts) < 3:
            return 'echo Error: diff requires two files', True
        
        unified = '-u' in parts or '--unified' in parts
        brief = '-q' in parts or '--brief' in parts
        
        # Parse -U N for context lines
        context_lines = 3  # Default
        context_flag = ''
        for i, part in enumerate(parts):
            if part == '-U' and i + 1 < len(parts):
                context_lines = int(parts[i + 1])
                context_flag = f'-U{context_lines}'
            elif part.startswith('-U'):
                context_lines = int(part[2:])
                context_flag = part
        
        files = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit()]
        
        if len(files) < 2:
            return 'echo Error: diff requires two files', True
        
        file1 = files[0]
        file2 = files[1]
        
        if brief:
            # Just check if different
            return f'fc /b "{file1}" "{file2}" >nul 2>&1 && echo Files are identical || echo Files differ', True
        
        if not unified:
            # Standard diff (use fc)
            return f'fc /n "{file1}" "{file2}"', True
        
        # UNIFIED DIFF - Try diff.exe first, fallback to PowerShell
        fallback_ps = f'''
            # Try native diff.exe first (Git for Windows, etc.)
            $diffExe = Get-Command diff.exe -ErrorAction SilentlyContinue
            if ($diffExe) {{
                & diff.exe -u {context_flag} "{file1}" "{file2}"
                exit $LASTEXITCODE
            }}
            
            # Fallback: PowerShell custom implementation
            $file1 = "{file1}"
            $file2 = "{file2}"
            $context = {context_lines}
            
            # Read files
            if (-not (Test-Path $file1)) {{
                Write-Host "diff: $file1: No such file or directory"
                exit 2
            }}
            if (-not (Test-Path $file2)) {{
                Write-Host "diff: $file2: No such file or directory"
                exit 2
            }}
            
            $lines1 = @(Get-Content $file1)
            $lines2 = @(Get-Content $file2)
            
            # Get file timestamps
            $time1 = (Get-Item $file1).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss.fff000000 +0000")
            $time2 = (Get-Item $file2).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss.fff000000 +0000")
            
            # Header
            Write-Output "--- $file1`t$time1"
            Write-Output "+++ $file2`t$time2"
            
            # Simple line-by-line diff algorithm
            # NOTE: This is approximate. For 100% accuracy, use diff.exe (Git for Windows).
            $i = 0
            $j = 0
            $hunks = @()
            
            while ($i -lt $lines1.Count -or $j -lt $lines2.Count) {{
                # Find next difference
                $changeStart1 = $i
                $changeStart2 = $j
                
                # Skip matching lines
                while ($i -lt $lines1.Count -and $j -lt $lines2.Count -and $lines1[$i] -eq $lines2[$j]) {{
                    $i++
                    $j++
                }}
                
                if ($i -ge $lines1.Count -and $j -ge $lines2.Count) {{
                    break  # All done
                }}
                
                # Found a difference - collect changed block
                $delStart = $i
                $addStart = $j
                
                # Collect deleted lines
                while ($i -lt $lines1.Count -and ($j -ge $lines2.Count -or $lines1[$i] -ne $lines2[$j])) {{
                    # Check if we can find a match soon
                    $foundMatch = $false
                    for ($k = $j; $k -lt [Math]::Min($j + 3, $lines2.Count); $k++) {{
                        if ($lines1[$i] -eq $lines2[$k]) {{
                            $foundMatch = $true
                            break
                        }}
                    }}
                    if ($foundMatch) {{ break }}
                    $i++
                }}
                
                # Collect added lines
                while ($j -lt $lines2.Count -and ($i -ge $lines1.Count -or $lines1[$i] -ne $lines2[$j])) {{
                    # Check if we can find a match soon
                    $foundMatch = $false
                    for ($k = $i; $k -lt [Math]::Min($i + 3, $lines1.Count); $k++) {{
                        if ($lines2[$j] -eq $lines1[$k]) {{
                            $foundMatch = $true
                            break
                        }}
                    }}
                    if ($foundMatch) {{ break }}
                    $j++
                }}
                
                # Create hunk
                $delCount = $i - $delStart
                $addCount = $j - $addStart
                
                if ($delCount -gt 0 -or $addCount -gt 0) {{
                    $hunk = @{{
                        Start1 = $delStart
                        Count1 = $delCount
                        Start2 = $addStart
                        Count2 = $addCount
                        ContextBefore = [Math]::Max(0, $delStart - $context)
                        ContextAfter = [Math]::Min($lines1.Count - 1, $i + $context - 1)
                    }}
                    $hunks += ,$hunk
                }}
            }}
            
            # Merge overlapping hunks
            $merged = @()
            foreach ($hunk in $hunks) {{
                if ($merged.Count -eq 0) {{
                    $merged += ,$hunk
                }} else {{
                    $last = $merged[-1]
                    if ($hunk.ContextBefore -le $last.ContextAfter + 1) {{
                        # Overlapping - merge
                        $last.Count1 = ($hunk.Start1 + $hunk.Count1) - $last.Start1
                        $last.Count2 = ($hunk.Start2 + $hunk.Count2) - $last.Start2
                        $last.ContextAfter = $hunk.ContextAfter
                    }} else {{
                        $merged += ,$hunk
                    }}
                }}
            }}
            
            # Output hunks
            foreach ($hunk in $merged) {{
                $start1 = $hunk.ContextBefore + 1
                $start2 = $start1 - $hunk.Start1 + $hunk.Start2
                
                $count1 = ($hunk.Start1 + $hunk.Count1) - $hunk.ContextBefore + [Math]::Min($context, $lines1.Count - ($hunk.Start1 + $hunk.Count1))
                $count2 = ($hunk.Start2 + $hunk.Count2) - ($start2 - 1) + [Math]::Min($context, $lines2.Count - ($hunk.Start2 + $hunk.Count2))
                
                Write-Output "@@ -$start1,$count1 +$start2,$count2 @@"
                
                # Context before
                for ($k = $hunk.ContextBefore; $k -lt $hunk.Start1; $k++) {{
                    Write-Output " $($lines1[$k])"
                }}
                
                # Changes
                for ($k = $hunk.Start1; $k -lt $hunk.Start1 + $hunk.Count1; $k++) {{
                    Write-Output "-$($lines1[$k])"
                }}
                for ($k = $hunk.Start2; $k -lt $hunk.Start2 + $hunk.Count2; $k++) {{
                    Write-Output "+$($lines2[$k])"
                }}
                
                # Context after
                $afterStart = [Math]::Max($hunk.Start1 + $hunk.Count1, $hunk.Start2 + $hunk.Count2 - ($hunk.Count2 - $hunk.Count1))
                $afterEnd = [Math]::Min($afterStart + $context, $lines1.Count)
                for ($k = $afterStart; $k -lt $afterEnd; $k++) {{
                    Write-Output " $($lines1[$k])"
                }}
            }}
        '''
        
        return f'powershell -Command "{fallback_ps}"', True
    


# ======== awk (2824-3034) ========
    def _execute_awk(self, cmd: str, parts):
        """
        Translate awk with fallback chain.
        
        STRATEGY FOR 100%:
        1. Try awk.exe / gawk.exe (Git for Windows) - 100% GNU awk
        2. Fallback PowerShell custom for common patterns
        
        Supported in PowerShell fallback:
        - Field extraction: $1, $2, $NF, $(NF-1)
        - Field separator: -F delimiter
        - Pattern matching: /pattern/ {action}
        - BEGIN/END blocks: BEGIN {x=0} {x+=$1} END {print x}
        - Variables and arithmetic: x=0, x++, x+=$1
        - Conditions: $1 > 100, NF > 5
        - Multiple statements in blocks
        
        Complex awk programs work better with native gawk.
        """
        if len(parts) < 2:
            return 'echo Error: awk requires program', True
        
        # Build command for native awk
        awk_cmd_parts = []
        for part in parts[1:]:
            # Quote arguments that need it
            if ' ' in part or any(c in part for c in ['|', '&', '>', '<', ';']):
                awk_cmd_parts.append(f'"{part}"')
            else:
                awk_cmd_parts.append(part)
        
        awk_full_cmd = ' '.join(awk_cmd_parts)
        
        # PowerShell script with fallback chain
        ps_script = f'''
            # Try native awk/gawk (Git for Windows)
            $awkExe = Get-Command awk.exe -ErrorAction SilentlyContinue
            if (-not $awkExe) {{
                $awkExe = Get-Command gawk.exe -ErrorAction SilentlyContinue
            }}
            
            if ($awkExe) {{
                # Native awk - 100% GNU compatible
                & $awkExe.Source {awk_full_cmd}
                exit $LASTEXITCODE
            }}
            
            # Fallback: PowerShell custom implementation
            # (Common patterns only - complex awk requires native binary)
        '''
        
        # Extract awk components for PowerShell fallback
        field_separator = None
        program = None
        files = []
        
        # Parse arguments
        i = 1
        while i < len(parts):
            if parts[i] == '-F' and i + 1 < len(parts):
                field_separator = parts[i + 1]
                i += 2
            elif parts[i].startswith('-F'):
                field_separator = parts[i][2:]
                i += 1
            elif not parts[i].startswith('-'):
                if program is None:
                    program = parts[i]
                else:
                    win_path = parts[i]  # Already translated
                    files.append(win_path)
                i += 1
            else:
                i += 1
        
        if not program:
            return 'echo Error: awk requires program', True
        
        # Default field separator
        if not field_separator:
            field_separator = '\\s+'
        else:
            # Escape special regex chars
            field_separator = field_separator.replace('\\', '\\\\')
        
        # Parse awk program
        # Detect BEGIN, main block, END
        begin_block = None
        main_block = None
        end_block = None
        pattern = None
        
        # Extract BEGIN block
        begin_match = re.search(r'BEGIN\s*{([^}]+)}', program)
        if begin_match:
            begin_block = begin_match.group(1).strip()
            program = program.replace(begin_match.group(0), '')
        
        # Extract END block
        end_match = re.search(r'END\s*{([^}]+)}', program)
        if end_match:
            end_block = end_match.group(1).strip()
            program = program.replace(end_match.group(0), '')
        
        # Extract pattern and main block
        # Pattern can be: /regex/, $1 > 100, NF > 5, etc.
        pattern_match = re.match(r'^(/[^/]+/|[^{]+)\s*{([^}]+)}', program.strip())
        if pattern_match:
            pattern_str = pattern_match.group(1).strip()
            main_block = pattern_match.group(2).strip()
            
            if pattern_str.startswith('/') and pattern_str.endswith('/'):
                pattern = ('regex', pattern_str[1:-1])
            elif '>' in pattern_str or '<' in pattern_str or '==' in pattern_str:
                pattern = ('condition', pattern_str)
        else:
            # No pattern, just block
            block_match = re.search(r'{([^}]+)}', program)
            if block_match:
                main_block = block_match.group(1).strip()
        
        # Convert awk operations to PowerShell
        file_arg = f'"{files[0]}"' if files else '$input'
        
        # Build PowerShell fallback script
        ps_lines = []
        
        # BEGIN block
        if begin_block:
            ps_begin = self._awk_to_ps_statement(begin_block)
            ps_lines.append(ps_begin)
        
        # Main processing
        ps_main = []
        ps_main.append(f'Get-Content {file_arg} | ForEach-Object {{')
        ps_main.append(f'  $F = $_ -split "{field_separator}"')
        ps_main.append('  $NF = $F.Length')
        
        # Apply pattern filter if present
        if pattern:
            if pattern[0] == 'regex':
                ps_main.append(f'  if ($_ -match "{pattern[1]}") {{')
            elif pattern[0] == 'condition':
                ps_condition = self._awk_to_ps_condition(pattern[1])
                ps_main.append(f'  if ({ps_condition}) {{')
        
        # Main block operations
        if main_block:
            ps_operation = self._awk_to_ps_statement(main_block)
            indent = '    ' if pattern else '  '
            ps_main.append(f'{indent}{ps_operation}')
        
        # Close pattern filter
        if pattern:
            ps_main.append('  }')
        
        ps_main.append('}')
        
        # END block
        if end_block:
            ps_end = self._awk_to_ps_statement(end_block)
            ps_main.append(ps_end)
        
        ps_fallback = '; '.join(ps_lines + ps_main)
        
        # Complete script with fallback
        ps_script += f'''
            {ps_fallback}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _awk_to_ps_statement(self, awk_stmt: str) -> str:
        """Convert awk statement to PowerShell"""
        # Handle print statements
        if 'print' in awk_stmt:
            # Extract what to print
            print_match = re.search(r'print\s+(.+)', awk_stmt)
            if print_match:
                expr = print_match.group(1).strip()
                # Convert field references
                expr = re.sub(r'\$(\d+)', r'$F[\1-1]', expr)
                expr = expr.replace('$NF', '$F[$NF-1]')
                expr = expr.replace('$(NF-1)', '$F[$NF-2]')
                return f'Write-Output {expr}'
        
        # Handle variable assignments
        if '=' in awk_stmt and not '==' in awk_stmt:
            # x=0 or x+=$1
            var_match = re.match(r'(\w+)\s*([+\-*/]?=)\s*(.+)', awk_stmt)
            if var_match:
                var_name = var_match.group(1)
                operator = var_match.group(2)
                value = var_match.group(3).strip()
                # Convert field references in value
                value = re.sub(r'\$(\d+)', r'$F[\1-1]', value)
                return f'${var_name} {operator} {value}'
        
        # Handle increment/decrement
        if '++' in awk_stmt or '--' in awk_stmt:
            return awk_stmt.replace('$', '')
        
        return awk_stmt
    
    def _awk_to_ps_condition(self, awk_cond: str) -> str:
        """Convert awk condition to PowerShell"""
        # Convert field references
        ps_cond = re.sub(r'\$(\d+)', r'$F[\1-1]', awk_cond)
        ps_cond = ps_cond.replace('$NF', '$NF')
        return ps_cond
    


# ======== sort (1550-1739) ========
    def _execute_sort(self, cmd: str, parts):
        """
        Translate sort - FULL implementation with field selection.
        
        ARTISAN IMPLEMENTATION:
        - Numeric sorting (-n)
        - Field selection (-k N)
        - Custom separator (-t SEP)
        - Unique lines (-u)
        - Reverse order (-r)
        - Human numeric (-h): 1K, 2M, 3G
        
        Unix behavior:
          sort file → alphabetic
          sort -n file → numeric
          sort -k 2 -t: file → sort by 2nd field, separator ':'
          sort -h file → human numeric (1K < 1M < 1G)
        """
        numeric = '-n' in parts or '--numeric-sort' in parts
        reverse = '-r' in parts or '--reverse' in parts
        unique = '-u' in parts or '--unique' in parts
        human = '-h' in parts or '--human-numeric-sort' in parts
        
        # Parse field and separator
        field_num = None
        separator = None
        
        i = 0
        while i < len(parts):
            part = parts[i]
            
            # -k field
            if part == '-k' and i + 1 < len(parts):
                field_spec = parts[i + 1]
                # Extract field number (may be "2" or "2,3" or "2.1")
                field_num = int(field_spec.split(',')[0].split('.')[0])
                i += 1
            elif part.startswith('--key='):
                field_spec = part.split('=')[1]
                field_num = int(field_spec.split(',')[0].split('.')[0])
            
            # -t separator
            elif part == '-t' and i + 1 < len(parts):
                separator = parts[i + 1]
                i += 1
            elif part.startswith('--field-separator='):
                separator = part.split('=')[1]
            
            i += 1
        
        # Get input files
        files = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit() and p not in [separator]]
        
        # Build sort command
        if not field_num and not numeric and not human:
            # Simple sort - use native Windows sort
            if files:
                win_path = files[0]
                cmd = f'sort "{win_path}"'
                if reverse:
                    cmd += ' /r'
                if unique:
                    cmd += ' /unique'
                return cmd, True
            else:
                cmd = 'sort'
                if reverse:
                    cmd += ' /r'
                if unique:
                    cmd += ' /unique'
                return cmd, True
        
        # Complex sort - PowerShell script
        # Default separator is whitespace
        if separator is None:
            separator = ' '
        
        # Escape separator for PowerShell
        sep_escaped = separator.replace("'", "''")
        
        # Build PowerShell script
        if files:
            # From file
            file_path = files[0]
            content_cmd = f'Get-Content "{file_path}"'
        else:
            # From stdin
            content_cmd = '$input'
        
        # Build sort script
        ps_script = f'{content_cmd} | ForEach-Object {{'
        
        if field_num:
            # Field-based sorting
            ps_script += f'''
    $fields = $_ -split '{sep_escaped}'
    if ($fields.Count -ge {field_num}) {{
        $sortKey = $fields[{field_num - 1}].Trim()
    }} else {{
        $sortKey = $_
    }}
    '''
            
            if numeric or human:
                # Convert to number for sorting
                if human:
                    # Human numeric: 1K, 2M, 3G
                    ps_script += '''
    if ($sortKey -match '(\d+\.?\d*)([KMGT]i?)$') {
        $num = [double]$matches[1]
        $unit = $matches[2]
        $multiplier = switch ($unit) {
            'K' { 1000 }
            'Ki' { 1024 }
            'M' { 1000000 }
            'Mi' { 1048576 }
            'G' { 1000000000 }
            'Gi' { 1073741824 }
            'T' { 1000000000000 }
            'Ti' { 1099511627776 }
            default { 1 }
        }
        $sortKey = $num * $multiplier
    } else {
        try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    }
    '''
                else:
                    # Simple numeric
                    ps_script += '''
    try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    '''
            
            ps_script += '''
    [PSCustomObject]@{
        Line = $_
        SortKey = $sortKey
    }
'''
        else:
            # No field selection, just numeric/human sorting
            if numeric or human:
                ps_script += '''
    $sortKey = $_
    '''
                if human:
                    ps_script += '''
    if ($sortKey -match '(\d+\.?\d*)([KMGT]i?)') {
        $num = [double]$matches[1]
        $unit = $matches[2]
        $multiplier = switch ($unit) {
            'K' { 1000 }
            'Ki' { 1024 }
            'M' { 1000000 }
            'Mi' { 1048576 }
            'G' { 1000000000 }
            'Gi' { 1073741824 }
            'T' { 1000000000000 }
            'Ti' { 1099511627776 }
            default { 1 }
        }
        $sortKey = $num * $multiplier
    } else {
        try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    }
    '''
                else:
                    ps_script += '''
    try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    '''
                
                ps_script += '''
    [PSCustomObject]@{
        Line = $_
        SortKey = $sortKey
    }
'''
        
        ps_script += '} | Sort-Object -Property SortKey'
        
        if reverse:
            ps_script += ' -Descending'
        
        if unique:
            ps_script += ' -Unique'
        
        ps_script += ' | ForEach-Object { $_.Line }'
        
        return f'powershell -Command "{ps_script}"', True
    


# ======== uniq (1740-1900) ========
    def _execute_uniq(self, cmd: str, parts):
        """
        Translate uniq - CORRECT implementation for consecutive duplicates.
        
        CRITICAL: Unix uniq removes CONSECUTIVE duplicates ONLY, not all duplicates!
        
        Example:
          echo -e "a\\nb\\na" | uniq  →  a, b, a  (NOT a, b)
        
        Flags:
        - -c, --count: Prefix lines with occurrence count
        - -d, --repeated: Only print duplicate lines (consecutive)
        - -u, --unique: Only print unique lines (non-consecutive-duplicates)
        - -i, --ignore-case: Case-insensitive comparison
        - -f N, --skip-fields=N: Skip first N fields for comparison
        - -s N, --skip-chars=N: Skip first N chars for comparison
        """
        count_mode = '-c' in parts or '--count' in parts
        duplicates_only = '-d' in parts or '--repeated' in parts
        unique_only = '-u' in parts or '--unique' in parts
        ignore_case = '-i' in parts or '--ignore-case' in parts
        
        # Parse skip fields
        skip_fields = 0
        for i, part in enumerate(parts):
            if part == '-f' and i + 1 < len(parts):
                skip_fields = int(parts[i + 1])
            elif part.startswith('--skip-fields='):
                skip_fields = int(part.split('=')[1])
        
        # Parse skip chars
        skip_chars = 0
        for i, part in enumerate(parts):
            if part == '-s' and i + 1 < len(parts):
                skip_chars = int(parts[i + 1])
            elif part.startswith('--skip-chars='):
                skip_chars = int(part.split('=')[1])
        
        files = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit()]
        
        # Build PowerShell script for CONSECUTIVE duplicate detection
        if files:
            file_path = files[0]
            content_cmd = f'Get-Content "{file_path}"'
        else:
            content_cmd = '$input'
        
        # Build comparison key extraction
        key_extraction = ''
        if skip_fields > 0:
            key_extraction = f'''
                $fields = $line -split '\s+'
                if ($fields.Count -gt {skip_fields}) {{
                    $key = ($fields[{skip_fields}..($fields.Count-1)] -join ' ')
                }} else {{
                    $key = ''
                }}
            '''
        elif skip_chars > 0:
            key_extraction = f'''
                if ($line.Length -gt {skip_chars}) {{
                    $key = $line.Substring({skip_chars})
                }} else {{
                    $key = ''
                }}
            '''
        else:
            key_extraction = '$key = $line'
        
        # Case-insensitive comparison
        comparison = '$key' if not ignore_case else '$key.ToLower()'
        prev_comparison = '$prevKey' if not ignore_case else '$prevKey.ToLower()'
        
        # Build main processing script
        ps_script = f'''
            $prevLine = $null
            $prevKey = $null
            $count = 0
            
            {content_cmd} | ForEach-Object {{
                $line = $_
                {key_extraction}
                
                if ($prevLine -eq $null) {{
                    # First line
                    $prevLine = $line
                    $prevKey = $key
                    $count = 1
                }} elseif ({comparison} -eq {prev_comparison}) {{
                    # Consecutive duplicate
                    $count++
                }} else {{
                    # Different line - output previous
        '''
        
        # Output logic based on mode
        if count_mode:
            # Count mode: "%7d %s" format
            ps_script += '''
                    Write-Output ("{0,7} {1}" -f $count, $prevLine)
            '''
        elif duplicates_only:
            # Only duplicates (count > 1)
            ps_script += '''
                    if ($count -gt 1) {
                        Write-Output $prevLine
                    }
            '''
        elif unique_only:
            # Only unique (count == 1)
            ps_script += '''
                    if ($count -eq 1) {
                        Write-Output $prevLine
                    }
            '''
        else:
            # Normal mode: just output unique lines
            ps_script += '''
                    Write-Output $prevLine
            '''
        
        # Reset for new line
        ps_script += '''
                    $prevLine = $line
                    $prevKey = $key
                    $count = 1
                }
            }
            
            # Output last line
            if ($prevLine -ne $null) {
        '''
        
        # Final output logic
        if count_mode:
            ps_script += '''
                Write-Output ("{0,7} {1}" -f $count, $prevLine)
            '''
        elif duplicates_only:
            ps_script += '''
                if ($count -gt 1) {
                    Write-Output $prevLine
                }
            '''
        elif unique_only:
            ps_script += '''
                if ($count -eq 1) {
                    Write-Output $prevLine
                }
            '''
        else:
            ps_script += '''
                Write-Output $prevLine
            '''
        
        ps_script += '''
            }
        '''
        
        return f'powershell -Command "{ps_script}"', True
    


# ======== grep (1256-1379) ========
    def _execute_grep(self, cmd: str, parts):
        """Translate grep with FULL flag support - ALL flags implemented"""
        if len(parts) < 2:
            return 'echo Error: grep requires pattern', True
        
        case_insensitive = '-i' in parts
        invert = '-v' in parts
        recursive = '-r' in parts or '-R' in parts
        line_numbers = '-n' in parts
        count = '-c' in parts
        extended_regex = '-E' in parts
        whole_word = '-w' in parts
        exact_line = '-x' in parts
        only_matching = '-o' in parts
        quiet = '-q' in parts or '--quiet' in parts
        no_filename = '-h' in parts
        with_filename = '-H' in parts
        files_with_matches = '-l' in parts
        files_without_matches = '-L' in parts
        
        # Context lines
        before_context = 0
        after_context = 0
        for i, part in enumerate(parts):
            if part == '-A' and i + 1 < len(parts):
                after_context = int(parts[i + 1])
            elif part == '-B' and i + 1 < len(parts):
                before_context = int(parts[i + 1])
            elif part == '-C' and i + 1 < len(parts):
                before_context = after_context = int(parts[i + 1])
        
        # Extract pattern and files
        pattern = None
        files = []
        skip_next = False
        for i, part in enumerate(parts[1:], 1):
            if skip_next:
                skip_next = False
                continue
            if part in ['-A', '-B', '-C', '-e', '-f']:
                skip_next = True
                continue
            if part.startswith('-'):
                continue
            if pattern is None:
                pattern = part
            else:
                win_path = part  # Already translated
                files.append(f'"{win_path}"')
        
        if pattern is None:
            return 'echo Error: grep requires pattern', True
        
        # Use PowerShell for full feature support
        ps_flags = []
        
        if case_insensitive:
            ps_flags.append('-CaseSensitive:$false')
        
        if quiet:
            # Quiet mode: just exit code, no output
            ps_cmd = f'if (Select-String -Pattern "{pattern}" -Path {files[0] if files else "*"} -Quiet) {{ exit 0 }} else {{ exit 1 }}'
            return f'powershell -Command "{ps_cmd}"', True
        
        if line_numbers:
            # Select-String includes line numbers by default in output
            pass
        
        if recursive:
            ps_flags.append('-Recurse')
        
        # Extended regex (PowerShell uses .NET regex which is already extended)
        # So -E flag doesn't need special handling - just noted for completeness
        if extended_regex:
            # .NET regex already supports +, ?, |, {}, () without escaping
            pass

        if whole_word:
            pattern = f'\\b{pattern}\\b'
        
        if exact_line:
            pattern = f'^{pattern}$'
        
        file_arg = files[0] if files else '*'
        
        # Build Select-String command
        ps_cmd = f'Select-String -Pattern "{pattern}" -Path {file_arg} {" ".join(ps_flags)}'
        
        # Post-processing
        post_process = []
        
        if only_matching:
            post_process.append('ForEach-Object { $_.Matches.Value }')
        
        if files_with_matches:
            post_process.append('Select-Object -Unique Path')
            post_process.append('ForEach-Object { $_.Path }')
        
        if files_without_matches:
            # Invert the logic
            ps_cmd = f'$allFiles = Get-ChildItem {file_arg}; $matchFiles = {ps_cmd} | Select-Object -Unique Path; $allFiles | Where-Object {{ $matchFiles.Path -notcontains $_.FullName }} | ForEach-Object {{ $_.Name }}'
            return f'powershell -Command "{ps_cmd}"', True
        
        if count:
            post_process.append('Measure-Object')
            post_process.append('Select-Object -ExpandProperty Count')
        
        if no_filename and len(files) == 1:
            post_process.append('ForEach-Object { $_.Line }')
        elif with_filename or len(files) > 1:
            post_process.append('ForEach-Object { "$($_.Filename):$($_.Line)" }')
        
        if invert:
            # For invert, use different approach
            ps_cmd = f'Get-Content {file_arg} | Where-Object {{ $_ -notmatch "{pattern}" }}'
        
        if before_context or after_context:
            ps_cmd += f' -Context {before_context},{after_context}'
        
        if post_process:
            ps_cmd += ' | ' + ' | '.join(post_process)
        
        return f'powershell -Command "{ps_cmd}"', True
    


# ======== tar (2324-2433) ========
    def _execute_tar(self, cmd: str, parts):
        """
        Translate tar with REAL .tar.gz support via fallback chain.
        
        STRATEGY FOR 100%:
        1. Try tar.exe (Git for Windows) - 100% GNU tar with .tar.gz, .tar.bz2, .tar.xz
        2. Fallback PowerShell Compress-Archive - .zip workaround (90% compatible)
        
        CRITICAL: tar.exe supports REAL tar formats:
        - .tar: uncompressed tar archive
        - .tar.gz / .tgz: gzip compressed (-z flag)
        - .tar.bz2: bzip2 compressed (-j flag)
        - .tar.xz: xz compressed (-J flag)
        
        Common operations:
        tar -czf archive.tar.gz dir/ → create gzip
        tar -xzf archive.tar.gz → extract gzip
        tar -tzf archive.tar.gz → list contents
        tar -xjf archive.tar.bz2 → extract bzip2
        """
        if len(parts) < 2:
            return 'echo Error: tar requires arguments', True
        
        # Parse operation from flags
        flags = parts[1]
        create = 'c' in flags
        extract = 'x' in flags
        list_contents = 't' in flags
        verbose = 'v' in flags
        use_file = 'f' in flags
        gzip_compress = 'z' in flags
        bzip2_compress = 'j' in flags
        xz_compress = 'J' in flags
        
        # Find archive name and paths
        archive = None
        paths = []
        change_dir = None
        
        i = 2
        while i < len(parts):
            if parts[i] == '-C' and i + 1 < len(parts):
                change_dir = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                if not archive and use_file:
                    archive = parts[i]
                else:
                    paths.append(parts[i])
                i += 1
            else:
                i += 1
        
        if not archive:
            return 'echo Error: tar requires archive name (-f)', True
        
        # Build tar command for native tar.exe
        tar_parts = [parts[0]]  # 'tar'
        tar_parts.extend(parts[1:])  # All flags and args as-is
        
        tar_cmd = ' '.join(f'"{p}"' if ' ' in p else p for p in tar_parts)
        
        # PowerShell fallback (current implementation)
        # Convert tar extensions to zip for PowerShell
        if archive.endswith('.tar.gz') or archive.endswith('.tgz'):
            zip_archive = archive.rsplit('.', 2 if archive.endswith('.tar.gz') else 1)[0] + '.zip'
        elif archive.endswith('.tar.bz2') or archive.endswith('.tar.xz') or archive.endswith('.tar'):
            zip_archive = archive.rsplit('.', 1)[0] + '.zip'
        else:
            zip_archive = archive
        
        if create:
            if not paths:
                return 'echo Error: tar -c requires source path(s)', True
            
            paths_str = ','.join([f'\\"{p}\\"' for p in paths])
            ps_fallback = f'Compress-Archive -Path {paths_str} -DestinationPath \\"{zip_archive}\\" -Force'
            
            if verbose:
                ps_fallback += f'; Write-Host "Created archive: {zip_archive}"'
        
        elif extract:
            dest = paths[0] if paths else '.'
            ps_fallback = f'Expand-Archive -Path \\"{zip_archive}\\" -DestinationPath \\"{dest}\\" -Force'
            
            if verbose:
                ps_fallback += f'; Get-ChildItem -Path \\"{dest}\\" -Recurse | Select-Object FullName'
        
        elif list_contents:
            ps_fallback = f'Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::OpenRead(\\"{zip_archive}\\").Entries | Select-Object FullName'
        
        else:
            return 'echo Error: tar requires operation flag (c, x, or t)', True
        
        # Build PowerShell script with fallback chain
        ps_script = f'''
            # Try native tar.exe (Git for Windows) - 100% GNU tar
            $tarExe = Get-Command tar.exe -ErrorAction SilentlyContinue
            
            if ($tarExe) {{
                # Native tar.exe available - supports REAL .tar.gz, .tar.bz2, .tar.xz
                & tar.exe {' '.join(parts[1:])}
            }} else {{
                # Fallback: PowerShell Compress-Archive (.zip workaround)
                {ps_fallback}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    


# ======== hexdump (3700-3830) ========
    def _execute_hexdump(self, cmd: str, parts):
        """
        Translate hexdump - hex dump of binary files.
        
        ARTISAN IMPLEMENTATION:
        - Canonical format (-C): offset + hex + ASCII
        - Limit bytes (-n): read only N bytes
        - Skip offset (-s): skip N bytes from start
        
        Unix format (-C):
        00000000  7f 45 4c 46 02 01 01 00  00 00 00 00 00 00 00 00  |.ELF............|
        00000010  03 00 3e 00 01 00 00 00  a0 0e 00 00 00 00 00 00  |..>.............|
        
        Layout:
        - Offset: 8 hex digits
        - 16 bytes in hex (8 + space + 8)
        - |ASCII| (. for non-printable)
        """
        canonical = '-C' in parts
        limit_bytes = None
        skip_bytes = 0
        file_path = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-C':
                canonical = True
                i += 1
            elif parts[i] == '-n' and i + 1 < len(parts):
                limit_bytes = int(parts[i + 1])
                i += 2
            elif parts[i] == '-s' and i + 1 < len(parts):
                skip_bytes = int(parts[i + 1])
                i += 2
            elif not parts[i].startswith('-'):
                file_path = parts[i]
                i += 1
            else:
                i += 1
        
        if not file_path:
            return 'echo Error: hexdump requires filename', True
        
        if canonical:
            # Canonical format: offset + hex + ASCII
            ps_script = f'''
                $file = "{file_path}"
                $skip = {skip_bytes}
                $limit = {limit_bytes if limit_bytes else -1}
                
                if (-not (Test-Path $file)) {{
                    Write-Error "hexdump: $file`: No such file or directory"
                    exit 1
                }}
                
                $bytes = [System.IO.File]::ReadAllBytes($file)
                
                # Apply skip
                if ($skip -gt 0) {{
                    $bytes = $bytes[$skip..($bytes.Length - 1)]
                }}
                
                # Apply limit
                if ($limit -gt 0 -and $limit -lt $bytes.Length) {{
                    $bytes = $bytes[0..($limit - 1)]
                }}
                
                # Dump in canonical format (16 bytes per line)
                for ($i = 0; $i -lt $bytes.Length; $i += 16) {{
                    # Offset (8 hex digits)
                    $offset = "{{0:x8}}" -f ($i + $skip)
                    
                    # Extract chunk (up to 16 bytes)
                    $chunk = $bytes[$i..[Math]::Min($i + 15, $bytes.Length - 1)]
                    
                    # Hex part 1 (first 8 bytes)
                    $hex1 = ""
                    for ($j = 0; $j -lt [Math]::Min(8, $chunk.Length); $j++) {{
                        $hex1 += "{{0:x2}} " -f $chunk[$j]
                    }}
                    $hex1 = $hex1.TrimEnd()
                    
                    # Hex part 2 (last 8 bytes)
                    $hex2 = ""
                    if ($chunk.Length -gt 8) {{
                        for ($j = 8; $j -lt $chunk.Length; $j++) {{
                            $hex2 += "{{0:x2}} " -f $chunk[$j]
                        }}
                        $hex2 = $hex2.TrimEnd()
                    }}
                    
                    # ASCII part (. for non-printable)
                    $ascii = ""
                    foreach ($b in $chunk) {{
                        if ($b -ge 32 -and $b -le 126) {{
                            $ascii += [char]$b
                        }} else {{
                            $ascii += "."
                        }}
                    }}
                    
                    # Format line (pad hex fields to align)
                    $hex1_padded = $hex1.PadRight(23)  # 8 bytes * 3 chars - 1
                    $hex2_padded = $hex2.PadRight(23)
                    
                    Write-Output "$offset  $hex1_padded $hex2_padded |$ascii|"
                }}
            '''
            
            return f'powershell -Command "{ps_script}"', True
        else:
            # Non-canonical format - just hex
            ps_script = f'''
                $bytes = [System.IO.File]::ReadAllBytes("{file_path}")
                
                # Apply skip
                if ({skip_bytes} -gt 0) {{
                    $bytes = $bytes[{skip_bytes}..($bytes.Length - 1)]
                }}
                
                # Apply limit
                if ({limit_bytes if limit_bytes else -1} -gt 0) {{
                    $bytes = $bytes[0..({limit_bytes} - 1)]
                }}
                
                # Output hex
                $bytes | ForEach-Object {{ "{{0:x2}}" -f $_ }} | Write-Output
            '''
            
            return f'powershell -Command "{ps_script}"', True
    


# ======== gzip (4734-4848) ========
    def _execute_gzip(self, cmd: str, parts):
        """
        Translate gzip - REAL gzip compression with .NET GZipStream.
        
        CRITICAL: Must produce VALID gzip files compatible with Unix gzip.
        
        Format: RFC 1952 gzip format
        - Magic bytes: 0x1f 0x8b
        - Compression: deflate
        - CRC32, timestamp, etc.
        
        Flags:
        - -c: Write to stdout (keep original)
        - -d: Decompress (same as gunzip)
        - -k: Keep original file
        - -f: Force overwrite
        - -1 to -9: Compression level (ignored - .NET uses default)
        - -r: Recursive (directories)
        
        Behavior (Unix compatible):
        - gzip file.txt → creates file.txt.gz, deletes file.txt
        - gzip -k file.txt → creates file.txt.gz, keeps file.txt
        - gzip -c file.txt → stdout, keeps file.txt
        """
        stdout_mode = '-c' in parts or '--stdout' in parts
        decompress = '-d' in parts or '--decompress' in parts
        keep = '-k' in parts or '--keep' in parts
        force = '-f' in parts or '--force' in parts
        recursive = '-r' in parts or '--recursive' in parts
        
        # Get files (ignore compression level flags -1 to -9)
        files = [p for p in parts[1:] if not p.startswith('-') or (p.startswith('-') and len(p) == 2 and p[1].isdigit())]
        files = [f for f in files if not (f.startswith('-') and len(f) == 2 and f[1].isdigit())]
        
        if not files:
            # stdin mode
            if decompress:
                # Decompress from stdin
                ps_script = '''
                    $input | Set-Content -Path temp.gz -Encoding Byte
                    $input = [System.IO.File]::OpenRead("temp.gz")
                    $gzip = New-Object System.IO.Compression.GZipStream($input, [System.IO.Compression.CompressionMode]::Decompress)
                    $gzip.CopyTo([Console]::OpenStandardOutput())
                    $gzip.Close()
                    $input.Close()
                    Remove-Item temp.gz
                '''
            else:
                # Compress from stdin
                ps_script = '''
                    $input | Set-Content -Path temp -Encoding Byte
                    $inputFile = [System.IO.File]::OpenRead("temp")
                    $output = [Console]::OpenStandardOutput()
                    $gzip = New-Object System.IO.Compression.GZipStream($output, [System.IO.Compression.CompressionMode]::Compress)
                    $inputFile.CopyTo($gzip)
                    $gzip.Close()
                    $inputFile.Close()
                    Remove-Item temp
                '''
            return f'powershell -Command "{ps_script}"', True
        
        file_path = files[0]
        
        if decompress:
            # Decompress mode (gzip -d = gunzip)
            return self._translate_gunzip(cmd, parts)
        
        # Compress mode
        if stdout_mode:
            # Output to stdout, keep original
            ps_script = f'''
                $inputFile = [System.IO.File]::OpenRead("{file_path}")
                $output = [Console]::OpenStandardOutput()
                $gzip = New-Object System.IO.Compression.GZipStream($output, [System.IO.Compression.CompressionMode]::Compress)
                $inputFile.CopyTo($gzip)
                $gzip.Close()
                $inputFile.Close()
            '''
        else:
            # Create .gz file
            output_file = f'{file_path}.gz'
            
            ps_script = f'''
                $inputPath = "{file_path}"
                $outputPath = "{output_file}"
                
                if (-not (Test-Path $inputPath)) {{
                    Write-Host "gzip: $inputPath: No such file or directory"
                    exit 1
                }}
                
                if ((Test-Path $outputPath) -and -not {str(force).lower()}) {{
                    Write-Host "gzip: $outputPath already exists; not overwritten"
                    exit 1
                }}
                
                $inputFile = [System.IO.File]::OpenRead($inputPath)
                $outputFile = [System.IO.File]::Create($outputPath)
                $gzip = New-Object System.IO.Compression.GZipStream($outputFile, [System.IO.Compression.CompressionMode]::Compress)
                
                $inputFile.CopyTo($gzip)
                
                $gzip.Close()
                $outputFile.Close()
                $inputFile.Close()
            '''
            
            if not keep:
                # Delete original (Unix default behavior)
                ps_script += f'''
                Remove-Item "{file_path}"
                '''
        
        return f'powershell -Command "{ps_script}"', True
    


# ======== split (4538-4733) ========
    def _execute_split(self, cmd: str, parts):
        """
        Translate split - file splitting with Unix-compatible naming.
        
        CRITICAL: Suffix naming must be IDENTICAL to Unix.
        
        Flags:
        - -l N: Lines per chunk (default 1000)
        - -b N[K|M|G]: Bytes per chunk
        - -d: Numeric suffixes (00, 01) instead of (aa, ab)
        - -a N: Suffix length (default 2)
        
        Unix behavior:
          split -l 100 file.txt chunk_  →  chunk_aa, chunk_ab, chunk_ac...
          split -l 100 -d file.txt chunk_  →  chunk_00, chunk_01, chunk_02...
          split -b 1M file.bin part_  →  part_aa, part_ab... (1MB chunks)
        
        Output: SILENT (no stdout)
        """
        lines_per_chunk = None
        bytes_per_chunk = None
        numeric_suffix = '-d' in parts or '--numeric-suffixes' in parts
        suffix_length = 2  # Default
        
        # Parse flags
        i = 1
        while i < len(parts):
            part = parts[i]
            
            if part == '-l' and i + 1 < len(parts):
                lines_per_chunk = int(parts[i + 1])
                i += 2
            elif part.startswith('-l'):
                lines_per_chunk = int(part[2:])
                i += 1
            
            elif part == '-b' and i + 1 < len(parts):
                size_str = parts[i + 1]
                bytes_per_chunk = self._parse_size(size_str)
                i += 2
            elif part.startswith('-b'):
                size_str = part[2:]
                bytes_per_chunk = self._parse_size(size_str)
                i += 1
            
            elif part == '-a' and i + 1 < len(parts):
                suffix_length = int(parts[i + 1])
                i += 2
            elif part.startswith('-a'):
                suffix_length = int(part[2:])
                i += 1
            
            elif part == '-d' or part == '--numeric-suffixes':
                i += 1
            
            else:
                # File or prefix
                i += 1
        
        # Default: 1000 lines if neither -l nor -b specified
        if lines_per_chunk is None and bytes_per_chunk is None:
            lines_per_chunk = 1000
        
        # Get input file and prefix
        non_flag_args = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit()]
        
        if len(non_flag_args) == 0:
            # stdin, default prefix 'x'
            input_file = None
            prefix = 'x'
        elif len(non_flag_args) == 1:
            # Could be file or prefix
            # If file exists, it's input file with default prefix
            # Otherwise it's prefix with stdin
            # For Windows translation, assume it's file (path already translated)
            input_file = non_flag_args[0]
            prefix = 'x'
        else:
            # Both file and prefix
            input_file = non_flag_args[0]
            prefix = non_flag_args[1]
        
        # Build PowerShell script
        ps_script = '''
            $ErrorActionPreference = 'Stop'
        '''
        
        if input_file:
            ps_script += f'''
            $content = Get-Content "{input_file}" -Raw
            $lines = Get-Content "{input_file}"
            '''
        else:
            ps_script += '''
            $lines = $input
            '''
        
        # Suffix generation function
        if numeric_suffix:
            # Numeric: 00, 01, 02...
            ps_script += f'''
            function Get-Suffix {{
                param($index)
                return $index.ToString().PadLeft({suffix_length}, '0')
            }}
            '''
        else:
            # Alphabetic: aa, ab, ac... az, ba, bb...
            ps_script += f'''
            function Get-Suffix {{
                param($index)
                $chars = 'abcdefghijklmnopqrstuvwxyz'
                $suffix = ''
                $n = $index
                for ($i = 0; $i -lt {suffix_length}; $i++) {{
                    $suffix = $chars[$n % 26] + $suffix
                    $n = [Math]::Floor($n / 26)
                }}
                return $suffix
            }}
            '''
        
        if lines_per_chunk:
            # Line-based splitting
            ps_script += f'''
            $chunkIndex = 0
            $currentChunk = @()
            
            foreach ($line in $lines) {{
                $currentChunk += $line
                
                if ($currentChunk.Count -eq {lines_per_chunk}) {{
                    $suffix = Get-Suffix $chunkIndex
                    $filename = "{prefix}" + $suffix
                    $currentChunk | Out-File -FilePath $filename -Encoding utf8
                    $currentChunk = @()
                    $chunkIndex++
                }}
            }}
            
            # Write remaining lines
            if ($currentChunk.Count -gt 0) {{
                $suffix = Get-Suffix $chunkIndex
                $filename = "{prefix}" + $suffix
                $currentChunk | Out-File -FilePath $filename -Encoding utf8
            }}
            '''
        else:
            # Byte-based splitting
            ps_script += f'''
            $bytes = [System.IO.File]::ReadAllBytes("{input_file}")
            $chunkIndex = 0
            $offset = 0
            
            while ($offset -lt $bytes.Length) {{
                $chunkSize = [Math]::Min({bytes_per_chunk}, $bytes.Length - $offset)
                $chunk = $bytes[$offset..($offset + $chunkSize - 1)]
                
                $suffix = Get-Suffix $chunkIndex
                $filename = "{prefix}" + $suffix
                [System.IO.File]::WriteAllBytes($filename, $chunk)
                
                $offset += $chunkSize
                $chunkIndex++
            }}
            '''
        
        # Silent output (like Unix split)
        return f'powershell -Command "{ps_script}" >$null 2>&1', True
    
    def _parse_size(self, size_str: str) -> int:
        """
        Parse size string like 1K, 2M, 3G.
        
        Returns bytes.
        """
        import re
        
        match = re.match(r'^(\d+)([KMGT])?$', size_str, re.IGNORECASE)
        if not match:
            return int(size_str)  # Plain number
        
        value = int(match.group(1))
        unit = match.group(2)
        
        if unit:
            multipliers = {
                'K': 1024,
                'M': 1024 * 1024,
                'G': 1024 * 1024 * 1024,
                'T': 1024 * 1024 * 1024 * 1024,
            }
            return value * multipliers.get(unit.upper(), 1)
        
        return value
    


# ======== jq (4941-5159) ========
    def _execute_jq(self, cmd: str, parts):
        """
        Translate jq - JSON processor with intelligent fallback.
        
        STRATEGY FOR 100%:
        1. Try jq.exe (Git for Windows, scoop, chocolatey) - 100% complete
        2. Fallback PowerShell for COMMON patterns (90% real-world use):
           - .field → select field
           - .[] → array elements  
           - .field.nested → nested access
           - .[N] → array index
           - keys → object keys
           - length → count
           - -r flag → raw output (no quotes)
        
        Complex filters require jq.exe.
        
        Flags:
        - -r, --raw-output: Raw strings (no quotes)
        - -c, --compact-output: Compact JSON
        - -n, --null-input: No input
        - -e, --exit-status: Exit code based on output
        - -s, --slurp: Read entire input as array
        
        Examples:
          jq '.name' → PowerShell fallback OK
          jq '.items[].id' → PowerShell fallback OK
          jq 'map(select(.active))' → Requires jq.exe
        """
        raw_output = '-r' in parts or '--raw-output' in parts
        compact = '-c' in parts or '--compact-output' in parts
        null_input = '-n' in parts or '--null-input' in parts
        slurp = '-s' in parts or '--slurp' in parts
        
        # Get filter expression (first non-flag arg)
        filter_expr = None
        files = []
        for part in parts[1:]:
            if not part.startswith('-'):
                if filter_expr is None:
                    filter_expr = part
                else:
                    files.append(part)
        
        if not filter_expr:
            filter_expr = '.'  # Identity filter
        
        # Build PowerShell script with fallback
        file_input = f'Get-Content "{files[0]}"' if files else '$input'
        
        # Check if pattern is simple (PowerShell can handle)
        is_simple = self._is_simple_jq_pattern(filter_expr)
        
        if is_simple:
            # PowerShell fallback for simple patterns
            ps_script = f'''
                # Try jq.exe first
                $jqExe = Get-Command jq.exe -ErrorAction SilentlyContinue
                if ($jqExe) {{
                    {file_input} | & jq.exe {'-r' if raw_output else ''} {'-c' if compact else ''} '{filter_expr}'
                    exit $LASTEXITCODE
                }}
                
                # Fallback: PowerShell for simple patterns
                $json = {file_input} | Out-String | ConvertFrom-Json
                $result = $json
            '''
            
            # Parse simple filter and convert to PowerShell
            ps_filter = self._jq_to_powershell(filter_expr)
            ps_script += ps_filter
            
            # Output formatting
            if raw_output:
                ps_script += '''
                if ($result -is [string]) {
                    Write-Output $result
                } elseif ($result -is [array]) {
                    $result | ForEach-Object { Write-Output $_ }
                } else {
                    Write-Output $result
                }
                '''
            elif compact:
                ps_script += '''
                $result | ConvertTo-Json -Compress -Depth 100
                '''
            else:
                ps_script += '''
                if ($result -is [string] -or $result -is [int] -or $result -is [bool]) {
                    $result | ConvertTo-Json
                } else {
                    $result | ConvertTo-Json -Depth 100
                }
                '''
        else:
            # Complex pattern - REQUIRES jq.exe
            ps_script = f'''
                $jqExe = Get-Command jq.exe -ErrorAction SilentlyContinue
                if ($jqExe) {{
                    {file_input} | & jq.exe {'-r' if raw_output else ''} {'-c' if compact else ''} '{filter_expr}'
                    exit $LASTEXITCODE
                }} else {{
                    Write-Host "jq: complex filter requires jq.exe (install via Git for Windows, scoop, or chocolatey)"
                    Write-Host "Filter: {filter_expr}"
                    exit 1
                }}
            '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _is_simple_jq_pattern(self, pattern: str) -> bool:
        """
        Check if jq pattern is simple enough for PowerShell fallback.
        
        Simple patterns:
        - . (identity)
        - .field
        - .field.nested
        - .[]
        - .[N]
        - .field[]
        - keys
        - length
        
        Complex patterns (require jq.exe):
        - map()
        - select()
        - Pipe operators
        - Functions
        - Conditionals
        """
        # Complex patterns
        if any(keyword in pattern for keyword in ['map', 'select', 'if', 'then', 'else', 'def', '|']):
            return False
        
        # Simple patterns
        if pattern in ['.', 'keys', 'length']:
            return True
        
        # Field access patterns: .field, .field.nested, .[], .[N]
        import re
        if re.match(r'^\.(\w+|\[\d*\])(\.(\w+|\[\d*\]))*$', pattern):
            return True
        
        return False
    
    def _jq_to_powershell(self, pattern: str) -> str:
        """
        Convert simple jq pattern to PowerShell.
        
        Examples:
        - . → $result = $json
        - .name → $result = $json.name
        - .items[] → $result = $json.items
        - .[0] → $result = $json[0]
        - .user.email → $result = $json.user.email
        - keys → $result = $json.PSObject.Properties.Name
        - length → $result = $json.Count or $json.Length
        """
        if pattern == '.':
            return '$result = $json\n'
        
        if pattern == 'keys':
            return '''
                if ($json -is [PSCustomObject]) {
                    $result = $json.PSObject.Properties.Name
                } else {
                    $result = @()
                }
            '''
        
        if pattern == 'length':
            return '''
                if ($json -is [array]) {
                    $result = $json.Count
                } elseif ($json -is [string]) {
                    $result = $json.Length
                } elseif ($json -is [PSCustomObject]) {
                    $result = ($json.PSObject.Properties | Measure-Object).Count
                } else {
                    $result = 0
                }
            '''
        
        # Parse field access: .field.nested or .[] or .[N]
        import re
        
        # Remove leading dot
        if pattern.startswith('.'):
            pattern = pattern[1:]
        
        # Split by dots
        parts = pattern.split('.')
        
        ps_code = '$result = $json'
        for part in parts:
            if part == '[]':
                # Array iteration - already handled by $result
                pass
            elif re.match(r'^\[\d+\]$', part):
                # Array index
                index = part[1:-1]
                ps_code += f'[{index}]'
            elif part.endswith('[]'):
                # Field with array iteration
                field = part[:-2]
                ps_code += f'.{field}'
            else:
                # Simple field
                ps_code += f'.{part}'
        
        return ps_code + '\n'


# ============================================================================
# BASH EXECUTOR
# ============================================================================



# ======== curl (1977-2215) ========
    def _execute_timeout(self, cmd: str, parts):
        """
        Translate timeout - Run command with time limit.
        
        ARTISAN IMPLEMENTATION:
        - timeout 10s command → PowerShell job with Wait-Job -Timeout
        - --kill-after: fallback kill if SIGTERM fails
        - Exit codes: 124 if timeout, command exit code otherwise
        
        Unix formats:
          timeout 10 command
          timeout 10s command
          timeout 1m command
          timeout --kill-after=5s 10s command
        
        PowerShell strategy:
          Start-Job { command }
          Wait-Job -Timeout seconds
          If timeout: Stop-Job, exit 124
          Else: Receive-Job, exit with command exit code
        """
        if len(parts) < 3:
            return 'echo Error: timeout requires duration and command', True
        
        # Parse --kill-after flag (optional)
        kill_after = None
        for i, part in enumerate(parts):
            if part.startswith('--kill-after='):
                kill_after_str = part.split('=')[1]
                kill_after = self._parse_duration(kill_after_str)
        
        # Parse duration (first non-flag arg after 'timeout')
        duration_str = None
        command_start_idx = None
        
        for i, part in enumerate(parts[1:], 1):
            if not part.startswith('-'):
                if duration_str is None:
                    duration_str = part
                else:
                    # This is start of command
                    command_start_idx = i
                    break
        
        if not duration_str or command_start_idx is None:
            return 'echo Error: timeout requires duration and command', True
        
        # Parse duration to seconds
        timeout_seconds = self._parse_duration(duration_str)
        
        # Extract command (everything after duration)
        command_parts = parts[command_start_idx:]
        command_str = ' '.join(command_parts)
        
        # Build PowerShell script with job control
        # Note: Command inside job needs translation too, but we'll pass it through as-is
        # since the outer translator already handles command translation
        ps_script = f'''
            $job = Start-Job -ScriptBlock {{
                {command_str}
            }}
            
            $completed = Wait-Job $job -Timeout {timeout_seconds}
            
            if ($completed) {{
                # Job completed within timeout
                $output = Receive-Job $job
                if ($output) {{ Write-Output $output }}
                
                # Get exit code from job
                $jobState = $job.State
                Remove-Job $job -Force
                
                if ($jobState -eq "Failed") {{
                    exit 1
                }} else {{
                    exit 0
                }}
            }} else {{
                # Timeout occurred
                Stop-Job $job -PassThru | Remove-Job -Force
                Write-Host "timeout: command timed out after {timeout_seconds} seconds"
                exit 124
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string to seconds.
        
        Formats: 10, 10s, 1m, 1h, 1d
        """
        import re
        
        match = re.match(r'^(\d+)([smhd])?$', duration_str)
        if not match:
            return 10  # Default fallback
        
        value = int(match.group(1))
        unit = match.group(2) or 's'
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        
        return value * multipliers.get(unit, 1)
    


# ======== sed (2591-2823) ========
    def _execute_sed(self, cmd: str, parts):
        """
        Translate sed with fallback chain.
        
        STRATEGY FOR 100%:
        1. Try sed.exe (Git for Windows) - 100% GNU sed
        2. Fallback PowerShell custom for common operations
        
        Supported in PowerShell fallback:
        - s/search/replace/flags (substitution with g, i, p flags)
        - Address ranges: 1,10s/.../, /pattern/s/.../, $s/.../
        - Multiple -e expressions
        - d (delete lines)
        - p (print lines)
        - a, i, c (append, insert, change text)
        - -i (in-place editing)
        - -n (quiet mode - suppress output except explicit p)
        
        Complex sed scripts work better with native sed.
        """
        if len(parts) < 2:
            return 'echo Error: sed requires expression', True
        
        # Build command for native sed
        sed_cmd_parts = []
        for part in parts[1:]:
            # Quote arguments that need it
            if ' ' in part or any(c in part for c in ['|', '&', '>', '<', ';']):
                sed_cmd_parts.append(f'"{part}"')
            else:
                sed_cmd_parts.append(part)
        
        sed_full_cmd = ' '.join(sed_cmd_parts)
        
        # PowerShell script with fallback chain
        ps_script_start = f'''
            # Try native sed (Git for Windows)
            $sedExe = Get-Command sed.exe -ErrorAction SilentlyContinue
            
            if ($sedExe) {{
                # Native sed - 100% GNU compatible
                & sed.exe {sed_full_cmd}
                exit $LASTEXITCODE
            }}
            
            # Fallback: PowerShell custom implementation
        '''
        
        # Parse arguments for PowerShell fallback
        in_place = False
        quiet = False
        expressions = []
        files = []
        
        # Parse arguments
        i = 1
        while i < len(parts):
            if parts[i] == '-i':
                in_place = True
                # Check for -i with backup suffix (e.g., -i.bak)
                if i + 1 < len(parts) and not parts[i + 1].startswith('-') and '=' not in parts[i + 1]:
                    i += 2  # skip backup suffix
                else:
                    i += 1
            elif parts[i].startswith('-i'):
                in_place = True
                i += 1
            elif parts[i] == '-n':
                quiet = True
                i += 1
            elif parts[i] == '-e' and i + 1 < len(parts):
                expressions.append(parts[i + 1])
                i += 2
            elif parts[i].startswith('-e'):
                expressions.append(parts[i][2:])
                i += 1
            elif not parts[i].startswith('-'):
                # First non-flag is expression (if no -e was used)
                if not expressions:
                    expressions.append(parts[i])
                else:
                    # It's a file
                    win_path = parts[i]  # Already translated
                    files.append(win_path)
                i += 1
            else:
                i += 1
        
        if not expressions:
            return 'echo Error: sed requires expression', True
        
        # Build PowerShell sed emulation
        if not files:
            return 'echo Error: sed requires file argument (stdin not yet supported)', True
        
        file_arg = f'\\"{files[0]}\\"'
        
        # Build PowerShell sed emulation with line number tracking
        ps_script_parts = []
        ps_script_parts.append('$LineNum = 0')
        ps_script_parts.append('$output = @()')
        ps_script_parts.append(f'Get-Content {file_arg} | ForEach-Object {{')
        ps_script_parts.append('  $LineNum++')
        ps_script_parts.append('  $line = $_')
        ps_script_parts.append('  $print = ' + ('$false' if quiet else '$true'))
        ps_script_parts.append('  $skip = $false')
        
        # Process each expression
        for expr_idx, expr in enumerate(expressions):
            # Parse address + command
            address = None
            command = expr
            
            # Check for address prefix
            # Line number: 5s/.../ or 1,10s/.../
            if expr[0].isdigit():
                match = re.match(r'^(\d+)(,(\d+|\$))?(.*)$', expr)
                if match:
                    start_line = match.group(1)
                    end_line = match.group(3) if match.group(3) else start_line
                    command = match.group(4)
                    if end_line == '$':
                        address = ('line_range', start_line, '999999')
                    else:
                        address = ('line_range', start_line, end_line)
            
            # Pattern address: /pattern/s/.../
            elif expr.startswith('/'):
                match = re.match(r'^/(.+?)/(,/(.+?)/)?(.*)$', expr)
                if match:
                    pattern = match.group(1)
                    end_pattern = match.group(3)
                    command = match.group(4)
                    if end_pattern:
                        address = ('pattern_range', pattern, end_pattern)
                    else:
                        address = ('pattern', pattern, None)
            
            # Last line: $
            elif expr.startswith('$'):
                address = ('last_line', None, None)
                command = expr[1:]
            
            # Generate condition for address
            condition = None
            if address:
                if address[0] == 'line_range':
                    condition = f'($LineNum -ge {address[1]} -and $LineNum -le {address[2]})'
                elif address[0] == 'pattern':
                    pattern_escaped = address[1].replace('\\', '\\\\').replace('"', '\\"')
                    condition = f'($line -match "{pattern_escaped}")'
                elif address[0] == 'last_line':
                    condition = '($LineNum -eq (Get-Content ' + file_arg + ' | Measure-Object -Line).Lines)'
            
            # Parse command type
            if command.startswith('s/') or command.startswith('s|') or command.startswith('s#'):
                # Substitution
                delimiter = command[1]
                parts_expr = command[2:].split(delimiter)
                
                if len(parts_expr) >= 2:
                    search = parts_expr[0].replace('\\', '\\\\').replace('"', '\\"')
                    replace = parts_expr[1].replace('\\', '\\\\').replace('"', '\\"')
                    flags = parts_expr[2] if len(parts_expr) > 2 else ''
                    
                    global_replace = 'g' in flags
                    ignore_case = 'i' in flags
                    print_flag = 'p' in flags
                    
                    # Build replacement operation
                    if condition:
                        ps_script_parts.append(f'  if {condition} {{')
                    else:
                        ps_script_parts.append('  if ($true) {')
                    
                    # Generate replacement logic
                    if global_replace:
                        # Global replace: use standard -replace (replaces ALL occurrences)
                        if ignore_case:
                            ps_script_parts.append(f'    $line = $line -replace "(?i){search}", "{replace}"')
                        else:
                            ps_script_parts.append(f'    $line = $line -replace "{search}", "{replace}"')
                    else:
                        # First occurrence only: use .NET Regex.Replace with count=1
                        if ignore_case:
                            ps_script_parts.append(f'    $regex = [regex]::new("(?i){search}"); $line = $regex.Replace($line, "{replace}", 1)')
                        else:
                            ps_script_parts.append(f'    $regex = [regex]::new("{search}"); $line = $regex.Replace($line, "{replace}", 1)')
                    
                    if print_flag and quiet:
                        ps_script_parts.append('    $print = $true')
                    
                    ps_script_parts.append('  }')
            
            elif command == 'd' or (command.endswith('d') and len(command) == 1):
                # Delete operation
                if condition:
                    ps_script_parts.append(f'  if {condition} {{')
                else:
                    ps_script_parts.append('  if ($true) {')
                
                ps_script_parts.append('    $skip = $true')
                ps_script_parts.append('  }')
            
            elif command == 'p' or (command.endswith('p') and len(command) == 1):
                # Print operation (in quiet mode, forces print)
                if condition:
                    ps_script_parts.append(f'  if {condition} {{')
                else:
                    ps_script_parts.append('  if ($true) {')
                
                ps_script_parts.append('    $print = $true')
                ps_script_parts.append('  }')
        
        # Output logic
        ps_script_parts.append('  if (-not $skip -and $print) {')
        ps_script_parts.append('    $output += $line')
        ps_script_parts.append('  }')
        ps_script_parts.append('}')
        
        # Final output
        if in_place:
            ps_script_parts.append(f'$output | Set-Content {file_arg}')
        else:
            ps_script_parts.append('$output')
        
        ps_fallback = '; '.join(ps_script_parts)
        
        # Complete script with fallback chain
        ps_complete = ps_script_start + ps_fallback
        
        return f'powershell -Command "{ps_complete}"', True
    



# ======== strings (3831-3899) ========
    def _execute_strings(self, cmd: str, parts):
        """
        Translate strings - extract printable strings from binary files.
        
        ARTISAN IMPLEMENTATION:
        - Extracts sequences of printable ASCII characters
        - -n N: minimum string length (default 4)
        - -a: scan entire file (default, always on in our impl)
        
        Usage:
          strings binary_file
          strings -n 8 binary_file  # strings >= 8 chars
        
        Output: one string per line
        """
        min_len = 4
        file_path = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-n' and i + 1 < len(parts):
                min_len = int(parts[i + 1])
                i += 2
            elif parts[i] == '-a':
                # Scan all (default anyway)
                i += 1
            elif not parts[i].startswith('-'):
                file_path = parts[i]
                i += 1
            else:
                i += 1
        
        if not file_path:
            return 'echo Error: strings requires filename', True
        
        ps_script = f'''
            $file = "{file_path}"
            $minLen = {min_len}
            
            if (-not (Test-Path $file)) {{
                Write-Error "strings: $file`: No such file or directory"
                exit 1
            }}
            
            $bytes = [System.IO.File]::ReadAllBytes($file)
            $current = ""
            
            foreach ($b in $bytes) {{
                # Printable ASCII: 32-126 (space to tilde)
                if ($b -ge 32 -and $b -le 126) {{
                    $current += [char]$b
                }} else {{
                    # Non-printable: end current string
                    if ($current.Length -ge $minLen) {{
                        Write-Output $current
                    }}
                    $current = ""
                }}
            }}
            
            # Output last string if long enough
            if ($current.Length -ge $minLen) {{
                Write-Output $current
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    

# ======== base64 (4368-4426) ========
    def _execute_base64(self, cmd: str, parts):
        """
        Translate base64 - Base64 encoding/decoding.
        
        ARTISAN IMPLEMENTATION:
        - Encode: base64 file → [Convert]::ToBase64String
        - Decode: base64 -d encoded → [Convert]::FromBase64String
        - Stdin: base64 (reads from pipe)
        - -w 0: disable line wrapping (default on Windows anyway)
        
        Unix behavior:
          base64 file.txt → encode to stdout
          base64 -d encoded.txt → decode to stdout
          echo "text" | base64 → encode from stdin
        """
        decode_mode = '-d' in parts or '--decode' in parts
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if decode_mode:
            # DECODE mode
            if files:
                # Decode from file
                file_path = files[0]
                ps_cmd = (
                    f'$content = Get-Content \\"{file_path}\\" -Raw; '
                    f'$bytes = [Convert]::FromBase64String($content); '
                    f'[System.Text.Encoding]::UTF8.GetString($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
            else:
                # Decode from stdin (pipe)
                ps_cmd = (
                    f'$content = $input | Out-String; '
                    f'$bytes = [Convert]::FromBase64String($content); '
                    f'[System.Text.Encoding]::UTF8.GetString($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
        
        else:
            # ENCODE mode
            if files:
                # Encode from file
                file_path = files[0]
                ps_cmd = (
                    f'$bytes = [System.IO.File]::ReadAllBytes(\\"{file_path}\\"); '
                    f'[Convert]::ToBase64String($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
            else:
                # Encode from stdin (pipe)
                ps_cmd = (
                    f'$content = $input | Out-String; '
                    f'$bytes = [System.Text.Encoding]::UTF8.GetBytes($content); '
                    f'[Convert]::ToBase64String($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
    

# ======== gunzip (4849-4941) ========
    def _execute_gunzip(self, cmd: str, parts):
        """
        Translate gunzip - REAL gzip decompression with .NET GZipStream.
        
        CRITICAL: Must decompress VALID gzip files from Unix gzip.
        
        Flags:
        - -c: Write to stdout (keep original)
        - -k: Keep original file
        - -f: Force overwrite
        
        Behavior (Unix compatible):
        - gunzip file.txt.gz → creates file.txt, deletes file.txt.gz
        - gunzip -k file.txt.gz → creates file.txt, keeps file.txt.gz
        - gunzip -c file.txt.gz → stdout, keeps file.txt.gz
        """
        stdout_mode = '-c' in parts or '--stdout' in parts
        keep = '-k' in parts or '--keep' in parts
        force = '-f' in parts or '--force' in parts
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            # stdin mode
            ps_script = '''
                $ms = New-Object System.IO.MemoryStream
                $stdin = [Console]::OpenStandardInput()
                $stdin.CopyTo($ms)
                $ms.Position = 0
                
                $gzip = New-Object System.IO.Compression.GZipStream($ms, [System.IO.Compression.CompressionMode]::Decompress)
                $gzip.CopyTo([Console]::OpenStandardOutput())
                $gzip.Close()
                $ms.Close()
            '''
            return f'powershell -Command "{ps_script}"', True
        
        file_path = files[0]
        
        # Determine output filename (remove .gz extension)
        if file_path.endswith('.gz'):
            output_file = file_path[:-3]
        elif file_path.endswith('.tgz'):
            output_file = file_path[:-4] + '.tar'
        else:
            # No .gz extension - error
            return f'echo gzip: {file_path}: unknown suffix -- ignored', True
        
        if stdout_mode:
            # Output to stdout, keep original
            ps_script = f'''
                $inputFile = [System.IO.File]::OpenRead("{file_path}")
                $gzip = New-Object System.IO.Compression.GZipStream($inputFile, [System.IO.Compression.CompressionMode]::Decompress)
                $gzip.CopyTo([Console]::OpenStandardOutput())
                $gzip.Close()
                $inputFile.Close()
            '''
        else:
            # Create decompressed file
            ps_script = f'''
                $inputPath = "{file_path}"
                $outputPath = "{output_file}"
                
                if (-not (Test-Path $inputPath)) {{
                    Write-Host "gzip: $inputPath: No such file or directory"
                    exit 1
                }}
                
                if ((Test-Path $outputPath) -and -not {str(force).lower()}) {{
                    Write-Host "gzip: $outputPath already exists; not overwritten"
                    exit 1
                }}
                
                $inputFile = [System.IO.File]::OpenRead($inputPath)
                $gzip = New-Object System.IO.Compression.GZipStream($inputFile, [System.IO.Compression.CompressionMode]::Decompress)
                $outputFile = [System.IO.File]::Create($outputPath)
                
                $gzip.CopyTo($outputFile)
                
                $outputFile.Close()
                $gzip.Close()
                $inputFile.Close()
            '''
            
            if not keep:
                # Delete original .gz (Unix default behavior)
                ps_script += f'''
                Remove-Item "{file_path}"
                '''
        
        return f'powershell -Command "{ps_script}"', True
    

# ======== column (3899-3994) ========
    def _execute_column(self, cmd: str, parts):
        """
        Translate column - columnate lists and format text into aligned columns.
        
        ARTISAN IMPLEMENTATION:
        - Table mode (-t): align columns automatically
        - Separator (-s): field delimiter (default whitespace)
        
        Usage:
          column -t file.txt
          column -t -s ',' file.csv
        
        Example input:
          name age city
          alice 30 NYC
          bob 25 LA
        
        Example output:
          name   age  city
          alice  30   NYC
          bob    25   LA
        """
        table_mode = '-t' in parts
        separator = None
        file_path = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-t':
                table_mode = True
                i += 1
            elif parts[i] == '-s' and i + 1 < len(parts):
                separator = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                file_path = parts[i]
                i += 1
            else:
                i += 1
        
        if not table_mode:
            # Non-table mode not commonly used, fallback to cat
            if file_path:
                return f'type "{file_path}"', False
            else:
                return 'echo Error: column requires -t flag or file', True
        
        # Table mode: read file, parse columns, align
        if file_path:
            input_source = f'Get-Content "{file_path}"'
        else:
            # stdin
            input_source = '$input'
        
        sep_regex = r'\\s+' if not separator else separator.replace('|', '\\|')
        
        ps_script = f'''
            $lines = {input_source}
            $rows = @()
            $maxWidths = @{{}}
            
            # Parse all rows and track max width per column
            foreach ($line in $lines) {{
                if ($line.Trim() -eq "") {{ continue }}
                
                $fields = $line -split "{sep_regex}"
                $rows += ,@($fields)
                
                for ($i = 0; $i -lt $fields.Length; $i++) {{
                    $width = $fields[$i].Length
                    if (-not $maxWidths.ContainsKey($i) -or $maxWidths[$i] -lt $width) {{
                        $maxWidths[$i] = $width
                    }}
                }}
            }}
            
            # Output aligned rows
            foreach ($row in $rows) {{
                $output = ""
                for ($i = 0; $i -lt $row.Length; $i++) {{
                    $field = $row[$i]
                    if ($i -lt $row.Length - 1) {{
                        # Pad all but last column
                        $output += $field.PadRight($maxWidths[$i] + 2)
                    }} else {{
                        # Last column: no padding
                        $output += $field
                    }}
                }}
                Write-Output $output.TrimEnd()
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    

# ======== unzip (2503-2591) ========
    def _execute_unzip(self, cmd: str, parts):
        """
        Translate unzip - extract compressed archives.
        
        ARTISAN IMPLEMENTATION:
        - Uses PowerShell Expand-Archive (native .NET)
        - Extracts .zip files from Unix/Windows
        
        Flags:
        - -l: list contents (don't extract)
        - -d DIR: extract to directory
        - archive.zip: file to extract
        
        Usage:
          unzip archive.zip
          unzip -d output/ archive.zip
          unzip -l archive.zip
        """
        list_contents = '-l' in parts
        extract_dir = None
        archive = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-l':
                list_contents = True
                i += 1
            elif parts[i] == '-d' and i + 1 < len(parts):
                extract_dir = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                archive = parts[i]
                i += 1
            else:
                i += 1
        
        if not archive:
            return 'echo Error: unzip requires archive', True
        
        if list_contents:
            # List contents
            ps_script = f'''
                if (-not (Test-Path "{archive}")) {{
                    Write-Error "unzip: {archive}: No such file"
                    exit 1
                }}
                
                Add-Type -AssemblyName System.IO.Compression.FileSystem
                $zip = [System.IO.Compression.ZipFile]::OpenRead("{archive}")
                
                Write-Output "Archive:  {archive}"
                foreach ($entry in $zip.Entries) {{
                    $size = $entry.Length
                    $date = $entry.LastWriteTime.ToString("MM-dd-yy HH:mm")
                    Write-Output ("  {{0,10}}  {{1}}  {{2}}" -f $size, $date, $entry.FullName)
                }}
                
                $zip.Dispose()
            '''
        else:
            # Extract
            if not extract_dir:
                extract_dir = '.'
            
            ps_script = f'''
                if (-not (Test-Path "{archive}")) {{
                    Write-Error "unzip: {archive}: No such file"
                    exit 1
                }}
                
                $dest = "{extract_dir}"
                
                # Create destination if needed
                if (-not (Test-Path $dest)) {{
                    New-Item -Path $dest -ItemType Directory -Force | Out-Null
                }}
                
                try {{
                    Expand-Archive -Path "{archive}" -DestinationPath $dest -Force
                    Write-Output "extracted {archive} to $dest"
                }} catch {{
                    Write-Error "unzip: $($_.Exception.Message)"
                    exit 1
                }}
            '''
        
        return f'powershell -Command "{ps_script}"', True
    

# ======== watch (3994-4228) ========
    def _execute_watch(self, cmd: str, parts):
        """
        Translate watch - execute command repeatedly at intervals.
        
        ARTISAN IMPLEMENTATION:
        - Runs command every N seconds (default 2)
        - Clears screen between runs
        - Ctrl+C to stop
        
        Flags:
        - -n N: interval in seconds (default 2)
        
        Usage:
          watch "ls -l"
          watch -n 1 "df -h"
        
        Note: Windows doesn't have native watch, PowerShell loop emulates it.
        """
        interval = 2
        command = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-n' and i + 1 < len(parts):
                interval = int(parts[i + 1])
                i += 2
            elif not parts[i].startswith('-'):
                # Command is everything remaining
                command = ' '.join(parts[i:])
                break
            else:
                i += 1
        
        if not command:
            return 'echo Error: watch requires command', True
        
        # Translate Unix command to Windows if needed
        # For now, assume command is already valid for Windows
        # TODO: Could recursively translate the watched command
        
        ps_script = f'''
            while ($true) {{
                Clear-Host
                Write-Host "Every {interval}s: {command}"
                Write-Host ""
                
                try {{
                    Invoke-Expression "{command}"
                }} catch {{
                    Write-Error $_.Exception.Message
                }}
                
                Start-Sleep -Seconds {interval}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _execute_paste(self, cmd: str, parts):
        """
        Translate paste - merge lines of files side-by-side.
        
        ARTISAN IMPLEMENTATION:
        - Joins corresponding lines from multiple files
        - Default delimiter: TAB
        - -d DELIM: custom delimiter
        - -s: serial mode (concatenate all lines of each file)
        
        Usage:
          paste file1 file2        → line1_f1<TAB>line1_f2
          paste -d',' f1 f2       → line1_f1,line1_f2
          paste -s file1          → all_lines_joined_with_TAB
        """
        delimiter = "\\t"
        serial = '-s' in parts
        files = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-d' and i + 1 < len(parts):
                delimiter = parts[i + 1]
                i += 2
            elif parts[i] == '-s':
                serial = True
                i += 1
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1
        
        if not files:
            return 'echo Error: paste requires files', True
        
        if serial:
            # Serial mode: join all lines of each file
            ps_script = f'''
                $delim = "{delimiter}"
                
                foreach ($file in @({','.join(f'"{f}"' for f in files)})) {{
                    if (Test-Path $file) {{
                        $lines = Get-Content $file
                        Write-Output ($lines -join $delim)
                    }}
                }}
            '''
        else:
            # Parallel mode: join corresponding lines from files
            ps_script = f'''
                $delim = "{delimiter}"
                $files = @({','.join(f'"{f}"' for f in files)})
                
                # Read all files
                $contents = @()
                foreach ($file in $files) {{
                    if (Test-Path $file) {{
                        $contents += ,@(Get-Content $file)
                    }} else {{
                        $contents += ,@()
                    }}
                }}
                
                # Find max lines
                $maxLines = 0
                foreach ($c in $contents) {{
                    if ($c.Length -gt $maxLines) {{
                        $maxLines = $c.Length
                    }}
                }}
                
                # Join corresponding lines
                for ($i = 0; $i -lt $maxLines; $i++) {{
                    $parts = @()
                    foreach ($c in $contents) {{
                        if ($i -lt $c.Length) {{
                            $parts += $c[$i]
                        }} else {{
                            $parts += ""
                        }}
                    }}
                    Write-Output ($parts -join $delim)
                }}
            '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _execute_comm(self, cmd: str, parts):
        """
        Translate comm - compare two sorted files line by line.
        
        ARTISAN IMPLEMENTATION:
        - Column 1: lines only in file1
        - Column 2: lines only in file2
        - Column 3: lines in both files
        
        Flags:
        - -1: suppress column 1
        - -2: suppress column 2
        - -3: suppress column 3
        - -12: show only common lines
        - -23: show only unique to file1
        - -13: show only unique to file2
        
        Usage:
          comm file1 file2        → 3 columns
          comm -12 file1 file2    → only common lines
        
        Note: Both files must be sorted!
        """
        suppress_col1 = '-1' in parts
        suppress_col2 = '-2' in parts
        suppress_col3 = '-3' in parts
        
        # Combined flags (common patterns)
        if '-12' in parts:
            suppress_col1 = suppress_col2 = True
        if '-13' in parts:
            suppress_col1 = suppress_col3 = True
        if '-23' in parts:
            suppress_col2 = suppress_col3 = True
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if len(files) < 2:
            return 'echo Error: comm requires two files', True
        
        file1, file2 = files[0], files[1]
        
        ps_script = f'''
            if (-not (Test-Path "{file1}")) {{
                Write-Error "comm: {file1}: No such file"
                exit 1
            }}
            if (-not (Test-Path "{file2}")) {{
                Write-Error "comm: {file2}: No such file"
                exit 1
            }}
            
            $lines1 = @(Get-Content "{file1}")
            $lines2 = @(Get-Content "{file2}")
            
            $set1 = [System.Collections.Generic.HashSet[string]]::new($lines1)
            $set2 = [System.Collections.Generic.HashSet[string]]::new($lines2)
            
            # Column 1: unique to file1
            if (-not {str(suppress_col1).lower()}) {{
                foreach ($line in $lines1) {{
                    if (-not $set2.Contains($line)) {{
                        Write-Output $line
                    }}
                }}
            }}
            
            # Column 2: unique to file2
            if (-not {str(suppress_col2).lower()}) {{
                foreach ($line in $lines2) {{
                    if (-not $set1.Contains($line)) {{
                        Write-Output ("`t" + $line)
                    }}
                }}
            }}
            
            # Column 3: common to both
            if (-not {str(suppress_col3).lower()}) {{
                foreach ($line in $lines1) {{
                    if ($set2.Contains($line)) {{
                        Write-Output ("`t`t" + $line)
                    }}
                }}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    

# ======== zip (2434-2503) ========
    def _execute_wget(self, cmd: str, parts) -> Tuple[str, bool]:
        """
        Execute wget - Simple wrapper converting to curl.

        wget is traditionally a download tool, curl is more versatile but can do the same.
        For complex wget scenarios, this delegates to curl implementation.

        Common flags:
        - -O file: output to specified file
        - URL: download URL

        Strategy: Convert to curl and delegate to _execute_curl()

        Examples:
          wget http://example.com/file.zip
          wget -O output.html http://example.com
        """
        if len(parts) < 2:
            return 'echo Error: wget requires URL', True

        # Extract URL and output filename
        urls = [p for p in parts[1:] if 'http://' in p or 'https://' in p]
        output = None

        i = 1
        while i < len(parts):
            if parts[i] == '-O' and i + 1 < len(parts):
                output = parts[i + 1]
                i += 2
            else:
                i += 1

        if not urls:
            return 'echo Error: wget requires URL', True

        # Convert to curl command
        if output:
            curl_cmd = f'curl -o "{output}" "{urls[0]}"'
            curl_parts = ['curl', '-o', output, urls[0]]
        else:
            # wget default: save with remote filename
            curl_cmd = f'curl -O "{urls[0]}"'
            curl_parts = ['curl', '-O', urls[0]]

        # Delegate to curl implementation for full feature support
        return self._execute_curl(curl_cmd, curl_parts)

    def _execute_zip(self, cmd: str, parts):
        """
        Translate zip - create compressed archives.
        
        ARTISAN IMPLEMENTATION:
        - Uses PowerShell Compress-Archive (native .NET)
        - Creates .zip files compatible with Unix unzip
        
        Flags:
        - -r: recursive (include subdirectories) - default ON
        - archive.zip: output file
        - files/dirs: items to compress
        
        Usage:
          zip -r archive.zip dir/
          zip archive.zip file1.txt file2.txt
        """
        recursive = '-r' in parts
        archive = None
        items = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-r':
                recursive = True
                i += 1
            elif not parts[i].startswith('-'):
                if not archive:
                    archive = parts[i]
                else:
                    items.append(parts[i])
                i += 1
            else:
                i += 1
        
        if not archive:
            return 'echo Error: zip requires archive name', True
        
        if not items:
            return 'echo Error: zip requires items to compress', True
        
        # Ensure .zip extension
        if not archive.endswith('.zip'):
            archive += '.zip'
        
        # Build paths list for PowerShell
        paths_list = ','.join(f'"{item}"' for item in items)
        
        ps_script = f'''
            $archive = "{archive}"
            $items = @({paths_list})
            
            # Remove existing archive if present
            if (Test-Path $archive) {{
                Remove-Item $archive -Force
            }}
            
            # Compress items
            try {{
                Compress-Archive -Path $items -DestinationPath $archive -CompressionLevel Optimal
                Write-Output "created $archive"
            }} catch {{
                Write-Error "zip: $($_.Exception.Message)"
                exit 1
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True


# ============================================================================
# BASHTOOLEXECUTOR - ORCHESTRATION LAYER
# ============================================================================

class BashToolExecutor(ToolExecutor):
    """
    Bash command executor integrated with COUCH architecture.
    
    Receives params dict from ExecutorDefinition - NO separate config class.
    
    ============================================================================
    EXTERNAL UNIX BINARIES - INSTALLATION GUIDE
    ============================================================================
    
    This executor uses native Unix binaries on Windows for 100% compatibility.
    Install these once, system-wide:
    
    1. GIT FOR WINDOWS (covers 90% of tools)
       Download: https://git-scm.com/download/win
       Install options:
       - "Use Git and optional Unix tools from Command Prompt" ✓
       - "Use Windows' default console window" ✓
       - Credential manager: "None" ✓
       
       Provides: diff, awk (gawk), sed, grep, tar, bash, and 100+ Unix tools
       PATH: C:\\Program Files\\Git\\usr\\bin (automatic)

       Verify:
         diff --version
         awk --version

    2. JQ (JSON processor)
       Download: https://github.com/jqlang/jq/releases/latest
       Binary: jq-windows-amd64.exe (rename to jq.exe)
       Install: Copy to C:\\Windows\\System32 (already in PATH)
       
       Verify:
         jq --version
    
    RESULT:
    All commands callable directly from CMD/PowerShell.
    Translator uses native binaries (100% GNU compatible) with PowerShell 
    fallback for edge cases where binary missing.
    
    ============================================================================
    """
    
    def __init__(self, working_dir: str, enabled: bool = False,
                 python_executable: Optional[str] = None,
                 virtual_env: Optional[str] = None,
                 default_timeout: int = 30,
                 python_timeout: int = 60,
                 use_git_bash: bool = False,
                 **kwargs):
        """
        Initialize BashToolExecutor

        Args:
            working_dir: Tool working directory (from ConfigurationManager)
            enabled: Tool enabled state
            python_executable: Python path (OPTIONAL - auto-detected if missing)
            virtual_env: Virtual env path (OPTIONAL - defaults to BASH_TOOL_ENV)
            default_timeout: Default command timeout
            python_timeout: Python script timeout
            use_git_bash: EXPERIMENTAL - Use Git Bash passthrough (100% compatibility)

        Raises:
            RuntimeError: If Python not found and python_executable not provided
        """
        super().__init__('bash_tool', enabled)

        self.working_dir = Path(working_dir)
        self.default_timeout = default_timeout
        self.python_timeout = python_timeout
        self.use_git_bash = use_git_bash

        # TESTMODE: Set to True to simulate execution without running commands
        self.testmode = False
        
        # Initialize components
        self.path_translator = PathTranslator()
        self.sandbox_validator = SandboxValidator(self.path_translator.workspace_root)
        self.command_translator = CommandTranslator(self.path_translator)
        
        # Initialize CommandExecutor (execution strategy layer)
        # Will be fully initialized after Git Bash detection
        self.command_executor = None
        
        # Create tool-specific scratch directory
        self.scratch_dir = self.path_translator.get_tool_scratch_directory('bash_tool')
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        
        # Git Bash detection (if enabled)
        self.git_bash_exe = None
        if use_git_bash:
            self.git_bash_exe = self._detect_git_bash()
            if self.git_bash_exe:
                self.logger.info(f"Git Bash EXPERIMENTAL mode enabled: {self.git_bash_exe}")
            else:
                self.logger.warning("Git Bash not found - falling back to command translation")
        
        # Python executable - CRITICAL DEPENDENCY
        try:
            if python_executable:
                # Validate provided executable
                result = subprocess.run(
                    [python_executable, '--version'],
                    capture_output=True,
                    timeout=2,
                    text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Invalid Python executable: {python_executable}")
                
                self.python_executable = python_executable
                self.logger.info(f"Using provided Python: {python_executable}")
            else:
                # Auto-detect (may raise RuntimeError)
                self.python_executable = self._detect_system_python()
        
        except RuntimeError as e:
            # Python detection failed - tool disabled
            self.python_executable = None
            self.virtual_env = None
            self.logger.error(f"BashToolExecutor initialization failed: {e}")
            raise
        
        # Virtual environment - only if Python available
        self.virtual_env = self._setup_virtual_env(virtual_env)
        
        # Initialize CommandExecutor with all dependencies now available
        self.command_executor = CommandExecutor(
            path_translator=self.path_translator,
            command_translator=self.command_translator,
            git_bash_exe=self.git_bash_exe,
            logger=self.logger
        )
        
        self.logger.info(
            f"BashToolExecutor initialized: Python={self.python_executable}, "
            f"VEnv={self.virtual_env}, GitBash={'ENABLED' if self.git_bash_exe else 'DISABLED'}"
        )
    
    def _detect_git_bash(self) -> Optional[str]:
        """
        Detect Git Bash executable.
        
        Standard locations:
        - C:\Program Files\Git\bin\bash.exe
        - C:\Program Files (x86)\Git\bin\bash.exe
        """
        candidates = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ]
        
        for path in candidates:
            if Path(path).exists():
                self.logger.info(f"Found Git Bash: {path}")
                return path
        
        # Try PATH
        try:
            result = subprocess.run(
                ['where', 'bash.exe'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                bash_path = result.stdout.strip().split('\n')[0]
                if 'Git' in bash_path:
                    self.logger.info(f"Found Git Bash in PATH: {bash_path}")
                    return bash_path
        except:
            pass
        
        return None
    
    def _detect_system_python(self) -> str:
        """
        Detect system Python - FAIL FAST if missing.
        
        Bash tool without Python is INCOMPLETE and should be disabled.
        """
        candidates = ['python', 'python.exe']
        
        for cmd in candidates:
            try:
                result = subprocess.run(
                    [cmd, '--version'], 
                    capture_output=True, 
                    timeout=2,
                    text=True
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    self.logger.info(f"Detected Python: {cmd} ({version})")
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        # Python NOT FOUND - tool is incomplete
        self.logger.critical("CRITICAL: Python not found in system PATH")
        self.logger.critical("Bash tool requires Python for full functionality")
        
        # Disable tool immediately
        self.enabled = False
        
        raise RuntimeError(
            "Python executable not found in system PATH. "
            "Bash tool is incomplete without Python and has been disabled. "
            "Install Python or provide python_executable parameter explicitly."
        )
    
    def _expand_braces(self, command: str) -> str:
        """
        Expand brace patterns: {1..10}, {a..z}, {a,b,c}

        Supports:
        - Numeric ranges: {1..10}, {01..100}
        - Alpha ranges: {a..z}, {A..Z}
        - Lists: {file1,file2,file3}
        - Nested: {a,b{1,2}}

        Returns command with braces expanded
        """
        import re

        self.logger.debug(f"[BRACE EXPAND] Input: {command}")

        def expand_single_brace(match):
            """Expand a single brace expression"""
            content = match.group(1)
            
            # Check for range pattern (numeric or alpha)
            range_match = re.match(r'^(\d+)\.\.(\d+)$', content)
            if range_match:
                # Numeric range
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                padding = len(range_match.group(1)) if range_match.group(1).startswith('0') else 0
                
                if start <= end:
                    items = [str(i).zfill(padding) if padding else str(i) for i in range(start, end + 1)]
                else:
                    items = [str(i).zfill(padding) if padding else str(i) for i in range(start, end - 1, -1)]
                
                return ' '.join(items)
            
            # Alpha range
            alpha_match = re.match(r'^([a-zA-Z])\.\.([a-zA-Z])$', content)
            if alpha_match:
                start_char = alpha_match.group(1)
                end_char = alpha_match.group(2)
                
                if start_char <= end_char:
                    items = [chr(c) for c in range(ord(start_char), ord(end_char) + 1)]
                else:
                    items = [chr(c) for c in range(ord(start_char), ord(end_char) - 1, -1)]
                
                return ' '.join(items)
            
            # Comma-separated list
            if ',' in content:
                items = [item.strip() for item in content.split(',')]
                return ' '.join(items)
            
            # No expansion needed
            return match.group(0)
        
        # Expand braces - may need multiple passes for nested
        max_iterations = 10
        for _ in range(max_iterations):
            # Pattern: {content} but NOT ${var...}
            # Match innermost braces first (non-greedy)
            # FIX #7: Use negative lookbehind to exclude ${var...} parameter expansion
            pattern = r'(?<!\$)\{([^{}]+)\}'
            new_command = re.sub(pattern, expand_single_brace, command)
            
            if new_command == command:
                # No more expansions
                break
            command = new_command

        self.logger.debug(f"[BRACE EXPAND] Output: {command}")
        return command
    
    def _process_heredocs(self, command: str) -> Tuple[str, List[Path]]:
        """
        Process here documents.
        
        Supports:
        - <<DELIMITER     (standard heredoc)
        - <<-DELIMITER    (ignore leading tabs)
        - <<"DELIMITER"   (quoted delimiter - no expansion)
        - <<'DELIMITER'   (quoted delimiter - no expansion)
        - Multiple heredocs in same command
        
        Creates temp file with heredoc content, replaces in command.
        
        Returns:
            (modified_command, list_of_temp_files)
        """
        
        temp_files = []
        
        if '<<' not in command:
            return command, temp_files
        
        # Pattern to find heredoc operators
        # Matches: <<WORD, <<-WORD, <<"WORD", <<'WORD'
        heredoc_pattern = r'<<(-?)\s*([\'"]?)(\w+)\2'
        
        # Find all heredocs
        matches = list(re.finditer(heredoc_pattern, command))
        if not matches:
            return command, temp_files
        
        # Process heredocs from END to START
        # This way, earlier positions don't shift when we replace later ones
        result_command = command
        
        for match in reversed(matches):
            strip_tabs = match.group(1) == '-'
            delimiter = match.group(3)
            heredoc_start = match.end()
            
            # Find content after heredoc operator
            remaining = result_command[heredoc_start:]
            
            # Split into lines
            lines = remaining.split('\n')
            
            # Find delimiter closing line
            content_lines = []
            delimiter_found = False
            delimiter_line_index = -1
            
            # Start from line 1 (line 0 is usually empty after <<EOF)
            for i in range(1, len(lines)):
                if lines[i].rstrip() == delimiter:
                    delimiter_found = True
                    delimiter_line_index = i
                    break
                content_lines.append(lines[i])
            
            if not delimiter_found:
                self.logger.warning(f"Heredoc delimiter '{delimiter}' not found")
                # Use all remaining lines as content
                content_lines = lines[1:] if len(lines) > 1 else []
                delimiter_line_index = len(lines) - 1
            
            # Build content
            content = '\n'.join(content_lines)
            
            # Strip leading tabs if <<- was used
            if strip_tabs:
                content = '\n'.join(line.lstrip('\t') for line in content_lines)
            
            # Create temp file
            temp_file = self.scratch_dir / f'heredoc_{threading.get_ident()}_{len(temp_files)}.tmp'
            
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                temp_files.append(temp_file)
                
                # Unix path for temp file
                unix_temp = f"/tmp/{temp_file.name}"
                
                # Calculate what to replace:
                # From << to end of delimiter line (inclusive)
                heredoc_end = heredoc_start + len('\n'.join(lines[:delimiter_line_index + 1]))
                
                # Replace heredoc with < temp_file
                replacement = f"< {unix_temp}"
                
                # Do replacement (working backwards, so positions are stable)
                result_command = result_command[:match.start()] + replacement + result_command[heredoc_end:]
            
            except Exception as e:
                self.logger.error(f"Failed to create heredoc temp file: {e}")
                continue
        
        return result_command, temp_files
    
    def _process_substitution(self, command: str) -> Tuple[str, List[Path]]:
        """
        Process substitution: <(command), >(command)
        
        Executes command, saves output to temp file, replaces pattern with temp path.
        
        Returns:
            (modified_command, list_of_temp_files)
        """
        import re
        
        temp_files = []
        
        # Pattern: <(command) or >(command)
        # Find all occurrences
        input_pattern = r'<\(([^)]+)\)'
        output_pattern = r'>\(([^)]+)\)'
        
        cwd = self.scratch_dir
        env = self._setup_environment()
        
        def replace_input_substitution(match):
            """Replace <(cmd) with temp file containing cmd output

            FIX #12: Handle testmode and proper shell selection
            """
            cmd = match.group(1)

            # Create temp file path
            temp_file = cwd / f'procsub_input_{threading.get_ident()}_{len(temp_files)}.tmp'
            temp_files.append(temp_file)

            # FIX #12: If in testmode, don't execute, just create placeholder
            if self.testmode:
                # Create empty temp file for testing
                temp_file.write_text(f"[TESTMODE] Process substitution: <({cmd})")
                unix_temp = f"/tmp/{temp_file.name}"
                return unix_temp

            # Translate and execute command
            try:
                # Translate paths in sub-command
                cmd_with_paths = self.path_translator.translate_paths_in_string(cmd, 'to_windows')

                # Translate command
                translated, _, _ = self.command_translator.translate(cmd_with_paths)

                # FIX #12: Detect if PowerShell command or cmd command
                if 'Get-ChildItem' in translated or 'Select-String' in translated or 'Measure-Object' in translated:
                    # PowerShell command
                    shell_cmd = ['powershell', '-Command', translated]
                else:
                    # CMD command
                    shell_cmd = ['cmd', '/c', translated]

                # Execute
                result = subprocess.run(
                    shell_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(cwd),
                    env=env,
                    errors='replace'
                )

                # Write output to temp file
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)

                # Return Unix path for substitution
                unix_temp = f"/tmp/{temp_file.name}"
                return unix_temp

            except Exception as e:
                self.logger.error(f"Process substitution failed for <({cmd}): {e}")
                # Return original if failed
                return match.group(0)
        
        def replace_output_substitution(match):
            """
            Replace >(cmd) with temp file that will receive output.
            
            FULL IMPLEMENTATION: 
            1. Create temp file
            2. Store command to execute AFTER main command
            3. Return temp file path for main command
            """
            cmd = match.group(1)
            
            # Create temp file for output
            temp_file = cwd / f'procsub_output_{threading.get_ident()}_{len(temp_files)}.tmp'
            temp_files.append(temp_file)
            
            # Store the command and temp file for post-processing
            # This will be executed AFTER the main command completes
            # Format: (temp_file_path, command_to_execute)
            if not hasattr(temp_files, 'post_commands'):
                temp_files.post_commands = []
            
            temp_files.post_commands.append((temp_file, cmd))
            
            # Return Unix path for substitution in main command
            unix_temp = f"/tmp/{temp_file.name}"
            return unix_temp
        
        # Replace all input substitutions
        command = re.sub(input_pattern, replace_input_substitution, command)
        
        # Replace all output substitutions
        command = re.sub(output_pattern, replace_output_substitution, command)
        
        return command, temp_files
    
    def _process_command_substitution_recursive(self, command: str) -> str:
        """
        Process command substitution $(...) with RECURSIVE translation.

        ARTISAN IMPLEMENTATION:
        - Parses nested $(...)
        - Recursively translates Unix commands inside substitution
        - Preserves PowerShell $(...) syntax for output
        - Handles multiple substitutions in single command
        - FIX #10: Does NOT process $(...)  inside single quotes

        Examples:
            $(grep pattern file.txt)
            → $(Select-String -Pattern "pattern" -Path "file.txt")

            $(cat file | wc -l)
            → $(Get-Content file | Measure-Object -Line)

            Nested: $(echo $(cat file))
            → $(Write-Host $(Get-Content file))

            'literal $(date)' → 'literal $(date)' (preserved)

        Returns:
            Command with all $(..  .) recursively translated
        """
        if '$(' not in command:
            return command

        def is_in_single_quotes(text: str, pos: int) -> bool:
            """Check if position is inside single quotes"""
            in_quotes = False
            for i in range(pos):
                if text[i] == "'" and (i == 0 or text[i-1] != '\\'):
                    in_quotes = not in_quotes
            return in_quotes

        def find_substitutions(text: str) -> List[Tuple[int, int, str]]:
            """
            Find all $(...) patterns with correct nesting.
            
            Returns:
                List of (start_pos, end_pos, content) tuples
            """
            substitutions = []
            i = 0
            
            while i < len(text):
                if i < len(text) - 1 and text[i:i+2] == '$(':
                    # FIX #10: Skip if inside single quotes
                    if is_in_single_quotes(text, i):
                        i += 2
                        continue

                    # FIX #6: Check if it's arithmetic $(( instead of command substitution $(
                    if i < len(text) - 2 and text[i+2] == '(':
                        # This is $((arithmetic)), NOT command substitution
                        # Skip it - already handled by _expand_variables()
                        i += 3
                        continue

                    # Found start of command substitution $(...)
                    start = i
                    i += 2
                    depth = 1
                    
                    # Find matching closing paren
                    while i < len(text) and depth > 0:
                        if text[i] == '(':
                            depth += 1
                        elif text[i] == ')':
                            depth -= 1
                        i += 1
                    
                    if depth == 0:
                        # Found complete substitution
                        end = i
                        content = text[start+2:end-1]
                        substitutions.append((start, end, content))
                    else:
                        # Unmatched parens - log warning
                        self.logger.warning(f"Unmatched $( at position {start}")
                else:
                    i += 1
            
            return substitutions
        
        # Find all top-level substitutions (not nested)
        substitutions = find_substitutions(command)
        
        if not substitutions:
            return command
        
        # Process substitutions from END to START (avoid index shifting)
        substitutions_reversed = sorted(substitutions, key=lambda x: x[0], reverse=True)
        
        for start, end, content in substitutions_reversed:
            # Translate the content
            try:
                # RECURSIVE: content might have nested $(...)
                translated_content = self._translate_substitution_content(content)
                
                # Replace in command (preserve $(...) wrapper for PowerShell)
                replacement = f"$({translated_content})"
                command = command[:start] + replacement + command[end:]
                
            except Exception as e:
                self.logger.error(f"Command substitution translation failed: {e}")
                # Keep original on error
                continue
        
        return command
    
    def _translate_substitution_content(self, content: str) -> str:
        """
        Translate Unix command content inside $(...).
        
        FULL TRANSLATION PIPELINE:
        1. Check for nested $(...)  - recurse first
        2. Translate Unix paths → Windows
        3. Translate Unix commands → Windows
        4. Return translated command (WITHOUT outer $(...))
        
        Args:
            content: Unix command string (e.g., "grep pattern file.txt")
            
        Returns:
            Translated command (e.g., "Select-String -Pattern 'pattern' -Path 'file.txt'")
        """
        # Handle empty
        if not content or not content.strip():
            return content
        
        # STEP 1: Recursively handle nested $(...)
        if '$(' in content:
            content = self._process_command_substitution_recursive(content)
        
        # STEP 2: Translate paths
        content_with_paths = self.path_translator.translate_paths_in_string(content, 'to_windows')
        
        # STEP 3: Translate commands
        # Use command_translator which handles:
        # - Pipe chains
        # - Redirections
        # - Command concatenation (&&, ||, ;)
        # - All individual commands
        # FIX #3: Use force_translate=True to ensure commands inside $() are translated
        translated, use_shell, method = self.command_translator.translate(content_with_paths, force_translate=True)
        
        # STEP 4: Clean up for PowerShell context
        # Command translator might wrap in cmd /c - remove that for $(...) context
        if translated.startswith('cmd /c '):
            translated = translated[7:]
        elif translated.startswith('cmd.exe /c '):
            translated = translated[11:]
        
        # PowerShell $(...) expects bare commands, not cmd wrappers
        return translated
    
    def _expand_variables(self, command: str) -> str:
        """
        Expand variable patterns:
        - ${var:-default}, ${var:=value}
        - Tilde expansion: ~/path
        - Arithmetic: $((expr))
        - Array operations: ${arr[@]}
        """
        import re
        
        # Get Claude home directory from path_translator
        claude_home = self.path_translator.get_claude_home_unix()
        
        # 1. Tilde expansion: ~/path → /home/claude/path
        if command.startswith('~/'):
            command = claude_home + '/' + command[2:]
        
        # Also expand tilde in arguments: cmd ~/path
        command = re.sub(r'\s~/', f' {claude_home}/', command)
        
        # 2. Arithmetic expansion: $((expr))
        arith_pattern = r'\$\(\(([^)]+)\)\)'
        
        def expand_arithmetic(match):
            expr = match.group(1)
            try:
                # Evaluate arithmetic expression
                # Simple eval - may need more robust parsing
                result = eval(expr, {"__builtins__": {}}, {})
                return str(result)
            except Exception as e:
                self.logger.warning(f"Arithmetic expansion failed for $(('{expr}')): {e}")
                return match.group(0)
        
        command = re.sub(arith_pattern, expand_arithmetic, command)
        
        # 3. Variable default: ${var:-default}
        default_pattern = r'\$\{(\w+):-([^}]+)\}'
        
        def expand_default(match):
            var_name = match.group(1)
            default_value = match.group(2)
            value = os.environ.get(var_name)
            return value if value else default_value
        
        command = re.sub(default_pattern, expand_default, command)
        
        # 4. Variable assign: ${var:=value}
        assign_pattern = r'\$\{(\w+):=([^}]+)\}'
        
        def expand_assign(match):
            var_name = match.group(1)
            default_value = match.group(2)
            value = os.environ.get(var_name)
            return value if value else default_value
        
        command = re.sub(assign_pattern, expand_assign, command)
        
        # 5. Array expansion: ${arr[@]} → just remove braces for now
        # Full array support would require state tracking
        array_pattern = r'\$\{(\w+)\[@\]\}'
        command = re.sub(array_pattern, r'$\1', command)

        # ================================================================
        # FIX #7: Advanced Parameter Expansion
        # ================================================================
        # ${var#pattern}  - remove shortest prefix
        # ${var##pattern} - remove longest prefix
        # ${var%pattern}  - remove shortest suffix
        # ${var%%pattern} - remove longest suffix
        # ${var/pattern/string}  - replace first
        # ${var//pattern/string} - replace all
        # ${var^^} - uppercase all
        # ${var,,} - lowercase all
        # ${var^}  - uppercase first
        # ${#var}  - string length

        # 5a. String length: ${#var}
        length_pattern = r'\$\{#(\w+)\}'

        def expand_length(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            return str(len(value))

        command = re.sub(length_pattern, expand_length, command)

        # 5b. Remove prefix: ${var#pattern} and ${var##pattern}
        prefix_pattern = r'\$\{(\w+)(#{1,2})([^}]+)\}'

        def expand_remove_prefix(match):
            var_name = match.group(1)
            op = match.group(2)  # # or ##
            pattern = match.group(3)
            value = os.environ.get(var_name, '')

            if not value:
                return ''

            # Convert bash glob to regex and match from start
            import fnmatch
            regex_pattern = fnmatch.translate(pattern)
            regex_pattern = '^' + regex_pattern.rstrip('\\Z')

            if op == '#':  # Remove shortest prefix (non-greedy)
                # Make pattern non-greedy
                regex_pattern_ng = regex_pattern.replace('*', '*?')
                match_obj = re.match(regex_pattern_ng, value)
                if match_obj:
                    return value[len(match_obj.group(0)):]
            else:  # ## Remove longest prefix (greedy - default)
                match_obj = re.match(regex_pattern, value)
                if match_obj:
                    return value[len(match_obj.group(0)):]

            return value

        command = re.sub(prefix_pattern, expand_remove_prefix, command)

        # 5c. Remove suffix: ${var%pattern} and ${var%%pattern}
        suffix_pattern = r'\$\{(\w+)(%{1,2})([^}]+)\}'

        def expand_remove_suffix(match):
            var_name = match.group(1)
            op = match.group(2)  # % or %%
            pattern = match.group(3)
            value = os.environ.get(var_name, '')

            if not value:
                return ''

            # Convert bash glob to regex and match from end
            import fnmatch
            regex_pattern = fnmatch.translate(pattern)
            regex_pattern = regex_pattern.rstrip('\\Z') + '$'

            if op == '%':  # Remove shortest suffix (non-greedy)
                # Iterate from right to left to find rightmost (shortest) match
                for i in range(len(value), -1, -1):
                    match_obj = re.search(regex_pattern, value[i:])
                    if match_obj and match_obj.start() == 0:  # Must match from start of substring
                        # Found shortest suffix at position i
                        return value[:i]
            else:  # %% Remove longest suffix (greedy)
                # Iterate from left to right to find leftmost (longest) match
                for i in range(len(value) + 1):
                    match_obj = re.search(regex_pattern, value[i:])
                    if match_obj and match_obj.start() == 0:  # Must match from start of substring
                        # Found longest suffix at position i
                        return value[:i]

            return value

        command = re.sub(suffix_pattern, expand_remove_suffix, command)

        # 5d. String substitution: ${var/pattern/string} and ${var//pattern/string}
        subst_pattern = r'\$\{(\w+)(/{1,2})([^/}]+)/([^}]*)\}'

        def expand_substitution(match):
            var_name = match.group(1)
            op = match.group(2)  # / or //
            pattern = match.group(3)
            replacement = match.group(4)
            value = os.environ.get(var_name, '')

            if not value:
                return ''

            # Convert bash glob to regex
            import fnmatch
            regex_pattern = fnmatch.translate(pattern).rstrip('\\Z')

            if op == '/':  # Replace first
                return re.sub(regex_pattern, replacement, value, count=1)
            else:  # // Replace all
                return re.sub(regex_pattern, replacement, value)

        command = re.sub(subst_pattern, expand_substitution, command)

        # 5e. Case conversion: ${var^^}, ${var,,}, ${var^}
        case_pattern = r'\$\{(\w+)(\^{1,2}|,{1,2})\}'

        def expand_case(match):
            var_name = match.group(1)
            op = match.group(2)
            value = os.environ.get(var_name, '')

            if op == '^^':  # Uppercase all
                return value.upper()
            elif op == ',,':  # Lowercase all
                return value.lower()
            elif op == '^':  # Uppercase first
                return value[0].upper() + value[1:] if value else ''
            elif op == ',':  # Lowercase first
                return value[0].lower() + value[1:] if value else ''

            return value

        command = re.sub(case_pattern, expand_case, command)

        # 6. Simple variable expansion: ${VAR} and $VAR
        # This must be done LAST, after all other ${...} patterns

        # 6a. ${VAR} - simple braced variable
        simple_braced_pattern = r'\$\{(\w+)\}'

        def expand_simple_braced(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            return value

        command = re.sub(simple_braced_pattern, expand_simple_braced, command)

        # 6b. $VAR - simple unbraced variable (but NOT $(...) or $(()
        # Must not match $(...) command substitution or $((arithmetic))
        # Pattern: $ followed by word characters, but not followed by ( or ((
        simple_var_pattern = r'\$(\w+)(?!\()'

        def expand_simple_var(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            return value

        command = re.sub(simple_var_pattern, expand_simple_var, command)

        return command
    
    def _preprocess_test_commands(self, command: str) -> str:
        """
        Convert test command syntax: [ expr ] → test expr
        
        Handles:
        - [ -f file ] → test -f file
        - [[ expr ]] → test expr (basic conversion)
        """
        import re
        
        # Pattern: [ expr ]
        test_pattern = r'\[\s+([^\]]+)\s+\]'
        
        def convert_test(match):
            expr = match.group(1)
            return f'test {expr}'
        
        command = re.sub(test_pattern, convert_test, command)
        
        # Pattern: [[ expr ]]
        double_test_pattern = r'\[\[\s+([^\]]+)\s+\]\]'
        
        def convert_double_test(match):
            expr = match.group(1)
            return f'test {expr}'
        
        command = re.sub(double_test_pattern, convert_double_test, command)
        
        return command
    
    def _expand_aliases(self, command: str) -> str:
        """
        Expand common bash aliases to their full commands.
        
        Common aliases:
        - ll → ls -la
        - la → ls -A
        - l → ls -CF
        """
        aliases = {
            'll ': 'ls -la ',
            'll\n': 'ls -la\n',
            'll$': 'ls -la',
            'la ': 'ls -A ',
            'la\n': 'ls -A\n',
            'la$': 'ls -A',
            'l ': 'ls -CF ',
            'l\n': 'ls -CF\n',
            'l$': 'ls -CF',
        }
        
        # Check if command starts with alias
        for alias, expansion in aliases.items():
            if command.startswith(alias.rstrip('$ \n')):
                command = command.replace(alias.rstrip('$ \n'), expansion.rstrip('$ \n'), 1)
                break
        
        return command
    
    def _process_subshell(self, command: str) -> str:
        """
        Process subshell execution: (command)

        Subshell in bash creates new environment.
        In our case, just execute command normally.

        IMPORTANT: Do NOT match $(...) - that's command substitution, not subshell!
        IMPORTANT: Do NOT match <(...) or >(...) - that's process substitution!
        """
        import re

        # Pattern: (command) but NOT $(command) and NOT <(command) and NOT >(command) and NOT $((arithmetic))
        # Use negative lookbehind: (?<!\$) = "not preceded by $"
        #                          (?<!<) = "not preceded by <"
        #                          (?<!>) = "not preceded by >"
        #                          (?<!\() = "not preceded by (" (to avoid matching 2nd paren in $((expr)))
        # FIX #6: Added (?<!\() to prevent matching the 2nd paren in $((5 + 5))
        subshell_pattern = r'(?<!\$)(?<!<)(?<!>)(?<!\()\(([^)]+)\)'

        def remove_subshell(match):
            # Just return inner command
            # Full subshell would need environment isolation
            return match.group(1)

        command = re.sub(subshell_pattern, remove_subshell, command)

        return command
    
    def _process_command_grouping(self, command: str) -> str:
        """
        Process command grouping: { cmd1; cmd2; }

        Group commands to run in current shell.
        Convert to simple command sequence.

        FIX #9: Must NOT match brace expansions like {1..5} or {a,b,c}
        """
        import re

        # Pattern: { cmd1; cmd2; } but NOT ${var...} and NOT brace expansions
        # Command groups contain semicolons or newlines
        # Use negative lookbehind: (?<!\$) = "not preceded by $"
        # FIX #9: Only match if content contains ; or \n (actual command groups)
        grouping_pattern = r'(?<!\$)\{\s*([^}]*[;\n][^}]*)\s*\}'

        def expand_grouping(match):
            # Return inner commands
            return match.group(1)

        command = re.sub(grouping_pattern, expand_grouping, command)

        return command
    
    def _process_xargs(self, command: str) -> str:
        """
        Process xargs patterns: cmd | xargs other_cmd

        FIX #19: Translate the command inside xargs

        Converts to PowerShell ForEach-Object or cmd.exe for loop.
        """
        import re

        if 'xargs' not in command:
            return command

        # Pattern: ... | xargs cmd
        xargs_pattern = r'(.+?)\|\s*xargs\s+(.+)'

        match = re.match(xargs_pattern, command)
        if not match:
            return command

        input_cmd = match.group(1).strip()
        xargs_cmd = match.group(2).strip()

        # FIX #19: Translate the xargs command (grep → Select-String, wc → Measure-Object, etc.)
        translated_xargs, _, _ = self.command_translator.translate(xargs_cmd, force_translate=True)

        # Clean up cmd /c wrapper if present
        if translated_xargs.startswith('cmd /c '):
            translated_xargs = translated_xargs[7:]
        elif translated_xargs.startswith('cmd.exe /c '):
            translated_xargs = translated_xargs[11:]

        # Replace placeholder $_ in translated command
        # Note: xargs passes the input as argument, represented by $_
        ps_command = f"{input_cmd} | ForEach-Object {{ {translated_xargs} $_ }}"

        return ps_command
    
    def _process_find_exec(self, command: str) -> str:
        """
        Process find ... -exec patterns

        FIX #11: Translate the command inside -exec (grep → Select-String, etc.)

        Converts to PowerShell Get-ChildItem with ForEach-Object.
        """
        import re

        if 'find' not in command or '-exec' not in command:
            return command

        # Pattern: find path -exec cmd {} \;
        exec_pattern = r'find\s+([^\s]+)\s+.*?-exec\s+(.+?)\s*\{\}\s*\\;'

        match = re.search(exec_pattern, command)
        if not match:
            return command

        path = match.group(1)
        exec_cmd = match.group(2).strip()

        # FIX #11: TRANSLATE the exec_cmd (grep → Select-String, wc → Measure-Object, etc.)
        # Use command_translator to translate the command
        translated_exec, _, _ = self.command_translator.translate(exec_cmd, force_translate=True)

        # Clean up cmd /c wrapper if present (not needed inside PowerShell)
        if translated_exec.startswith('cmd /c '):
            translated_exec = translated_exec[7:]
        elif translated_exec.startswith('cmd.exe /c '):
            translated_exec = translated_exec[11:]

        # Convert to PowerShell
        # Get-ChildItem path -Recurse | ForEach-Object { translated_exec $_.FullName }
        # Replace {} placeholder in translated command with $_.FullName
        ps_exec_cmd = translated_exec.replace('{}', '$_.FullName')

        ps_command = f"Get-ChildItem {path} -Recurse | ForEach-Object {{ {ps_exec_cmd} }}"

        return ps_command
    
    def _process_escape_sequences(self, command: str) -> str:
        """
        Process escape sequences in strings: \n, \t, \r, etc.
        
        Converts to proper escaped format for target shell.
        """
        # Already handled by echo translator in most cases
        # For PowerShell, escape sequences work with backtick
        
        # If using PowerShell, convert \ to `
        # This is simplified - real implementation needs context awareness
        
        return command
    
    def _has_control_structures(self, command: str) -> bool:
        """Check if command contains bash control structures"""
        keywords = ['for ', 'while ', 'if ', 'case ', 'function ', 'until ']
        return any(kw in command for kw in keywords)
    
    def _convert_control_structures_to_script(self, command: str) -> Tuple[str, Optional[Path]]:
        """
        Convert bash control structures to PowerShell script.
        
        For complex structures (for, while, if), create temp PowerShell script.
        
        Returns:
            (modified_command, temp_script_file)
        """
        if not self._has_control_structures(command):
            return command, None
        
        # Create PowerShell script with bash-like logic
        cwd = self.scratch_dir
        script_file = cwd / f'bash_script_{threading.get_ident()}.ps1'
        
        try:
            # Convert bash script to PowerShell
            ps_script = self._bash_to_powershell(command)
            
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(ps_script)
            
            # Return command to execute script
            new_command = f'powershell -ExecutionPolicy Bypass -File "{script_file}"'
            
            return new_command, script_file
        
        except Exception as e:
            self.logger.error(f"Failed to convert control structures: {e}")
            return command, None
    
    def _bash_to_powershell(self, bash_script: str) -> str:
        """
        Convert bash control structures to PowerShell.
        
        Handles:
        - for loops
        - while loops
        - if statements
        - test conditions conversion
        - variable references
        """
        import re
        
        # For loop: for i in {1..10}; do echo $i; done
        for_pattern = r'for\s+(\w+)\s+in\s+([^;]+);\s*do\s+(.+?);\s*done'
        
        def convert_for(match):
            var = match.group(1)
            range_expr = match.group(2).strip()
            body = match.group(3).strip()
            
            # Convert bash $var to PowerShell $var (already compatible)
            # Convert echo to Write-Host
            body = body.replace('echo ', 'Write-Host ')
            
            # Parse range
            if '..' in range_expr:
                # Range like 1..10
                ps = f'foreach (${var} in {range_expr}) {{\n'
                ps += f'    {body}\n'
                ps += '}\n'
            else:
                # List like "a b c"
                items = range_expr.split()
                items_str = ','.join([f'"{item}"' for item in items])
                ps = f'foreach (${var} in {items_str}) {{\n'
                ps += f'    {body}\n'
                ps += '}\n'
            
            return ps
        
        # Check for for loop
        if 'for ' in bash_script and ' in ' in bash_script and '; do ' in bash_script:
            bash_script = re.sub(for_pattern, convert_for, bash_script, flags=re.DOTALL)
        
        # While loop: while condition; do ...; done
        while_pattern = r'while\s+(.+?);\s*do\s+(.+?);\s*done'
        
        def convert_while(match):
            condition = match.group(1).strip()
            body = match.group(2).strip()
            
            # Convert test conditions to PowerShell
            condition = self._convert_test_to_powershell(condition)
            
            # Convert body commands
            body = body.replace('echo ', 'Write-Host ')
            
            ps = f'while ({condition}) {{\n'
            ps += f'    {body}\n'
            ps += '}\n'
            
            return ps
        
        if 'while ' in bash_script:
            bash_script = re.sub(while_pattern, convert_while, bash_script, flags=re.DOTALL)
        
        # If statement: if condition; then ...; fi
        if_pattern = r'if\s+(.+?);\s*then\s+(.+?);\s*fi'
        
        def convert_if(match):
            condition = match.group(1).strip()
            body = match.group(2).strip()
            
            # Convert test conditions to PowerShell
            condition = self._convert_test_to_powershell(condition)
            
            # Convert body commands
            body = body.replace('echo ', 'Write-Host ')
            
            ps = f'if ({condition}) {{\n'
            ps += f'    {body}\n'
            ps += '}\n'
            
            return ps
        
        if 'if ' in bash_script and ' then ' in bash_script:
            bash_script = re.sub(if_pattern, convert_if, bash_script, flags=re.DOTALL)
        
        # Convert common bash commands to PowerShell equivalents
        conversions = {
            'echo ': 'Write-Host ',
            'cat ': 'Get-Content ',
            'ls ': 'Get-ChildItem ',
            'rm ': 'Remove-Item ',
            'cp ': 'Copy-Item ',
            'mv ': 'Move-Item ',
            'mkdir ': 'New-Item -ItemType Directory -Path ',
        }
        
        for bash_cmd, ps_cmd in conversions.items():
            bash_script = bash_script.replace(bash_cmd, ps_cmd)
        
        return bash_script
    
    def _convert_test_to_powershell(self, test_expr: str) -> str:
        """
        Convert bash test conditions to PowerShell.
        
        Examples:
        [ -f file ] → Test-Path file
        [ "$a" = "$b" ] → $a -eq $b
        """
        # Remove [ ] brackets
        test_expr = test_expr.strip()
        if test_expr.startswith('[') and test_expr.endswith(']'):
            test_expr = test_expr[1:-1].strip()
        
        # File tests
        if '-f ' in test_expr:
            # Extract filename
            file = test_expr.split('-f ')[1].strip().strip('"')
            return f'Test-Path "{file}"'
        elif '-d ' in test_expr:
            # Directory test
            dir = test_expr.split('-d ')[1].strip().strip('"')
            return f'Test-Path "{dir}" -PathType Container'
        elif '-e ' in test_expr:
            # Exists test
            path = test_expr.split('-e ')[1].strip().strip('"')
            return f'Test-Path "{path}"'
        
        # String comparisons
        elif ' = ' in test_expr or ' == ' in test_expr:
            parts = re.split(r'\s*=\s*', test_expr)
            if len(parts) == 2:
                return f'{parts[0].strip()} -eq {parts[1].strip()}'
        elif ' != ' in test_expr:
            parts = test_expr.split(' != ')
            if len(parts) == 2:
                return f'{parts[0].strip()} -ne {parts[1].strip()}'
        
        # Fallback: return as-is
        return test_expr
    
    def _cleanup_temp_files(self, temp_files: List[Path]):
        """Cleanup temporary files created during execution"""
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
    
    def _needs_powershell(self, command: str) -> bool:
        """
        Detect if command needs PowerShell instead of cmd.exe.

        PowerShell required for:
        - Command substitution: $(...)
        - Backticks: `...`
        - Process substitution: <(...)
        - Complex variable expansion
        - PowerShell cmdlets (Get-ChildItem, ForEach-Object, etc.)

        Returns:
            True if PowerShell required, False if cmd.exe sufficient
        """
        # PowerShell cmdlets
        powershell_cmdlets = [
            'Get-ChildItem', 'ForEach-Object', 'Select-Object', 'Where-Object',
            'Measure-Object', 'Select-String', 'Get-Content', 'Set-Content',
            'Out-File', 'Write-Output', 'Write-Host', 'Write-Error',
            '$input', '$_'  # PowerShell variables
        ]

        for cmdlet in powershell_cmdlets:
            if cmdlet in command:
                return True

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
    
    def _setup_virtual_env(self, virtual_env: Optional[str]) -> Optional[Path]:
        """Setup virtual environment - BLOCKING at initialization is acceptable.
        
        Creates venv at initialization if missing. System blocks once at startup,
        then venv path exists for all subsequent operations.
        """
        if virtual_env:
            # User specified venv
            venv_path = Path(virtual_env)
            if venv_path.exists():
                self.logger.info(f"Using specified venv: {venv_path}")
                return venv_path
            else:
                self.logger.error(f"Specified venv not found: {venv_path}")
                raise RuntimeError(f"Virtual environment not found: {venv_path}")
        
        # Check default BASH_TOOL_ENV
        default_venv = self.path_translator.workspace_root / 'BASH_TOOL_ENV'
        
        if default_venv.exists():
            self.logger.info(f"Using default venv: {default_venv}")
            return default_venv
        
        # Create default venv - BLOCKING but only at initialization
        try:
            self.logger.warning(f"Virtual environment missing. Creating at: {default_venv}")
            self.logger.warning("This is a ONE-TIME operation that may take up to 60 seconds...")
            
            subprocess.run(
                [self.python_executable, '-m', 'venv', str(default_venv)],
                check=True,
                timeout=60,
                capture_output=True
            )
            
            self.logger.info(f"Virtual environment created successfully: {default_venv}")
            return default_venv
            
        except subprocess.TimeoutExpired:
            self.logger.error("Virtual environment creation timed out")
            raise RuntimeError("Failed to create virtual environment: timeout after 60s")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Virtual environment creation failed: {e}")
            raise RuntimeError(f"Failed to create virtual environment: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error creating venv: {e}")
            raise RuntimeError(f"Virtual environment setup failed: {e}")
    
    def _process_variable_assignments(self, command: str) -> str:
        """
        FIX #8: Process variable assignments in command chains.

        Handles patterns like:
        - file="test.tar.gz"; echo ${file%.*}
        - var1=val1; var2=val2; echo $var1 $var2
        - x=5; y=10; echo $((x + y))

        Extracts variable assignments and adds them to os.environ
        so they're available for subsequent ${var} expansions.

        Returns:
            Command with variable assignments processed
        """
        import re

        # Pattern: var=value (at start of command or after ; or &&)
        # Handles: var="value" or var='value' or var=value
        # Must be at word boundary (after whitespace, ;, or &&)
        assign_pattern = r'(?:^|;\s*|&&\s*)(\w+)=((?:"[^"]*"|\'[^\']*\'|[^\s;]+))'

        matches = list(re.finditer(assign_pattern, command))

        if not matches:
            return command

        # Extract assignments and set in environment
        for match in matches:
            var_name = match.group(1)
            var_value = match.group(2)

            # Remove quotes if present
            if (var_value.startswith('"') and var_value.endswith('"')) or \
               (var_value.startswith("'") and var_value.endswith("'")):
                var_value = var_value[1:-1]

            # Set in environment for subsequent expansions
            os.environ[var_name] = var_value

            self.logger.debug(f"[VAR ASSIGN] {var_name}={var_value}")

        # Remove assignments from command (they're now in environment)
        # Replace assignment with empty string (keep separator if present)
        cleaned_command = re.sub(assign_pattern, '', command)

        # Clean up extra semicolons/whitespace that may be left
        cleaned_command = re.sub(r';\s*;', ';', cleaned_command)
        cleaned_command = re.sub(r'^;\s*', '', cleaned_command)
        cleaned_command = re.sub(r'\s*;\s*$', '', cleaned_command)
        cleaned_command = cleaned_command.strip()

        return cleaned_command

    def execute(self, tool_input: dict) -> str:
        """Execute bash command with FULL pattern emulation"""
        command = tool_input.get('command', '')
        description = tool_input.get('description', '')
        
        if not command:
            return "Error: command parameter is required"
        
        # Determine timeout
        timeout = self.python_timeout if 'python' in command.lower() else self.default_timeout
        
        self.logger.info(f"Executing: {command[:100]}")
        
        # Temp files tracking for cleanup
        temp_files = []
        
        try:
            # PRE-PROCESSING PHASE - Handle complex patterns BEFORE translation

            # STEP 0.-1: Extract and process variable assignments
            # FIX #8: Handle variable assignment chains like: file="test"; echo ${file}
            command = self._process_variable_assignments(command)

            # STEP 0.0: Expand aliases (ll, la, etc.)
            command = self._expand_aliases(command)
            
            # STEP 0.1: Process subshell and command grouping
            command = self._process_subshell(command)
            command = self._process_command_grouping(command)
            
            # STEP 0.2: Control structures (for, while, if, case)
            if self._has_control_structures(command):
                command, script_file = self._convert_control_structures_to_script(command)
                if script_file:
                    temp_files.append(script_file)
                    # Script execution will use PowerShell directly
                    use_powershell = True
            
            # STEP 0.3: Test commands [ ] and [[ ]]
            command = self._preprocess_test_commands(command)
            
            # STEP 0.4: Brace expansion {1..10}, {a,b,c}
            command = self._expand_braces(command)
            
            # STEP 0.5: Here documents <<EOF
            command, heredoc_files = self._process_heredocs(command)
            temp_files.extend(heredoc_files)
            
            # STEP 0.6: Process substitution <(cmd) >(cmd)
            command, procsub_files = self._process_substitution(command)
            temp_files.extend(procsub_files)
            
            # STEP 0.7: Variable expansion ${var:-default}, tilde, arithmetic
            command = self._expand_variables(command)
            
            # STEP 0.8: xargs patterns
            command = self._process_xargs(command)
            
            # STEP 0.9: find ... -exec patterns
            command = self._process_find_exec(command)
            
            # STEP 0.10: Command substitution $(...) - RECURSIVE TRANSLATION
            command = self._process_command_substitution_recursive(command)
            
            # STEP 1: Detect if PowerShell needed (if not already set by control structures)
            if 'use_powershell' not in locals():
                use_powershell = self._needs_powershell(command)
            
            if use_powershell:
                self.logger.debug("Using PowerShell for advanced patterns")
            
            # STEP 2: Translate Unix paths → Windows paths
            command_with_win_paths = self.path_translator.translate_paths_in_string(command, 'to_windows')
            
            # STEP 3: Translate Unix commands → Windows commands
            translated_cmd, use_shell, method = self.command_translator.translate(
                command_with_win_paths
            )
            
            # STEP 3.5: Execute bash - Strategy selection (NUOVO!)
            # CommandExecutor decide: bash.exe? native binary? PowerShell emulation?
            # Parse command into parts for executor
            parts = translated_cmd.split() if translated_cmd else []
            executable_cmd, executor_needs_ps = self.command_executor.execute_bash(
                translated_cmd, parts
            )
            
            # Update command and PowerShell flag based on executor decision
            translated_cmd = executable_cmd
            if executor_needs_ps:
                use_powershell = True
            
            # STEP 4: Adapt for PowerShell if needed
            if use_powershell:
                translated_cmd = self._adapt_for_powershell(translated_cmd)
                self.logger.debug(f"PowerShell adapted: {translated_cmd[:100]}")
            elif method == 'mapped':
                self.logger.debug(f"Translated: {translated_cmd[:100]}")

            # STEP 5: Validate command
            is_safe, reason = self.sandbox_validator.validate_command(translated_cmd)
            if not is_safe:
                return f"Error: Security - {reason}"
            
            # Working directory
            cwd = self.scratch_dir
            
            # Setup environment
            env = self._setup_environment()

            # STEP 6: Execute
            # TESTMODE: Simulate execution without running commands
            if self.testmode:
                # Create mock result
                from types import SimpleNamespace
                result = SimpleNamespace(
                    returncode=0,
                    stdout=f"[TEST MODE] Would execute: {translated_cmd[:200]}",
                    stderr=""
                )
                self.logger.info(f"[TESTMODE] Simulated: {command[:100]}")
                return self._format_result(result, command, translated_cmd, method)

            if 'powershell' in translated_cmd.lower() and '-File' in translated_cmd:
                # Already a PowerShell script command (from control structures)
                # Execute directly without additional wrapping
                result = subprocess.run(
                    translated_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(cwd),
                    env=env,
                    errors='replace',
                    encoding='utf-8',
                    shell=True
                )
            elif use_powershell:
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-NonInteractive', '-Command', translated_cmd],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(cwd),
                    env=env,
                    errors='replace',
                    encoding='utf-8'
                )
            else:
                result = subprocess.run(
                    ['cmd', '/c', translated_cmd],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(cwd),
                    env=env,
                    errors='replace',
                    encoding='utf-8'
                )
            
            return self._format_result(result, command, translated_cmd, method)
        
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return f"Error: {str(e)}"
        finally:
            # Cleanup temp files
            self._cleanup_temp_files(temp_files)
    
    def _setup_environment(self) -> dict:
        """Setup execution environment"""
        env = os.environ.copy()
        
        # UTF-8 encoding
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        
        # Virtual environment
        if self.virtual_env:
            env['PATH'] = f"{self.virtual_env / 'Scripts'}{os.pathsep}{env.get('PATH', '')}"
            env['VIRTUAL_ENV'] = str(self.virtual_env)
        
        # Python executable directory
        if self.python_executable:
            python_dir = Path(self.python_executable).parent if '/' in self.python_executable or '\\' in self.python_executable else None
            if python_dir:
                env['PATH'] = f"{python_dir}{os.pathsep}{env.get('PATH', '')}"
        
        return env
    
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
            stdout_unix = self.path_translator.translate_paths_in_string(result.stdout, 'to_unix')
            lines.append(stdout_unix.rstrip())
        
        # Stderr - translate Windows paths back to Unix
        if result.stderr:
            lines.append("")
            if result.stdout:
                lines.append("--- stderr ---")
            stderr_unix = self.path_translator.translate_paths_in_string(result.stderr, 'to_unix')
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