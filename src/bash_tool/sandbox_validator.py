"""
Sandbox validator for bash command execution

ARCHITECTURE:
- Security layer enforcing workspace containment and command safety
- First line of defense before command execution
- Used by BashToolExecutor to validate commands pre-execution
- Stateless validator - no side effects, only validation

RESPONSIBILITIES:
- Validate commands don't escape workspace boundaries
- Block dangerous system commands (format, reg, shutdown, etc.)
- Enforce drive access restrictions (only workspace drive)
- Validate restricted commands (del, move, copy within workspace)

NOT RESPONSIBLE FOR:
- Executing commands (done by ExecutionEngine)
- Translating commands (done by CommandEmulator)
- Path translation (done by PathTranslator)
- Making execution strategy decisions

SECURITY MODEL:
- Workspace containment: Commands can only access workspace directory
- Command blacklist: Dangerous system commands blocked
- Drive restrictions: Only workspace drive accessible
- Path enforcement: Absolute paths outside workspace rejected
- NOT A FULL SANDBOX: Protection against common dangerous operations,
  not designed to stop determined attackers (not the use case)

USAGE PATTERN:
validator = SandboxValidator(workspace_root=Path("C:/project"))
is_safe, reason = validator.validate_command("rm -rf /")
if not is_safe:
    raise SecurityError(reason)

VALIDATION FLOW:
command → check dangerous_commands → check path boundaries →
check drive access → check restricted commands → (True, "OK")

DESIGN PATTERN: Validator + Strategy (multiple validation strategies)
"""
import re
from pathlib import Path


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
                return False, f"Access to drive {drive}: blocked (workspace is on {self.workspace_drive}:)"

        return True, "OK"

    def _validate_restricted_command(self, command: str, cmd_name: str) -> tuple[bool, str]:
        """Validate restricted command with extra checks"""
        # For now, just allow restricted commands within workspace
        # Future: add more granular checks (e.g., del ../.. blocked)
        return True, "OK"
