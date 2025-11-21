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
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, List


class PersistentBashSession:
    """
    Persistent bash session - ONE user, ONE marker, BRUTAL efficiency
    
    CRITICAL: Commands must NOT be interactive (no stdin required)
    """
    
    # Marker improbabile - mix di caratteri che difficilmente appare in output
    MARKER = "<<<__EOF_b4sh_x9z_cmd_DONE_f7e3a2__>>>"
    
    def __init__(self, bash_path: str, env: dict, working_dir: Path):
        
        # ===== DIAGNOSTIC HEADER =====
        # Add diagnostic info BEFORE the actual command
        init_command = """
    echo "====== BASH DIAGNOSTIC INFO ======" >&2
    echo "PATH: $PATH" >&2
    echo "Python location: $(which python 2>&1 || echo 'NOT FOUND')" >&2
    echo "Python3 location: $(which python3 2>&1 || echo 'NOT FOUND')" >&2
    echo "Working dir: $(pwd)" >&2
    echo "Environment vars: HOME=$HOME USER=$USER" >&2
    echo "===================================" >&2
    """
        
        """Initialize persistent bash session"""
        self.process = subprocess.Popen(
            [bash_path, '--noprofile'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr → stdout
            text=True,
            encoding='utf-8',
            bufsize=1,  # Line buffered
            cwd=str(working_dir),
            env=env
        )
        
        # Setup PATH once
        self.process.stdin.write(init_command)  
        self.process.stdin.flush()
        
        # Eat initial output until ready
        self._eat_until_ready()
    
    def _eat_until_ready(self):
        """Wait for bash to be ready"""
        self.process.stdin.write(f"echo '{self.MARKER}'\n")
        self.process.stdin.flush()
        
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Bash process died during initialization")
            if self.MARKER in line:
                break
    
    def execute(self, command: str) -> tuple[str, int]:
        """Execute command and return (stdout, exitcode)"""
        full_cmd = (
            f"{command}\n"
            f"__EXITCODE=$?\n"
            f"echo '{self.MARKER}'\n"
            f"echo 'EXITCODE:'$__EXITCODE\n"
        )
        
        self.process.stdin.write(full_cmd)
        self.process.stdin.flush()
        
        output_lines = []
        exitcode = 0
        
        while True:
            line = self.process.stdout.readline()
            
            if not line:
                raise RuntimeError("Bash process died during command execution")
            
            if self.MARKER in line:
                exitcode_line = self.process.stdout.readline()
                if not exitcode_line:
                    raise RuntimeError("Missing exitcode line after marker")
                    
                if exitcode_line.startswith("EXITCODE:"):
                    try:
                        exitcode = int(exitcode_line.split(":")[1].strip())
                    except (IndexError, ValueError):
                        exitcode = -1
                break

            output_lines.append(line)
        
        return ''.join(output_lines), exitcode
    
    def close(self):
        """Close bash session gracefully"""
        if hasattr(self, 'process') and self.process.poll() is None:
            try:
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=5)
            except:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except:
                    self.process.kill()
    
    def __del__(self):
        """Cleanup on garbage collection"""
        self.close()
        

