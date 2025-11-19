"""
Constants and configuration for bash tool executor
"""

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
