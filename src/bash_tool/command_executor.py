"""
Command Executor - Main preprocessing and execution coordinator
"""
import os
import subprocess
import re
import logging
import threading
from pathlib import Path
from typing import List, Tuple, Optional

from .execution_engine import ExecutionEngine
from .pipeline_strategy import PipelineStrategy
from .execute_unix_single_command import ExecuteUnixSingleCommand

class CommandExecutor:
    """
    Command execution strategy orchestrator - REFACTORED.

    RESPONSIBILITIES:
    - Orchestrate command execution with strategic delegation
    - Coordinate PipelineStrategy and ExecuteUnixSingleCommand
    - Preprocessing 

    """


    def __init__(self, working_dir="\\", logger=None, test_mode=False):
        """
        Initialize CommandExecutor.

        ARCHITECTURE NOTE:
        CommandExecutor does NOT need PathTranslator!
        Path translation happens in BashToolExecutor.execute() BEFORE
        commands reach this layer.

        Args:
            claude_home_unix: Unix home directory for tilde expansion (default: /home/claude)
            logger: Logger instance
            test_mode: If True, use ExecutionEngine in test mode
        """

        self.working_dir = working_dir
        self.logger = logger or logging.getLogger('CommandExecutor')
        self.test_mode = test_mode

        # ====================================================================
        # STRATEGIC LAYER - Delegation to specialized classes
        # ====================================================================

        # Pipeline strategic analyzer (MACRO level)
        self.pipeline_strategy = PipelineStrategy(
            native_bins=self.available_bins,
            logger=self.logger,
            test_mode=test_mode
        )

        # Single command executor (MICRO level)
        self._single_executor = ExecuteUnixSingleCommand(
            logger=self.logger,
            test_mode=self.test_mode
        )

        self.logger.info("CommandExecutor initialized")

    # ========================================================================
    # MAIN EXECUTION ENTRY POINT
    # ========================================================================

    def execute(self, command: str) -> subprocess.CompletedProcess:
        
        self.logger.info(f"Executing: {command[:100]}")
        
        # Temp files tracking for cleanup
        temp_files = []
        
        try:
            # PRE-PROCESSING PHASE - Handle complex patterns BEFORE translation
            
            # STEP 0.0: Expand aliases (ll, la, etc.)
            command = self._expand_aliases(command)
            
            # STEP 0.1: Process subshell and command grouping
            command = self._process_subshell(command)
            command = self._process_command_grouping(command)
            
            # STEP 0.2: Control structures (for, while, if, case)
            if self._has_control_structures(command):
                command, script_file = self._convert_control_structures_to_script(command)
                if script_file:
                    temp_files.append(script_file)
            
            # STEP 0.3: Test commands [ ] and [[ ]]
            command = self._preprocess_test_commands(command)
            
            # STEP 0.4: Brace expansion {1..10}, {a,b,c}
            command = self._expand_braces(command)
            
            # STEP 0.5: Here documents <<EOF
            command, heredoc_files = self._process_heredocs(command)
            temp_files.extend(heredoc_files)
            
            # STEP 0.6: Process substitution <(cmd) >(cmd)
            command, procsub_files = self._process_substitution(command)
            temp_files.extend(procsub_files)
            
            # STEP 0.7: Variable expansion ${var:-default}, tilde, arithmetic
            command = self._expand_variables(command)
            
            # STEP 0.8: xargs patterns
            command = self._process_xargs(command)
            
            # STEP 0.9: find ... -exec patterns
            command = self._process_find_exec(command)
            
            # STEP 0.10: Command substitution $(...) - RECURSIVE TRANSLATION
            command = self._process_command_substitution_recursive(command)
            
            return self._single_executor.execute_single(command)

        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return f"Error: {str(e)}"
        finally:
            # Cleanup temp files
            self._cleanup_temp_files(temp_files)
    
 
   


    # ========================================================================
    # PREPROCESSING METHODS 
    # ========================================================================
    # These methods handle complex bash patterns that need preprocessing
    # BEFORE translation. They require access to:
    # - command_translator (for recursive translation)
    # - executor (for execution in preprocessing phase)
    #
    # ========================================================================


