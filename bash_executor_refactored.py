"""
REFACTORED ARCHITECTURE - Clean separation of concerns

ExecutionEngine: subprocess concentration
CommandExecutor: preprocessing + strategy + uses ExecutionEngine
BashToolExecutor: minimal tool interface, path translation only
"""

import os
import subprocess
import json
import re
import logging
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod
from unix_translator import PathTranslator, CommandTranslator


# ============================================================================
# EXECUTION ENGINE - Subprocess concentration point
# ============================================================================

class ExecutionEngine:
    """
    UNICO PUNTO di esecuzione subprocess.
    """

    def __init__(self, test_mode: bool = False, logger: logging.Logger = None):
        self.test_mode = test_mode
        self.logger = logger or logging.getLogger('ExecutionEngine')
        self.stats = {'cmd': 0, 'powershell': 0, 'bash': 0, 'native': 0, 'total': 0}

    def execute_cmd(self, command: str, **kwargs) -> subprocess.CompletedProcess:
        self.stats['cmd'] += 1
        self.stats['total'] += 1
        if self.test_mode:
            self.logger.info(f"[TEST-CMD] {command}")
            return subprocess.CompletedProcess(args=['cmd', '/c', command], returncode=0, stdout=f"[TEST] {command}", stderr="")
        return subprocess.run(['cmd', '/c', command], capture_output=True, text=True, **kwargs)

    def execute_powershell(self, command: str, **kwargs) -> subprocess.CompletedProcess:
        self.stats['powershell'] += 1
        self.stats['total'] += 1
        if self.test_mode:
            self.logger.info(f"[TEST-PowerShell] {command}")
            return subprocess.CompletedProcess(args=['powershell', '-Command', command], returncode=0, stdout=f"[TEST] {command}", stderr="")
        return subprocess.run(['powershell', '-Command', command], capture_output=True, text=True, **kwargs)

    def execute_bash(self, bash_path: str, command: str, **kwargs) -> subprocess.CompletedProcess:
        self.stats['bash'] += 1
        self.stats['total'] += 1
        if self.test_mode:
            self.logger.info(f"[TEST-Bash] {command}")
            return subprocess.CompletedProcess(args=[bash_path, '-c', command], returncode=0, stdout=f"[TEST] {command}", stderr="")
        return subprocess.run([bash_path, '-c', command], capture_output=True, text=True, **kwargs)

    def execute_native(self, bin_path: str, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        self.stats['native'] += 1
        self.stats['total'] += 1
        if self.test_mode:
            self.logger.info(f"[TEST-Native] {bin_path} {' '.join(args)}")
            return subprocess.CompletedProcess(args=[bin_path] + args, returncode=0, stdout=f"[TEST] {bin_path}", stderr="")
        return subprocess.run([bin_path] + args, capture_output=True, text=True, **kwargs)


# ============================================================================
# COMMAND EXECUTOR - Preprocessing + Strategy + Execution
# ============================================================================

class CommandExecutor:
    """
    Command execution with preprocessing, strategy selection, and execution.
    
    RESPONSIBILITIES:
    - Bash preprocessing (braces, variables, heredocs, substitution)
    - Conversion (bash to powershell, control structures)
    - Strategy selection (bash.exe, powershell, cmd, native)
    - Uses ExecutionEngine for actual execution
    - Uses CommandTranslator for command translation
    """
    
    def __init__(self, test_mode: bool = False, git_bash_path: str = None):
        self.executor = ExecutionEngine(test_mode=test_mode)
        self.translator = CommandTranslator()
        self.git_bash_path = git_bash_path
        self.logger = logging.getLogger('CommandExecutor')
        self.env = os.environ.copy()
        self.temp_files = []
        
        # Detect git bash if not provided
        if not self.git_bash_path:
            self.git_bash_path = self._detect_git_bash()
        
        # Detect python
        self.python_exe = self._detect_system_python()
    
    
    def _detect_git_bash(self) -> Optional[str]:
        """Detect Git Bash installation"""
        possible_paths = [
            r'C:\Program Files\Git\bin\bash.exe',
            r'C:\Program Files (x86)\Git\bin\bash.exe',
            r'C:\Git\bin\bash.exe',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"Found Git Bash: {path}")
                return path
        
        # Try via PATH
        try:
            result = subprocess.run(['where', 'bash'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                self.logger.info(f"Found Git Bash in PATH: {path}")
                return path
        except:
            pass
        
        self.logger.warning("Git Bash not found")
        return None
    
    def _detect_system_python(self) -> Optional[str]:
        """Detect system Python installation"""
        try:
            result = subprocess.run(['where', 'python'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                self.logger.info(f"Found Python: {path}")
                return path
        except:
            pass
        
        self.logger.warning("Python not found")
        return None

    def _expand_braces(self, command: str) -> str:
        """
        Expand brace patterns: {1..10}, {a..z}, {a,b,c}
        
        Supports:
        - Numeric ranges: {1..10}, {01..100}
        - Alpha ranges: {a..z}, {A..Z}
        - Lists: {file1,file2,file3}
        - Nested: {a,b{1,2}}
        
        Returns command with braces expanded
        """
        import re
        
        def expand_single_brace(match):
            """Expand a single brace expression"""
            content = match.group(1)
            
            # Check for range pattern (numeric or alpha)
            range_match = re.match(r'^(\d+)\.\.(\d+)$', content)
            if range_match:
                # Numeric range
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                padding = len(range_match.group(1)) if range_match.group(1).startswith('0') else 0
                
                if start <= end:
                    items = [str(i).zfill(padding) if padding else str(i) for i in range(start, end + 1)]
                else:
                    items = [str(i).zfill(padding) if padding else str(i) for i in range(start, end - 1, -1)]
                
                return ' '.join(items)
            
            # Alpha range
            alpha_match = re.match(r'^([a-zA-Z])\.\.([a-zA-Z])$', content)
            if alpha_match:
                start_char = alpha_match.group(1)
                end_char = alpha_match.group(2)
                
                if start_char <= end_char:
                    items = [chr(c) for c in range(ord(start_char), ord(end_char) + 1)]
                else:
                    items = [chr(c) for c in range(ord(start_char), ord(end_char) - 1, -1)]
                
                return ' '.join(items)
            
            # Comma-separated list
            if ',' in content:
                items = [item.strip() for item in content.split(',')]
                return ' '.join(items)
            
            # No expansion needed
            return match.group(0)
        
        # Expand braces - may need multiple passes for nested
        max_iterations = 10
        for _ in range(max_iterations):
            # Pattern: {content} but NOT ${var...}
            # Match innermost braces first (non-greedy)
            # FIX #7: Use negative lookbehind to exclude ${var...} parameter expansion
            pattern = r'(?<!\$)\{([^{}]+)\}'
            new_command = re.sub(pattern, expand_single_brace, command)
            
            if new_command == command:
                # No more expansions
                break
            command = new_command
        
        return command
    
    def _process_heredocs(self, command: str) -> Tuple[str, List[Path]]:
        """
        Process here documents.
        
        Supports:
    def _process_heredocs(self, command: str) -> Tuple[str, List[Path]]:
        """
        Process here documents.
        
        Supports:
        - <<DELIMITER     (standard heredoc)
        - <<-DELIMITER    (ignore leading tabs)
        - <<"DELIMITER"   (quoted delimiter - no expansion)
        - <<'DELIMITER'   (quoted delimiter - no expansion)
        - Multiple heredocs in same command
        
        Creates temp file with heredoc content, replaces in command.
        
        Returns:
            (modified_command, list_of_temp_files)
        """
        
        temp_files = []
        
        if '<<' not in command:
            return command, temp_files
        
        # Pattern to find heredoc operators
        # Matches: <<WORD, <<-WORD, <<"WORD", <<'WORD'
        heredoc_pattern = r'<<(-?)\s*([\'"]?)(\w+)\2'
        
        # Find all heredocs
        matches = list(re.finditer(heredoc_pattern, command))
        if not matches:
            return command, temp_files
        
        # Process heredocs from END to START
        # This way, earlier positions don't shift when we replace later ones
        result_command = command
        
        for match in reversed(matches):
            strip_tabs = match.group(1) == '-'
            quote_char = match.group(2)  # Captures ' or " if delimiter was quoted
            delimiter = match.group(3)
            heredoc_start = match.end()

            # Find content after heredoc operator
            remaining = result_command[heredoc_start:]

            # Split into lines
            lines = remaining.split('\n')

            # Find delimiter closing line
            content_lines = []
            delimiter_found = False
            delimiter_line_index = -1

            # Start from line 1 (line 0 is usually empty after <<EOF)
            for i in range(1, len(lines)):
                if lines[i].rstrip() == delimiter:
                    delimiter_found = True
                    delimiter_line_index = i
                    break
                content_lines.append(lines[i])

            if not delimiter_found:
                self.logger.warning(f"Heredoc delimiter '{delimiter}' not found")
                # Use all remaining lines as content
                content_lines = lines[1:] if len(lines) > 1 else []
                delimiter_line_index = len(lines) - 1

            # Build content
            content = '\n'.join(content_lines)

            # Strip leading tabs if <<- was used
            if strip_tabs:
                content = '\n'.join(line.lstrip('\t') for line in content_lines)

            # ================================================================
            # ARTIGIANO: Heredoc Variable Expansion
            # ================================================================
            # CRITICAL: In bash, heredocs expand variables and commands UNLESS
            # the delimiter is quoted (<<"EOF" or <<'EOF')
            #
            # <<EOF          -> Expand $VAR, $(cmd), `cmd`, $((expr))
            # <<"EOF"        -> NO expansion (literal)
            # <<'EOF'        -> NO expansion (literal)
            #
            # BEHAVIOR:
            # - Unquoted delimiter -> Use bash.exe to expand content
            # - Quoted delimiter -> Write content literally
            # - No bash.exe -> Write literally + warning
            #
            # This ensures heredoc-generated configs/scripts have correct values.

            should_expand = (quote_char == '')  # Empty = unquoted delimiter

            if should_expand:
                # Attempt variable expansion via bash.exe
                if self.git_bash_exe:
                    try:
                        # Use bash to expand the content
                        # We pass content via echo to let bash do expansion
                        # Use printf for better control over newlines and special chars

                        # Escape content for bash heredoc (preserve literal backslashes)
                        # We'll use bash itself to expand, via a heredoc to bash
                        expansion_script = f'''cat <<'EXPAND_DELIMITER'
{content}
EXPAND_DELIMITER'''
    def _expand_variables(self, command: str) -> str:
        """
        Expand variable patterns:
        - ${var:-default}, ${var:=value}
        - Tilde expansion: ~/path
        - Arithmetic: $((expr))
        - Array operations: ${arr[@]}
        """
        import re

        # NOTE: claude_home_unix is passed via __init__, no PathTranslator needed
        claude_home = self.claude_home_unix

        # 1. Tilde expansion: ~/path -> /home/claude/path
        if command.startswith('~/'):
            command = claude_home + '/' + command[2:]

        # Also expand tilde in arguments: cmd ~/path
        command = re.sub(r'\s~/', f' {claude_home}/', command)
        
        # 2. Arithmetic expansion: $((expr))
        arith_pattern = r'\$\(\(([^)]+)\)\)'
        
        def expand_arithmetic(match):
            expr = match.group(1)
            try:
                # Evaluate arithmetic expression
                # Simple eval - may need more robust parsing
                result = eval(expr, {"__builtins__": {}}, {})
                return str(result)
            except Exception as e:
                self.logger.warning(f"Arithmetic expansion failed for $(('{expr}')): {e}")
                return match.group(0)
        
        command = re.sub(arith_pattern, expand_arithmetic, command)
        
        # 3. Variable default: ${var:-default}
        default_pattern = r'\$\{(\w+):-([^}]+)\}'
        
        def expand_default(match):
            var_name = match.group(1)
            default_value = match.group(2)
            value = os.environ.get(var_name)
            return value if value else default_value
        
        command = re.sub(default_pattern, expand_default, command)
        
        # 4. Variable assign: ${var:=value}
        assign_pattern = r'\$\{(\w+):=([^}]+)\}'
        
        def expand_assign(match):
            var_name = match.group(1)
            default_value = match.group(2)
            value = os.environ.get(var_name)
            return value if value else default_value
        
        command = re.sub(assign_pattern, expand_assign, command)
        
        # 5. Array expansion: ${arr[@]} -> just remove braces for now
        # Full array support would require state tracking
        array_pattern = r'\$\{(\w+)\[@\]\}'
        command = re.sub(array_pattern, r'$\1', command)

        # ================================================================
        # FIX #7: Advanced Parameter Expansion
        # ================================================================
        # ${var#pattern}  - remove shortest prefix
        # ${var##pattern} - remove longest prefix
        # ${var%pattern}  - remove shortest suffix
        # ${var%%pattern} - remove longest suffix
        # ${var/pattern/string}  - replace first
        # ${var//pattern/string} - replace all
        # ${var^^} - uppercase all
        # ${var,,} - lowercase all
        # ${var^}  - uppercase first
        # ${#var}  - string length

        # 5a. String length: ${#var}
        length_pattern = r'\$\{#(\w+)\}'

        def expand_length(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            return str(len(value))

        command = re.sub(length_pattern, expand_length, command)

        # 5b. Remove prefix: ${var#pattern} and ${var##pattern}
        # Pattern: ${var#pattern} or ${var##pattern}
        prefix_pattern = r'\$\{(\w+)(#{1,2})([^}]+)\}'

        def expand_remove_prefix(match):
            var_name = match.group(1)
            op = match.group(2)  # # or ##
            pattern = match.group(3)
            value = os.environ.get(var_name, '')

            if not value:
                return ''

            # Convert bash glob to regex
            import fnmatch
            regex_pattern = fnmatch.translate(pattern)

            # Convert bash glob to regex and match from start
            regex_pattern = '^' + regex_pattern.rstrip('\\Z')

            if op == '#':  # Remove shortest prefix (non-greedy)
                # Make pattern non-greedy by adding '?' after '*'
                regex_pattern_ng = regex_pattern.replace('*', '*?')
                match_obj = re.match(regex_pattern_ng, value)
                if match_obj:
                    return value[len(match_obj.group(0)):]
            else:  # ## Remove longest prefix (greedy - default)
                # fnmatch patterns are already greedy by default
                match_obj = re.match(regex_pattern, value)
                if match_obj:
                    return value[len(match_obj.group(0)):]

            return value

        command = re.sub(prefix_pattern, expand_remove_prefix, command)

        # 5c. Remove suffix: ${var%pattern} and ${var%%pattern}
        suffix_pattern = r'\$\{(\w+)(%{1,2})([^}]+)\}'

        def expand_remove_suffix(match):
            var_name = match.group(1)
            op = match.group(2)  # % or %%
            pattern = match.group(3)
            value = os.environ.get(var_name, '')

            if not value:
                return ''

            # Convert bash glob to regex and match from end
            import fnmatch
            regex_pattern = fnmatch.translate(pattern)
            regex_pattern = regex_pattern.rstrip('\\Z') + '$'

            if op == '%':  # Remove shortest suffix (non-greedy)
                # Iterate from right to left to find rightmost (shortest) match
                for i in range(len(value), -1, -1):
                    match_obj = re.search(regex_pattern, value[i:])
                    if match_obj and match_obj.start() == 0:  # Must match from start of substring
                        # Found shortest suffix at position i
                        return value[:i]
            else:  # %% Remove longest suffix (greedy)
                # Iterate from left to right to find leftmost (longest) match
                for i in range(len(value) + 1):
                    match_obj = re.search(regex_pattern, value[i:])
                    if match_obj and match_obj.start() == 0:  # Must match from start of substring
                        # Found longest suffix at position i
                        return value[:i]

            return value

        command = re.sub(suffix_pattern, expand_remove_suffix, command)

        # 5d. String substitution: ${var/pattern/string} and ${var//pattern/string}
        subst_pattern = r'\$\{(\w+)(/{1,2})([^/}]+)/([^}]*)\}'

        def expand_substitution(match):
            var_name = match.group(1)
            op = match.group(2)  # / or //
            pattern = match.group(3)
            replacement = match.group(4)
            value = os.environ.get(var_name, '')

            if not value:
                return ''

            # Convert bash glob to regex
            import fnmatch
            regex_pattern = fnmatch.translate(pattern).rstrip('\\Z')

            if op == '/':  # Replace first
                return re.sub(regex_pattern, replacement, value, count=1)
            else:  # // Replace all
                return re.sub(regex_pattern, replacement, value)

        command = re.sub(subst_pattern, expand_substitution, command)

        # 5e. Case conversion: ${var^^}, ${var,,}, ${var^}
        case_pattern = r'\$\{(\w+)(\^{1,2}|,{1,2})\}'

        def expand_case(match):
            var_name = match.group(1)
            op = match.group(2)
            value = os.environ.get(var_name, '')

            if op == '^^':  # Uppercase all
                return value.upper()
            elif op == ',,':  # Lowercase all
                return value.lower()
            elif op == '^':  # Uppercase first
                return value[0].upper() + value[1:] if value else ''
            elif op == ',':  # Lowercase first
                return value[0].lower() + value[1:] if value else ''

            return value

        command = re.sub(case_pattern, expand_case, command)

        # ================================================================
        # ARTIGIANO: Simple Variable Expansion
        # ================================================================
        # CRITICAL: Must expand basic $VAR and ${VAR} forms!
        # Previous code only handled ${VAR:-default}, missing simple expansion.
        #
        # This BROKE commands like:
        #   cd $HOME        -> cd $HOME (literal! Wrong!)
        #   echo $PATH      -> echo $PATH (literal!)
        #   cp file $USER/  -> cp file $USER/ (fails!)
        #
        # 6. Simple ${VAR} expansion
        simple_brace_pattern = r'\$\{(\w+)\}'

        def expand_simple_brace(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            if not value:
                self.logger.debug(f"Variable ${{{var_name}}} not found in environment, expanding to empty string")
            return value

        command = re.sub(simple_brace_pattern, expand_simple_brace, command)

        # 7. Simple $VAR expansion (without braces)
        # Must be AFTER ${VAR} to avoid double-expansion
        # Match $VAR but NOT $((, ${, $@, $*, $#, $?, $$, $!, $0-9
    def _process_substitution(self, command: str) -> Tuple[str, List[Path]]:
        """
        Process substitution: <(command), >(command)
        
        Executes command, saves output to temp file, replaces pattern with temp path.
        
        Returns:
            (modified_command, list_of_temp_files)
        """
        import re
        
        temp_files = []
        
        # Pattern: <(command) or >(command)
        # Find all occurrences
        input_pattern = r'<\(([^)]+)\)'
        output_pattern = r'>\(([^)]+)\)'
        
        cwd = self.scratch_dir
        env = self._setup_environment()
        
        def replace_input_substitution(match):
            """Replace <(cmd) with temp file containing cmd output"""
            cmd = match.group(1)

            # Translate and execute command
            try:
                # NOTE: Paths already translated by BashToolExecutor.execute()
                # No need to translate again here

                # Translate command
                translated, _, _ = self.command_translator.translate(cmd)
                
                # Execute
                result = subprocess.run(
                    ['cmd', '/c', translated],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(cwd),
                    env=env,
                    errors='replace'
                )
                
                # Create temp file with output
                temp_file = cwd / f'procsub_input_{threading.get_ident()}_{len(temp_files)}.tmp'
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                temp_files.append(temp_file)
                
                # Return Unix path for substitution
                unix_temp = f"/tmp/{temp_file.name}"
                return unix_temp
            
            except Exception as e:
                self.logger.error(f"Process substitution failed for <({cmd}): {e}")
                # Return original if failed
                return match.group(0)
        
        def replace_output_substitution(match):
            """
            Replace >(cmd) with temp file that will receive output.
            
            FULL IMPLEMENTATION: 
            1. Create temp file
            2. Store command to execute AFTER main command
            3. Return temp file path for main command
            """
            cmd = match.group(1)
            
            # Create temp file for output
            temp_file = cwd / f'procsub_output_{threading.get_ident()}_{len(temp_files)}.tmp'
            temp_files.append(temp_file)
            
            # Store the command and temp file for post-processing
            # This will be executed AFTER the main command completes
            # Format: (temp_file_path, command_to_execute)
            if not hasattr(temp_files, 'post_commands'):
                temp_files.post_commands = []
            
            temp_files.post_commands.append((temp_file, cmd))
            
            # Return Unix path for substitution in main command
            unix_temp = f"/tmp/{temp_file.name}"
            return unix_temp
        
        # Replace all input substitutions
        matches = list(re.finditer(input_pattern, command))
        command = re.sub(input_pattern, replace_input_substitution, command)

        # Replace all output substitutions
        command = re.sub(output_pattern, replace_output_substitution, command)

        return command, temp_files
    
    def _process_command_substitution_recursive(self, command: str) -> str:
        """
        Process command substitution $(...) with RECURSIVE translation.
    def _process_command_substitution_recursive(self, command: str) -> str:
        """
        Process command substitution $(...) with RECURSIVE translation.

        ARTISAN IMPLEMENTATION:
        - Parses nested $(...)
        - Recursively translates Unix commands inside substitution
        - Preserves PowerShell $(...) syntax for output
        - Handles multiple substitutions in single command

        Examples:
            $(grep pattern file.txt)
            -> $(Select-String -Pattern "pattern" -Path "file.txt")

            $(cat file | wc -l)
            -> $(Get-Content file | Measure-Object -Line)

            Nested: $(echo $(cat file))
            -> $(Write-Host $(Get-Content file))

        Returns:
            Command with all $(..  .) recursively translated
        """
        if '$(' not in command:
            return command
        
        def find_substitutions(text: str) -> List[Tuple[int, int, str]]:
            """
            Find all $(...) patterns with correct nesting.
            
            Returns:
                List of (start_pos, end_pos, content) tuples
            """
            substitutions = []
            i = 0
            
            while i < len(text):
                if i < len(text) - 1 and text[i:i+2] == '$(':
                    # FIX #6: Check if it's arithmetic $(( instead of command substitution $(
                    if i < len(text) - 2 and text[i+2] == '(':
                        # This is $((arithmetic)), NOT command substitution
                        # Skip it - already handled by _expand_variables()
                        i += 3
                        continue

                    # Found start of command substitution $(...)
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
                        # Found complete substitution
                        end = i
                        content = text[start+2:end-1]
                        substitutions.append((start, end, content))
                    else:
                        # Unmatched parens - log warning
                        self.logger.warning(f"Unmatched $( at position {start}")
                else:
                    i += 1
            
            return substitutions
        
        # Find all top-level substitutions (not nested)
        substitutions = find_substitutions(command)

        if not substitutions:
            return command

        for start, end, content in substitutions:
            print(f"  - Position {start}-{end}: '{content}'")
        
        # Process substitutions from END to START (avoid index shifting)
        substitutions_reversed = sorted(substitutions, key=lambda x: x[0], reverse=True)
        
        for start, end, content in substitutions_reversed:
            # Translate the content
            try:
                # RECURSIVE: content might have nested $(...)
                translated_content = self._translate_substitution_content(content)

                # Replace in command (preserve $(...) wrapper for PowerShell)
                replacement = f"$({translated_content})"
                command = command[:start] + replacement + command[end:]
                
            except Exception as e:
                self.logger.error(f"Command substitution translation failed: {e}")
                # Keep original on error
                continue
        
        return command
    
    def _translate_substitution_content(self, content: str) -> str:
        """
        Translate Unix command content inside $(...) - ARTIGIANO STRATEGY.

        CRITICAL: Commands inside $(...) must be EXECUTED to capture output.
        Cannot just "pass to bash.exe" - must run and get result.

        ARTIGIANO STRATEGY:
        1. Detect if command is COMPLEX (would fail in PowerShell emulation)
        2. Complex -> execute with bash.exe, capture output, return as string
        3. Simple -> translate to PowerShell, execute in $(...) context

        COMPLEXITY TRIGGERS:
        - Pipeline with critical commands (find, xargs, awk, sed)
        - Command chains (&&, ||)
    def _has_control_structures(self, command: str) -> bool:
        """Check if command contains bash control structures"""
        keywords = ['for ', 'while ', 'if ', 'case ', 'function ', 'until ']
        return any(kw in command for kw in keywords)
    
    def _convert_control_structures_to_script(self, command: str) -> Tuple[str, Optional[Path]]:
        """
        Convert bash control structures to PowerShell script.
        
        For complex structures (for, while, if), create temp PowerShell script.
    def _bash_to_powershell(self, bash_script: str) -> str:
        """
        Convert bash control structures to PowerShell.
        
        Handles:
        - for loops
        - while loops
        - if statements
        - test conditions conversion
        - variable references
        """
        import re
        
        # For loop: for i in {1..10}; do echo $i; done
        for_pattern = r'for\s+(\w+)\s+in\s+([^;]+);\s*do\s+(.+?);\s*done'
        
        def convert_for(match):
            var = match.group(1)
            range_expr = match.group(2).strip()
            body = match.group(3).strip()
            
            # Convert bash $var to PowerShell $var (already compatible)
            # Convert echo to Write-Host
            body = body.replace('echo ', 'Write-Host ')
            
            # Parse range
            if '..' in range_expr:
                # Range like 1..10
                ps = f'foreach (${var} in {range_expr}) {{\n'
                ps += f'    {body}\n'
                ps += '}\n'
            else:
                # List like "a b c"
                items = range_expr.split()
                items_str = ','.join([f'"{item}"' for item in items])
                ps = f'foreach (${var} in {items_str}) {{\n'
                ps += f'    {body}\n'
                ps += '}\n'
            
            return ps
        
        # Check for for loop
        if 'for ' in bash_script and ' in ' in bash_script and '; do ' in bash_script:
            bash_script = re.sub(for_pattern, convert_for, bash_script, flags=re.DOTALL)
        
        # While loop: while condition; do ...; done
        while_pattern = r'while\s+(.+?);\s*do\s+(.+?);\s*done'
        
        def convert_while(match):
            condition = match.group(1).strip()
            body = match.group(2).strip()
            
            # Convert test conditions to PowerShell
            condition = self._convert_test_to_powershell(condition)
            
            # Convert body commands
            body = body.replace('echo ', 'Write-Host ')
            
            ps = f'while ({condition}) {{\n'
            ps += f'    {body}\n'
            ps += '}\n'
            
            return ps
        
        if 'while ' in bash_script:
            bash_script = re.sub(while_pattern, convert_while, bash_script, flags=re.DOTALL)
        
        # If statement: if condition; then ...; fi
        if_pattern = r'if\s+(.+?);\s*then\s+(.+?);\s*fi'
        
        def convert_if(match):
            condition = match.group(1).strip()
            body = match.group(2).strip()
            
            # Convert test conditions to PowerShell
            condition = self._convert_test_to_powershell(condition)
            
            # Convert body commands
            body = body.replace('echo ', 'Write-Host ')
            
            ps = f'if ({condition}) {{\n'
            ps += f'    {body}\n'
            ps += '}\n'
            
            return ps
        
        if 'if ' in bash_script and ' then ' in bash_script:
            bash_script = re.sub(if_pattern, convert_if, bash_script, flags=re.DOTALL)
        
        # Convert common bash commands to PowerShell equivalents
        conversions = {
            'echo ': 'Write-Host ',
            'cat ': 'Get-Content ',
            'ls ': 'Get-ChildItem ',
            'rm ': 'Remove-Item ',
            'cp ': 'Copy-Item ',
            'mv ': 'Move-Item ',
            'mkdir ': 'New-Item -ItemType Directory -Path ',
        }
        
        for bash_cmd, ps_cmd in conversions.items():
            bash_script = bash_script.replace(bash_cmd, ps_cmd)
        
        return bash_script
    
    def _convert_test_to_powershell(self, test_expr: str) -> str:
        """
        Convert bash test conditions to PowerShell.
        
        Examples:
    def _needs_powershell(self, command: str) -> bool:
        """
        Detect if command needs PowerShell instead of cmd.exe.

        PowerShell required for:
        - Command substitution: $(...)
        - Backticks: `...`
        - Process substitution: <(...)
        - Complex variable expansion
        - PowerShell cmdlets (Get-ChildItem, ForEach-Object, etc.)

        Returns:
            True if PowerShell required, False if cmd.exe sufficient
        """
        # PowerShell cmdlets
        powershell_cmdlets = [
            'Get-ChildItem', 'ForEach-Object', 'Select-Object', 'Where-Object',
            'Measure-Object', 'Select-String', 'Get-Content', 'Set-Content',
            'Out-File', 'Write-Output', 'Write-Host', 'Write-Error',
            '$input', '$_'  # PowerShell variables
        ]

        for cmdlet in powershell_cmdlets:
            if cmdlet in command:
                return True

        # Command substitution patterns
        if '$(' in command:
            return True

        # Backtick command substitution
        if '`' in command:
            # Check it's not just in a string
            # Simple heuristic: backticks outside of quotes
            in_quotes = False
            quote_char = None
            for i, char in enumerate(command):
                if char in ('"', "'") and (i == 0 or command[i-1] != '\\'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                elif char == '`' and not in_quotes:
                    return True

        # Process substitution
        if '<(' in command or '>(' in command:
            return True

        return False
    
    def _adapt_for_powershell(self, command: str) -> str:
        """
        Adapt Unix command for PowerShell execution.
        
        Translations:
        - Backticks `cmd` -> $(...) PowerShell syntax
        - Preserve pipes, redirects, logical operators
    
    def execute_bash(self, command: str) -> str:
        """
        Execute bash command with preprocessing and strategy selection.
        
        Main entry point that:
        1. Preprocesses bash syntax
        2. Translates to Windows
        3. Selects execution strategy
        4. Uses ExecutionEngine to execute
        """
        # 1. Preprocessing
        command = self._expand_braces(command)
        command, heredoc_files = self._process_heredocs(command)
        command = self._process_substitution(command)
        command = self._expand_variables(command)
        
        # 2. Translation
        translated, use_shell = self.translator.translate(command)
        
        # 3. Execution via ExecutionEngine
        if self.git_bash_path and self._should_use_bash(command):
            result = self.executor.execute_bash(self.git_bash_path, command)
        elif self._needs_powershell(translated):
            result = self.executor.execute_powershell(translated)
        else:
            result = self.executor.execute_cmd(translated)
        
        # 4. Cleanup
        for f in heredoc_files:
            try:
                f.unlink()
            except:
                pass
        
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    
    def _should_use_bash(self, command: str) -> bool:
        """Decide if command should use bash.exe"""
        # Complex commands need bash
        if '|' in command or '&&' in command or '<(' in command:
            return True
        # Pattern matching commands
        if any(cmd in command for cmd in ['find', 'awk', 'sed', 'grep', 'xargs']):
            return True
        return False


# ============================================================================
# BASH TOOL EXECUTOR - Minimal tool interface
# ============================================================================

class BashToolExecutor:
    """
    Minimal tool executor - ONLY path translation and delegation.
    
    ARCHITECTURE:
    Like WebToolExecutor uses Browser, BashToolExecutor uses CommandExecutor.
    
    RESPONSIBILITIES:
    1. Path translation IN (command line)
    2. Delegation to CommandExecutor
    3. Path translation OUT (result)
    4. Tool definition
    
    NOT responsible for:
    - Preprocessing (CommandExecutor)
    - Conversion (CommandExecutor)
    - Execution (ExecutionEngine via CommandExecutor)
    - Subprocess calls (ZERO subprocess here!)
    """
    
    def __init__(self, working_dir: str, test_mode: bool = False):
        self.working_dir = Path(working_dir)
        self.path_translator = PathTranslator()
        self.command_executor = CommandExecutor(test_mode=test_mode)
        self.logger = logging.getLogger('BashToolExecutor')
    
    def execute(self, params: Dict[str, Any]) -> str:
        """
        Execute bash command (MINIMAL - only path translation + delegation)
        """
        command = params.get('command', '')
        
        if not command:
            return "Error: No command provided"
        
        # 1. Path translation IN
        command_with_windows_paths = self.path_translator.translate_paths_in_string(
            command, direction='to_windows'
        )
        
        # 2. Delegation to CommandExecutor
        result = self.command_executor.execute_bash(command_with_windows_paths)
        
        # 3. Path translation OUT
        result_with_unix_paths = self.path_translator.translate_paths_in_string(
            result, direction='to_unix'
        )
        
        return result_with_unix_paths
    
    def get_definition(self) -> Dict:
        """Tool definition for API"""
        return {
            'type': 'bash_20241022',
            'name': 'bash',
            'display_name': 'Bash Tool',
            'description': 'Execute bash commands'
        }