class ExecutionEngine:
    """
    UNICO PUNTO di esecuzione subprocess.

    Concentra TUTTE le chiamate subprocess in un solo posto per:
    - Test mode: vedere cosa viene eseguito senza eseguire
    - Logging: tracciare tutte le execution
    - Metrics: contare tipi di execution
    - Error handling: gestione errori centralizzata

    """

    # Native Windows binaries to detect
    # Format: 'name': ('binary.exe', 'default_path')
    # default_path = None → solo PATH detection, no fallback
    NATIVE_BINS = {
        'diff': ('diff.exe', r'C:\Program Files\Git\usr\bin\diff.exe'),
        'tar': ('tar.exe', r'C:\Program Files\Git\usr\bin\tar.exe'),
        'awk': ('awk.exe', r'C:\Program Files\Git\usr\bin\awk.exe'),
        'sed': ('sed.exe', r'C:\Program Files\Git\usr\bin\sed.exe'),
        'grep': ('grep.exe', r'C:\Program Files\Git\usr\bin\grep.exe'),
        'jq': ('jq.exe', r'C:\Program Files\Git\usr\bin\jq.exe'),
        'python': ('python.exe', None),  # Solo PATH detection (no default path)
    }

    def __init__(self, working_dir,
                 test_mode: bool = False,
                 logger: logging.Logger = None,
                 test_capabilities: Optional[Dict] = None):
        """
        Initialize execution engine.

        Args:
            working_dir: Workspace root directory (for venv setup)
            test_mode: If True, print commands instead of executing
            logger: Logger instance for execution tracking
            test_capabilities: Dict for TEST MODE ONLY - override availability detection
                Example: {'bash': False, 'grep': True, 'awk': False}
                - If None in test mode → all True (default mock behavior)
                - If dict provided → use those values to force specific test scenarios

        TEST MODE CAPABILITY CONTROL:
        This allows unit tests to simulate different environments:
        - {'bash': False} → Force MANUAL execution (test AST walking)
        - {'bash': True, 'grep': False} → Test bash with missing native bins
        - {'bash': False, 'grep': True} → Test manual with some native bins
        """
        self.working_dir = working_dir
        self.test_mode = test_mode
        self.test_capabilities = test_capabilities
        self.logger = logger or logging.getLogger('ExecutionEngine')

        # Timeouts
        self.default_timeout = 120  # 2 minutes
        self.python_timeout = 300   # 5 minutes

        # Detect bash availability
        self.bash_available = self._detect_bash()

        # Detect native bins availability (with default paths)
        self.available_bins = self._detect_native_bins()

        # Build capabilities dict
        self.capabilities = {
            'bash': self.bash_available,
            'python': 'python' in self.available_bins,
        }
        # Add native bins to capabilities
        for bin_name in self.available_bins:
            self.capabilities[bin_name] = True

        if test_mode:
            self.logger.info("[TEST MODE] ExecutionEngine initialized")
            self._setup_test_environment()
            self.virtual_env = None
            self.environment = os.environ.copy()
            self.bash_session = None  # No persistent session in test mode
        else:
            # Setup virtual environment
            self.virtual_env = self._setup_virtual_env(None)

            # Setup execution environment
            self.environment = self._setup_environment()

        # ===== CREATE PERSISTENT BASH SESSION =====
        if self.bash_available:
            try:
                env = self._build_bash_environment()
                self.bash_session = PersistentBashSession(
                    bash_path=self.bash_path,
                    env=env,
                    working_dir=self.working_dir
                )
                self.logger.info("Persistent bash session created")
            except Exception as e:
                self.logger.error(f"Failed to create persistent bash session: {e}")
                self.bash_session = None
        else:
            self.bash_session = None
        # ==========================================

        # Execution statistics
        self.stats = {
            'cmd': 0,
            'powershell': 0,
            'bash': 0,
            'native': 0,
            'total': 0
        }

    def _setup_test_environment(self):
        """Setup mock environment for testing"""
        import os
        
        # Mock environment variables (for testing variable expansion)
        os.environ['TEST_VAR'] = 'test_value'
        os.environ['NUM'] = '42'  # For arithmetic tests
        os.environ['PATH_VAR'] = '/tmp/test'
        os.environ['EMPTY_VAR'] = ''
        
        # Note: available_bins is now populated by _detect_native_bins()
        
        self.logger.info(f"[TEST MODE] Mock env vars: {list(os.environ.keys())[-4:]}")
        self.logger.info(f"[TEST MODE] Mock available bins: {len(self.available_bins)} bins detected")
    
    def _detect_bash(self) -> bool:
        """Quick bash.exe detection"""
        # In test mode, use test_capabilities if provided, otherwise default to True
        if self.test_mode:
            if self.test_capabilities is not None:
                # Use configured test capability
                bash_available = self.test_capabilities.get('bash', False)
                self.bash_path = 'bash' if bash_available else None
                return bash_available
            else:
                # Default test mode: all available
                self.bash_path = 'bash'
                return True

        try:
            import shutil
            self.bash_path = shutil.which('bash')
            if self.bash_path:
                return True
            return False
        except:
            self.bash_path = None
            return False
    
    def _detect_native_bins(self) -> dict:
        """
        Detect native binaries availability
        
        STRATEGY:
        1. Try shutil.which() first (checks PATH)
        2. If not found AND default_path exists, try default location
        3. If found, store full path
        
        default_path = None → solo PATH detection (es. python)
        
        Returns:
            Dict mapping bin_name -> full_path (if available)
        """
        if self.test_mode:
            # Test mode: use test_capabilities if provided, otherwise all available
            if self.test_capabilities is not None:
                # Use configured test capabilities - only include bins marked as True
                return {
                    name: bin_exe
                    for name, (bin_exe, _) in self.NATIVE_BINS.items()
                    if self.test_capabilities.get(name, False)
                }
            else:
                # Default test mode: all bins available (mock)
                return {
                    name: bin_exe
                    for name, (bin_exe, _) in self.NATIVE_BINS.items()
                }
        
        import shutil
        available = {}
        
        for name, (bin_exe, default_path) in self.NATIVE_BINS.items():
            # Try PATH first
            path = shutil.which(bin_exe)
            
            if path:
                available[name] = path
                self.logger.debug(f"Found {name} in PATH: {path}")
                continue
            
            # Try default location (if specified)
            if default_path:
                default = Path(default_path)
                if default.exists():
                    available[name] = str(default)
                    self.logger.debug(f"Found {name} at default: {default}")
                    continue
            
            self.logger.debug(f"Binary {name} not found")
        
        self.logger.info(f"Detected {len(available)}/{len(self.NATIVE_BINS)} native bins")
        return available

    def _windows_to_gitbash_paths(self, cmd: str) -> str:
        """
        Convert Windows paths in command to Git Bash format.
        
        C:\\path\\to\\file -> /c/path/to/file
        
        CRITICAL: bash.exe expects Unix-style paths!
        
        Args:
            cmd: Command string with Windows paths
            
        Returns:
            Command with converted paths
        """
        def convert_path(match):
            path = match.group(0)
            if ':' in path:
                # C:\path\to\file -> /c/path/to/file
                drive = path[0].lower()
                rest = path[3:].replace('\\', '/')
                return f'/{drive}/{rest}'
            # Just convert backslashes
            return path.replace('\\', '/')
        
        # Match Windows absolute paths (C:\path, D:\path, etc)
        pattern = r'[A-Za-z]:[/\\][^\s;|&<>()]*'
        return re.sub(pattern, convert_path, cmd)

    def _build_bash_environment(self) -> dict:
        """
        Build environment for Git Bash 
        
        Process:
            Take available bins (self.available_bins: {'python': 'C:\\Python\\python.exe'})
  

        Returns:
            Environment dict with PATH for Git Bash
        """
        import os

        # Inhert environment
        env = os.environ.copy()
 
        # Build PATH from available bins (convert Windows → Git Bash format)
        paths = []

        for bin_name, bin_path_str in self.available_bins.items():
            # bin_path_str is like: C:\Python311\python.exe
            # We need directory: C:\Python311
            bin_path = Path(bin_path_str)
            bin_dir = str(bin_path.parent)

            # Add to paths (avoid duplicates)
            if bin_dir not in paths:
                paths.append(bin_dir)
                self.logger.debug(f"Added to PATH: {bin_dir} (from {bin_name})")

        # Join with ; 
        env['PATH'] = ';'.join(paths)
        env['MSYS2_PATH_TYPE'] = 'inherit'
        
        self.logger.debug(f"Built Unix PATH for Git Bash: {env['PATH']}")

        return env

    def _simulate_command_output(self, command: str, stdin: str = None) -> str:
        """
        Simulate realistic command output for test mode
        
        Args:
            command: Command string
            stdin: Optional stdin data
            
        Returns:
            Simulated output
        """
        # Parse command
        parts = command.split()
        if not parts:
            return ""
        
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Simulate common commands
        if cmd == 'echo':
            # Echo just returns the arguments
            return ' '.join(args) + '\n'
        
        elif cmd == 'cat':
            # Cat returns stdin or file marker
            if stdin:
                return stdin
            elif args:
                return f"[content of {args[0]}]\n"
            return ""
        
        elif cmd == 'ls':
            # Ls returns file list + command marker for test verification
            marker = f"[{command}]\n" if len(command) < 50 else ""
            return marker + "file1.txt\nfile2.txt\nfile3.txt\n"
        
        elif cmd == 'pwd':
            # Pwd returns current dir
            return "/home/claude\n"
        
        elif cmd == 'test':
            # Test command returns empty (exit code is what matters)
            # But for test verification, return simple marker
            return f"test {' '.join(args)}\n"
        
        elif cmd == 'grep':
            # Grep filters stdin
            if stdin and args:
                pattern = args[0]
                lines = stdin.split('\n')
                matched = [l for l in lines if pattern in l]
                return '\n'.join(matched) + '\n' if matched else ""
            return ""
        
        elif cmd == 'wc':
            # Wc counts lines
            if stdin:
                lines = len(stdin.split('\n'))
                return f"  {lines}\n"
            return "  0\n"
        
        elif cmd == 'head':
            # Head returns first lines
            if stdin:
                lines = stdin.split('\n')[:10]
                return '\n'.join(lines) + '\n'
            return ""
        
        elif cmd == 'tail':
            # Tail returns last lines
            if stdin:
                lines = stdin.split('\n')[-10:]
                return '\n'.join(lines) + '\n'
            return ""
        
        elif cmd == 'sort':
            # Sort sorts lines
            if stdin:
                lines = stdin.split('\n')
                lines.sort()
                return '\n'.join(lines) + '\n'
            return ""
        
        elif cmd == 'test':
            # Test returns command marker for verification (exit code is what matters)
            return f"[{command}]\n"
        
        # Default: return simple marker
        return f"[output of {command}]\n"

    def execute_cmd(self, command: str, stdin: str = None, test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
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
            stdout = test_mode_stdout if test_mode_stdout is not None else self._simulate_command_output(command, stdin)

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
            timeout=self.default_timeout,
            **kwargs
        )

    def execute_powershell(self, command: str, stdin: str = None, test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
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
            stdout = test_mode_stdout if test_mode_stdout is not None else self._simulate_command_output(command, stdin)

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
    
    def execute_bash(self, command: str, stdin: str = None, test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
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
            stdout = test_mode_stdout if test_mode_stdout is not None else self._simulate_command_output(command, stdin)

            return subprocess.CompletedProcess(
                args=[self.bash_path, '-c', command],
                returncode=0,
                stdout=stdout,
                stderr=""
            )
        
        # Convert Windows paths to Git Bash format (C:\path -> /c/path)
        git_command = self._windows_to_gitbash_paths(command)

        env = self._build_bash_environment()
        
        # ===== USE PERSISTENT SESSION =====
        if self.bash_session:
            try:
                self.logger.debug(f"Executing via persistent session: {git_command}")
                output, exitcode = self.bash_session.execute(git_command)
                
                return subprocess.CompletedProcess(
                    args=[self.bash_path, '-c', git_command],
                    returncode=exitcode,
                    stdout=output,
                    stderr=""  # Already merged in stdout
                )
            except RuntimeError as e:
                self.logger.error(f"Persistent bash session died: {e}")
                # Session died - try to recreate
                try:

                    self.bash_session = PersistentBashSession(
                        bash_path=self.bash_path,
                        env=env,
                        working_dir=str(self.working_dir)
                    )
                    self.logger.info("Recreated persistent bash session")
                    # Retry command
                    output, exitcode = self.bash_session.execute(git_command)
                    return subprocess.CompletedProcess(
                        args=[self.bash_path, '-c', git_command],
                        returncode=exitcode,
                        stdout=output,
                        stderr=""
                    )
                except Exception as e2:
                    self.logger.error(f"Failed to recreate session: {e2}")
                    raise RuntimeError(f"Bash session failed: {e}") from e2
        # ==================================

        # Fallback: old method (shouldn't happen)
        
        self.logger.debug(f"Executing NEW Git Bash: {git_command}")
        return subprocess.run(
            [self.bash_path, '-c', git_command],
            capture_output=True,
            text=True,
            cwd=str(self.working_dir),
            env=env,
            **kwargs
        )

    def execute_native(self, bin_name: str, args: List[str], stdin: str = None, test_mode_stdout=None, **kwargs) -> subprocess.CompletedProcess:
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
        
        cmd = [bin_name] + args
        cmd_str = ' '.join(cmd)

        if self.test_mode:
            self.logger.info(f"[TEST-Native] {cmd_str}")
            print(f"[TEST MODE] Would execute (Native): {cmd_str}")

            # Use AS IF stdout if provided, otherwise echo
            stdout = test_mode_stdout if test_mode_stdout is not None else self._simulate_command_output(cmd_str, stdin)

            return subprocess.CompletedProcess(
                args=cmd,
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
            cmd,
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
        is_available = self.available_bins.get(name.lower(), None)
        return True if is_available else False

    # ==================== SETUP/DETECTION METHODS ====================

    def _setup_virtual_env(self, virtual_env: Optional[str] = None) -> Optional[Path]:
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
        default_venv = self.working_dir / 'BASH_TOOL_ENV'

        if default_venv.exists():
            self.logger.info(f"Using default venv: {default_venv}")
            return default_venv

        # Create default venv - BLOCKING but only at initialization
        python_exe = self.available_bins.get('python')
        if not python_exe:
            self.logger.warning("No Python executable configured, cannot create virtual environment")
            return None

        try:
            self.logger.warning(f"Virtual environment missing. Creating at: {default_venv}")
            self.logger.warning("This is a ONE-TIME operation that may take up to 60 seconds...")

            subprocess.run(
                [python_exe, '-m', 'venv', str(default_venv)],
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
            venv_scripts = str(self.virtual_env / 'Scripts')
            env['PATH'] = f"{venv_scripts}{os.pathsep}{env.get('PATH', '')}"
            env['VIRTUAL_ENV'] = str(self.virtual_env)

        # Python executable directory
        if self.is_available('python'):
            python_dir = Path(self.available_bins['python']).parent if '/' in self.available_bins['python'] or '\\' in self.available_bins['python'] else None
            if python_dir:
                env['PATH'] = f"{str(python_dir)}{os.pathsep}{env.get('PATH', '')}"
        
        return env

    def close(self):
        """Close persistent bash session"""
        if hasattr(self, 'bash_session') and self.bash_session:
            self.bash_session.close()
            self.bash_session = None
            self.logger.info("Persistent bash session closed")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.close()
