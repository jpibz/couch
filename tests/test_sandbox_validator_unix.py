#!/usr/bin/env python3
"""
Test SandboxValidator with Unix commands

Verifies that SandboxValidator correctly:
1. Blocks dangerous Unix commands (dd, mkfs, sudo, etc.)
2. Blocks access to system directories (/etc, /sys, /dev, etc.)
3. Allows safe commands within workspace
4. Handles mixed Unix syntax + Windows paths (after translation)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bash_tool.sandbox_validator import SandboxValidator

# Initialize validator with REAL workspace (current directory)
# On Linux, use actual Linux paths; validator will work with both
workspace = Path("/home/user/couch").resolve()
validator = SandboxValidator(workspace)

def test_command(name, command, should_pass):
    """Test a command and verify expected result"""
    is_safe, reason = validator.validate_command(command)

    status = "✅ PASS" if (is_safe == should_pass) else "❌ FAIL"
    expected = "ALLOW" if should_pass else "BLOCK"
    actual = "ALLOWED" if is_safe else f"BLOCKED: {reason}"

    print(f"{status} | {name}")
    print(f"     Command: {command}")
    print(f"     Expected: {expected} | Actual: {actual}")
    print()

    return is_safe == should_pass


print("=" * 100)
print("SANDBOX VALIDATOR - Unix Command Tests")
print("=" * 100)
print()

results = []

# ============================================================================
# TEST GROUP 1: Dangerous Commands (should BLOCK)
# ============================================================================
print("--- TEST GROUP 1: Dangerous Unix Commands (MUST BLOCK) ---")
print()

results.append(test_command(
    "Block dd command",
    "dd if=/dev/zero of=/dev/sda",
    should_pass=False
))

results.append(test_command(
    "Block mkfs command",
    "mkfs.ext4 /dev/sdb1",
    should_pass=False
))

results.append(test_command(
    "Block sudo command",
    "sudo apt-get install malware",
    should_pass=False
))

results.append(test_command(
    "Block shutdown command",
    "shutdown -h now",
    should_pass=False
))

results.append(test_command(
    "Block apt-get command",
    "apt-get install suspicious-package",
    should_pass=False
))

results.append(test_command(
    "Block systemctl command",
    "systemctl stop firewall",
    should_pass=False
))

# ============================================================================
# TEST GROUP 2: System Directory Access (should BLOCK)
# ============================================================================
print("--- TEST GROUP 2: System Directory Access (MUST BLOCK) ---")
print()

results.append(test_command(
    "Block /etc access",
    "cat /etc/passwd",
    should_pass=False
))

results.append(test_command(
    "Block /sys access",
    "ls /sys/class/net",
    should_pass=False
))

results.append(test_command(
    "Block /dev access",
    "cat /dev/sda",
    should_pass=False
))

results.append(test_command(
    "Block /proc access",
    "cat /proc/meminfo",
    should_pass=False
))

results.append(test_command(
    "Block /root access",
    "ls /root/.ssh",
    should_pass=False
))

results.append(test_command(
    "Block /var/log access",
    "tail /var/log/syslog",
    should_pass=False
))

# ============================================================================
# TEST GROUP 3: Dangerous rm patterns (should BLOCK)
# ============================================================================
print("--- TEST GROUP 3: Dangerous rm Patterns (MUST BLOCK) ---")
print()

results.append(test_command(
    "Block rm -rf /",
    "rm -rf /",
    should_pass=False
))

results.append(test_command(
    "Block rm -rf /*",
    "rm -rf /*",
    should_pass=False
))

results.append(test_command(
    "Block rm -rf ~",
    "rm -rf ~",
    should_pass=False
))

# ============================================================================
# TEST GROUP 4: Safe Commands Within Workspace (should ALLOW)
# ============================================================================
print("--- TEST GROUP 4: Safe Commands Within Workspace (MUST ALLOW) ---")
print()

results.append(test_command(
    "Allow ls in workspace",
    "ls -la /home/user/couch",
    should_pass=True
))

results.append(test_command(
    "Allow grep in workspace",
    "grep -r TODO /home/user/couch",
    should_pass=True
))

results.append(test_command(
    "Allow rm in workspace",
    "rm /home/user/couch/temp.txt",
    should_pass=True
))

results.append(test_command(
    "Allow mv in workspace",
    "mv /home/user/couch/old.txt /home/user/couch/new.txt",
    should_pass=True
))

results.append(test_command(
    "Allow cp in workspace",
    "cp /home/user/couch/file.txt /home/user/couch/backup.txt",
    should_pass=True
))

results.append(test_command(
    "Allow cat in workspace",
    "cat /home/user/couch/README.md",
    should_pass=True
))

results.append(test_command(
    "Allow find in workspace",
    "find /home/user/couch -name *.py",
    should_pass=True
))

# ============================================================================
# TEST GROUP 5: Mixed Unix/Windows Paths (should handle correctly)
# ============================================================================
print("--- TEST GROUP 5: Mixed Unix/Windows Paths ---")
print()

results.append(test_command(
    "Allow /tmp paths (temp files)",
    "echo test > /tmp/output.txt",
    should_pass=True
))

results.append(test_command(
    "Block Unix path outside workspace",
    "rm /opt/sensitive_data/file.txt",
    should_pass=False
))

results.append(test_command(
    "Block access to parent directory escape",
    "ls /home/user/other_project",
    should_pass=False
))

# ============================================================================
# TEST GROUP 6: Edge Cases
# ============================================================================
print("--- TEST GROUP 6: Edge Cases ---")
print()

results.append(test_command(
    "Allow empty command",
    "",
    should_pass=True
))

results.append(test_command(
    "Allow simple echo",
    "echo Hello World",
    should_pass=True
))

results.append(test_command(
    "Allow command with pipes",
    "cat /home/user/couch/file.txt | grep pattern",
    should_pass=True
))

results.append(test_command(
    "Block dd even in pipeline",
    "ls /dev | dd of=/dev/sda",
    should_pass=False
))

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 100)
print("SUMMARY")
print("=" * 100)

passed = sum(results)
total = len(results)
failed = total - passed

print(f"Total tests: {total}")
print(f"Passed: {passed} ✅")
print(f"Failed: {failed} ❌")
print()

if failed == 0:
    print("🎉 ALL TESTS PASSED! SandboxValidator correctly handles Unix commands.")
else:
    print(f"⚠️  {failed} tests failed. Review implementation.")

print("=" * 100)
