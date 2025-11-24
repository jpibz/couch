"""
Sandbox validator for bash command execution

ARCHITECTURE:
- Security layer enforcing workspace containment and command safety
- First line of defense before command execution
- Used by BashToolExecutor to validate commands pre-execution
- Stateless validator - no side effects, only validation

RESPONSIBILITIES:
- Validate commands don't escape workspace boundaries
- Block dangerous Unix/Linux commands (rm -rf /, dd, mkfs, etc.)
- Block access to system directories (/etc, /sys, /dev, /proc, etc.)
- Enforce workspace containment for both Unix and Windows paths
- Validate restricted commands (rm, mv, cp within workspace)

NOT RESPONSIBLE FOR:
- Executing commands (done by ExecutionEngine)
- Translating commands (done by CommandEmulator)
- Path translation (done by PathTranslator)
- Making execution strategy decisions

SECURITY MODEL:
- Workspace containment: Commands can only access workspace directory
- Command blacklist: Dangerous Unix/Linux commands blocked
- System directory protection: /etc, /sys, /dev, /proc, /var blocked
- Path enforcement: Absolute paths outside workspace rejected
- NOT A FULL SANDBOX: Protection against common dangerous operations,
  not designed to stop determined attackers (not the use case)

USAGE PATTERN:
validator = SandboxValidator(workspace_root=Path("C:/project"))
is_safe, reason = validator.validate_command("rm -rf /")
if not is_safe:
    raise SecurityError(reason)

VALIDATION FLOW:
command → check dangerous_commands → check system_directories →
check path boundaries → check restricted commands → (True, "OK")

INPUT FORMAT:
Receives pure Unix commands BEFORE path translation:
  Example: "rm -rf /home/user/workspace/file.txt"
  - Unix syntax (rm -rf)
  - Unix paths (/home/user/...)

DESIGN PATTERN: Validator + Strategy (multiple validation strategies)
"""
import re
from pathlib import Path