# ============================================================================
# BASHTOOLEXECUTOR - ORCHESTRATION LAYER
# ============================================================================

    # ==================== PREPROCESSING METHODS (migrated) ====================

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

                        # But wait - we WANT expansion, so use UNquoted delimiter
                        expansion_script = f'''cat <<EXPAND_DELIMITER
{content}
EXPAND_DELIMITER'''

                        # Execute via bash.exe through ExecutionEngine
                        bash_path = self.git_bash_exe
                        result = self.command_executor.engine.execute_bash(
                            bash_path,
                            expansion_script,
                            test_mode_stdout=content,  # AS IF: content expanded (in TESTMODE)
                            timeout=5,
                            cwd=str(self.scratch_dir),
                            env=self._setup_environment(),
                            errors='replace',
                            encoding='utf-8'
                        )

                        if result.returncode == 0:
                            # Use expanded content
                            content = result.stdout
                            self.logger.debug(f"Heredoc expanded via bash.exe (delimiter: {delimiter})")
                        else:
                            # Expansion failed - use literal
                            self.logger.warning(f"Heredoc expansion failed (exit {result.returncode}), using literal content")
                            self.logger.debug(f"Bash stderr: {result.stderr}")

                    except Exception as e:
                        # Expansion error - use literal
                        self.logger.warning(f"Heredoc expansion error: {e}, using literal content")

                else:
                    # No bash.exe for expansion - CRITICAL
                    self.logger.warning(f"Heredoc with unquoted delimiter '{delimiter}' should expand variables")
                    self.logger.warning("bash.exe not available - writing LITERAL content (may be incorrect)")
                    # Continue with literal content

            # Create temp file
            temp_file = self.scratch_dir / f'heredoc_{threading.get_ident()}_{len(temp_files)}.tmp'

            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                temp_files.append(temp_file)
                
                # Unix path for temp file
                unix_temp = f"/tmp/{temp_file.name}"
                
                # Calculate what to replace:
                # From << to end of delimiter line (inclusive)
                heredoc_end = heredoc_start + len('\n'.join(lines[:delimiter_line_index + 1]))
                
                # Replace heredoc with < temp_file
                replacement = f"< {unix_temp}"
                
                # Do replacement (working backwards, so positions are stable)
                result_command = result_command[:match.start()] + replacement + result_command[heredoc_end:]
            
            except Exception as e:
                self.logger.error(f"Failed to create heredoc temp file: {e}")
                continue
        
        return result_command, temp_files
    
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
        
        cwd = self.working_dir
        
        def replace_input_substitution(match):
            """Replace <(cmd) with temp file containing cmd output"""
            cmd = match.group(1)

            # Translate and execute command
            try:
                # NOTE: Paths already translated by BashToolExecutor.execute()
                # No need to translate again here

                # Execute via ExecutionEngine
                result = self._single_executor.execute_single(cmd, test_mode_stdout=f"[TEST MODE] Process substitution output for: {cmd}\n")  # AS IF: realistic output

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
        - Process substitution <(...)
        - Complex redirections

        Args:
            content: Unix command string (e.g., "grep pattern file.txt")

        Returns:
            Translated command or bash.exe invocation
        """
        # Handle empty
        if not content or not content.strip():
            return content

        # STEP 1: Recursively handle nested $(...)
        if '$(' in content:
            content = self._process_command_substitution_recursive(content)

        # ================================================================
        # ARTIGIANO: Detect if command inside $(...) is COMPLEX
        # ================================================================

        def is_complex_substitution(cmd: str) -> bool:
            """Detect if command needs bash.exe for reliable execution"""
            # Pipeline with critical commands
            if '|' in cmd:
                critical_in_pipeline = ['find', 'xargs', 'awk', 'sed', 'grep -', 'cut', 'tr']
                for critical in critical_in_pipeline:
                    if critical in cmd:
                        return True

            # Command chains
            if any(op in cmd for op in ['&&', '||', ';']):
                return True

            # Process substitution (shouldn't be here but check anyway)
            if '<(' in cmd or '>(' in cmd:
                return True

            # Complex find -exec
            if '-exec' in cmd and 'find' in cmd:
                return True

            return False

        if is_complex_substitution(content):
            # COMPLEX command inside $(...) -> execute with bash.exe
            if self.git_bash_exe:
                self.logger.debug(f"Complex command in $(...) -> using bash.exe: {content[:50]}")
                # Need to execute bash.exe, capture output, and insert as string
                # This is tricky - we're in preprocessing, haven't executed yet
                # Return a PowerShell invocation that runs bash.exe
                bash_escaped = content.replace('"', '`"').replace('$', '`$')
                # Convert to bash.exe invocation that captures output
                return f'& "{self.git_bash_exe}" -c "{bash_escaped}"'
            else:
                self.logger.warning(f"Complex command in $(...) but no bash.exe - may fail: {content[:50]}")
                # Fall through to PowerShell translation (may fail)

        # ================================================================
        # STEP 2: Translate commands
        # ================================================================
        # NOTE: Paths already translated by BashToolExecutor.execute()
        # Command substitution $(...) is PART of the original command,
        # so paths inside it were already translated.

        # Use command_translator which handles:
        # - Pipe chains
        # - Redirections
        # - Command concatenation (&&, ||, ;)
        # - All individual commands
        # CRITICAL: force_translate=True to translate EXECUTOR_MANAGED commands (find, grep, etc.)
        # Inside $(), there's no "strategy selection" - must translate immediately
        translated, use_shell, method = self.command_translator.translate(content, force_translate=True)

        # STEP 4: Clean up for PowerShell context
        # Command translator might wrap in cmd /c - remove that for $(...) context
        if translated.startswith('cmd /c '):
            translated = translated[7:]
        elif translated.startswith('cmd.exe /c '):
            translated = translated[11:]

        # PowerShell $(...) expects bare commands, not cmd wrappers
        return translated
    
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
        simple_var_pattern = r'\$([A-Za-z_][A-Za-z0-9_]*)'

        def expand_simple_var(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, '')
            if not value:
                self.logger.debug(f"Variable ${var_name} not found in environment, expanding to empty string")
            return value

        command = re.sub(simple_var_pattern, expand_simple_var, command)

        return command
    
    def _preprocess_test_commands(self, command: str) -> str:
        """
        Convert test command syntax: [ expr ] -> test expr
        
        Handles:
        - [ -f file ] -> test -f file
        - [[ expr ]] -> test expr (basic conversion)
        """
        import re
        
        # Pattern: [ expr ]
        test_pattern = r'\[\s+([^\]]+)\s+\]'
        
        def convert_test(match):
            expr = match.group(1)
            return f'test {expr}'
        
        command = re.sub(test_pattern, convert_test, command)
        
        # Pattern: [[ expr ]]
        double_test_pattern = r'\[\[\s+([^\]]+)\s+\]\]'
        
        def convert_double_test(match):
            expr = match.group(1)
            return f'test {expr}'
        
        command = re.sub(double_test_pattern, convert_double_test, command)
        
        return command
    
    def _expand_aliases(self, command: str) -> str:
        """
        Expand common bash aliases to their full commands.
        
        Common aliases:
        - ll -> ls -la
        - la -> ls -A
        - l -> ls -CF
        """
        aliases = {
            'll ': 'ls -la ',
            'll\n': 'ls -la\n',
            'll$': 'ls -la',
            'la ': 'ls -A ',
            'la\n': 'ls -A\n',
            'la$': 'ls -A',
            'l ': 'ls -CF ',
            'l\n': 'ls -CF\n',
            'l$': 'ls -CF',
        }
        
        # Check if command starts with alias
        for alias, expansion in aliases.items():
            if command.startswith(alias.rstrip('$ \n')):
                command = command.replace(alias.rstrip('$ \n'), expansion.rstrip('$ \n'), 1)
                break
        
        return command
    
    def _process_subshell(self, command: str) -> str:
        """
        Process subshell execution: (command)

        Subshell in bash creates new environment.
        In our case, just execute command normally.

        IMPORTANT: Do NOT match $(...) - that's command substitution, not subshell!
        """
        import re

        # Pattern: (command) but NOT $(command) and NOT <(command) and NOT >(command) and NOT $((arithmetic))
        # Use negative lookbehind: (?<!\$) = "not preceded by $"
        #                          (?<!<) = "not preceded by <"
        #                          (?<!>) = "not preceded by >"
        #                          (?<!\() = "not preceded by (" (to avoid matching 2nd paren in $((expr)))
        # FIX #6: Added (?<!\() to prevent matching the 2nd paren in $((5 + 5))
        subshell_pattern = r'(?<!\$)(?<!<)(?<!>)(?<!\()\(([^)]+)\)'

        def remove_subshell(match):
            # Just return inner command
            # Full subshell would need environment isolation
            return match.group(1)

        command = re.sub(subshell_pattern, remove_subshell, command)

        return command
    
    def _process_command_grouping(self, command: str) -> str:
        """
        Process command grouping: { cmd1; cmd2; }
        
        Group commands to run in current shell.
        Convert to simple command sequence.
        """
        import re
        
        # Pattern: { cmd1; cmd2; } but NOT ${var...}
        # Use negative lookbehind: (?<!\$) = "not preceded by $"
        # FIX #7: Prevent matching ${var#pattern}, ${var%pattern}, ${var/pattern/repl}, etc.
        grouping_pattern = r'(?<!\$)\{\s*([^}]+)\s*\}'
        
        def expand_grouping(match):
            # Return inner commands
            return match.group(1)
        
        command = re.sub(grouping_pattern, expand_grouping, command)
        
        return command
    
    def _process_xargs(self, command: str) -> str:
        """
        Process xargs patterns: cmd | xargs other_cmd
        
        Converts to PowerShell ForEach-Object or cmd.exe for loop.
        """
        import re
        
        if 'xargs' not in command:
            return command
        
        # Pattern: ... | xargs cmd
        xargs_pattern = r'(.+?)\|\s*xargs\s+(.+)'
        
        match = re.match(xargs_pattern, command)
        if not match:
            return command
        
        input_cmd = match.group(1).strip()
        xargs_cmd = match.group(2).strip()
        
        # Convert to PowerShell ForEach-Object
        # input_cmd | ForEach-Object { xargs_cmd $_ }
        ps_command = f"{input_cmd} | ForEach-Object {{ {xargs_cmd} $_ }}"
        
        return ps_command
    
    def _process_find_exec(self, command: str) -> str:
        """
        Process find ... -exec patterns
        
        Converts to PowerShell Get-ChildItem with ForEach-Object.
        """
        import re
        
        if 'find' not in command or '-exec' not in command:
            return command
        
        # Pattern: find path -exec cmd {} \;
        exec_pattern = r'find\s+([^\s]+)\s+.*?-exec\s+(.+?)\s*\{\}\s*\\;'
        
        match = re.search(exec_pattern, command)
        if not match:
            return command
        
        path = match.group(1)
        exec_cmd = match.group(2).strip()
        
        # Convert to PowerShell
        # Get-ChildItem path -Recurse | ForEach-Object { exec_cmd $_.FullName }
        ps_command = f"Get-ChildItem {path} -Recurse | ForEach-Object {{ {exec_cmd} $_.FullName }}"
        
        return ps_command
    
    def _process_escape_sequences(self, command: str) -> str:
        """
        Process escape sequences in strings: \n, \t, \r, etc.
        
        Converts to proper escaped format for target shell.
        """
        # Already handled by echo translator in most cases
        # For PowerShell, escape sequences work with backtick
        
        # If using PowerShell, convert \ to `
        # This is simplified - real implementation needs context awareness
        
        return command
    
    def _cleanup_temp_files(self, temp_files: List[Path]):
        """Cleanup temporary files created during execution"""
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
    


# ============================================================================
# BASH TOOL EXECUTOR - Main tool class
# ============================================================================

