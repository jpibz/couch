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
from translators import PathTranslator, CommandEmulator


# ============================================================================
# BASH GIT MINIMAL - Unsupported Commands
# ============================================================================
# Git Bash (minimal) is a lightweight POSIX environment for Windows.
# It includes most standard UNIX commands but LACKS external tools.
#
# SUPPORTED: find, grep, awk, sed, tar, gzip, sort, uniq, cut, etc.
# NOT SUPPORTED: External tools that require separate installation
#
# This set defines commands that Git Bash CANNOT execute.
# Used by ExecuteUnixSingleCommand to skip Bash attempt and go to script.
BASH_GIT_UNSUPPORTED_COMMANDS = {
    # JSON/data tools (require external installation)
    'jq',         # JSON processor - not included in Git Bash

    # Network tools (may not be available in minimal Git Bash)
    'wget',       # Download tool - not always present
    'curl',       # URL tool - may have limited version or absent

    # GNU-specific tools (not in minimal POSIX)
    'timeout',    # GNU timeout command - not in Git Bash

    # Checksums (may use different syntax or be absent)
    'sha256sum',  # May not be available or have different name
    'sha1sum',    # May not be available or have different name
    'md5sum',     # May not be available or have different name

    # Compression (some formats not supported)
    'zip',        # Requires Info-ZIP tools
    'unzip',      # Requires Info-ZIP tools

    # Special tools
    'watch',      # Not in minimal Git Bash
}


# ====================================================================
# Git Bash PASSTHROUGH (100% Unix compatibility)
# ====================================================================
# Complex commands with heavy emulation → use REAL bash instead!
# These commands have 100+ lines PowerShell emulation - bash is better.

GITBASH_PASSTHROUGH_COMMANDS = {
    # Heavy emulation (200+ lines PowerShell) → bash wins
    'find',      # 300 lines PowerShell vs native find
    'awk',       # Turing-complete language vs PowerShell approx
    'sed',       # Complex regex engine vs PowerShell approx
    'grep',      # Advanced patterns vs Select-String limits
    'diff',      # Unified format perfect vs PowerShell approx
    'tar',       # Real .tar.gz vs Compress-Archive .zip
    
    # Perfect Unix compatibility needed
    'sort',      # -k field selection edge cases
    'uniq',      # Consecutive duplicates exact behavior
    'split',     # Suffix naming exact match
    'join',      # SQL-like join perfect compatibility
    'comm',      # Sorted file comparison exact
    'paste',     # Column merging exact
}

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


