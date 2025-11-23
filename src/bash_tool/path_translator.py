"""
Path Translator - Unix/Windows path translation
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

class PathTranslator:
    """
    Unix↔Windows path translation layer for Claude interface.
    
    ARCHITECTURE:
    Claude operates with Unix-style paths (natural interface).
    Backend operates on Windows filesystem (real implementation).
    
    VIRTUAL UNIX STRUCTURE (Claude-side):
    /home/claude              → Claude's working directory (SHARED across tools)
    /mnt/user-data/uploads    → User uploaded files
    /mnt/user-data/outputs    → Files for user download
    
    REAL WINDOWS STRUCTURE (Backend):
    \\tools_executors_workspace\\claude\\          → Shared Claude working directory
    \\tools_executors_workspace\\uploads\\         → Shared uploads
    \\tools_executors_workspace\\outputs\\         → Shared outputs
    \\tools_executors_workspace\\{tool_name}\\     → Tool scratch (NOT managed by PathTranslator)
    
    EXAMPLE TRANSLATIONS:
    Claude: /home/claude/script.py
    → Windows: \\tools_executors_workspace\\claude\\script.py
    
    Claude: /mnt/user-data/uploads/data.csv
    → Windows: \\tools_executors_workspace\\uploads\\data.csv
    
    Claude: /mnt/user-data/outputs/report.pdf
    → Windows: \\tools_executors_workspace\\outputs\\report.pdf
    
    NOTE: Tool-specific scratch directories (workspace_root/{tool_name}/)
    are managed directly by tools via get_tool_scratch_directory(), NOT via path translation.
    """
    
    def __init__(self):
        
        # Base workspace directory
        app_dir = os.path.dirname(os.path.abspath(__file__))
        self.workspace_root = Path(os.path.join(app_dir, "tools_executors_workspace"))
        
        # Virtual Unix paths (what Claude sees)
        self.unix_home = '/home/claude'
        self.unix_uploads = '/mnt/user-data/uploads'
        self.unix_outputs = '/mnt/user-data/outputs'
        
        # Ensure directories exist at initialization
        self.ensure_directories_exist()
    
    # ========== WORKSPACE MANAGEMENT ==========
    
    def get_workspace_root(self) -> Path:
        """
        Get workspace root directory (Windows path).
        
        Returns:
            Path: Base workspace directory
        """
        return self.workspace_root
    
    def get_tool_scratch_directory(self, tool_name: str) -> Path:
        """
        Get tool-specific scratch directory (Windows path).
        
        Tool scratch directories are for internal temp files and operations.
        These are NOT visible to Claude - they're for tool internal use only.
        
        Args:
            tool_name: Name of the tool (e.g., 'bash_tool', 'view')
            
        Returns:
            Path: Tool scratch directory (e.g., workspace_root/bash_tool/)
        """
        return self.workspace_root / tool_name
    
    # ========== CLAUDE HOME DIRECTORY ==========
    
    def get_claude_home_unix(self) -> str:
        """
        Get Claude's home directory Unix path.
        
        This is Claude's main working directory, shared across all tools.
        
        Returns:
            str: Unix path for Claude's home directory (/home/claude)
        """
        return self.unix_home
    
    def get_claude_home_windows(self) -> Path:
        """
        Get Claude's home directory Windows path.
        
        Returns:
            Path: Windows path for Claude's home directory
        """
        return self.workspace_root / 'claude'
    
    # ========== UPLOADS DIRECTORY ==========
    
    def get_uploads_directory_unix(self) -> str:
        """
        Get uploads directory Unix path.
        
        Returns:
            str: Unix path for uploads directory
        """
        return self.unix_uploads
    
    def get_uploads_directory_windows(self) -> Path:
        """
        Get uploads directory Windows path.
        
        Returns:
            Path: Windows path for uploads directory
        """
        return self.workspace_root / 'uploads'
    
    # ========== OUTPUTS DIRECTORY ==========
    
    def get_outputs_directory_unix(self) -> str:
        """
        Get outputs directory Unix path.
        
        Returns:
            str: Unix path for outputs directory
        """
        return self.unix_outputs
    
    def get_outputs_directory_windows(self) -> Path:
        """
        Get outputs directory Windows path.
        
        Returns:
            Path: Windows path for outputs directory
        """
        return self.workspace_root / 'outputs'
    
    # ========== PATH TRANSLATION ==========
    
    def to_windows(self, unix_path: str) -> Path:
        """
        Translate Unix path → Windows path.
        
        Handles Claude's home, uploads, and outputs directories.
        
        Args:
            unix_path: Unix-style path from Claude
            
        Returns:
            Windows Path object for actual filesystem operations
            
        Raises:
            ValueError: If path is not in managed directories
        """
        # Normalize Unix path
        unix_path = unix_path.replace('\\', '/')
        
        # Check for Claude home directory
        if unix_path.startswith(self.unix_home):
            relative = unix_path[len(self.unix_home):].lstrip('/')
            if relative:
                return self.workspace_root / 'claude' / relative
            else:
                return self.workspace_root / 'claude'
        
        # Check for uploads directory
        elif unix_path.startswith(self.unix_uploads):
            relative = unix_path[len(self.unix_uploads):].lstrip('/')
            if relative:
                return self.workspace_root / 'uploads' / relative
            else:
                return self.workspace_root / 'uploads'
        
        # Check for outputs directory
        elif unix_path.startswith(self.unix_outputs):
            relative = unix_path[len(self.unix_outputs):].lstrip('/')
            if relative:
                return self.workspace_root / 'outputs' / relative
            else:
                return self.workspace_root / 'outputs'
        
        else:
            # Path not recognized - raise error
            raise ValueError(f"PathTranslator only handles /home/claude, uploads, outputs. Got: {unix_path}")
    
    def to_unix(self, windows_path: Path) -> str:
        """
        Translate Windows path → Unix path.
        
        Handles Claude's home, uploads, and outputs directories.
        
        Args:
            windows_path: Windows Path object
            
        Returns:
            Unix-style path string for Claude
            
        Raises:
            ValueError: If path is not in managed directories
        """
        # Convert to absolute path
        windows_path = windows_path.resolve()
        
        # Check Claude home
        claude_dir = self.workspace_root / 'claude'
        if windows_path.is_relative_to(claude_dir):
            relative = windows_path.relative_to(claude_dir)
            if str(relative) == '.':
                return self.unix_home
            return f"{self.unix_home}/{relative.as_posix()}"
        
        # Check uploads
        uploads_dir = self.workspace_root / 'uploads'
        if windows_path.is_relative_to(uploads_dir):
            relative = windows_path.relative_to(uploads_dir)
            if str(relative) == '.':
                return self.unix_uploads
            return f"{self.unix_uploads}/{relative.as_posix()}"
        
        # Check outputs
        outputs_dir = self.workspace_root / 'outputs'
        if windows_path.is_relative_to(outputs_dir):
            relative = windows_path.relative_to(outputs_dir)
            if str(relative) == '.':
                return self.unix_outputs
            return f"{self.unix_outputs}/{relative.as_posix()}"
        
        # Path not in managed directories - raise error
        raise ValueError(f"PathTranslator only handles claude/, uploads/, outputs/. Got: {windows_path}")
    
    # ========== INITIALIZATION ==========
    
    def ensure_directories_exist(self):
        """
        Ensure all managed directories exist on Windows filesystem.
        
        Creates:
        - claude/ (Claude's working directory)
        - uploads/ (user uploaded files)
        - outputs/ (files for user download)
        """
        (self.workspace_root / 'claude').mkdir(parents=True, exist_ok=True)
        (self.workspace_root / 'uploads').mkdir(parents=True, exist_ok=True)
        (self.workspace_root / 'outputs').mkdir(parents=True, exist_ok=True)

    # ========== BATCH TRANSLATION ==========

    def translate_paths_in_string(self, text: str, direction: str) -> str:
        """
        Translate ALL paths in a string (Unix↔Windows).
        
        Args:
            text: String containing paths to translate
            direction: 'to_windows' or 'to_unix'
            
        Returns:
            String with all paths translated
            
        Usage:
            # Before command execution (Unix → Windows):
            cmd = translator.translate_paths_in_string(cmd, 'to_windows')
            
            # After command execution (Windows → Unix):
            output = translator.translate_paths_in_string(output, 'to_unix')
        """
        if not text:
            return text
        
        if direction == 'to_windows':
            return self._translate_unix_paths_to_windows(text)
        elif direction == 'to_unix':
            return self._translate_windows_paths_to_unix(text)
        else:
            raise ValueError(f"Invalid direction: {direction}")
    
    def _translate_unix_paths_to_windows(self, text: str) -> str:
        """
        Find and translate Unix absolute paths → Windows

        STRATEGY (TWO-PASS WITH MARKERS):
        1. First pass: Translate known paths (home/claude, uploads, outputs) → MARKER
        2. Second pass: Translate other Unix absolute paths as relative to /home/claude/
        3. Final: Replace all markers with actual paths

        EXAMPLES:
        - /home/claude/file.txt → workspace_root/claude/file.txt (known path)
        - /mnt/user-data/uploads/data.csv → workspace_root/uploads/data.csv (known path)
        - /tmp/file.txt → workspace_root/claude/tmp/file.txt (relative path, DEFAULT)
        - /var/log/app.log → workspace_root/claude/var/log/app.log (relative path, DEFAULT)
        """

        # Marker for translated paths (prevents double-translation)
        MARKER_PREFIX = "<<<TRANSLATED_PATH_"
        MARKER_SUFFIX = ">>>"
        translated_paths = {}  # marker_id → actual_path
        marker_counter = [0]  # Use list for mutable counter in closure

        # PASS 1: Known paths (home/claude, uploads, outputs)
        # Pattern: Unix absolute path for home/uploads/outputs
        # Matches: /home/claude/..., /mnt/user-data/uploads/..., /mnt/user-data/outputs/...
        pattern_known = r'(/(?:home/claude|mnt/user-data/(?:uploads|outputs))(?:/[\w\-\.]+)*)'

        def replace_known_path(match):
            unix_path = match.group(1)
            try:
                windows_path = self.to_windows(unix_path)
                # Quote if contains spaces
                if ' ' in str(windows_path):
                    windows_path_str = f'"{windows_path}"'
                else:
                    windows_path_str = str(windows_path)

                # Use marker to prevent double-translation
                marker_id = marker_counter[0]
                marker_counter[0] += 1
                marker = f"{MARKER_PREFIX}{marker_id}{MARKER_SUFFIX}"
                translated_paths[marker] = windows_path_str
                return marker
            except Exception:
                # Keep original if translation fails
                return unix_path

        text = re.sub(pattern_known, replace_known_path, text)

        # PASS 2: Other Unix absolute paths (DEFAULT: relative to /home/claude/)
        # Pattern: Unix absolute path that is NOT already translated
        # Matches: /tmp/..., /var/..., /etc/..., etc.
        # Excludes: Known paths (home/claude, mnt/user-data) and markers
        pattern_relative = r'(/(?!home/claude|mnt/user-data/)[\w\-\.]+(?:/[\w\-\.]+)*)'

        def replace_relative_path(match):
            unix_path = match.group(1)

            # Skip if INSIDE a marker (between PREFIX and SUFFIX)
            # Check if there's an unclosed PREFIX before this match
            match_start = match.start()
            context_before = text[max(0, match_start-50):match_start]

            # Count PREFIX and SUFFIX in context_before
            prefix_count = context_before.count(MARKER_PREFIX)
            suffix_count = context_before.count(MARKER_SUFFIX)

            # If more PREFIXes than SUFFIXes, we're inside a marker
            if prefix_count > suffix_count:
                # Inside a marker, skip
                return unix_path

            # Translate as relative to /home/claude/
            # /tmp/file.txt → /home/claude/tmp/file.txt
            relative_unix_path = f"{self.unix_home}{unix_path}"

            try:
                windows_path = self.to_windows(relative_unix_path)
                # Quote if contains spaces
                if ' ' in str(windows_path):
                    return f'"{windows_path}"'
                return str(windows_path)
            except Exception:
                # Keep original if translation fails
                return unix_path

        text = re.sub(pattern_relative, replace_relative_path, text)

        # FINAL: Replace all markers with actual translated paths
        for marker, path in translated_paths.items():
            text = text.replace(marker, path)

        return text
    
    def _translate_windows_paths_to_unix(self, text: str) -> str:
        """
        Find and translate Windows paths → Unix (only workspace paths)

        STRATEGY (TWO-PASS):
        1. First pass: Translate workspace paths to Unix paths
           - workspace_root/claude/... → /home/claude/...
           - workspace_root/uploads/... → /mnt/user-data/uploads/...
           - workspace_root/outputs/... → /mnt/user-data/outputs/...
        2. Second pass: Reverse relative path translation
           - /home/claude/tmp/... → /tmp/... (INVERSE of Unix→Windows)
           - /home/claude/var/... → /var/...
           - Maintains bidirectional symmetry

        EXAMPLES:
        - workspace_root/claude/tmp/file.txt → /home/claude/tmp/file.txt → /tmp/file.txt
        - workspace_root/uploads/data.csv → /mnt/user-data/uploads/data.csv (unchanged)
        """
        # PASS 1: Translate workspace paths to Unix paths
        # Pattern: workspace path (supports both Windows \ and Unix / separators)
        # Matches:
        #   - C:\workspace\claude\... (Windows)
        #   - /path/to/workspace/claude/... (Unix/Linux)
        workspace_str = str(self.workspace_root)

        # Escape special regex chars and create pattern for both separators
        # Replace both / and \ with [/\\] to match either
        workspace_pattern = re.escape(workspace_str).replace('\\\\', '[/\\\\]').replace('/', '[/\\\\]')

        # Match workspace_root/claude, workspace_root/uploads, workspace_root/outputs
        pattern = f'{workspace_pattern}[/\\\\](?:claude|uploads|outputs)(?:[/\\\\][\\w\\-\\.]+)*'

        def replace_path(match):
            windows_path_str = match.group(0)
            try:
                windows_path = Path(windows_path_str)
                unix_path = self.to_unix(windows_path)
                return unix_path
            except Exception:
                # Keep original if translation fails
                return windows_path_str

        text = re.sub(pattern, replace_path, text)

        # PASS 2: Reverse relative path translation
        # Convert /home/claude/DIRNAME to /DIRNAME for common relative paths
        # This is the INVERSE of the Unix→Windows translation
        # Common Unix directories that should be treated as absolute
        relative_dirs = [
            'tmp', 'var', 'etc', 'opt', 'usr', 'srv', 'run', 'sys', 'proc',
            'dev', 'bin', 'sbin', 'lib', 'lib64', 'boot', 'root'
        ]

        for dirname in relative_dirs:
            # Pattern: /home/claude/DIRNAME/... or /home/claude/DIRNAME (end)
            # Replace with: /DIRNAME/... or /DIRNAME
            pattern_relative = f'{self.unix_home}/{dirname}(/[\\w\\-\\.]+|(?=[\\s"\']|$))'
            replacement = f'/{dirname}\\1'
            text = re.sub(pattern_relative, replacement, text)

        return text


