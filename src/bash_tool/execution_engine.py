"""
Execution Engine - Single point for all subprocess operations

ARCHITECTURE:
This is the SINGLE SUBPROCESS EXECUTION POINT for the entire bash_tool system.
ALL subprocess calls MUST go through this class (no direct subprocess.run() elsewhere).

Position in hierarchy:
    ├── ExecuteUnixSingleCommand
    ├── PipelineStrategy
    └── CommandExecutor
           ↓
        ExecutionEngine ← THIS CLASS (SINGLE POINT)
           ↓
        subprocess.run() / subprocess.Popen()

RESPONSIBILITIES:
1. Single execution point for ALL subprocess operations
2. Environment detection and capability discovery:
   - Python executable detection
   - Virtual environment setup and management
   - Git Bash detection (bash.exe)
   - Native binary detection (grep.exe, awk.exe, sed.exe, diff.exe, tar.exe, jq.exe)
3. Multiple execution methods:
   - execute_bash(): Execute via Git Bash (bash.exe -c "command")
   - execute_native(): Execute native binary (grep.exe args)
   - execute_powershell(): Execute PowerShell script
   - execute_cmd(): Execute cmd.exe command
   - execute_python(): Execute Python script (with venv support)
4. Test mode: Print commands without executing (for testing)
5. Logging: Trace all executions for debugging
6. Metrics: Track execution types (future feature)
7. Error handling: Centralized subprocess error management

NOT RESPONSIBLE FOR:
- Command translation (done by CommandEmulator)
- Execution strategy decisions (done by PipelineStrategy/ExecuteUnixSingleCommand)
- Path translation (done by PathTranslator)
- Security validation (done by SandboxValidator)
- Preprocessing (done by CommandExecutor)

WHY SINGLE POINT?
1. Test mode: Switch test/production in ONE place (no scattered subprocess calls)
2. Logging: All executions visible in logs
3. Metrics: Count execution types (bash vs native vs powershell)
4. Error handling: Consistent error handling
5. Environment management: Virtual environment activation in ONE place

CAPABILITY DETECTION:
On initialization, ExecutionEngine detects available capabilities:
- self.capabilities['python'] = True/False
- self.capabilities['bash'] = True/False
- self.capabilities['grep'] = True/False (native grep.exe)
- self.capabilities['awk'] = True/False (native awk.exe)
- etc.

These capabilities are used by upper layers to decide execution strategy.

DESIGN PATTERN:
- Facade Pattern: Simple interface hiding complex subprocess management
- Strategy Pattern: Different execution methods (bash, native, powershell, cmd, python)
- Singleton Pattern (conceptual): Should be single instance per BashToolExecutor
- Factory Pattern: Creates subprocess with correct configuration

EXECUTION METHODS:
1. execute_bash(command) → CompletedProcess
   - Uses: bash.exe -c "command"
   - Best for: POSIX compatibility, complex pipelines, stderr redirection
   - Requires: Git Bash installed

2. execute_native(cmd_name, args) → CompletedProcess
   - Uses: cmd_name.exe args (direct binary execution)
   - Best for: Performance (no translation overhead)
   - Requires: Native binary available (grep.exe, awk.exe, etc.)

3. execute_powershell(script) → CompletedProcess
   - Uses: powershell.exe -Command "script"
   - Best for: Emulated commands, complex PowerShell scripts
   - Requires: PowerShell (always available on Windows)

4. execute_cmd(command) → CompletedProcess
   - Uses: cmd.exe /c "command"
   - Best for: Simple Windows commands (dir, type, etc.)
   - Requires: cmd.exe (always available on Windows)

5. execute_python(script) → CompletedProcess
   - Uses: python.exe script.py (with venv activation if configured)
   - Best for: Python-based emulations
   - Requires: Python installed

DATA FLOW:
    execute_bash("grep -r TODO .") →
        1. Test mode? → Log and return fake result
        2. bash.exe available? → Check self.capabilities['bash']
        3. Build command: ["bash.exe", "-c", "grep -r TODO ."]
        4. subprocess.run(command, capture_output=True, timeout=timeout)
        5. Return CompletedProcess

USAGE PATTERN:
    engine = ExecutionEngine(
        working_dir=Path("C:/workspace"),
        test_mode=False,
        logger=logger
    )

    # Check capabilities
    if engine.capabilities['bash']:
        result = engine.execute_bash("find . -name '*.py'")
    elif engine.is_available('grep'):
        result = engine.execute_native('grep', ['-r', 'TODO', '.'])
    else:
        result = engine.execute_powershell("Get-ChildItem -Recurse *.py")

TEST MODE:
When test_mode=True:
- All capabilities set to True (bash, python, native bins)
- Commands logged but NOT executed
- Fake CompletedProcess returned with test_mode_stdout parameter

VIRTUAL ENVIRONMENT:
ExecutionEngine manages Python virtual environment:
1. Detection: Check if venv exists at workspace_root/venv
2. Activation: Prepend venv/Scripts to PATH when executing Python
3. Isolation: Python scripts run in isolated environment

NATIVE BINARY DETECTION:
ExecutionEngine scans PATH for native Windows binaries:
- grep.exe (GNU grep for Windows)
- awk.exe (GNU awk)
- sed.exe (GNU sed)
- diff.exe (GNU diff)
- tar.exe (BSD tar, included in Windows 10+)
- jq.exe (JSON processor)

These provide BEST PERFORMANCE (no translation) when available.
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, List

from .path_translator import PathTranslator

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

