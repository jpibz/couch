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
        """Find and translate Unix absolute paths → Windows"""
        # Pattern: Unix absolute path for home/uploads/outputs
        # Matches: /home/claude/..., /mnt/user-data/uploads/..., /mnt/user-data/outputs/...
        pattern = r'(/(?:home/claude|mnt/user-data/(?:uploads|outputs))(?:/[\w\-\.]+)*)'
        
        def replace_path(match):
            unix_path = match.group(1)
            try:
                windows_path = self.to_windows(unix_path)
                # Quote if contains spaces
                if ' ' in str(windows_path):
                    return f'"{windows_path}"'
                return str(windows_path)
            except Exception:
                # Keep original if translation fails
                return unix_path
        
        return re.sub(pattern, replace_path, text)
    
    def _translate_windows_paths_to_unix(self, text: str) -> str:
        """Find and translate Windows paths → Unix (only workspace paths)"""
        workspace_str = str(self.workspace_root).replace('\\', '\\\\')
        
        # Pattern: Windows absolute path within workspace claude/uploads/outputs
        # Matches: C:\workspace\claude\..., C:\workspace\uploads\..., C:\workspace\outputs\...
        pattern = f'{workspace_str}\\\\(?:claude|uploads|outputs)(?:[\\\\\\w\\-\\.]+)*'
        
        def replace_path(match):
            windows_path_str = match.group(0)
            try:
                windows_path = Path(windows_path_str)
                unix_path = self.to_unix(windows_path)
                return unix_path
            except Exception:
                # Keep original if translation fails
                return windows_path_str
        
        return re.sub(pattern, replace_path, text)


