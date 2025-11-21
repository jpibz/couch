"""
BashCommandPreprocessor - COMANDO LEVEL preprocessing

RESPONSIBILITIES:
- CATEGORIA 1 (SEMPRE): Variable expansion, braces, arithmetic, tilde, aliases
- CATEGORIA 2 (SOLO EMULATED): Command/operator translation for PowerShell

INPUT: Command string (Windows paths!)
OUTPUT: Preprocessed command string

CRITICAL:
- All paths are WINDOWS format during preprocessing
- Categoria 1 is SAFE for bash/native/emulated (only expands shortcuts)
- Categoria 2 is DANGEROUS (PowerShell specific syntax)

NOT RESPONSIBLE FOR:
- Pipeline level preprocessing (that's BashPipelinePreprocessor)
- Execution (that's ExecutionEngine)
"""
import os
import re
import logging
from typing import Optional


class BashCommandPreprocessor:
    """
    Command level preprocessor - handles variable/brace expansion and emulation adaptation
    
    Two preprocessing categories:
    1. SAFE expansion (always) - expands shortcuts to explicit form
    2. DANGEROUS translation (only for emulation) - translates syntax
    """
    
    def __init__(self, logger=None):
        """
        Initialize preprocessor
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger('BashCommandPreprocessor')
    
    # ========================================================================
    # CATEGORIA 1: SAFE EXPANSION (SEMPRE!)
    # ========================================================================
    
    def preprocess_always(self, command: str) -> str:
        """
        CATEGORIA 1 - SAFE preprocessing (always apply)
        
        Expands shortcuts to explicit form, but keeps syntax universal.
        Safe for bash, native binaries, and PowerShell emulation.
        
        Handles:
        - Aliases (ll → ls -la)
        - Tilde expansion (~/  → C:\\Users\\...\\) [WINDOWS PATH!]
        - Variable expansion ($VAR, ${VAR}, ${VAR:-default}, etc)
        - Brace expansion ({1..10} → 1 2 3 ...)
        - Arithmetic expansion ($((5+3)) → 8)
        
        Args:
            command: Command string with Windows paths
            
        Returns:
            Command with shortcuts expanded (still universal syntax)
        """
        # 1. Expand aliases
        command = self._expand_aliases(command)
        
        # 2. Expand tilde (WINDOWS PATH!)
        command = self._expand_tilde(command)
        
        # 3. Expand arithmetic FIRST (before braces!)
        # This prevents brace scanning from breaking $((expr)) in the middle
        command = self._expand_arithmetic(command)
        
        # 4. Expand variables (all forms except arithmetic which is done above)
        command = self._expand_variables(command)
        
        # 5. Expand braces (after arithmetic so $((expr)) is already resolved)
        command = self._expand_braces(command)
        
        return command
    
    # ========================================================================
    # CATEGORIA 2: DANGEROUS TRANSLATION (SOLO EMULATED!)
    # ========================================================================
    
    def preprocess_for_emulation(self, command: str) -> str:
        """
        CATEGORIA 2 - DANGEROUS preprocessing (only for emulation)
        
        Translates syntax for PowerShell/CMD emulation.
        NOT safe for bash or native binaries!
        
        Handles:
        - Test command translation ([ ] → test) - if needed by emulator
        - Other emulation-specific adaptations
        
        NOTE: Most translation (grep → Select-String) is done by CommandEmulator,
              not here. This is for preprocessing-level adaptations only.
        
        Args:
            command: Command string (already preprocessed categoria 1)
            
        Returns:
            Command adapted for emulation
        """
        # Test command translation
        command = self._preprocess_test_commands(command)
        
        # Future: Other emulation adaptations
        
        return command
    
    # ========================================================================
    # CATEGORIA 1 IMPLEMENTATIONS
    # ========================================================================
    
    def _expand_aliases(self, command: str) -> str:
        """Expand bash aliases"""
        aliases = {
            'll ': 'ls -la ',
            'll\n': 'ls -la\n',
            'la ': 'ls -A ',
            'la\n': 'ls -A\n',
            'l ': 'ls -CF ',
            'l\n': 'ls -CF\n',
        }
        
        for alias, expansion in aliases.items():
            if command.startswith(alias.rstrip(' \n')):
                command = command.replace(alias.rstrip(' \n'), expansion.rstrip(' \n'), 1)
                break
        
        return command
    
    def _expand_tilde(self, command: str) -> str:
        """
        Expand tilde ~/
        
        CRITICAL: Returns WINDOWS path!
        Example: ~/docs → C:\\Users\\User\\working_dir\\docs
        """
        # Get working directory (WINDOWS PATH!)
        # This should be passed from BashToolExecutor's working dir
        # For now, use a placeholder that can be configured
        home_dir = os.path.expanduser('~')  # Windows home
        
        # TODO: Should use actual Claude working dir from config
        # home_dir = self.working_dir if hasattr(self, 'working_dir') else os.path.expanduser('~')
        
        # Expand ~/
        if command.startswith('~/'):
            # Windows path separator!
            command = home_dir + '\\' + command[2:].replace('/', '\\')
        
        # Expand in arguments
        command = re.sub(r'\s~/', f' {home_dir}\\\\', command)
        
        return command
    
    def _expand_variables(self, command: str) -> str:
        """
        Expand all variable forms
        
        Supports:
        - Simple: $VAR, ${VAR}
        - Default: ${VAR:-default}
        - Length: ${#VAR}
        - Remove prefix/suffix: ${VAR#pattern}, ${VAR%pattern}
        - Substitution: ${VAR/old/new}
        - Case: ${VAR^^}, ${VAR,,}
        - Arithmetic in variables: Works with _expand_arithmetic
        """
        # Order matters!
        
        # 1. String length ${#VAR}
        command = self._expand_variable_length(command)
        
        # 2. Remove prefix ${VAR#pattern}, ${VAR##pattern}
        command = self._expand_remove_prefix(command)
        
        # 3. Remove suffix ${VAR%pattern}, ${VAR%%pattern}
        command = self._expand_remove_suffix(command)
        
        # 4. Substitution ${VAR/old/new}, ${VAR//old/new}
        command = self._expand_substitution(command)
        
        # 5. Case conversion ${VAR^^}, ${VAR,,}
        command = self._expand_case(command)
        
        # 6. Default value ${VAR:-default}
        command = self._expand_default(command)
        
        # 7. Simple ${VAR}
        command = self._expand_simple_brace(command)
        
        # 8. Simple $VAR (last to avoid conflicts)
        command = self._expand_simple_var(command)
        
        return command
    
    def _expand_variable_length(self, command: str) -> str:
        """${#VAR} → length"""
        pattern = r'\$\{#(\w+)\}'

        def replace(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            return str(len(value))

        return re.sub(pattern, replace, command)
    
    def _expand_remove_prefix(self, command: str) -> str:
        """${VAR#pattern} and ${VAR##pattern}"""
        pattern = r'\$\{(\w+)(#{1,2})([^}]+)\}'

        def replace(match):
            var_name = match.group(1)
            op = match.group(2)
            glob_pattern = match.group(3)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            if not value:
                return ''
            
            # Convert glob to regex
            import fnmatch
            regex = fnmatch.translate(glob_pattern)
            regex = '^' + regex.rstrip('\\Z')
            
            if op == '#':  # Shortest (non-greedy)
                regex = regex.replace('*', '*?')
                m = re.match(regex, value)
                if m:
                    return value[len(m.group(0)):]
            else:  # Longest (greedy)
                m = re.match(regex, value)
                if m:
                    return value[len(m.group(0)):]
            
            return value
        
        return re.sub(pattern, replace, command)
    
    def _expand_remove_suffix(self, command: str) -> str:
        """${VAR%pattern} and ${VAR%%pattern}"""
        pattern = r'\$\{(\w+)(%{1,2})([^}]+)\}'

        def replace(match):
            var_name = match.group(1)
            op = match.group(2)
            glob_pattern = match.group(3)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            if not value:
                return ''
            
            # Convert glob to regex
            import fnmatch
            regex = fnmatch.translate(glob_pattern)
            regex = regex.rstrip('\\Z') + '$'
            
            if op == '%':  # Shortest
                for i in range(len(value), -1, -1):
                    if re.search(regex, value[i:]) and re.search(regex, value[i:]).start() == 0:
                        return value[:i]
            else:  # Longest
                for i in range(len(value) + 1):
                    if re.search(regex, value[i:]) and re.search(regex, value[i:]).start() == 0:
                        return value[:i]
            
            return value
        
        return re.sub(pattern, replace, command)
    
    def _expand_substitution(self, command: str) -> str:
        """${VAR/old/new} and ${VAR//old/new}"""
        pattern = r'\$\{(\w+)(/{1,2})([^/}]+)/([^}]*)\}'

        def replace(match):
            var_name = match.group(1)
            op = match.group(2)
            glob_pattern = match.group(3)
            replacement = match.group(4)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            if not value:
                return ''
            
            import fnmatch
            regex = fnmatch.translate(glob_pattern).rstrip('\\Z')
            
            if op == '/':  # First
                return re.sub(regex, replacement, value, count=1)
            else:  # All
                return re.sub(regex, replacement, value)
        
        return re.sub(pattern, replace, command)
    
    def _expand_case(self, command: str) -> str:
        """${VAR^^}, ${VAR,,}, ${VAR^}, ${VAR,}"""
        pattern = r'\$\{(\w+)(\^{1,2}|,{1,2})\}'

        def replace(match):
            var_name = match.group(1)
            op = match.group(2)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            if op == '^^':
                return value.upper()
            elif op == ',,':
                return value.lower()
            elif op == '^':
                return value[0].upper() + value[1:] if value else ''
            elif op == ',':
                return value[0].lower() + value[1:] if value else ''
            
            return value
        
        return re.sub(pattern, replace, command)
    
    def _expand_default(self, command: str) -> str:
        """${VAR:-default}"""
        pattern = r'\$\{(\w+):-([^}]+)\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            return value if value else default

        return re.sub(pattern, replace, command)
    
    def _expand_simple_brace(self, command: str) -> str:
        """${VAR}"""
        pattern = r'\$\{(\w+)\}'

        def replace(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            return value

        return re.sub(pattern, replace, command)
    
    def _expand_simple_var(self, command: str) -> str:
        """$VAR"""
        pattern = r'\$([A-Za-z_][A-Za-z0-9_]*)'

        def replace(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, None)

            # If variable doesn't exist, leave it for bash to handle
            if value is None:
                return match.group(0)

            return value

        return re.sub(pattern, replace, command)
    
    def _expand_braces(self, command: str) -> str:
        """
        Expand brace patterns with complete cartesian product support + NESTED
        
        Handles:
        - Single: {1..10} → 1 2 3 ... 10
        - List: {a,b,c} → a b c
        - Adjacent: {a,b}{1,2} → a1 a2 b1 b2
        - Multiple: {a,b}{1,2}{x,y} → a1x a1y a2x a2y b1x b1y b2x b2y
        - With prefix/suffix: file{a,b}{1,2}.txt → filea1.txt filea2.txt fileb1.txt fileb2.txt
        - Nested: {a,b{1,2}} → a b1 b2
        
        STRATEGY: Iterative innermost-first expansion for nested braces
        """
        from itertools import product
        
        def expand_items(content):
            """Generate items from single brace content"""
            # Numeric range
            m = re.match(r'^(\d+)\.\.(\d+)$', content)
            if m:
                start = int(m.group(1))
                end = int(m.group(2))
                padding = len(m.group(1)) if m.group(1).startswith('0') else 0
                
                if start <= end:
                    return [str(i).zfill(padding) if padding else str(i) 
                           for i in range(start, end + 1)]
                else:
                    return [str(i).zfill(padding) if padding else str(i) 
                           for i in range(start, end - 1, -1)]
            
            # Alpha range
            m = re.match(r'^([a-zA-Z])\.\.([a-zA-Z])$', content)
            if m:
                start_char = m.group(1)
                end_char = m.group(2)
                
                if start_char <= end_char:
                    return [chr(c) for c in range(ord(start_char), ord(end_char) + 1)]
                else:
                    return [chr(c) for c in range(ord(start_char), ord(end_char) - 1, -1)]
            
            # List (may contain spaces from previous expansion!)
            if ',' in content:
                # Split by comma, but be careful with spaces from nested expansions
                return [item.strip() for item in content.split(',')]
            
            return None
        
        def find_innermost_brace(text):
            """
            Find the innermost (deepest nested) brace pattern
            
            Strategy: Build depth map, find brace with highest depth that has no nested braces
            
            Returns: (start, end, content) or None
            """
            # Build depth map and find all braces with their depths
            depth = 0
            brace_info = []  # (start, end, content, depth)
            stack = []
            
            for i, char in enumerate(text):
                if char == '{' and (i == 0 or text[i-1] != '$'):
                    stack.append((i, depth))
                    depth += 1
                elif char == '}' and stack:
                    start_pos, brace_depth = stack.pop()
                    depth -= 1
                    content = text[start_pos+1:i]
                    brace_info.append((start_pos, i+1, content, brace_depth))
            
            # Find the brace with HIGHEST depth that has no nested braces
            deepest = None
            max_depth = -1
            
            for start, end, content, brace_depth in brace_info:
                # Check if content has no nested braces
                if '{' not in content and '}' not in content:
                    if brace_depth > max_depth:
                        max_depth = brace_depth
                        deepest = (start, end, content)
            
            return deepest
        
        def expand_word_with_braces(word):
            """
            Expand a single word containing one or more brace patterns (non-nested)
            
            Examples:
            - {a,b} → ['a', 'b']
            - {a,b}{1,2} → ['a1', 'a2', 'b1', 'b2']
            - file{a,b}.txt → ['filea.txt', 'fileb.txt']
            """
            # Find all NON-NESTED brace patterns in word
            # Pattern: {content} but not ${var} and no nested {}
            brace_pattern = r'(?<!\$)\{([^{}]+)\}'
            
            matches = list(re.finditer(brace_pattern, word))
            
            if not matches:
                return [word]
            
            # Extract all brace contents and expand to items
            expanded_lists = []
            for match in matches:
                content = match.group(1)
                items = expand_items(content)
                if items is None:
                    # Can't expand this brace, use literal
                    items = ['{' + content + '}']
                expanded_lists.append(items)
            
            # Cartesian product of all expanded lists
            cartesian = list(product(*expanded_lists))
            
            # Reconstruct word for each combination
            results = []
            for combo in cartesian:
                # Replace braces with combo items (from end to start for stable indices)
                result = word
                for match, item in zip(reversed(matches), reversed(combo)):
                    result = result[:match.start()] + item + result[match.end():]
                results.append(result)
            
            return results
        
        # MULTI-PASS EXPANSION:
        # Pass 1: Expand innermost nested braces first
        # Pass 2: Token-based expansion for remaining braces
        
        # Pass 1: Innermost-first for NESTED braces only
        # This pass flattens nested structures like {a,b{1,2}} → {a,b1,b2}
        # Top-level braces are left for Pass 2
        max_nested_iter = 20
        for _ in range(max_nested_iter):
            innermost = find_innermost_brace(command)
            if innermost is None:
                break
            
            start, end, content = innermost
            items = expand_items(content)
            
            if items is None:
                break
            
            # Find prefix before this brace
            prefix_start = start - 1
            while prefix_start >= 0 and command[prefix_start] not in ',{ \t\n;|&':
                prefix_start -= 1

            # Determine if this is a nested brace or top-level
            # NESTED if: there's a prefix (even if preceded by { or ,)
            # TOP-LEVEL if: no prefix (directly after space/beginning/{ with no chars between)

            if prefix_start < 0:
                # At beginning of string
                prefix = command[0:start]
            elif command[prefix_start] in ',{':
                # After comma or opening brace
                prefix = command[prefix_start+1:start]
            else:
                # After space/delimiter - top-level
                prefix = ''

            if not prefix:
                # No prefix → TOP-LEVEL brace
                # Leave it for Pass 2!
                break
            else:
                # Has prefix → NESTED brace → expand it!
                # Calculate actual prefix_start (after the delimiter)
                if prefix_start >= 0 and command[prefix_start] in ',{':
                    prefix_start += 1

                # Expand with prefix: b{1,2} → b1,b2
                expanded_items = [prefix + item for item in items]
                replacement = ','.join(expanded_items)

                # Replace from prefix_start (include prefix in replacement)
                command = command[:prefix_start] + replacement + command[end:]
        
        # Pass 2: Token-based expansion for adjacent braces
        max_iter = 10
        prev = None
        
        for iteration in range(max_iter):
            if command == prev:
                break
            prev = command
            
            # Split by delimiters but preserve them
            # Delimiters: space, tab, newline, ;, |, &
            # NOTE: Do NOT include comma! Commas inside braces {a,b} must be preserved!
            tokens = re.split(r'([ \t\n;|&])', command)
            
            result_tokens = []
            
            for token in tokens:
                # Preserve delimiters as-is
                if token in [' ', '\t', '\n', ';', '|', '&', '']:
                    result_tokens.append(token)
                    continue
                
                # Check if token contains braces (but not ${var})
                if not re.search(r'(?<!\$)\{[^{}]+\}', token):
                    result_tokens.append(token)
                    continue
                
                # Token has braces! Expand it with cartesian product
                expanded = expand_word_with_braces(token)
                
                # Join expanded items with space
                result_tokens.append(' '.join(expanded))
            
            command = ''.join(result_tokens)
        
        return command
    
    def _expand_arithmetic(self, command: str) -> str:
        """$((expr)) → result"""
        pattern = r'\$\(\(([^)]+)\)\)'
        
        def replace(match):
            expr = match.group(1)
            
            try:
                # Expand variables in expression first
                var_pattern = r'([A-Za-z_][A-Za-z0-9_]*)'
                
                def replace_var(m):
                    var_name = m.group(1)
                    if var_name in os.environ:
                        return os.environ[var_name]
                    return m.group(0)
                
                expr = re.sub(var_pattern, replace_var, expr)
                
                # Evaluate
                result = eval(expr, {"__builtins__": {}}, {})
                return str(result)
            
            except Exception as e:
                self.logger.warning(f"Arithmetic expansion failed: {e}")
                return match.group(0)
        
        return re.sub(pattern, replace, command)
    
    # ========================================================================
    # CATEGORIA 2 IMPLEMENTATIONS
    # ========================================================================
    
    def _preprocess_test_commands(self, command: str) -> str:
        """Convert [ expr ] → test expr"""
        # [ expr ]
        command = re.sub(r'\[\s+([^\]]+)\s+\]', lambda m: f'test {m.group(1)}', command)
        
        # [[ expr ]]
        command = re.sub(r'\[\[\s+([^\]]+)\s+\]\]', lambda m: f'test {m.group(1)}', command)
        
        return command