class ExecutionEngine:
    """
    UNICO PUNTO di esecuzione subprocess.

    Concentra TUTTE le chiamate subprocess in un solo posto per:
    - Test mode: vedere cosa viene eseguito senza eseguire
    - Logging: tracciare tutte le execution
    - Metrics: contare tipi di execution
    - Error handling: gestione errori centralizzata

    ARCHITECTURE:
    CommandExecutor usa ExecutionEngine, non subprocess direttamente.
    Questo permette switching test/production in UN punto.
    """

    # Native Windows binaries to detect
    NATIVE_BINS = {
        'diff': 'diff.exe',
        'tar': 'tar.exe',
        'awk': 'awk.exe',
        'sed': 'sed.exe',
        'grep': 'grep.exe',
        'jq': 'jq.exe',
    }

    def __init__(self, working_dir,
                 test_mode: bool = False,
                 logger: logging.Logger = None):
        """
        Initialize execution engine.

        Args:
            test_mode: If True, print commands instead of executing
            logger: Logger instance for execution tracking
            python_executable: Path to Python executable (for venv setup)
            workspace_root: Workspace root directory (for venv setup)
            virtual_env: Virtual environment path (optional)
        """
        self.working_dir = working_dir
        self.test_mode = test_mode
        self.logger = logger or logging.getLogger('ExecutionEngine')
        self.path_translator = PathTranslator()
        # Python and virtual environment setup
        self.workspace_root = self.path_translator.get_tool_scratch_directory('bash_tool')
        self.bash_path = None
        self.python_timeout = 60
        self.default_timeout = 30
        
        if test_mode:
            # TEST MODE: Skip detection and setup, assume everything is available
            self.python_executable = 'python'
            self.virtual_env = None
            self.environment = os.environ.copy()

            # Populate availability dict with all capabilities as True
            self.available = {
                'python': True,
                'bash': True,
            }
            # Add all native binaries as available
            for cmd in self.NATIVE_BINS.keys():
                self.available[cmd] = True

            self.logger.info("[TEST MODE] All capabilities set as available")
        else:
            # PRODUCTION MODE: Perform real detection and setup
            # Detect system Python inline
            self.python_executable = None
            for cmd in ['python', 'python.exe']:
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
                        self.python_executable = cmd
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    continue

            if not self.python_executable:
                self.logger.critical("CRITICAL: Python not found in system PATH")
                self.logger.critical("Bash tool requires Python for full functionality")

            # Setup virtual environment
            self.virtual_env = self._setup_virtual_env()
    
            # Setup execution environment
            self.environment = self._setup_environment()

            # Detect available binaries and capabilities
            self.available, self.paths = self._detect_available_capabilities()

        # Execution statistics
        self.stats = {
            'cmd': 0,
            'powershell': 0,
            'bash': 0,
            'native': 0,
            'total': 0
        }

    def _detect_available_capabilities(self) -> Dict[str, bool]:
        """
        Detect all available capabilities at initialization.

        Returns:
            Dict mapping capability name to availability status
        """
        capabilities = {}
        bin_paths ={}
        # Python availability
        capabilities['python'] = bool(self.python_executable)
        bin_paths['python'] = self.python_executable

        # Git Bash availability - detect inline
        bash_found = False
        for path in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"]:
            if Path(path).exists():
                self.logger.info(f"Found Git Bash: {path}")
                bash_found = True
                break

        if not bash_found:
            try:
                result = subprocess.run(
                    ['where', 'bash.exe'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    self.bash_path = result.stdout.strip().split('\n')[0]
                    if 'Git' in self.bash_path:
                        self.logger.info(f"Found Git Bash in PATH: {self.bash_path}")
                        bin_paths['bash'] = self.bash_path
                        bash_found = True
            except:
                pass

        capabilities['bash'] = bash_found

        # Native binaries availability
        for cmd, binary in self.NATIVE_BINS.items():
            try:
                result = subprocess.run(
                    ['where', binary],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                capabilities[cmd] = (result.returncode == 0)
                if capabilities[cmd]:
                    bin_paths[cmd] = binary
            except Exception:
                capabilities[cmd] = False

        return capabilities, bin_paths

    def execute_cmd(self, command: str, test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Execute command via cmd.exe

        Args:
            command: Command string to execute
            test_mode_stdout: Optional stdout to return in test mode (AS IF execution succeeded)
            **kwargs: Additional subprocess.run arguments

        Returns:
            CompletedProcess result or mock result in test mode
        """
        self.stats['cmd'] += 1
        self.stats['total'] += 1

        if self.test_mode:
            self.logger.info(f"[TEST-CMD] {command}")
            print(f"[TEST MODE] Would execute (CMD): {command}")

            # Use AS IF stdout if provided, otherwise echo
            stdout = test_mode_stdout if test_mode_stdout is not None else f"[TEST MODE OUTPUT] cmd: {command}"

            return subprocess.CompletedProcess(
                args=['cmd', '/c', command],
                returncode=0,
                stdout=stdout,
                stderr=""
            )

        self.logger.debug(f"Executing CMD: {command}")
        return subprocess.run(
            ['cmd', '/c', command],
            capture_output=True,
            text=True,
            cwd=str(self.working_dir),
            **kwargs
        )

    def execute_powershell(self, command: str, test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Execute command via PowerShell

        Args:
            command: PowerShell command string
            test_mode_stdout: Optional stdout to return in test mode (AS IF execution succeeded)
            **kwargs: Additional subprocess.run arguments

        Returns:
            CompletedProcess result or mock result in test mode
        """
        self.stats['powershell'] += 1
        self.stats['total'] += 1

        if self.test_mode:
            self.logger.info(f"[TEST-PowerShell] {command}")
            print(f"[TEST MODE] Would execute (PowerShell): {command}")

            # Use AS IF stdout if provided, otherwise echo
            stdout = test_mode_stdout if test_mode_stdout is not None else f"[TEST MODE OUTPUT] powershell: {command}"

            return subprocess.CompletedProcess(
                args=['powershell', '-Command', command],
                returncode=0,
                stdout=stdout,
                stderr=""
            )

        self.logger.debug(f"Executing PowerShell: {command}")
        if 'powershell' in command.lower() and '-File' in command:
            # Already a PowerShell script command (from control structures)
            # Execute directly without additional wrapping
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.default_timeout,
                cwd=str(self.working_dir),

                errors='replace',
                encoding='utf-8',
                shell=True
            )
        else:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-Command', command],
                capture_output=True,
                text=True,
                timeout=self.default_timeout,
                cwd=str(self.working_dir),
                errors='replace',
                encoding='utf-8'
            )

        return result
    
    def execute_bash(self, command: str, test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Execute command via Git Bash

        Args:
            bash_path: Path to bash.exe
            command: Bash command string
            test_mode_stdout: Optional stdout to return in test mode (AS IF execution succeeded)
            **kwargs: Additional subprocess.run arguments

        Returns:
            CompletedProcess result or mock result in test mode
        """
        self.stats['bash'] += 1
        self.stats['total'] += 1

        if self.test_mode:
            self.logger.info(f"[TEST-Git Bash] {command}")
            print(f"[TEST MODE] Would execute (Git Bash): {command}")

            # Use AS IF stdout if provided, otherwise echo
            stdout = test_mode_stdout if test_mode_stdout is not None else f"[TEST MODE OUTPUT] bash: {command}"

            return subprocess.CompletedProcess(
                args=[self.bash_path, '-c', command],
                returncode=0,
                stdout=stdout,
                stderr=""
            )

        # Convert Windows paths to Git Bash format (C:\path -> /c/path)
        git_command = self._windows_to_gitbash_paths(command)

        self.logger.debug(f"Executing Git Bash: {git_command}")
        return subprocess.run(
            [self.bash_path, '-c', command],
            capture_output=True,
            text=True,
            **kwargs
        )
   
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

    def execute_native(self, bin_name: str, args: List[str], test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
        """
        Execute native binary directly

        Args:
            bin_path: name of binary
            args: Command arguments
            test_mode_stdout: Optional stdout to return in test mode (AS IF execution succeeded)
            **kwargs: Additional subprocess.run arguments

        Returns:
            CompletedProcess result or mock result in test mode
        """
        self.stats['native'] += 1
        self.stats['total'] += 1
        
        bin_path = self.bin_paths[bin_name]
        cmd_str = f"{bin_path} {' '.join(args)}"

        if self.test_mode:
            self.logger.info(f"[TEST-Native] {cmd_str}")
            print(f"[TEST MODE] Would execute (Native): {cmd_str}")

            # Use AS IF stdout if provided, otherwise echo
            stdout = test_mode_stdout if test_mode_stdout is not None else f"[TEST MODE OUTPUT] native: {cmd_str}"

            return subprocess.CompletedProcess(
                args=[bin_path] + args,
                returncode=0,
                stdout=stdout,
                stderr=""
            )

        # Check if executing Python - use configured environment with venv
        is_python = bin_name in ['python', 'python.exe', 'python3', 'python3.exe']

        if is_python:
            # Use configured environment (includes venv PATH, PYTHONIOENCODING, etc.)
            kwargs['env'] = self.environment
            kwargs['timeout'] = self.python_timeout
            venv_info = f" with venv: {self.virtual_env}" if self.virtual_env else ""
            self.logger.debug(f"Executing Python{venv_info}: {cmd_str}")
        else:
            kwargs['timeout'] = self.default_timeout
            self.logger.debug(f"Executing Native: {cmd_str}")

        return subprocess.run(
            [bin_path] + args,
            capture_output=True,
            text=True,
            **kwargs
        )

    def get_stats(self) -> Dict[str, int]:
        """Get execution statistics"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset execution statistics"""
        for key in self.stats:
            self.stats[key] = 0

    def is_available(self, name: str) -> bool:
        """
        Check if a binary/functionality is available.

        Args:
            name: Name to check - can be:
                  - "python": Check if Python executable is configured
                  - "bash": Check if Git Bash is available
                  - Native bin name (e.g., "grep", "awk"): Check if binary exists in PATH

        Returns:
            True if available, False otherwise
        """
        return self.available.get(name.lower(), False)

    # ==================== SETUP/DETECTION METHODS ====================

    def _setup_virtual_env(self, virtual_env: Optional[str]) -> Optional[Path]:
        """Setup virtual environment - BLOCKING at initialization is acceptable.

        Creates venv at initialization if missing. System blocks once at startup,
        then venv path exists for all subsequent operations.

        Args:
            virtual_env: Optional virtual environment path

        Returns:
            Path to virtual environment or None
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
        default_venv =  self.path_translator.get_workspace_root() / 'BASH_TOOL_ENV'
        
        if default_venv.exists():
            self.logger.info(f"Using default venv: {default_venv}")
            return default_venv

        # Create default venv - BLOCKING but only at initialization
        if not self.python_executable:
            self.logger.warning("No Python executable configured, cannot create virtual environment")
            return None

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


# ============================================================================
# STRATEGIC ANALYSIS LAYER - Pipeline & Command Strategy
# ============================================================================

@dataclass
class PipelineAnalysis:
    """
    Result of pipeline strategic analysis.

    Contains all information needed to decide execution strategy.
    """
    has_pipeline: bool = False          # Contains | operator
    has_chain: bool = False             # Contains &&, ||, or ;
    has_redirection: bool = False       # Contains >, >>, <
    has_stderr_redir: bool = False      # Contains 2>, 2>&1, |&
    has_process_subst: bool = False     # Contains <(...) or >(...)
    matched_pattern: Optional[str] = None     # Regex pattern matched from PIPELINE_STRATEGIES
    complexity_level: str = 'LOW'       # HIGH, MEDIUM, LOW
    command_count: int = 1              # Number of commands in pipeline
    command_names: List[str] = field(default_factory=list)  # List of command names


@dataclass
class ExecutionStrategy:
    """
    Execution strategy decision for a command/pipeline.

    Describes HOW to execute the command and what fallbacks are available.
    """
    strategy_type: str  # BASH_REQUIRED, BASH_PREFERRED, HYBRID, NATIVE, POWERSHELL
    can_split: bool = False             # Can split pipeline into parts
    split_points: List[int] = field(default_factory=list)  # Where to split
    reason: str = ""                    # Why this strategy was chosen
    fallback_strategy: Optional['ExecutionStrategy'] = None  # Fallback if primary fails


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

    def execute_single(self, command: str) -> subprocess.CompletedProcess:
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
            return self.engine.execute_native(cmd_name, parts[1:])

        # ================================================================
        # PRIORITY 2: CommandEmulator Quick (FAST INLINE)
        # ================================================================
        if self.emulator.is_quick_command(cmd_name) and cmd_name not in GITBASH_PASSTHROUGH_COMMANDS:
            self.logger.debug(f"Strategy: Quick PowerShell script ({cmd_name})")
            translated = self.emulator.emulate_command(command)
            if self._needs_powershell(translated):
                return self.engine.execute_powershell(translated)
            else:
                return self.engine.execute_cmd(translated)

        # ================================================================
        # PRIORITY 3: Bash Git (if supported) + FALLBACK TO SCRIPT
        # ================================================================
        if cmd_name not in BASH_GIT_UNSUPPORTED_COMMANDS and self.engine.capabilities['bash']:
            try:
                self.logger.debug(f"Strategy: Bash Git ({cmd_name})")
                return self.engine.execute_bash(command)
            except Exception:
                # Fallback to script if bash conversion fails
                self.logger.debug(f"Strategy: Bash conversion failed, fallback to script ({cmd_name})")
                translated = self.emulator.emulate_command(command)
                if self._needs_powershell(translated):
                    return self.engine.execute_powershell(translated)
                else:
                    return self.engine.execute_cmd(translated)

        # ================================================================
        # PRIORITY 4: CommandEmulator Script (HEAVY EMULATION)
        # ================================================================
        self.logger.debug(f"Strategy: Heavy PowerShell script ({cmd_name})")
        translated = self.emulator.emulate_command(command)
        return self.engine.execute_powershell(translated)


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

class CommandExecutor:
    """
    Command execution strategy orchestrator - REFACTORED.

    RESPONSIBILITIES:
    - Orchestrate command execution with strategic delegation
    - Coordinate PipelineStrategy and ExecuteUnixSingleCommand
    - Preprocessing 

    """


    def __init__(self, working_dir="\\", logger=None, test_mode=False):
        """
        Initialize CommandExecutor.

        ARCHITECTURE NOTE:
        CommandExecutor does NOT need PathTranslator!
        Path translation happens in BashToolExecutor.execute() BEFORE
        commands reach this layer.

        Args:
            claude_home_unix: Unix home directory for tilde expansion (default: /home/claude)
            logger: Logger instance
            test_mode: If True, use ExecutionEngine in test mode
        """

        self.working_dir = working_dir
        self.logger = logger or logging.getLogger('CommandExecutor')
        self.test_mode = test_mode

        
        # ExecutionEngine - UNICO PUNTO per subprocess
        self.engine = ExecutionEngine(working_dir=working_dir, test_mode=test_mode, logger=self.logger)

        # ====================================================================
        # STRATEGIC LAYER - Delegation to specialized classes
        # ====================================================================

        # Pipeline strategic analyzer (MACRO level)
        self.pipeline_strategy = PipelineStrategy(
            native_bins=self.available_bins,
            logger=self.logger,
            test_mode=test_mode
        )

        # Single command executor (MICRO level)
        self._single_executor = ExecuteUnixSingleCommand(
            logger=self.logger,
            test_mode=self.test_mode
        )

        self.logger.info("CommandExecutor initialized")

    # ========================================================================
    # MAIN EXECUTION ENTRY POINT
    # ========================================================================

    def execute(self, command: str) -> subprocess.CompletedProcess:
        
        self.logger.info(f"Executing: {command[:100]}")
        
        # Temp files tracking for cleanup
        temp_files = []
        
        try:
            # PRE-PROCESSING PHASE - Handle complex patterns BEFORE translation
            
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
            
            return self._single_executor.execute_single(command)

        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return f"Error: {str(e)}"
        finally:
            # Cleanup temp files
            self._cleanup_temp_files(temp_files)
    
 
   


    # ========================================================================
    # PREPROCESSING METHODS 
    # ========================================================================
    # These methods handle complex bash patterns that need preprocessing
    # BEFORE translation. They require access to:
    # - command_translator (for recursive translation)
    # - executor (for execution in preprocessing phase)
    #
    # ========================================================================


# ============================================================================
# BASHTOOLEXECUTOR - ORCHESTRATION LAYER
# ============================================================================

    # ==================== PREPROCESSING METHODS (migrated) ====================

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
            quote_char = match.group(2)  # Captures ' or " if delimiter was quoted
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

            # ================================================================
            # ARTIGIANO: Heredoc Variable Expansion
            # ================================================================
            # CRITICAL: In bash, heredocs expand variables and commands UNLESS
            # the delimiter is quoted (<<"EOF" or <<'EOF')
            #
            # <<EOF          -> Expand $VAR, $(cmd), `cmd`, $((expr))
            # <<"EOF"        -> NO expansion (literal)
            # <<'EOF'        -> NO expansion (literal)
            #
            # BEHAVIOR:
            # - Unquoted delimiter -> Use bash.exe to expand content
            # - Quoted delimiter -> Write content literally
            # - No bash.exe -> Write literally + warning
            #
            # This ensures heredoc-generated configs/scripts have correct values.

            should_expand = (quote_char == '')  # Empty = unquoted delimiter

            if should_expand:
                # Attempt variable expansion via bash.exe
                if self.git_bash_exe:
                    try:
                        # Use bash to expand the content
                        # We pass content via echo to let bash do expansion
                        # Use printf for better control over newlines and special chars

                        # Escape content for bash heredoc (preserve literal backslashes)
                        # We'll use bash itself to expand, via a heredoc to bash
                        expansion_script = f'''cat <<'EXPAND_DELIMITER'
{content}
EXPAND_DELIMITER'''

                        # But wait - we WANT expansion, so use UNquoted delimiter
                        expansion_script = f'''cat <<EXPAND_DELIMITER
{content}
EXPAND_DELIMITER'''

                        # Execute via bash.exe through ExecutionEngine
                        bash_path = self.git_bash_exe
                        result = self.command_executor.engine.execute_bash(
                            bash_path,
                            expansion_script,
                            test_mode_stdout=content,  # AS IF: content expanded (in TESTMODE)
                            timeout=5,
                            cwd=str(self.scratch_dir),
                            env=self._setup_environment(),
                            errors='replace',
                            encoding='utf-8'
                        )

                        if result.returncode == 0:
                            # Use expanded content
                            content = result.stdout
                            self.logger.debug(f"Heredoc expanded via bash.exe (delimiter: {delimiter})")
                        else:
                            # Expansion failed - use literal
                            self.logger.warning(f"Heredoc expansion failed (exit {result.returncode}), using literal content")
                            self.logger.debug(f"Bash stderr: {result.stderr}")

                    except Exception as e:
                        # Expansion error - use literal
                        self.logger.warning(f"Heredoc expansion error: {e}, using literal content")

                else:
                    # No bash.exe for expansion - CRITICAL
                    self.logger.warning(f"Heredoc with unquoted delimiter '{delimiter}' should expand variables")
                    self.logger.warning("bash.exe not available - writing LITERAL content (may be incorrect)")
                    # Continue with literal content

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
            """Replace <(cmd) with temp file containing cmd output"""
            cmd = match.group(1)

            # Translate and execute command
            try:
                # NOTE: Paths already translated by BashToolExecutor.execute()
                # No need to translate again here

                # Translate command
                translated, _, _ = self.command_translator.translate(cmd)

                # Execute via ExecutionEngine
                result = self.command_executor.engine.execute_cmd(
                    translated,
                    test_mode_stdout=f"[TEST MODE] Process substitution output for: {cmd}\n",  # AS IF: realistic output
                    timeout=30,
                    cwd=str(cwd),
                    env=env,
                    errors='replace'
                )

                # Create temp file with output
                temp_file = cwd / f'procsub_input_{threading.get_ident()}_{len(temp_files)}.tmp'

                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                temp_files.append(temp_file)
                
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
        matches = list(re.finditer(input_pattern, command))
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

        Examples:
            $(grep pattern file.txt)
            -> $(Select-String -Pattern "pattern" -Path "file.txt")

            $(cat file | wc -l)
            -> $(Get-Content file | Measure-Object -Line)

            Nested: $(echo $(cat file))
            -> $(Write-Host $(Get-Content file))

        Returns:
            Command with all $(..  .) recursively translated
        """
        if '$(' not in command:
            return command
        
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

        for start, end, content in substitutions:
            print(f"  - Position {start}-{end}: '{content}'")
        
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
        Translate Unix command content inside $(...) - ARTIGIANO STRATEGY.

        CRITICAL: Commands inside $(...) must be EXECUTED to capture output.
        Cannot just "pass to bash.exe" - must run and get result.

        ARTIGIANO STRATEGY:
        1. Detect if command is COMPLEX (would fail in PowerShell emulation)
        2. Complex -> execute with bash.exe, capture output, return as string
        3. Simple -> translate to PowerShell, execute in $(...) context

        COMPLEXITY TRIGGERS:
        - Pipeline with critical commands (find, xargs, awk, sed)
        - Command chains (&&, ||)
        - Process substitution <(...)
        - Complex redirections

        Args:
            content: Unix command string (e.g., "grep pattern file.txt")

        Returns:
            Translated command or bash.exe invocation
        """
        # Handle empty
        if not content or not content.strip():
            return content

        # STEP 1: Recursively handle nested $(...)
        if '$(' in content:
            content = self._process_command_substitution_recursive(content)

        # ================================================================
        # ARTIGIANO: Detect if command inside $(...) is COMPLEX
        # ================================================================

        def is_complex_substitution(cmd: str) -> bool:
            """Detect if command needs bash.exe for reliable execution"""
            # Pipeline with critical commands
            if '|' in cmd:
                critical_in_pipeline = ['find', 'xargs', 'awk', 'sed', 'grep -', 'cut', 'tr']
                for critical in critical_in_pipeline:
                    if critical in cmd:
                        return True

            # Command chains
            if any(op in cmd for op in ['&&', '||', ';']):
                return True

            # Process substitution (shouldn't be here but check anyway)
            if '<(' in cmd or '>(' in cmd:
                return True

            # Complex find -exec
            if '-exec' in cmd and 'find' in cmd:
                return True

            return False

        if is_complex_substitution(content):
            # COMPLEX command inside $(...) -> execute with bash.exe
            if self.git_bash_exe:
                self.logger.debug(f"Complex command in $(...) -> using bash.exe: {content[:50]}")
                # Need to execute bash.exe, capture output, and insert as string
                # This is tricky - we're in preprocessing, haven't executed yet
                # Return a PowerShell invocation that runs bash.exe
                bash_escaped = content.replace('"', '`"').replace('$', '`$')
                # Convert to bash.exe invocation that captures output
                return f'& "{self.git_bash_exe}" -c "{bash_escaped}"'
            else:
                self.logger.warning(f"Complex command in $(...) but no bash.exe - may fail: {content[:50]}")
                # Fall through to PowerShell translation (may fail)

        # ================================================================
        # STEP 2: Translate commands
        # ================================================================
        # NOTE: Paths already translated by BashToolExecutor.execute()
        # Command substitution $(...) is PART of the original command,
        # so paths inside it were already translated.

        # Use command_translator which handles:
        # - Pipe chains
        # - Redirections
        # - Command concatenation (&&, ||, ;)
        # - All individual commands
        # CRITICAL: force_translate=True to translate EXECUTOR_MANAGED commands (find, grep, etc.)
        # Inside $(), there's no "strategy selection" - must translate immediately
        translated, use_shell, method = self.command_translator.translate(content, force_translate=True)

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

        # NOTE: claude_home_unix is passed via __init__, no PathTranslator needed
        claude_home = self.claude_home_unix

        # 1. Tilde expansion: ~/path -> /home/claude/path
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
        
        # 5. Array expansion: ${arr[@]} -> just remove braces for now
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
        # Pattern: ${var#pattern} or ${var##pattern}
        prefix_pattern = r'\$\{(\w+)(#{1,2})([^}]+)\}'

        def expand_remove_prefix(match):
            var_name = match.group(1)
            op = match.group(2)  # # or ##
            pattern = match.group(3)
            value = os.environ.get(var_name, '')

            if not value:
                return ''

            # Convert bash glob to regex
            import fnmatch
            regex_pattern = fnmatch.translate(pattern)

            # Convert bash glob to regex and match from start
            regex_pattern = '^' + regex_pattern.rstrip('\\Z')

            if op == '#':  # Remove shortest prefix (non-greedy)
                # Make pattern non-greedy by adding '?' after '*'
                regex_pattern_ng = regex_pattern.replace('*', '*?')
                match_obj = re.match(regex_pattern_ng, value)
                if match_obj:
                    return value[len(match_obj.group(0)):]
            else:  # ## Remove longest prefix (greedy - default)
                # fnmatch patterns are already greedy by default
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

        # ================================================================
        # ARTIGIANO: Simple Variable Expansion
        # ================================================================
        # CRITICAL: Must expand basic $VAR and ${VAR} forms!
        # Previous code only handled ${VAR:-default}, missing simple expansion.
        #
        # This BROKE commands like:
        #   cd $HOME        -> cd $HOME (literal! Wrong!)
        #   echo $PATH      -> echo $PATH (literal!)
        #   cp file $USER/  -> cp file $USER/ (fails!)
        #
        # 6. Simple ${VAR} expansion
        simple_brace_pattern = r'\$\{(\w+)\}'

        def expand_simple_brace(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            if not value:
                self.logger.debug(f"Variable ${{{var_name}}} not found in environment, expanding to empty string")
            return value

        command = re.sub(simple_brace_pattern, expand_simple_brace, command)

        # 7. Simple $VAR expansion (without braces)
        # Must be AFTER ${VAR} to avoid double-expansion
        # Match $VAR but NOT $((, ${, $@, $*, $#, $?, $$, $!, $0-9
        simple_var_pattern = r'\$([A-Za-z_][A-Za-z0-9_]*)'

        def expand_simple_var(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            if not value:
                self.logger.debug(f"Variable ${var_name} not found in environment, expanding to empty string")
            return value

        command = re.sub(simple_var_pattern, expand_simple_var, command)

        return command
    
    def _preprocess_test_commands(self, command: str) -> str:
        """
        Convert test command syntax: [ expr ] -> test expr
        
        Handles:
        - [ -f file ] -> test -f file
        - [[ expr ]] -> test expr (basic conversion)
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
        - ll -> ls -la
        - la -> ls -A
        - l -> ls -CF
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
        """
        import re
        
        # Pattern: { cmd1; cmd2; } but NOT ${var...}
        # Use negative lookbehind: (?<!\$) = "not preceded by $"
        # FIX #7: Prevent matching ${var#pattern}, ${var%pattern}, ${var/pattern/repl}, etc.
        grouping_pattern = r'(?<!\$)\{\s*([^}]+)\s*\}'
        
        def expand_grouping(match):
            # Return inner commands
            return match.group(1)
        
        command = re.sub(grouping_pattern, expand_grouping, command)
        
        return command
    
    def _process_xargs(self, command: str) -> str:
        """
        Process xargs patterns: cmd | xargs other_cmd
        
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
        
        # Convert to PowerShell ForEach-Object
        # input_cmd | ForEach-Object { xargs_cmd $_ }
        ps_command = f"{input_cmd} | ForEach-Object {{ {xargs_cmd} $_ }}"
        
        return ps_command
    
    def _process_find_exec(self, command: str) -> str:
        """
        Process find ... -exec patterns
        
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
        
        # Convert to PowerShell
        # Get-ChildItem path -Recurse | ForEach-Object { exec_cmd $_.FullName }
        ps_command = f"Get-ChildItem {path} -Recurse | ForEach-Object {{ {exec_cmd} $_.FullName }}"
        
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
    
    def _cleanup_temp_files(self, temp_files: List[Path]):
        """Cleanup temporary files created during execution"""
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
    


# ============================================================================
# BASH TOOL EXECUTOR - Main tool class
# ============================================================================

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
