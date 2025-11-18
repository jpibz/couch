#!/usr/bin/env python3
"""Sposta 4 metodi setup - versione SEMPLICE con testo esatto"""

# Leggi file come TESTO
with open('bash_tool_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File letto")

# METODO 1: _detect_git_bash (righe 7606-7640)
method1 = '''    def _detect_git_bash(self) -> Optional[str]:
        """
        Detect Git Bash executable.

        Standard locations:
        - C:\\Program Files\\Git\\bin\\bash.exe
        - C:\\Program Files (x86)\\Git\\bin\\bash.exe
        """
        candidates = [
            r"C:\\Program Files\\Git\\bin\\bash.exe",
            r"C:\\Program Files (x86)\\Git\\bin\\bash.exe",
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
                bash_path = result.stdout.strip().split('\\n')[0]
                if 'Git' in bash_path:
                    self.logger.info(f"Found Git Bash in PATH: {bash_path}")
                    return bash_path
        except:
            pass

        return None
'''

# METODO 2: _detect_system_python (righe 7642-7676)
method2 = '''    def _detect_system_python(self) -> str:
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
'''

# METODO 3: _setup_virtual_env (righe 7678-7724)
method3 = '''    def _setup_virtual_env(self, virtual_env: Optional[str]) -> Optional[Path]:
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
'''

# METODO 4: _setup_environment (righe 7789-7808)
method4 = '''    def _setup_environment(self) -> dict:
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
            python_dir = Path(self.python_executable).parent if '/' in self.python_executable or '\\\\' in self.python_executable else None
            if python_dir:
                env['PATH'] = f"{python_dir}{os.pathsep}{env.get('PATH', '')}"

        return env
'''

# Trova dove inserire (prima di class BashToolExecutor)
insert_marker = 'class BashToolExecutor(ToolExecutor):'
if insert_marker not in content:
    print("❌ Non trovato BashToolExecutor!")
    exit(1)

insert_pos = content.find(insert_marker)

# Inserisci i 4 metodi prima di BashToolExecutor
separator = "\n    # ==================== SETUP/DETECTION METHODS (migrated from BashToolExecutor) ====================\n\n"
methods_block = separator + method1 + '\n' + method2 + '\n' + method3 + '\n' + method4 + '\n\n'

content = content[:insert_pos] + methods_block + content[insert_pos:]

print("Inseriti 4 metodi prima di BashToolExecutor")

# Rimuovi i metodi originali da BashToolExecutor
# Trova e rimuovi method1
start1 = content.find('    def _detect_git_bash(self) -> Optional[str]:', insert_pos + len(methods_block))
if start1 != -1:
    end1 = content.find('\n    def ', start1 + 50)  # Trova prossimo metodo
    if end1 != -1:
        content = content[:start1] + content[end1:]
        print("Rimosso _detect_git_bash da BashToolExecutor")

# Trova e rimuovi method2
start2 = content.find('    def _detect_system_python(self) -> str:', insert_pos)
if start2 != -1:
    end2 = content.find('\n    def ', start2 + 50)
    if end2 != -1:
        content = content[:start2] + content[end2:]
        print("Rimosso _detect_system_python da BashToolExecutor")

# Trova e rimuovi method3
start3 = content.find('    def _setup_virtual_env(self, virtual_env: Optional[str]) -> Optional[Path]:', insert_pos)
if start3 != -1:
    end3 = content.find('\n    def ', start3 + 50)
    if end3 != -1:
        content = content[:start3] + content[end3:]
        print("Rimosso _setup_virtual_env da BashToolExecutor")

# Trova e rimuovi method4
start4 = content.find('    def _setup_environment(self) -> dict:', insert_pos)
if start4 != -1:
    end4 = content.find('\n    def ', start4 + 50)
    if end4 != -1:
        content = content[:start4] + content[end4:]
        print("Rimosso _setup_environment da BashToolExecutor")

# Scrivi file
with open('bash_tool_executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ File scritto")
print("🎉 MIGRAZIONE SETUP METHODS COMPLETATA!")
