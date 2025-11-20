"""
BashPipelinePreprocessor - PIPELINE LEVEL preprocessing

RESPONSIBILITIES:
- Process command substitution $(...)
- Process process substitution <(...), >(...)
- Process heredocs <<EOF

INPUT: Pure AST from parser
OUTPUT: Modified AST with preprocessing done + temp files created

SIDE EFFECTS: 
- Executes commands (for command substitution)
- Creates temp files (for process substitution, heredocs)

NOT RESPONSIBLE FOR:
- Comando level preprocessing (variables, braces, etc) - that's BashCommandPreprocessor
- Parsing - that's BashPipelineParser
- Execution - that's ExecutionEngine
"""
import logging
import re
import threading
from pathlib import Path
from typing import Tuple, List, Any

# Will need to import AST node types from parser
from .bash_pipeline_parser import (
    SimpleCommand, Pipeline, AndList, OrList, Sequence,
    Subshell, CommandGroup, Background, ProcessSubstitution,
    Redirect
)


class BashPipelinePreprocessor:
    """
    Pipeline level preprocessor - handles command/process substitution and heredocs
    
    Works on AST level, executes commands, creates temp files.
    """
    
    def __init__(self, executor, logger=None, temp_dir=None):
        """
        Initialize preprocessor
        
        Args:
            executor: CommandExecutor instance (for recursive command execution)
            logger: Logger instance
            temp_dir: Directory for temp files (default: C:\\Temp or /tmp)
        """
        self.executor = executor
        self.logger = logger or logging.getLogger('BashPipelinePreprocessor')
        
        # Temp directory (Windows path!)
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            # Use C:\Temp on Windows, /tmp fallback
            self.temp_dir = Path('C:\\Temp') if Path('C:\\Temp').exists() else Path('/tmp')
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def preprocess(self, command: str, nesting_level: int = 0) -> Tuple[str, List[Path]]:
        """
        Preprocess command at PIPELINE level
        
        Handles:
        - Command substitution $(...)
        - Process substitution <(...), >(...)
        - Heredocs <<EOF
        
        Args:
            command: Bash command string (Windows paths!)
            nesting_level: Recursion depth (for temp file naming)
            
        Returns:
            (preprocessed_command, temp_files_created)
        """
        temp_files = []
        
        # 1. Process command substitution $(...)
        command = self._process_command_substitution(command, nesting_level, temp_files)
        
        # 2. Process heredocs <<EOF
        command, heredoc_files = self._process_heredocs(command, nesting_level)
        temp_files.extend(heredoc_files)
        
        # 3. Process substitution <(...), >(...)
        command, procsub_files = self._process_substitution(command, nesting_level)
        temp_files.extend(procsub_files)
        
        return command, temp_files
    
    # ========================================================================
    # COMMAND SUBSTITUTION $(...)
    # ========================================================================
    
    def _process_command_substitution(self, command: str, nesting_level: int, temp_files: list) -> str:
        """
        Process command substitution: $(cmd)
        
        Execute command recursively with our strategy, substitute output.
        
        FIXED: Properly substitutes ALL occurrences from end to start.
        """
        if '$(' not in command:
            return command
        
        # Find all $(...)
        substitutions = self._find_command_substitutions(command)
        
        if not substitutions:
            return command
        
        # Process from END to START (stable indices)
        for start, end, content in reversed(substitutions):
            try:
                # EXECUTE command recursively (with our strategy!)
                self.logger.debug(f"Executing command substitution: {content[:50]}...")
                result = self.executor.execute(content, nesting_level + 1)
                
                # Get output
                output = result.stdout.strip()
                
                # SUBSTITUTE in command
                command = command[:start] + output + command[end:]
                
                self.logger.debug(f"Command substitution result: {output[:50]}...")
            
            except Exception as e:
                self.logger.error(f"Command substitution failed: {e}")
                # Keep original on error
                continue
        
        return command
    
    def _find_command_substitutions(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Find all $(...) patterns with correct nesting
        
        Returns:
            List of (start_pos, end_pos, content)
        """
        substitutions = []
        i = 0
        
        while i < len(text):
            if i < len(text) - 1 and text[i:i+2] == '$(':
                # Check if arithmetic $((
                if i < len(text) - 2 and text[i+2] == '(':
                    # This is $((arithmetic)), skip
                    i += 3
                    continue
                
                # Found command substitution
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
                    end = i
                    content = text[start+2:end-1]
                    substitutions.append((start, end, content))
                else:
                    self.logger.warning(f"Unmatched $( at position {start}")
            else:
                i += 1
        
        return substitutions
    
    # ========================================================================
    # HEREDOCS <<EOF
    # ========================================================================
    
    def _process_heredocs(self, command: str, nesting_level: int) -> Tuple[str, List[Path]]:
        """
        Process heredocs: <<DELIMITER
        
        Creates temp file with content, replaces with < temp_file
        
        WINDOWS PATHS!
        """
        temp_files = []
        
        if '<<' not in command:
            return command, temp_files
        
        # Pattern: <<WORD, <<-WORD, <<"WORD", <<'WORD'
        heredoc_pattern = r'<<(-?)\s*([\'"]?)(\w+)\2'
        
        matches = list(re.finditer(heredoc_pattern, command))
        if not matches:
            return command, temp_files
        
        # Process from END to START
        result_command = command
        
        for match in reversed(matches):
            strip_tabs = match.group(1) == '-'
            quote_char = match.group(2)
            delimiter = match.group(3)
            heredoc_start = match.end()
            
            remaining = result_command[heredoc_start:]
            lines = remaining.split('\n')
            
            # Find delimiter line
            content_lines = []
            delimiter_found = False
            delimiter_line_index = -1
            
            for i in range(1, len(lines)):
                if lines[i].rstrip() == delimiter:
                    delimiter_found = True
                    delimiter_line_index = i
                    break
                content_lines.append(lines[i])
            
            if not delimiter_found:
                self.logger.warning(f"Heredoc delimiter '{delimiter}' not found")
                content_lines = lines[1:] if len(lines) > 1 else []
                delimiter_line_index = len(lines) - 1
            
            content = '\n'.join(content_lines)
            
            # Strip tabs if <<-
            if strip_tabs:
                content = '\n'.join(line.lstrip('\t') for line in content_lines)
            
            # Variable expansion in heredoc (if unquoted)
            # TODO: This could use BashCommandPreprocessor for variable expansion
            # For now, skip (bash will expand if we pass to bash)
            
            # Create temp file (WINDOWS PATH!)
            temp_file = self.temp_dir / f'heredoc_{nesting_level}_{threading.get_ident()}_{len(temp_files)}.tmp'
            
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                temp_files.append(temp_file)
                
                # Windows path string
                temp_path = str(temp_file)
                
                # Calculate replacement range
                heredoc_end = heredoc_start + len('\n'.join(lines[:delimiter_line_index + 1]))
                
                # Replace heredoc with < temp_file
                replacement = f"< {temp_path}"
                result_command = result_command[:match.start()] + replacement + result_command[heredoc_end:]
            
            except Exception as e:
                self.logger.error(f"Failed to create heredoc temp file: {e}")
                continue
        
        return result_command, temp_files
    
    # ========================================================================
    # PROCESS SUBSTITUTION <(...), >(...)
    # ========================================================================
    
    def _process_substitution(self, command: str, nesting_level: int) -> Tuple[str, List[Path]]:
        """
        Process substitution: <(cmd), >(cmd)
        
        Creates temp files, executes commands, replaces with temp paths.
        
        WINDOWS PATHS!
        """
        temp_files = []
        
        # Patterns
        input_pattern = r'<\(([^)]+)\)'
        output_pattern = r'>\(([^)]+)\)'
        
        def replace_input_substitution(match):
            """<(cmd) → temp file with cmd output"""
            cmd = match.group(1)
            
            try:
                # Execute command recursively
                self.logger.debug(f"Executing process substitution <({cmd[:30]}...)")
                result = self.executor.execute(cmd, nesting_level + 1)
                
                # Create temp file (WINDOWS PATH!)
                temp_file = self.temp_dir / f'procsub_in_{nesting_level}_{threading.get_ident()}_{len(temp_files)}.tmp'
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                temp_files.append(temp_file)
                
                # Return Windows path
                return str(temp_file)
            
            except Exception as e:
                self.logger.error(f"Process substitution <(...) failed: {e}")
                return match.group(0)
        
        def replace_output_substitution(match):
            """>(cmd) → temp file for output (post-process queue)"""
            cmd = match.group(1)
            
            # Create temp file (WINDOWS PATH!)
            temp_file = self.temp_dir / f'procsub_out_{nesting_level}_{threading.get_ident()}_{len(temp_files)}.tmp'
            temp_files.append(temp_file)
            
            # Store command for post-processing
            # TODO: Implement post-processing queue
            if not hasattr(temp_files, 'post_commands'):
                temp_files.post_commands = []
            
            temp_files.post_commands.append((temp_file, cmd))
            
            # Return Windows path
            return str(temp_file)
        
        # Replace all substitutions
        command = re.sub(input_pattern, replace_input_substitution, command)
        command = re.sub(output_pattern, replace_output_substitution, command)
        
        return command, temp_files