class SandboxValidator:
    """
    Sandbox validator for Unix/Linux bash command execution.

    SECURITY MODEL:
    - Workspace containment: Commands can only access workspace directory
    - Command blacklist: Dangerous Unix commands blocked
    - System directory protection: /etc, /sys, /dev, /proc blocked
    - Path enforcement: Absolute paths outside workspace rejected

    NOT A FULL SANDBOX: Protection against common dangerous operations,
    not designed to stop determined attackers (not the use case).
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        # Extract drive for Windows path validation (if on Windows)
        self.workspace_drive = self.workspace_root.drive.upper() if self.workspace_root.drive else None

        # BLACKLIST: Dangerous Unix/Linux commands that should NEVER execute
        self.dangerous_commands = {
            # Disk/filesystem destructive operations
            'dd',           # Can wipe drives: dd if=/dev/zero of=/dev/sda
            'mkfs',         # Format filesystem
            'fdisk',        # Partition table manipulation
            'parted',       # Partition editor
            'shred',        # Secure file deletion (often on system files)

            # System modification
            'reboot',       # System reboot
            'shutdown',     # System shutdown
            'halt',         # System halt
            'poweroff',     # Power off
            'init',         # Change runlevel
            'telinit',      # Change runlevel

            # Kernel/module operations
            'insmod',       # Insert kernel module
            'rmmod',        # Remove kernel module
            'modprobe',     # Load kernel module

            # System administration (when used maliciously)
            'iptables',     # Firewall rules
            'ip6tables',    # IPv6 firewall
            'sysctl',       # Kernel parameters

            # Package managers (could install malware)
            'apt-get',      # Debian/Ubuntu package manager
            'yum',          # RedHat/CentOS package manager
            'dnf',          # Fedora package manager
            'pacman',       # Arch package manager
            'snap',         # Snap package manager

            # Service management
            'systemctl',    # Systemd service control
            'service',      # SysV service control

            # User/permission escalation
            'sudo',         # Run as superuser
            'su',           # Switch user
            'chroot',       # Change root directory
        }

        # RESTRICTED: Unix commands allowed only with careful argument checking
        self.restricted_commands = {
            'rm',           # Remove files (check for -rf / or system paths)
            'mv',           # Move files (check destination)
            'cp',           # Copy files (check destination)
            'chmod',        # Change permissions (check not on system files)
            'chown',        # Change ownership (check not on system files)
            'ln',           # Create links (check not to system files)
        }

        # SYSTEM DIRECTORIES: Unix paths that should NEVER be accessed
        self.protected_unix_paths = {
            '/etc',         # System configuration
            '/sys',         # Kernel/system info
            '/dev',         # Device files
            '/proc',        # Process info
            '/boot',        # Boot files
            '/root',        # Root user home
            '/bin',         # System binaries
            '/sbin',        # System admin binaries
            '/lib',         # System libraries
            '/lib64',       # 64-bit libraries
            '/usr/bin',     # User binaries (system)
            '/usr/sbin',    # User admin binaries
            '/usr/lib',     # User libraries
            '/var/log',     # System logs
            '/var/run',     # Runtime data
        }

    def validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate Unix command for sandbox safety.

        Args:
            command: Unix command with mixed Unix/Windows paths (after path translation)

        Returns:
            (is_safe, reason)
            - (True, "OK") if safe
            - (False, "reason") if blocked
        """
        if not command or not command.strip():
            return True, "OK"

        command_lower = command.lower().strip()

        # Check 1: Dangerous Unix commands blacklist
        for dangerous_cmd in self.dangerous_commands:
            if self._contains_command(command_lower, dangerous_cmd):
                return False, f"Dangerous command blocked: {dangerous_cmd}"

        # Check 2: Protected Unix system directories
        is_safe, reason = self._check_unix_system_directories(command)
        if not is_safe:
            return False, reason

        # Check 3: Unix absolute paths outside workspace
        is_safe, reason = self._check_unix_path_boundaries(command)
        if not is_safe:
            return False, reason

        # Check 4: Windows absolute paths outside workspace (after path translation)
        is_safe, reason = self._check_windows_path_boundaries(command)
        if not is_safe:
            return False, reason

        # Check 5: Drive access restrictions (Windows)
        if self.workspace_drive:
            is_safe, reason = self._check_drive_access(command)
            if not is_safe:
                return False, reason

        # Check 6: Restricted commands need extra validation
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

    def _check_unix_system_directories(self, command: str) -> tuple[bool, str]:
        """Check that command doesn't access protected Unix system directories"""
        # SAFE exceptions: commonly used in bash commands
        safe_system_files = [
            '/dev/null',      # Discard output
            '/dev/zero',      # Zero bytes source
            '/dev/urandom',   # Random bytes
            '/dev/stdin',     # Standard input
            '/dev/stdout',    # Standard output
            '/dev/stderr',    # Standard error
        ]

        # Check for any protected path in command
        for protected_path in self.protected_unix_paths:
            # Match protected path as:
            # - Exact match: /etc (end of string or followed by space/quote)
            # - Subpath: /etc/passwd
            # - With trailing slash: /etc/
            pattern = re.escape(protected_path) + r'(?:/|[\s"\']|$)'

            matches = re.finditer(pattern, command)
            for match in matches:
                full_match = command[match.start():min(match.end() + 20, len(command))]

                # Check if this is a safe exception
                is_safe_exception = any(safe_file in full_match for safe_file in safe_system_files)
                if is_safe_exception:
                    continue

                return False, f"Access to system directory blocked: {protected_path}"

        return True, "OK"

    def _check_unix_path_boundaries(self, command: str) -> tuple[bool, str]:
        """Check that Unix absolute paths don't escape workspace"""
        # Pattern: Unix absolute path starting with /
        # Matches: /home/user/file, /etc/passwd, etc.
        # But NOT Windows paths like C:\path or \\network\path
        pattern = r'(?<![A-Z]:)(/[^\s"\']+)'

        matches = re.finditer(pattern, command)

        for match in matches:
            unix_path = match.group(1)

            # SKIP sed/awk patterns and regex - NOT real paths!
            if self._is_sed_awk_pattern(unix_path):
                continue

            # SKIP bash variables - NOT real paths!
            if self._is_bash_variable_path(unix_path):
                continue

            # Special case: /tmp and /var/tmp are always allowed (temp files)
            if unix_path.startswith(('/tmp/', '/var/tmp/')):
                continue

            # Try to validate Unix path against workspace
            # If workspace is Unix path, check containment
            # If workspace is Windows path, assume Unix paths should have been translated
            try:
                unix_path_obj = Path(unix_path)

                # If workspace is Unix (starts with /), validate containment
                if str(self.workspace_root).startswith('/'):
                    try:
                        # Resolve both to handle symlinks and relative components
                        resolved_path = unix_path_obj.resolve()
                        resolved_path.relative_to(self.workspace_root)
                        # Path is within workspace - OK
                        continue
                    except (ValueError, OSError):
                        # Path is OUTSIDE workspace
                        # Block system paths AND non-system paths outside workspace
                        # (unless they're allowed prefixes like /tmp handled above)
                        return False, f"Path outside workspace blocked: {unix_path}"

                else:
                    # Workspace is Windows path
                    # Unix paths should have been translated, if we see them it's suspicious
                    # Allow common patterns that PathTranslator handles
                    allowed_prefixes = ['/home/', '/workspace/']
                    is_allowed = any(unix_path.startswith(prefix) for prefix in allowed_prefixes)

                    if not is_allowed:
                        if unix_path.startswith(('/etc', '/sys', '/dev', '/proc', '/boot', '/root',
                                                '/bin', '/sbin', '/lib', '/usr', '/var', '/opt')):
                            return False, f"System path access blocked: {unix_path}"

            except Exception:
                # Invalid path - let it fail naturally
                pass

        return True, "OK"

    def _check_windows_path_boundaries(self, command: str) -> tuple[bool, str]:
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
        """
        Check that command doesn't access other drives

        IMPORTANT: This check is for RAW drive access (D:, E:, etc.)
        NOT for paths translated by PathTranslator!

        PathTranslator may translate paths to different drives (e.g., F:\workspace\...)
        which are SAFE because they're managed by PathTranslator.

        We only block RAW drive letters that are NOT part of a full path.
        """
        # Pattern: Drive letter references (C:, D:, etc.)
        # But EXCLUDE if followed by backslash (full path, likely from PathTranslator)
        pattern = r'\b([A-Z]):(?!\\)'

        matches = re.finditer(pattern, command, re.IGNORECASE)

        for match in matches:
            drive = match.group(1).upper()
            if drive != self.workspace_drive:
                return False, f"Access to drive {drive}: blocked (workspace is on {self.workspace_drive}:)"

        return True, "OK"

    def _validate_restricted_command(self, command: str, cmd_name: str) -> tuple[bool, str]:
        """Validate restricted Unix command with extra checks"""

        # Special handling for 'rm' command
        if cmd_name == 'rm':
            # Block extremely dangerous patterns
            dangerous_rm_patterns = [
                r'rm\s+.*-rf\s+/',      # rm -rf / or rm -rf /*
                r'rm\s+.*-rf\s+\*',     # rm -rf * (in root context)
                r'rm\s+.*-rf\s+~',      # rm -rf ~ (delete home)
            ]

            for pattern in dangerous_rm_patterns:
                if re.search(pattern, command.lower()):
                    return False, f"Dangerous rm pattern blocked: {cmd_name}"

        # For mv, cp, chmod, chown, ln - check they don't target system paths
        # (already checked by system directory validation)

        # Allow restricted commands with workspace paths
        # Additional granular checks can be added here in future
        return True, "OK"

    def _is_sed_awk_pattern(self, path: str) -> bool:
        """
        Check if this is a sed/awk pattern, NOT a real path.

        Sed/awk patterns:
        - /pattern/replacement/ (has multiple /)
        - /^regex/ (starts with regex chars)
        - /pattern/flags (ends with flags like g, i)
        - Contains regex metacharacters: ^, $, [, ], *, +, ?, |, \
        """
        # Has multiple / → likely s/pattern/replacement/
        if path.count('/') >= 2:
            return True

        # Starts with regex metacharacters
        if len(path) > 1 and path[1] in ('^', '$', '[', '.', '*', '+', '?', '|', '\\'):
            return True

        # Contains typical sed/awk patterns
        if any(char in path for char in ('^', '$', '[', ']', '*', '+', '?', '|', '&')):
            return True

        # Ends with ) → likely awk variable like /count)
        if path.endswith(')'):
            return True

        return False

    def _is_bash_variable_path(self, path: str) -> bool:
        """
        Check if this contains bash variables, NOT a real path.

        Examples:
        - /$var
        - /${var}
        - /$env/$svc
        - /}:
        """
        # Contains $ → bash variable
        if '$' in path:
            return True

        # Contains {, } → bash expansion
        if '{' in path or '}' in path:
            return True

        # Very short with special chars → likely not a real path
        if len(path) <= 3 and any(c in path for c in ('$', '{', '}', ')')):
            return True

        return False
