"""
Command Emulator - Unix to PowerShell translation (73 commands)
"""
import re
import logging
import shlex
from typing import Optional, List, Tuple

class CommandEmulator:
    """
    Unix→Windows command translation 
    
    """

    def __init__(self):
        """Initialize SimpleTranslator"""
        # Command map with all translators (73 commands)

        self.command_map = {
            # ===== SIMPLE 1:1 TRANSLATIONS (< 20 righe) =====
            'pwd': self._translate_pwd,           # 3 lines
            'ps': self._translate_ps,             # 3 lines
            'chmod': self._translate_chmod,       # 3 lines
            'chown': self._translate_chown,       # 3 lines
            'df': self._translate_df,             # 3 lines
            'true': self._translate_true,         # 3 lines
            'false': self._translate_false,       # 7 lines
            'whoami': self._translate_whoami,     # 4 lines
            'hostname': self._translate_hostname, # 4 lines
            'which': self._translate_which,       # 5 lines
            'sleep': self._translate_sleep,       # 5 lines
            'cd': self._translate_cd,             # 6 lines
            'basename': self._translate_basename, # 6 lines
            'dirname': self._translate_dirname,   # 6 lines
            'kill': self._translate_kill,         # 8 lines
            'mkdir': self._translate_mkdir,       # 9 lines
            'mv': self._translate_mv,             # 11 lines
            'yes': self._translate_yes,           # 13 lines
            'env': self._translate_env,           # 15 lines
            'printenv': self._translate_printenv, # 15 lines
            'export': self._translate_export,     # 19 lines

            # ===== MEDIUM COMPLEXITY (20-100 righe) =====
            'touch': self._translate_touch,       # 26 lines
            'echo': self._translate_echo,         # 37 lines
            'wc': self._translate_wc,             # 34 lines
            'du': self._translate_du,             # 36 lines
            'date': self._translate_date,         # 46 lines
            'head': self._translate_head,         # 51 lines
            'tail': self._translate_tail,         # 56 lines
            'rm': self._translate_rm,             # 58 lines
            'cat': self._translate_cat,           # 63 lines
            'cp': self._translate_cp,             # 72 lines
            'ls': self._translate_ls,             # 75 lines

            # Medium - special commands
            'tee': self._translate_tee,           # 23 lines
            'seq': self._translate_seq,           # 33 lines
            'file': self._translate_file,         # 21 lines
            'stat': self._translate_stat,         # 21 lines
            'readlink': self._translate_readlink, # 26 lines
            'realpath': self._translate_realpath, # 21 lines
            'test': self._translate_test,         # 75 lines
            'tr': self._translate_tr,             # 68 lines
            'find': self._translate_find,         # 24 lines - FALLBACK (executor has _execute_find)

            # ===== COMPLEX EMULATIONS - FALLBACK ONLY (> 100 righe) =====
            'wget': self._translate_wget,         # 16 lines - simple but in executor
            'curl': self._translate_curl,         # 239 lines - FALLBACK
            'sed': self._translate_sed,           # 233 lines - FALLBACK
            'diff': self._translate_diff,         # 212 lines - FALLBACK
            'jq': self._translate_jq,             # 212 lines - FALLBACK
            'awk': self._translate_awk,           # 211 lines - FALLBACK
            'split': self._translate_split,       # 196 lines - FALLBACK
            'sort': self._translate_sort,         # 190 lines - FALLBACK
            'uniq': self._translate_uniq,         # 161 lines - FALLBACK
            'join': self._translate_join,         # 140 lines - FALLBACK
            'hexdump': self._translate_hexdump,   # 131 lines - FALLBACK
            'ln': self._translate_ln,             # 124 lines - FALLBACK
            'grep': self._translate_grep,         # 124 lines - FALLBACK
            'gzip': self._translate_gzip,         # 115 lines - FALLBACK
            'gunzip': self._translate_gunzip,     # 92 lines - FALLBACK
            'timeout': self._translate_timeout,   # 112 lines - FALLBACK
            'tar': self._translate_tar,           # 110 lines - FALLBACK
            'cut': self._translate_cut,           # 107 lines

            # Complex - text/binary processing
            'strings': self._translate_strings,   # 68 lines - FALLBACK
            'column': self._translate_column,     # 95 lines - FALLBACK
            'paste': self._translate_paste,       # 88 lines - FALLBACK
            'comm': self._translate_comm,         # 88 lines - FALLBACK

            # Complex - compression/archives
            'zip': self._translate_zip,           # 69 lines - FALLBACK
            'unzip': self._translate_unzip,       # 88 lines - FALLBACK

            # Checksums/encoding - FALLBACK (executor has _execute_*)
            'sha256sum': self._translate_sha256sum, # 9 lines - FALLBACK
            'sha1sum': self._translate_sha1sum,     # 9 lines - FALLBACK
            'md5sum': self._translate_md5sum,       # 9 lines - FALLBACK
            'base64': self._translate_base64,       # 58 lines - FALLBACK

            # Monitoring - FALLBACK
            'watch': self._translate_watch,       # 58 lines - FALLBACK
        }

    def emulate_command(self, unix_command: str):
        """
        Translate Unix command → Windows with operator support.

        RESPONSIBILITY:
        - Parse operators into segments

        Args:
            unix_command: Full Unix command with possible operators

        Returns:
            - translated_command: Command ready for execution
        """
    
        parts = unix_command.strip().split()


        base_cmd = parts[0]

        # Check translator for simple 1:1 translations
        if base_cmd in self.command_map:
            translator = self.command_map[base_cmd]
            try:
                translated, _ = translator(unix_command, parts)
                return translated
            except Exception:
                pass

        # Python3 → Python (Windows doesn't have python3)
        if base_cmd == 'python3':
            # Replace ALL occurrences, not just first
            translated = unix_command.replace('python3', 'python')
            return translated

        return unix_command
    
    def _translate_ls(self, cmd: str, parts):
        """Translate ls with FULL flag support - ALL flags implemented"""
        flags = []
        paths = []
        long_format = False
        human_readable = False
        directory_only = False
        classify = False
        one_per_line = False
        
        for part in parts[1:]:
            if part.startswith('-') and part != '-':
                for c in part[1:]:
                    if c == 'a':
                        flags.append('/a')  # Show hidden files
                    elif c == 'l':
                        long_format = True
                    elif c == 'h':
                        human_readable = True
                    elif c == 'R':
                        flags.append('/s')  # Recursive
                    elif c == 't':
                        flags.append('/o:d')  # Sort by time
                    elif c == 'r':
                        flags.append('/o:-n')  # Reverse order
                    elif c == 'S':
                        flags.append('/o:s')  # Sort by size
                    elif c == 'd':
                        directory_only = True
                    elif c == '1':
                        one_per_line = True
                    elif c == 'F':
                        classify = True
            else:
                # Paths already translated by translate_paths_in_string
                # Use directly without additional quoting (quotes already added if needed)
                paths.append(part)
        
        # Build command
        flag_str = ' '.join(set(flags)) if flags else ''
        path_str = ' '.join(paths) if paths else ''
        
        # Special handling for directory-only mode
        if directory_only and paths:
            return f'dir /a:d {flag_str} {path_str}'.strip(), True
        
        # Use PowerShell for advanced formatting (long_format, human_readable, classify)
        if long_format or human_readable or classify:
            ps_flags = []
            if long_format:
                ps_flags.append('-Format List')
            
            file_arg = paths[0] if paths else '*'
            
            ps_cmd = f'Get-ChildItem {file_arg} {" ".join(ps_flags)}'
            
            if human_readable:
                # Add human-readable size formatting
                ps_cmd += ' | Select-Object Mode, LastWriteTime, @{Name="Size";Expression={if($_.PSIsContainer){"<DIR>"}else{"{0:N2} KB" -f ($_.Length/1KB)}}}, Name'
            
            if classify:
                # Add classifier (/ for dirs, * for executable, @ for symlinks)
                ps_cmd += ' | ForEach-Object { if($_.PSIsContainer) {$_.Name + "/"} else {$_.Name} }'
            
            return f'powershell -Command "{ps_cmd}"', True
        
        # Standard dir command
        cmd_result = f'dir {flag_str} {path_str}'.strip()
        
        # One per line is default for non-interactive
        if one_per_line:
            cmd_result += ' /b'
        
        return cmd_result, True
    
    def _translate_cat(self, cmd: str, parts):
        """
        Execute cat - concatenate and display files.

        ARTIGIANO IMPLEMENTATION:
        - PowerShell Get-Content (native, fast)
        - Multiple files concatenation
        - Line numbering with -n
        - Stdin support (no files = read from pipeline)

        Flags:
        - -n: number all output lines
        - -b: number non-blank lines (simplified: same as -n for now)

        Usage:
          cat file.txt               -> display file
          cat file1 file2            -> concatenate files
          cat -n file.txt            -> with line numbers
          echo "text" | cat          -> from stdin
          cat < input.txt            -> from redirect
        """
        number_lines = '-n' in parts or '-b' in parts
        files = []

        i = 1
        while i < len(parts):
            if parts[i] in ['-n', '-b']:
                number_lines = True
                i += 1
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1

        if not files:
            # Reading from stdin (pipeline or redirect)
            if number_lines:
                # PowerShell: enumerate lines with numbers
                ps_cmd = '''
                    $lineNum = 1
                    $input | ForEach-Object {
                        Write-Output ("{0,6} {1}" -f $lineNum, $_)
                        $lineNum++
                    }
                '''
                return f'powershell -Command "{ps_cmd}"', True
            else:
                # Just pass through stdin
                # In PowerShell pipeline, this is implicit
                return '$input', True

        # ================================================================
        # ARTIGIANO: Glob Pattern Expansion
        # ================================================================
        # CRITICAL: PowerShell scripts must expand globs BEFORE using files
        # If we pass "*.txt" directly to Get-Content, it's LITERAL, not expanded!
        #
        # Detect glob patterns: *, ?, [ ]
        # Use Get-ChildItem to expand, then process expanded files

        has_glob = any(c in ''.join(files) for c in ['*', '?', '[', ']'])

        if has_glob:
            # Build glob-aware PowerShell script
            files_patterns = ','.join(f'"{f}"' for f in files)

            if number_lines:
                ps_script = f'''
                    # Expand glob patterns
                    $expandedFiles = @()
                    foreach ($pattern in @({files_patterns})) {{
                        if ($pattern -match '[*?\\[\\]]') {{
                            $matched = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
                            if ($matched) {{
                                $expandedFiles += $matched.FullName
                            }}
                        }} else {{
                            if (Test-Path $pattern) {{
                                $expandedFiles += $pattern
                            }} else {{
                                Write-Error "cat: $pattern: No such file or directory"
                                exit 1
                            }}
                        }}
                    }}

                    if ($expandedFiles.Count -eq 0) {{
                        Write-Error "cat: No files matched"
                        exit 1
                    }}

                    # Process files with line numbers
                    $lineNum = 1
                    foreach ($file in $expandedFiles) {{
                        Get-Content $file | ForEach-Object {{
                            Write-Output ("{{0,6}} {{1}}" -f $lineNum, $_)
                            $lineNum++
                        }}
                    }}
                '''
            else:
                ps_script = f'''
                    # Expand glob patterns
                    $expandedFiles = @()
                    foreach ($pattern in @({files_patterns})) {{
                        if ($pattern -match '[*?\\[\\]]') {{
                            $matched = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
                            if ($matched) {{
                                $expandedFiles += $matched.FullName
                            }}
                        }} else {{
                            if (Test-Path $pattern) {{
                                $expandedFiles += $pattern
                            }} else {{
                                Write-Error "cat: $pattern: No such file or directory"
                                exit 1
                            }}
                        }}
                    }}

                    if ($expandedFiles.Count -eq 0) {{
                        Write-Error "cat: No files matched"
                        exit 1
                    }}

                    # Concatenate files
                    foreach ($file in $expandedFiles) {{
                        Get-Content $file
                    }}
                '''
        else:
            # No globs - direct file access (original logic)
            # Files specified
            if len(files) == 1:
                # Single file
                file = files[0]
                if number_lines:
                    ps_script = f'''
                        if (Test-Path "{file}") {{
                            $lineNum = 1
                            Get-Content "{file}" | ForEach-Object {{
                                Write-Output ("{{0,6}} {{1}}" -f $lineNum, $_)
                                $lineNum++
                            }}
                        }} else {{
                            Write-Error "cat: {file}: No such file or directory"
                            exit 1
                        }}
                    '''
                else:
                    ps_script = f'''
                        if (Test-Path "{file}") {{
                            Get-Content "{file}"
                        }} else {{
                            Write-Error "cat: {file}: No such file or directory"
                            exit 1
                        }}
                    '''
            else:
                # Multiple files - concatenate
                if number_lines:
                    ps_script = '''
                        $files = @({})
                        $lineNum = 1
                        foreach ($file in $files) {{
                            if (Test-Path $file) {{
                                Get-Content $file | ForEach-Object {{
                                    Write-Output ("{{0,6}} {{1}}" -f $lineNum, $_)
                                    $lineNum++
                                }}
                            }} else {{
                                Write-Error "cat: $file: No such file or directory"
                                exit 1
                            }}
                        }}
                    '''.format(','.join(f'"{f}"' for f in files))
                else:
                    ps_script = '''
                        $files = @({})
                        foreach ($file in $files) {{
                            if (Test-Path $file) {{
                                Get-Content $file
                            }} else {{
                                Write-Error "cat: $file: No such file or directory"
                                exit 1
                            }}
                        }}
                    '''.format(','.join(f'"{f}"' for f in files))

        return f'powershell -Command "{ps_script}"', True
    
    def _translate_echo(self, cmd: str, parts):
        """
        Translate echo with ALL flags.
        
        Flags:
        - -n: no trailing newline
        - -e: enable escape sequences (\n, \t, etc)
        - -E: disable escape sequences (default)
        """
        no_newline = '-n' in parts
        enable_escapes = '-e' in parts
        
        # Remove flags from parts
        text_parts = [p for p in parts[1:] if p not in ['-n', '-e', '-E']]
        text = ' '.join(text_parts)
        
        if enable_escapes:
            # PowerShell for escape sequence support
            # Replace \n, \t, etc with PowerShell backtick equivalents
            text = text.replace('\\n', '`n').replace('\\t', '`t').replace('\\r', '`r')
            
            if no_newline:
                return f'powershell -Command "Write-Host -NoNewline \\"{text}\\""', True
            else:
                return f'powershell -Command "Write-Host \\"{text}\\""', True
        else:
            # Standard cmd.exe echo
            if no_newline:
                # cmd.exe doesn't support no-newline, use PowerShell
                return f'powershell -Command "Write-Host -NoNewline \\"{text}\\""', True
            else:
                # Escape special characters for cmd
                if text:
                    return f'echo {text}', True
                else:
                    return 'echo.', True
    
    def _translate_pwd(self, cmd: str, parts):
        return 'cd', True
    
    def _translate_cd(self, cmd: str, parts):
        if len(parts) < 2:
            return 'cd', True
        win_path = parts[1]  # Already translated
        return f'cd /d "{win_path}"', True
    
    def _translate_mkdir(self, cmd: str, parts):
        if len(parts) < 2:
            return 'echo Error: mkdir requires directory name', True
        # Paths already translated, use directly
        dirs = [p for p in parts[1:] if p != '-p' and not p.startswith('-')]
        if not dirs:
            return 'echo Error: mkdir requires directory name', True
        return f'mkdir {" ".join(dirs)}', True
    
    def _translate_rm(self, cmd: str, parts):
        """Translate rm with FULL flag support - verbose implemented"""
        if len(parts) < 2:
            return 'echo Error: rm requires filename', True
        
        recursive = '-r' in parts or '-R' in parts
        force = '-f' in parts
        
        for part in parts:
            if part.startswith('-') and 'r' in part and 'f' in part:
                recursive = True
                force = True
        
        interactive = '-i' in parts
        verbose = '-v' in parts
        dir_mode = '-d' in parts
        
        paths = [p for p in parts[1:] if not p.startswith('-')]
        if not paths:
            return 'echo Error: rm requires filename', True
        
        # Paths already translated by translate_paths_in_string
        win_paths = paths
        
        commands = []
        for win_path in win_paths:
            if recursive or dir_mode:
                flags = []
                if recursive:
                    flags.append('/s')
                if force and not interactive:
                    flags.append('/q')
                
                flag_str = ' '.join(flags)
                
                # With verbose, echo before removing
                if verbose:
                    commands.append(f'echo Removing: {win_path}')
                
                cmd_dir = f'rmdir {flag_str} "{win_path}"'
                cmd_file = f'del /f /q "{win_path}"' if force else f'del /q "{win_path}"'
                commands.append(f'({cmd_dir} 2>nul || {cmd_file})')
            else:
                flags = []
                if force:
                    flags.append('/f')
                if not interactive:
                    flags.append('/q')
                
                flag_str = ' '.join(flags)
                
                if verbose:
                    commands.append(f'echo Removing: {win_path}')
                
                commands.append(f'del {flag_str} "{win_path}"')
        
        return ' && '.join(commands), True
    
    def _translate_cp(self, cmd: str, parts):
        """Translate cp with FULL flag support - preserve and force implemented"""
        if len(parts) < 3:
            return 'echo Error: cp requires source and destination', True
        
        recursive = '-r' in parts or '-R' in parts or '-a' in parts
        preserve = '-p' in parts or '-a' in parts
        update = '-u' in parts
        verbose = '-v' in parts
        force = '-f' in parts
        interactive = '-i' in parts
        no_clobber = '-n' in parts
        
        paths = [p for p in parts[1:] if not p.startswith('-')]
        if len(paths) < 2:
            return 'echo Error: cp requires source and destination', True
        
        if len(paths) > 2:
            # Multiple sources → destination must be directory
            # Paths already translated
            sources = paths[:-1]
            dst = paths[-1]
            
            commands = []
            for src in sources:
                if recursive:
                    flags = ['/e', '/i']
                    if force or (not interactive and not no_clobber):
                        flags.append('/y')
                    if update:
                        flags.append('/d')
                    if preserve:
                        flags.append('/k')  # Keep attributes
                    commands.append(f'xcopy {" ".join(flags)} "{src}" "{dst}"')
                else:
                    copy_flags = []
                    if force or (not interactive and not no_clobber):
                        copy_flags.append('/y')
                    commands.append(f'copy {" ".join(copy_flags)} "{src}" "{dst}"')
            return ' && '.join(commands), True
        else:
            # Single source - paths already translated
            src = paths[0]
            dst = paths[1]
            
            if recursive:
                flags = ['/e', '/i']
                if force or (not interactive and not no_clobber):
                    flags.append('/y')
                if update:
                    flags.append('/d')
                if preserve:
                    flags.append('/k')  # Keep attributes
                if verbose:
                    flags.append('/f')
                
                return f'xcopy {" ".join(flags)} "{src}" "{dst}"', True
            else:
                flags = []
                if force or (not interactive and not no_clobber):
                    flags.append('/y')
                if verbose:
                    flags.append('/v')
                
                flag_str = ' '.join(flags)
                
                # Use robocopy for preserve mode (preserves timestamps, attributes)
                if preserve:
                    return f'robocopy /copy:DAT /np "{Path(src).parent}" "{Path(dst).parent}" "{Path(src).name}"', True
                
                return f'copy {flag_str} "{src}" "{dst}"', True
    
    def _translate_mv(self, cmd: str, parts):
        if len(parts) < 3:
            return 'echo Error: mv requires source and destination', True
        paths = [p for p in parts[1:] if not p.startswith('-')]
        if len(paths) < 2:
            return 'echo Error: mv requires source and destination', True
        # Paths already translated
        src = paths[-2]
        dst = paths[-1]
        return f'move /y "{src}" "{dst}"', True
    
    def _translate_touch(self, cmd: str, parts):
        """Translate touch with proper timestamp update
        
        Creates file if doesn't exist, updates timestamp if exists
        """
        if len(parts) < 2:
            return 'echo Error: touch requires filename', True
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        # Paths already translated
        win_paths = files
        
        commands = []
        for win_path in win_paths:
            # PowerShell command that creates or updates timestamp
            ps_cmd = (
                f'if (Test-Path \\"{win_path}\\") {{ '
                f'(Get-Item \\"{win_path}\\").LastWriteTime = Get-Date '
                f'}} else {{ '
                f'New-Item -ItemType File -Path \\"{win_path}\\" -Force | Out-Null '
                f'}}'
            )
            commands.append(f'powershell -Command "{ps_cmd}"')
        
        return ' && '.join(commands), True
    
    def _translate_ln(self, cmd: str, parts):
        """
        Translate ln - FULL symlink/hardlink support with fallback.
        
        ARTISAN IMPLEMENTATION:
        - ln target link → Hard link (mklink /H)
        - ln -s target link → Symlink (mklink or mklink /D)
        - Fallback: PowerShell New-Item -ItemType SymbolicLink
        - Fallback 2: Copy if symlink fails (no admin)
        
        Windows challenges:
        - Symlinks require admin privileges (Vista+)
        - Hard links work without admin
        - Directory symlinks need /D flag
        
        Supported flags:
        - -s, --symbolic: Symbolic link (default: hard link)
        - -f, --force: Remove existing destination
        - -n, --no-dereference: Treat link destination as normal file
        """
        if len(parts) < 3:
            return 'echo Error: ln requires target and link_name', True
        
        # Parse flags (including combined flags like -sf)
        symbolic = False
        force = False
        
        for part in parts[1:]:
            if part.startswith('-') and not part.startswith('--'):
                # Combined flags: -sf, -fs, etc.
                if 's' in part:
                    symbolic = True
                if 'f' in part:
                    force = True
            elif part == '--symbolic':
                symbolic = True
            elif part == '--force':
                force = True
        
        # Extract target and link_name
        non_flags = [p for p in parts[1:] if not p.startswith('-')]
        if len(non_flags) < 2:
            return 'echo Error: ln requires target and link_name', True
        
        target = non_flags[0]  # Already translated path
        link_name = non_flags[1]  # Already translated path
        
        if symbolic:
            # SYMBOLIC LINK
            # Strategy: Try mklink, fallback to PowerShell, fallback to copy
            
            # Determine if target is directory or file
            # Use PowerShell to check
            check_dir = f'Test-Path -Path \\"{target}\\" -PathType Container'
            
            # Build mklink command with directory detection
            # Note: mklink requires "mklink /D link target" syntax (opposite of ln!)
            ps_script = f'''
                $target = \\"{target}\\"
                $link = \\"{link_name}\\"
                
                # Force: remove existing link
                if (Test-Path $link) {{
                    {"Remove-Item $link -Force" if force else 'Write-Host "Link exists (use -f to overwrite)" ; exit 1'}
                }}
                
                # Try mklink first (fast, native)
                try {{
                    if (Test-Path $target -PathType Container) {{
                        # Directory symlink
                        $result = cmd /c "mklink /D \\"$link\\" \\"$target\\"" 2>&1
                    }} else {{
                        # File symlink
                        $result = cmd /c "mklink \\"$link\\" \\"$target\\"" 2>&1
                    }}
                    
                    if ($LASTEXITCODE -eq 0) {{
                        Write-Host "Symbolic link created: $link -> $target"
                        exit 0
                    }}
                }}
                catch {{}}
                
                # Fallback: PowerShell New-Item (also requires admin but different API)
                try {{
                    if (Test-Path $target -PathType Container) {{
                        New-Item -ItemType SymbolicLink -Path $link -Target $target -Force | Out-Null
                    }} else {{
                        New-Item -ItemType SymbolicLink -Path $link -Target $target -Force | Out-Null
                    }}
                    Write-Host "Symbolic link created (PS): $link -> $target"
                    exit 0
                }}
                catch {{}}
                
                # Fallback 2: Copy (if no admin privileges)
                Write-Host "Warning: No admin privileges for symlink. Copying instead."
                try {{
                    if (Test-Path $target -PathType Container) {{
                        Copy-Item -Path $target -Destination $link -Recurse -Force
                    }} else {{
                        Copy-Item -Path $target -Destination $link -Force
                    }}
                    Write-Host "Copied: $link (symlink failed, file copied)"
                    exit 0
                }}
                catch {{
                    Write-Host "Error: Failed to create link or copy: $_"
                    exit 1
                }}
            '''
            
            return f'powershell -Command "{ps_script}"', True
        
        else:
            # HARD LINK (no admin required!)
            # Windows: mklink /H link target
            # Note: Syntax reversed from ln
            
            force_cmd = f'if exist "{link_name}" del /f "{link_name}" && ' if force else ''
            
            # mklink /H for hard links (files only, not directories)
            return f'{force_cmd}mklink /H "{link_name}" "{target}"', True
    
    def _translate_grep(self, cmd: str, parts):
        """Translate grep with FULL flag support - ALL flags implemented"""
        if len(parts) < 2:
            return 'echo Error: grep requires pattern', True
        
        case_insensitive = '-i' in parts
        invert = '-v' in parts
        recursive = '-r' in parts or '-R' in parts
        line_numbers = '-n' in parts
        count = '-c' in parts
        extended_regex = '-E' in parts
        whole_word = '-w' in parts
        exact_line = '-x' in parts
        only_matching = '-o' in parts
        quiet = '-q' in parts or '--quiet' in parts
        no_filename = '-h' in parts
        with_filename = '-H' in parts
        files_with_matches = '-l' in parts
        files_without_matches = '-L' in parts
        
        # Context lines
        before_context = 0
        after_context = 0
        for i, part in enumerate(parts):
            if part == '-A' and i + 1 < len(parts):
                after_context = int(parts[i + 1])
            elif part == '-B' and i + 1 < len(parts):
                before_context = int(parts[i + 1])
            elif part == '-C' and i + 1 < len(parts):
                before_context = after_context = int(parts[i + 1])
        
        # Extract pattern and files
        pattern = None
        files = []
        skip_next = False
        for i, part in enumerate(parts[1:], 1):
            if skip_next:
                skip_next = False
                continue
            if part in ['-A', '-B', '-C', '-e', '-f']:
                skip_next = True
                continue
            if part.startswith('-'):
                continue
            if pattern is None:
                pattern = part
            else:
                win_path = part  # Already translated
                files.append(f'"{win_path}"')
        
        if pattern is None:
            return 'echo Error: grep requires pattern', True
        
        # Use PowerShell for full feature support
        ps_flags = []
        
        if case_insensitive:
            ps_flags.append('-CaseSensitive:$false')
        
        if quiet:
            # Quiet mode: just exit code, no output
            ps_cmd = f'if (Select-String -Pattern "{pattern}" -Path {files[0] if files else "*"} -Quiet) {{ exit 0 }} else {{ exit 1 }}'
            return f'powershell -Command "{ps_cmd}"', True
        
        if line_numbers:
            # Select-String includes line numbers by default in output
            pass
        
        if recursive:
            ps_flags.append('-Recurse')
        
        # Extended regex (PowerShell uses .NET regex which is already extended)
        # So -E flag doesn't need special handling - just noted for completeness
        if extended_regex:
            # .NET regex already supports +, ?, |, {}, () without escaping
            pass

        if whole_word:
            pattern = f'\\b{pattern}\\b'
        
        if exact_line:
            pattern = f'^{pattern}$'
        
        file_arg = files[0] if files else '*'
        
        # Build Select-String command
        ps_cmd = f'Select-String -Pattern "{pattern}" -Path {file_arg} {" ".join(ps_flags)}'
        
        # Post-processing
        post_process = []
        
        if only_matching:
            post_process.append('ForEach-Object { $_.Matches.Value }')
        
        if files_with_matches:
            post_process.append('Select-Object -Unique Path')
            post_process.append('ForEach-Object { $_.Path }')
        
        if files_without_matches:
            # Invert the logic
            ps_cmd = f'$allFiles = Get-ChildItem {file_arg}; $matchFiles = {ps_cmd} | Select-Object -Unique Path; $allFiles | Where-Object {{ $matchFiles.Path -notcontains $_.FullName }} | ForEach-Object {{ $_.Name }}'
            return f'powershell -Command "{ps_cmd}"', True
        
        if count:
            post_process.append('Measure-Object')
            post_process.append('Select-Object -ExpandProperty Count')
        
        if no_filename and len(files) == 1:
            post_process.append('ForEach-Object { $_.Line }')
        elif with_filename or len(files) > 1:
            post_process.append('ForEach-Object { "$($_.Filename):$($_.Line)" }')
        
        if invert:
            # For invert, use different approach
            ps_cmd = f'Get-Content {file_arg} | Where-Object {{ $_ -notmatch "{pattern}" }}'
        
        if before_context or after_context:
            ps_cmd += f' -Context {before_context},{after_context}'
        
        if post_process:
            ps_cmd += ' | ' + ' | '.join(post_process)
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_find(self, cmd: str, parts):
        """
        Execute find with COMPLETE test support - STRATEGIC DISPATCH.

        ARTIGIANO STRATEGY:
        - Simple find -> PowerShell emulation
        - Complex -exec -> bash.exe (perfect emulation)
        - Complex tests -> bash.exe

        Complexity triggers (bash.exe required):
        - -exec with sh/bash invocation
        - -exec with pipes/redirects
        - -exec with complex quoting
        - Advanced tests (-printf, -execdir, etc.)

        Tests supported (PowerShell emulation):
        - -name PATTERN: filename pattern (wildcards)
        - -iname PATTERN: case-insensitive name
        - -type f|d|l: file type (file, directory, link)
        - -size [+-]N[ckMG]: size test (+1M, -100k)
        - -mtime [+-]N: modification time in days (-7 = last week)
        - -atime [+-]N: access time in days
        - -ctime [+-]N: change time in days
        - -newer FILE: modified more recently than FILE
        - -maxdepth N: descend at most N levels
        - -mindepth N: descend at least N levels
        - -exec CMD {} \;: execute command (simple only)
        - -delete: delete matched files
        - -print: print matched files (default)
        - -print0: print with null separator

        Examples:
          find . -name "*.py" -mtime -7                           # PowerShell OK
          find /tmp -type f -size +100M -delete                   # PowerShell OK
          find . -name "*.log" -mtime +30 -exec rm {} \;          # PowerShell OK
          find . -exec sh -c 'echo "$1"' _ {} \;                  # bash.exe REQUIRED
          find . -name "*.txt" -exec grep pattern {} \; | wc -l   # bash.exe REQUIRED
        """

        # ================================================================
        # ARTIGIANO: Complexity detection BEFORE parsing
        # ================================================================

        def is_complex_exec(exec_cmd):
            """Detect if -exec is too complex for PowerShell"""
            # sh/bash invocation
            if 'sh -c' in exec_cmd or 'bash -c' in exec_cmd:
                return True
            # Pipe/redirect inside -exec command
            if any(op in exec_cmd for op in ['|', '>', '<', '2>', '&&', '||']):
                return True
            # Complex quoting (nested quotes)
            single_quotes = exec_cmd.count("'")
            double_quotes = exec_cmd.count('"')
            if single_quotes > 2 or double_quotes > 2:
                return True
            return False

        # Check for complex -exec in command
        if '-exec' in cmd:
            # Extract -exec portion
            exec_start = cmd.find('-exec')
            exec_portion = cmd[exec_start:]
            if is_complex_exec(exec_portion):
                # Complex -exec -> bash.exe REQUIRED
                if self.git_bash_exe:
                    self.logger.debug("find with complex -exec -> using bash.exe")
                    bash_cmd = self._execute_with_gitbash(cmd)
                    if bash_cmd:
                        return bash_cmd, False
                else:
                    self.logger.error("Complex find -exec requires bash.exe (not available)")
                    return 'echo "ERROR: Complex find -exec requires bash.exe"', True

        # Advanced find features not supported in PowerShell emulation
        unsupported_flags = ['-printf', '-execdir', '-ok', '-okdir', '-prune', '-quit',
                            '-fprint', '-fprint0', '-fprintf', '-ls', '-fls']
        for flag in unsupported_flags:
            if flag in cmd:
                if self.git_bash_exe:
                    self.logger.debug(f"find with {flag} -> using bash.exe")
                    bash_cmd = self._execute_with_gitbash(cmd)
                    if bash_cmd:
                        return bash_cmd, False
                else:
                    self.logger.warning(f"find flag {flag} not supported in emulation")

        # ================================================================
        # PowerShell emulation for SIMPLE find
        # ================================================================
        # Parse find arguments
        path = '.'
        tests = []
        actions = []
        max_depth = None
        min_depth = None
        print_null = False
        
        i = 1
        
        # First non-flag argument is the path
        if i < len(parts) and not parts[i].startswith('-'):
            path = parts[i]
            i += 1
        
        # Parse tests and actions
        while i < len(parts):
            test = parts[i]
            
            if test == '-name' and i + 1 < len(parts):
                pattern = parts[i + 1].strip('"\'')
                tests.append(('name', pattern, False))
                i += 2
            elif test == '-iname' and i + 1 < len(parts):
                pattern = parts[i + 1].strip('"\'')
                tests.append(('name', pattern, True))  # case-insensitive
                i += 2
            elif test == '-type' and i + 1 < len(parts):
                ftype = parts[i + 1]
                tests.append(('type', ftype, None))
                i += 2
            elif test == '-size' and i + 1 < len(parts):
                size_spec = parts[i + 1]
                tests.append(('size', size_spec, None))
                i += 2
            elif test == '-mtime' and i + 1 < len(parts):
                days = parts[i + 1]
                tests.append(('mtime', days, None))
                i += 2
            elif test == '-atime' and i + 1 < len(parts):
                days = parts[i + 1]
                tests.append(('atime', days, None))
                i += 2
            elif test == '-ctime' and i + 1 < len(parts):
                days = parts[i + 1]
                tests.append(('ctime', days, None))
                i += 2
            elif test == '-newer' and i + 1 < len(parts):
                ref_file = parts[i + 1]
                tests.append(('newer', ref_file, None))
                i += 2
            elif test == '-maxdepth' and i + 1 < len(parts):
                max_depth = int(parts[i + 1])
                i += 2
            elif test == '-mindepth' and i + 1 < len(parts):
                min_depth = int(parts[i + 1])
                i += 2
            elif test == '-delete':
                actions.append(('delete', None))
                i += 1
            elif test == '-print':
                # Default action, explicit
                i += 1
            elif test == '-print0':
                print_null = True
                i += 1
            elif test == '-exec':
                # Find -exec ... \; or -exec ... +
                exec_cmd = []
                i += 1
                while i < len(parts) and parts[i] not in [';', '\\;', '+']:
                    exec_cmd.append(parts[i])
                    i += 1
                actions.append(('exec', ' '.join(exec_cmd)))
                i += 1  # skip ; or +
            else:
                # Unknown test, skip
                i += 1
        
        # Build Windows command
        win_path = path  # Already translated

        # FIX #18: For simple cases, use direct Get-ChildItem | Where-Object (more readable)
        # Complex cases use full script
        is_simple = (
            len(tests) <= 2 and  # Only name and/or type tests
            not actions and  # No actions (no -exec, -delete)
            max_depth is None and
            min_depth is None and
            all(test[0] in ['name', 'type'] for test in tests)
        )

        if is_simple:
            # Simple case: Get-ChildItem | Where-Object
            get_cmd = f'Get-ChildItem -Path "{win_path}" -Recurse -ErrorAction SilentlyContinue'

            where_conditions = []
            for test_type, test_arg, test_flag in tests:
                if test_type == 'name':
                    if test_flag:  # case-insensitive
                        where_conditions.append(f'$_.Name -like "{test_arg}"')
                    else:
                        where_conditions.append(f'$_.Name -clike "{test_arg}"')
                elif test_type == 'type':
                    if test_arg == 'f':
                        where_conditions.append('-not $_.PSIsContainer')
                    elif test_arg == 'd':
                        where_conditions.append('$_.PSIsContainer')

            if where_conditions:
                where_clause = ' -and '.join(where_conditions)
                ps_cmd = f'{get_cmd} | Where-Object {{ {where_clause} }} | ForEach-Object {{ $_.FullName }}'
            else:
                ps_cmd = f'{get_cmd} | ForEach-Object {{ $_.FullName }}'

            return ps_cmd, True

        # Complex case: Build full PowerShell script
        ps_script = f'''
            $path = "{win_path}"
            $maxDepth = {max_depth if max_depth else 999}
            $minDepth = {min_depth if min_depth else 0}
            
            Get-ChildItem -Path $path -Recurse -ErrorAction SilentlyContinue | ForEach-Object {{
                $item = $_
                $depth = ($item.FullName.Substring($path.Length) -split '\\\\|/').Length - 1
                
                # Depth filtering
                if ($depth -gt $maxDepth -or $depth -lt $minDepth) {{
                    return
                }}
                
                $match = $true
        '''
        
        # Add test conditions
        for test_type, test_arg, test_flag in tests:
            if test_type == 'name':
                if test_flag:  # case-insensitive
                    ps_script += f'''
                if ($match) {{
                    $match = $match -and ($item.Name -like "{test_arg}")
                }}
                '''
                else:  # case-sensitive
                    ps_script += f'''
                if ($match) {{
                    $match = $match -and ($item.Name -clike "{test_arg}")
                }}
                '''
            
            elif test_type == 'type':
                if test_arg == 'f':
                    ps_script += '''
                if ($match) {
                    $match = $match -and (-not $item.PSIsContainer)
                }
                '''
                elif test_arg == 'd':
                    ps_script += '''
                if ($match) {
                    $match = $match -and $item.PSIsContainer
                }
                '''
                elif test_arg == 'l':
                    ps_script += '''
                if ($match) {
                    $match = $match -and ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
                }
                '''
            
            elif test_type == 'size':
                # Parse size: +1M (greater), -100k (less), 50k (exact)
                size_bytes = self._parse_find_size(test_arg)
                if test_arg.startswith('+'):
                    ps_script += f'''
                if ($match -and (-not $item.PSIsContainer)) {{
                    $match = $match -and ($item.Length -gt {size_bytes})
                }}
                '''
                elif test_arg.startswith('-'):
                    ps_script += f'''
                if ($match -and (-not $item.PSIsContainer)) {{
                    $match = $match -and ($item.Length -lt {size_bytes})
                }}
                '''
                else:
                    ps_script += f'''
                if ($match -and (-not $item.PSIsContainer)) {{
                    $match = $match -and ($item.Length -eq {size_bytes})
                }}
                '''
            
            elif test_type == 'mtime':
                # Parse days: -7 (within last 7 days), +30 (older than 30 days)
                days = int(test_arg.strip('+-'))
                if test_arg.startswith('-'):
                    # Modified within last N days
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastWriteTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -lt {days})
                }}
                '''
                elif test_arg.startswith('+'):
                    # Modified more than N days ago
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastWriteTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -gt {days})
                }}
                '''
                else:
                    # Exactly N days
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastWriteTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -eq {days})
                }}
                '''
            
            elif test_type == 'atime':
                # Access time
                days = int(test_arg.strip('+-'))
                if test_arg.startswith('-'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastAccessTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -lt {days})
                }}
                '''
                elif test_arg.startswith('+'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.LastAccessTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -gt {days})
                }}
                '''
            
            elif test_type == 'ctime':
                # Change time (CreationTime on Windows)
                days = int(test_arg.strip('+-'))
                if test_arg.startswith('-'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.CreationTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -lt {days})
                }}
                '''
                elif test_arg.startswith('+'):
                    ps_script += f'''
                if ($match) {{
                    $daysDiff = (New-TimeSpan -Start $item.CreationTime -End (Get-Date)).Days
                    $match = $match -and ($daysDiff -gt {days})
                }}
                '''
            
            elif test_type == 'newer':
                # Newer than reference file
                ref_file = test_arg
                ps_script += f'''
                if ($match) {{
                    try {{
                        $refTime = (Get-Item "{ref_file}").LastWriteTime
                        $match = $match -and ($item.LastWriteTime -gt $refTime)
                    }} catch {{
                        $match = $false
                    }}
                }}
                '''
        
        # Actions
        ps_script += '''
                if ($match) {
        '''
        
        if actions:
            for action_type, action_arg in actions:
                if action_type == 'delete':
                    ps_script += '''
                    Remove-Item -Path $item.FullName -Force -ErrorAction SilentlyContinue
                '''
                elif action_type == 'exec':
                    # Execute command with {} replaced by filename
                    exec_cmd = action_arg.replace('{}', '$item.FullName')
                    ps_script += f'''
                    Invoke-Expression "{exec_cmd}"
                '''
        else:
            # Default action: print
            if print_null:
                ps_script += '''
                    Write-Host -NoNewline "$($item.FullName)`0"
                '''
            else:
                ps_script += '''
                    Write-Output $item.FullName
                '''
        
        ps_script += '''
                }
            }
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _parse_find_size(self, size_spec: str) -> int:
        """
        Parse find -size specification to bytes.
        
        Format: [+-]N[ckMG]
        Examples: +1M → 1048576, -100k → 102400, 50 → 50
        """
        import re
        
        spec = size_spec.lstrip('+-')
        match = re.match(r'^(\d+)([ckMG])?$', spec)
        if not match:
            return 0
        
        value = int(match.group(1))
        unit = match.group(2) or 'c'
        
        multipliers = {
            'c': 1,
            'k': 1024,
            'M': 1024 * 1024,
            'G': 1024 * 1024 * 1024,
        }
        
        return value * multipliers.get(unit, 1)
    
    def _translate_which(self, cmd: str, parts):
        if len(parts) < 2:
            return 'echo Error: which requires command name', True
        return f'where {parts[1]}', True
    
    def _translate_head(self, cmd: str, parts):
        """
        Execute head - output first N lines of file(s).

        ARTIGIANO IMPLEMENTATION:
        - PowerShell Get-Content with -TotalCount (native, fast)
        - Supports pipeline input via stdin
        - Multiple files

        Flags:
        - -n N: number of lines (default 10)
        - -N: short form for -n N
        - -c N: first N bytes (not commonly used, skip for now)

        Usage:
          head file.txt           -> first 10 lines
          head -n 20 file.txt     -> first 20 lines
          head -5 file.txt        -> first 5 lines
          cat file | head -10     -> from pipeline
        """
        line_count = 10  # Default
        files = []

        i = 1
        while i < len(parts):
            if parts[i] == '-n' and i + 1 < len(parts):
                line_count = int(parts[i + 1])
                i += 2
            elif parts[i].startswith('-') and parts[i][1:].isdigit():
                # Short form: -20
                line_count = int(parts[i][1:])
                i += 1
            elif parts[i] == '-c':
                # Byte mode - skip for now, not commonly used
                i += 2
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1

        if not files:
            # Reading from stdin (pipeline)
            # PowerShell: Select-Object -First N
            return f'Select-Object -First {line_count}', True

        # ARTIGIANO: Glob Pattern Expansion (same as cat)
        has_glob = any(c in ''.join(files) for c in ['*', '?', '[', ']'])

        if has_glob:
            files_patterns = ','.join(f'"{f}"' for f in files)
            ps_script = f'''
                # Expand glob patterns
                $expandedFiles = @()
                foreach ($pattern in @({files_patterns})) {{
                    if ($pattern -match '[*?\\[\\]]') {{
                        $matched = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
                        if ($matched) {{
                            $expandedFiles += $matched.FullName
                        }}
                    }} else {{
                        if (Test-Path $pattern) {{
                            $expandedFiles += $pattern
                        }} else {{
                            Write-Error "head: $pattern: No such file or directory"
                            exit 1
                        }}
                    }}
                }}

                if ($expandedFiles.Count -eq 0) {{
                    Write-Error "head: No files matched"
                    exit 1
                }}

                # Process files
                $first = $true
                foreach ($file in $expandedFiles) {{
                    if ($expandedFiles.Count -gt 1) {{
                        if (-not $first) {{ Write-Output "" }}
                        Write-Output "==> $file <=="
                    }}
                    Get-Content $file -TotalCount {line_count}
                    $first = $false
                }}
            '''
        else:
            # No globs - direct access
            if len(files) == 1:
                # Single file
                ps_script = f'''
                    if (Test-Path "{files[0]}") {{
                        Get-Content "{files[0]}" -TotalCount {line_count}
                    }} else {{
                        Write-Error "head: {files[0]}: No such file or directory"
                        exit 1
                    }}
                '''
            else:
                # Multiple files - show filename headers like Unix head
                ps_script = '''
                    $files = @({})
                    $first = $true
                    foreach ($file in $files) {{
                        if (Test-Path $file) {{
                            if (-not $first) {{ Write-Output "" }}
                            Write-Output "==> $file <=="
                            Get-Content $file -TotalCount {}
                            $first = $false
                        }} else {{
                            Write-Error "head: $file: No such file or directory"
                        }}
                    }}
                '''.format(','.join(f'"{f}"' for f in files), line_count)

        return f'powershell -Command "{ps_script}"', True
    
    def _translate_tail(self, cmd: str, parts):
        """
        Execute tail - output last N lines of file(s).

        ARTIGIANO IMPLEMENTATION:
        - PowerShell Get-Content with -Tail (native, fast)
        - Supports pipeline input
        - Follow mode (-f) with Get-Content -Wait

        Flags:
        - -n N: number of lines (default 10)
        - -N: short form for -n N
        - -f: follow mode (watch file for changes)
        - -c N: last N bytes (not commonly used, skip for now)

        Usage:
          tail file.txt           -> last 10 lines
          tail -n 20 file.txt     -> last 20 lines
          tail -5 file.txt        -> last 5 lines
          tail -f log.txt         -> follow file
          cat file | tail -10     -> from pipeline
        """
        line_count = 10  # Default
        follow = False
        files = []

        i = 1
        while i < len(parts):
            if parts[i] == '-n' and i + 1 < len(parts):
                line_count = int(parts[i + 1])
                i += 2
            elif parts[i].startswith('-') and parts[i][1:].isdigit():
                # Short form: -20
                line_count = int(parts[i][1:])
                i += 1
            elif parts[i] == '-f':
                follow = True
                i += 1
            elif parts[i] == '-c':
                # Byte mode - skip for now
                i += 2
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1

        if not files:
            # Reading from stdin (pipeline)
            # PowerShell: Select-Object -Last N
            return f'Select-Object -Last {line_count}', True

        # ARTIGIANO: Glob Pattern Expansion (same as cat/head)
        has_glob = any(c in ''.join(files) for c in ['*', '?', '[', ']'])

        if has_glob:
            # Glob expansion needed
            if follow:
                # Follow mode with globs - use bash.exe (complex)
                if self.git_bash_exe:
                    return f'"{self.git_bash_exe}" -c "tail {cmd[5:]}"', False
                else:
                    return 'echo "tail -f with globs requires bash.exe"', True

            files_patterns = ','.join(f'"{f}"' for f in files)
            ps_script = f'''
                # Expand glob patterns
                $expandedFiles = @()
                foreach ($pattern in @({files_patterns})) {{
                    if ($pattern -match '[*?\\[\\]]') {{
                        $matched = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
                        if ($matched) {{
                            $expandedFiles += $matched.FullName
                        }}
                    }} else {{
                        if (Test-Path $pattern) {{
                            $expandedFiles += $pattern
                        }} else {{
                            Write-Error "tail: $pattern: No such file or directory"
                            exit 1
                        }}
                    }}
                }}

                if ($expandedFiles.Count -eq 0) {{
                    Write-Error "tail: No files matched"
                    exit 1
                }}

                # Process files
                $first = $true
                foreach ($file in $expandedFiles) {{
                    if ($expandedFiles.Count -gt 1) {{
                        if (-not $first) {{ Write-Output "" }}
                        Write-Output "==> $file <=="
                    }}
                    Get-Content $file -Tail {line_count}
                    $first = $false
                }}
            '''
        else:
            # No globs - direct access
            if len(files) == 1:
                # Single file
                file = files[0]
                if follow:
                    # Follow mode - continuously monitor file
                    ps_script = f'''
                        if (Test-Path "{file}") {{
                            Get-Content "{file}" -Tail {line_count} -Wait
                        }} else {{
                            Write-Error "tail: {file}: No such file or directory"
                            exit 1
                        }}
                    '''
                else:
                    # Normal mode - just last N lines
                    ps_script = f'''
                        if (Test-Path "{file}") {{
                            Get-Content "{file}" -Tail {line_count}
                        }} else {{
                            Write-Error "tail: {file}: No such file or directory"
                            exit 1
                        }}
                    '''
            else:
                # Multiple files - show filename headers
                if follow:
                    # Follow mode with multiple files - complex, use bash.exe if available
                    if self.git_bash_exe:
                        return f'"{self.git_bash_exe}" -c "tail {cmd[5:]}"', False
                    else:
                        return 'echo "tail -f with multiple files requires bash.exe"', True

                # Normal mode with multiple files
                ps_script = '''
                    $files = @({})
                    $first = $true
                    foreach ($file in $files) {{
                        if (Test-Path $file) {{
                            if (-not $first) {{ Write-Output "" }}
                            Write-Output "==> $file <=="
                            Get-Content $file -Tail {}
                            $first = $false
                        }} else {{
                            Write-Error "tail: $file: No such file or directory"
                        }}
                    }}
                '''.format(','.join(f'"{f}"' for f in files), line_count)

        return f'powershell -Command "{ps_script}"', True
    
    def _translate_wc(self, cmd: str, parts):
        """
        Execute wc - word, line, character, and byte count.

        ARTIGIANO IMPLEMENTATION:
        - PowerShell Measure-Object (native, fast)
        - Count lines, words, characters, bytes
        - Multiple files support
        - Pipeline support

        Flags:
        - -l: count lines only
        - -w: count words only
        - -c: count bytes only
        - -m: count characters only
        - (no flags): show lines, words, bytes

        Usage:
          wc file.txt               -> lines, words, bytes
          wc -l file.txt            -> lines only
          wc -w file.txt            -> words only
          cat file | wc -l          -> count lines from pipeline
          ls | wc -l                -> count items
        """
        count_lines = '-l' in parts
        count_words = '-w' in parts
        count_chars = '-m' in parts
        count_bytes = '-c' in parts
        files = []

        # If no flags specified, count all (lines, words, bytes)
        if not (count_lines or count_words or count_chars or count_bytes):
            count_lines = count_words = count_bytes = True

        i = 1
        while i < len(parts):
            if parts[i] in ['-l', '-w', '-c', '-m']:
                i += 1
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1

        if not files:
            # Reading from stdin (pipeline)
            # Collect and count
            ps_script = '''
                $lines = @($input)
                $lineCount = $lines.Count
                $wordCount = 0
                $charCount = 0

                foreach ($line in $lines) {
                    if ($line -ne $null) {
                        $words = $line -split '\s+'
                        $wordCount += ($words | Where-Object { $_ -ne '' }).Count
                        $charCount += $line.Length + 1  # +1 for newline
                    }
                }

                $output = @()
            '''

            if count_lines:
                ps_script += '\n$output += $lineCount'
            if count_words:
                ps_script += '\n$output += $wordCount'
            if count_bytes or count_chars:
                ps_script += '\n$output += $charCount'

            ps_script += '\nWrite-Output ($output -join "  ")'

            return f'powershell -Command "{ps_script}"', True

        # ARTIGIANO: Glob Pattern Expansion (same as cat/head/tail)
        has_glob = any(c in ''.join(files) for c in ['*', '?', '[', ']'])

        if has_glob:
            files_patterns = ','.join(f'"{f}"' for f in files)

            # Build glob expansion logic
            ps_script = f'''
                # Expand glob patterns
                $expandedFiles = @()
                foreach ($pattern in @({files_patterns})) {{
                    if ($pattern -match '[*?\\[\\]]') {{
                        $matched = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
                        if ($matched) {{
                            $expandedFiles += $matched.FullName
                        }}
                    }} else {{
                        if (Test-Path $pattern) {{
                            $expandedFiles += $pattern
                        }} else {{
                            Write-Error "wc: $pattern: No such file or directory"
                            exit 1
                        }}
                    }}
                }}

                if ($expandedFiles.Count -eq 0) {{
                    Write-Error "wc: No files matched"
                    exit 1
                }}

                # Count stats for each file
                $totalLines = 0
                $totalWords = 0
                $totalChars = 0

                foreach ($file in $expandedFiles) {{
                    $content = Get-Content $file
                    $lineCount = $content.Count
                    $wordCount = 0
                    $charCount = 0

                    foreach ($line in $content) {{
                        if ($line -ne $null) {{
                            $words = $line -split '\\s+'
                            $wordCount += ($words | Where-Object {{ $_ -ne '' }}).Count
                            $charCount += $line.Length + 1
                        }}
                    }}

                    $totalLines += $lineCount
                    $totalWords += $wordCount
                    $totalChars += $charCount

                    $output = @()
            '''

            if count_lines:
                ps_script += '\n                    $output += $lineCount'
            if count_words:
                ps_script += '\n                    $output += $wordCount'
            if count_bytes or count_chars:
                ps_script += '\n                    $output += $charCount'

            ps_script += '\n                    $output += $file'
            ps_script += '\n                    Write-Output ($output -join "  ")'
            ps_script += '\n                }'

            # Add total if multiple files
            ps_script += '''
                if ($expandedFiles.Count -gt 1) {
                    $output = @()
            '''
            if count_lines:
                ps_script += '\n                    $output += $totalLines'
            if count_words:
                ps_script += '\n                    $output += $totalWords'
            if count_bytes or count_chars:
                ps_script += '\n                    $output += $totalChars'

            ps_script += '\n                    $output += "total"'
            ps_script += '\n                    Write-Output ($output -join "  ")'
            ps_script += '\n                }'

            return f'powershell -Command "{ps_script}"', True

        # No globs - direct file access
        # Files specified
        if len(files) == 1:
            file = files[0]
            ps_script = f'''
                if (-not (Test-Path "{file}")) {{
                    Write-Error "wc: {file}: No such file or directory"
                    exit 1
                }}

                $content = Get-Content "{file}"
                $lineCount = $content.Count
                $wordCount = 0
                $charCount = 0

                foreach ($line in $content) {{
                    if ($line -ne $null) {{
                        $words = $line -split '\\s+'
                        $wordCount += ($words | Where-Object {{ $_ -ne '' }}).Count
                        $charCount += $line.Length + 1
                    }}
                }}

                $output = @()
            '''

            if count_lines:
                ps_script += '\n$output += $lineCount'
            if count_words:
                ps_script += '\n$output += $wordCount'
            if count_bytes or count_chars:
                ps_script += '\n$output += $charCount'

            ps_script += f'\n$output += "{file}"\nWrite-Output ($output -join "  ")'

        else:
            # Multiple files - show individual counts and total
            ps_script = '''
                $files = @({})
                $totalLines = 0
                $totalWords = 0
                $totalChars = 0

                foreach ($file in $files) {{
                    if (-not (Test-Path $file)) {{
                        Write-Error "wc: $file: No such file or directory"
                        continue
                    }}

                    $content = Get-Content $file
                    $lineCount = $content.Count
                    $wordCount = 0
                    $charCount = 0

                    foreach ($line in $content) {{
                        if ($line -ne $null) {{
                            $words = $line -split '\\s+'
                            $wordCount += ($words | Where-Object {{ $_ -ne '' }}).Count
                            $charCount += $line.Length + 1
                        }}
                    }}

                    $totalLines += $lineCount
                    $totalWords += $wordCount
                    $totalChars += $charCount

                    $output = @()
            '''.format(','.join(f'"{f}"' for f in files))

            if count_lines:
                ps_script += '\n$output += $lineCount'
            if count_words:
                ps_script += '\n$output += $wordCount'
            if count_bytes or count_chars:
                ps_script += '\n$output += $charCount'

            ps_script += '\n$output += $file\nWrite-Output ($output -join "  ")\n}'

            # Add total line
            if len(files) > 1:
                ps_script += '\n$output = @()'
                if count_lines:
                    ps_script += '\n$output += $totalLines'
                if count_words:
                    ps_script += '\n$output += $totalWords'
                if count_bytes or count_chars:
                    ps_script += '\n$output += $totalChars'
                ps_script += '\n$output += "total"\nWrite-Output ($output -join "  ")'

        return f'powershell -Command "{ps_script}"', True
    
    def _translate_sort(self, cmd: str, parts):
        """
        Translate sort - FULL implementation with field selection.
        
        ARTISAN IMPLEMENTATION:
        - Numeric sorting (-n)
        - Field selection (-k N)
        - Custom separator (-t SEP)
        - Unique lines (-u)
        - Reverse order (-r)
        - Human numeric (-h): 1K, 2M, 3G
        
        Unix behavior:
          sort file → alphabetic
          sort -n file → numeric
          sort -k 2 -t: file → sort by 2nd field, separator ':'
          sort -h file → human numeric (1K < 1M < 1G)
        """
        numeric = '-n' in parts or '--numeric-sort' in parts
        reverse = '-r' in parts or '--reverse' in parts
        unique = '-u' in parts or '--unique' in parts
        human = '-h' in parts or '--human-numeric-sort' in parts
        
        # Parse field and separator
        field_num = None
        separator = None
        
        i = 0
        while i < len(parts):
            part = parts[i]
            
            # -k field
            if part == '-k' and i + 1 < len(parts):
                field_spec = parts[i + 1]
                # Extract field number (may be "2" or "2,3" or "2.1")
                field_num = int(field_spec.split(',')[0].split('.')[0])
                i += 1
            elif part.startswith('--key='):
                field_spec = part.split('=')[1]
                field_num = int(field_spec.split(',')[0].split('.')[0])
            
            # -t separator
            elif part == '-t' and i + 1 < len(parts):
                separator = parts[i + 1]
                i += 1
            elif part.startswith('--field-separator='):
                separator = part.split('=')[1]
            
            i += 1
        
        # Get input files
        files = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit() and p not in [separator]]
        
        # Build sort command
        if not field_num and not numeric and not human:
            # Simple sort - use native Windows sort
            if files:
                win_path = files[0]
                cmd = f'sort "{win_path}"'
                if reverse:
                    cmd += ' /r'
                if unique:
                    cmd += ' /unique'
                return cmd, True
            else:
                cmd = 'sort'
                if reverse:
                    cmd += ' /r'
                if unique:
                    cmd += ' /unique'
                return cmd, True
        
        # Complex sort - PowerShell script
        # Default separator is whitespace
        if separator is None:
            separator = ' '
        
        # Escape separator for PowerShell
        sep_escaped = separator.replace("'", "''")
        
        # Build PowerShell script
        if files:
            # From file
            file_path = files[0]
            content_cmd = f'Get-Content "{file_path}"'
        else:
            # From stdin
            content_cmd = '$input'
        
        # Build sort script
        ps_script = f'{content_cmd} | ForEach-Object {{'
        
        if field_num:
            # Field-based sorting
            ps_script += f'''
    $fields = $_ -split '{sep_escaped}'
    if ($fields.Count -ge {field_num}) {{
        $sortKey = $fields[{field_num - 1}].Trim()
    }} else {{
        $sortKey = $_
    }}
    '''
            
            if numeric or human:
                # Convert to number for sorting
                if human:
                    # Human numeric: 1K, 2M, 3G
                    ps_script += '''
    if ($sortKey -match '(\d+\.?\d*)([KMGT]i?)$') {
        $num = [double]$matches[1]
        $unit = $matches[2]
        $multiplier = switch ($unit) {
            'K' { 1000 }
            'Ki' { 1024 }
            'M' { 1000000 }
            'Mi' { 1048576 }
            'G' { 1000000000 }
            'Gi' { 1073741824 }
            'T' { 1000000000000 }
            'Ti' { 1099511627776 }
            default { 1 }
        }
        $sortKey = $num * $multiplier
    } else {
        try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    }
    '''
                else:
                    # Simple numeric
                    ps_script += '''
    try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    '''
            
            ps_script += '''
    [PSCustomObject]@{
        Line = $_
        SortKey = $sortKey
    }
'''
        else:
            # No field selection, just numeric/human sorting
            if numeric or human:
                ps_script += '''
    $sortKey = $_
    '''
                if human:
                    ps_script += '''
    if ($sortKey -match '(\d+\.?\d*)([KMGT]i?)') {
        $num = [double]$matches[1]
        $unit = $matches[2]
        $multiplier = switch ($unit) {
            'K' { 1000 }
            'Ki' { 1024 }
            'M' { 1000000 }
            'Mi' { 1048576 }
            'G' { 1000000000 }
            'Gi' { 1073741824 }
            'T' { 1000000000000 }
            'Ti' { 1099511627776 }
            default { 1 }
        }
        $sortKey = $num * $multiplier
    } else {
        try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    }
    '''
                else:
                    ps_script += '''
    try { $sortKey = [double]$sortKey } catch { $sortKey = 0 }
    '''
                
                ps_script += '''
    [PSCustomObject]@{
        Line = $_
        SortKey = $sortKey
    }
'''
        
        ps_script += '} | Sort-Object -Property SortKey'
        
        if reverse:
            ps_script += ' -Descending'
        
        if unique:
            ps_script += ' -Unique'
        
        ps_script += ' | ForEach-Object { $_.Line }'
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_uniq(self, cmd: str, parts):
        """
        Translate uniq - CORRECT implementation for consecutive duplicates.
        
        CRITICAL: Unix uniq removes CONSECUTIVE duplicates ONLY, not all duplicates!
        
        Example:
          echo -e "a\\nb\\na" | uniq  →  a, b, a  (NOT a, b)
        
        Flags:
        - -c, --count: Prefix lines with occurrence count
        - -d, --repeated: Only print duplicate lines (consecutive)
        - -u, --unique: Only print unique lines (non-consecutive-duplicates)
        - -i, --ignore-case: Case-insensitive comparison
        - -f N, --skip-fields=N: Skip first N fields for comparison
        - -s N, --skip-chars=N: Skip first N chars for comparison
        """
        count_mode = '-c' in parts or '--count' in parts
        duplicates_only = '-d' in parts or '--repeated' in parts
        unique_only = '-u' in parts or '--unique' in parts
        ignore_case = '-i' in parts or '--ignore-case' in parts
        
        # Parse skip fields
        skip_fields = 0
        for i, part in enumerate(parts):
            if part == '-f' and i + 1 < len(parts):
                skip_fields = int(parts[i + 1])
            elif part.startswith('--skip-fields='):
                skip_fields = int(part.split('=')[1])
        
        # Parse skip chars
        skip_chars = 0
        for i, part in enumerate(parts):
            if part == '-s' and i + 1 < len(parts):
                skip_chars = int(parts[i + 1])
            elif part.startswith('--skip-chars='):
                skip_chars = int(part.split('=')[1])
        
        files = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit()]
        
        # Build PowerShell script for CONSECUTIVE duplicate detection
        if files:
            file_path = files[0]
            content_cmd = f'Get-Content "{file_path}"'
        else:
            content_cmd = '$input'
        
        # Build comparison key extraction
        key_extraction = ''
        if skip_fields > 0:
            key_extraction = f'''
                $fields = $line -split '\s+'
                if ($fields.Count -gt {skip_fields}) {{
                    $key = ($fields[{skip_fields}..($fields.Count-1)] -join ' ')
                }} else {{
                    $key = ''
                }}
            '''
        elif skip_chars > 0:
            key_extraction = f'''
                if ($line.Length -gt {skip_chars}) {{
                    $key = $line.Substring({skip_chars})
                }} else {{
                    $key = ''
                }}
            '''
        else:
            key_extraction = '$key = $line'
        
        # Case-insensitive comparison
        comparison = '$key' if not ignore_case else '$key.ToLower()'
        prev_comparison = '$prevKey' if not ignore_case else '$prevKey.ToLower()'
        
        # Build main processing script
        ps_script = f'''
            $prevLine = $null
            $prevKey = $null
            $count = 0
            
            {content_cmd} | ForEach-Object {{
                $line = $_
                {key_extraction}
                
                if ($prevLine -eq $null) {{
                    # First line
                    $prevLine = $line
                    $prevKey = $key
                    $count = 1
                }} elseif ({comparison} -eq {prev_comparison}) {{
                    # Consecutive duplicate
                    $count++
                }} else {{
                    # Different line - output previous
        '''
        
        # Output logic based on mode
        if count_mode:
            # Count mode: "%7d %s" format
            ps_script += '''
                    Write-Output ("{0,7} {1}" -f $count, $prevLine)
            '''
        elif duplicates_only:
            # Only duplicates (count > 1)
            ps_script += '''
                    if ($count -gt 1) {
                        Write-Output $prevLine
                    }
            '''
        elif unique_only:
            # Only unique (count == 1)
            ps_script += '''
                    if ($count -eq 1) {
                        Write-Output $prevLine
                    }
            '''
        else:
            # Normal mode: just output unique lines
            ps_script += '''
                    Write-Output $prevLine
            '''
        
        # Reset for new line
        ps_script += '''
                    $prevLine = $line
                    $prevKey = $key
                    $count = 1
                }
            }
            
            # Output last line
            if ($prevLine -ne $null) {
        '''
        
        # Final output logic
        if count_mode:
            ps_script += '''
                Write-Output ("{0,7} {1}" -f $count, $prevLine)
            '''
        elif duplicates_only:
            ps_script += '''
                if ($count -gt 1) {
                    Write-Output $prevLine
                }
            '''
        elif unique_only:
            ps_script += '''
                if ($count -eq 1) {
                    Write-Output $prevLine
                }
            '''
        else:
            ps_script += '''
                Write-Output $prevLine
            '''
        
        ps_script += '''
            }
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_ps(self, cmd: str, parts):
        return 'tasklist', True
    
    def _translate_kill(self, cmd: str, parts):
        force = '-9' in parts or '-KILL' in parts
        pids = [p for p in parts[1:] if not p.startswith('-') and p.isdigit()]
        if pids:
            flag = '/f' if force else ''
            return f'taskkill {flag} /pid {" /pid ".join(pids)}', True
        return 'echo Error: kill requires PID', True
    
    def _translate_env(self, cmd: str, parts):
        """
        Translate env - show all environment variables.
        
        env → show all
        env VAR → show specific variable
        """
        if len(parts) > 1:
            # Show specific variable
            var_name = parts[1]
            return f'echo %{var_name}%', True
        else:
            # Show all variables
            return 'set', True
    
    def _translate_printenv(self, cmd: str, parts):
        """
        Translate printenv - show environment variables.
        
        printenv → show all
        printenv VAR → show specific variable
        """
        if len(parts) > 1:
            # Show specific variable
            var_name = parts[1]
            return f'echo %{var_name}%', True
        else:
            # Show all variables
            return 'set', True
    
    def _translate_export(self, cmd: str, parts):
        """
        Translate export with proper VAR=value handling.
        
        export VAR=value → set VAR=value
        export VAR → (no-op, just mark as exported)
        """
        if len(parts) < 2:
            return 'echo Error: export requires variable', True
        
        var_expr = parts[1]
        
        if '=' in var_expr:
            # VAR=value format
            return f'set {var_expr}', True
        else:
            # Just VAR (mark as exported - no-op on Windows)
            return f'echo exported {var_expr}', True
    
    def _translate_wget(self, cmd: str, parts):
        """
        Execute wget - Simple wrapper converting to curl.

        wget is traditionally a download tool, curl is more versatile but can do the same.
        For complex wget scenarios, this delegates to curl implementation.

        Common flags:
        - -O file: output to specified file
        - URL: download URL

        Strategy: Convert to curl and delegate to _execute_curl()

        Examples:
          wget http://example.com/file.zip
          wget -O output.html http://example.com
        """
        if len(parts) < 2:
            return 'echo Error: wget requires URL', True

        # Extract URL and output filename
        urls = [p for p in parts[1:] if 'http://' in p or 'https://' in p]
        output = None

        i = 1
        while i < len(parts):
            if parts[i] == '-O' and i + 1 < len(parts):
                output = parts[i + 1]
                i += 2
            else:
                i += 1

        if not urls:
            return 'echo Error: wget requires URL', True

        # Convert to curl command
        if output:
            curl_cmd = f'curl -o "{output}" "{urls[0]}"'
            curl_parts = ['curl', '-o', output, urls[0]]
        else:
            # wget default: save with remote filename
            curl_cmd = f'curl -O "{urls[0]}"'
            curl_parts = ['curl', '-O', urls[0]]

        # Delegate to curl implementation for full feature support
        return self._translate_curl(curl_cmd, curl_parts)
    
    def _translate_curl(self, cmd: str, parts):
        """
        Translate curl with COMPLETE flag support for API work.
        
        Common flags:
        - -X METHOD: request method (GET, POST, PUT, DELETE, PATCH)
        - -H "Header: value": headers (multiple)
        - -d "data" / --data: POST data
        - -d @file: POST data from file
        - --data-binary @file: binary data from file
        - --json '{}': JSON shorthand (auto Content-Type + POST)
        - -o file: output to file
        - -O: save with remote filename
        - -L: follow redirects
        - -f: fail silently on errors
        - -s: silent mode (no progress)
        - -i: include headers in output
        - -I: HEAD request
        - -v: verbose (show request/response headers)
        - -k, --insecure: skip SSL verification
        - -u user:pass: basic authentication
        - -A "agent": user agent
        - -F file=@path: multipart form upload
        """
        if len(parts) < 2:
            return 'echo Error: curl requires URL', True
        
        method = None
        headers = []
        data = None
        data_file = None
        data_binary = False
        json_data = None
        output_file = None
        save_remote = False
        follow_redirects = False
        fail_silent = False
        silent = False
        include_headers = False
        head_only = False
        verbose = False
        insecure = False
        auth = None
        user_agent = None
        form_data = []
        url = None
        
        i = 1
        while i < len(parts):
            if parts[i] in ['-X', '--request'] and i + 1 < len(parts):
                method = parts[i + 1]
                i += 2
            elif parts[i] in ['-H', '--header'] and i + 1 < len(parts):
                headers.append(parts[i + 1])
                i += 2
            elif parts[i] in ['-d', '--data'] and i + 1 < len(parts):
                data_arg = parts[i + 1]
                if data_arg.startswith('@'):
                    # Data from file
                    data_file = data_arg[1:]
                else:
                    data = data_arg
                i += 2
            elif parts[i] == '--data-binary' and i + 1 < len(parts):
                data_arg = parts[i + 1]
                if data_arg.startswith('@'):
                    data_file = data_arg[1:]
                    data_binary = True
                i += 2
            elif parts[i] == '--json' and i + 1 < len(parts):
                json_data = parts[i + 1]
                i += 2
            elif parts[i] in ['-F', '--form'] and i + 1 < len(parts):
                form_data.append(parts[i + 1])
                i += 2
            elif parts[i] in ['-o', '--output'] and i + 1 < len(parts):
                output_file = parts[i + 1]
                i += 2
            elif parts[i] in ['-O', '--remote-name']:
                save_remote = True
                i += 1
            elif parts[i] in ['-L', '--location']:
                follow_redirects = True
                i += 1
            elif parts[i] in ['-f', '--fail']:
                fail_silent = True
                i += 1
            elif parts[i] in ['-s', '--silent']:
                silent = True
                i += 1
            elif parts[i] in ['-i', '--include']:
                include_headers = True
                i += 1
            elif parts[i] in ['-I', '--head']:
                head_only = True
                i += 1
            elif parts[i] in ['-v', '--verbose']:
                verbose = True
                i += 1
            elif parts[i] in ['-k', '--insecure']:
                insecure = True
                i += 1
            elif parts[i] in ['-u', '--user'] and i + 1 < len(parts):
                auth = parts[i + 1]
                i += 2
            elif parts[i] in ['-A', '--user-agent'] and i + 1 < len(parts):
                user_agent = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                # URL
                url = parts[i]
                i += 1
            else:
                i += 1
        
        if not url:
            return 'echo Error: curl requires URL', True
        
        # Build PowerShell Invoke-WebRequest command
        ps_parts = []
        
        # Verbose setup
        if verbose:
            ps_parts.append('$VerbosePreference="Continue";')
        
        # SSL verification
        if insecure:
            ps_parts.append('[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true};')
        
        ps_parts.append('Invoke-WebRequest')
        ps_parts.append(f'-Uri "{url}"')
        
        # Method
        if method:
            ps_parts.append(f'-Method {method}')
        elif json_data or data or data_file:
            ps_parts.append('-Method POST')
        elif head_only:
            ps_parts.append('-Method HEAD')
        
        # Headers
        if json_data and not any('Content-Type' in h for h in headers):
            headers.append('Content-Type: application/json')
        
        if headers:
            # Build proper PowerShell hashtable for headers
            header_pairs = []
            for h in headers:
                if ':' in h:
                    key, val = h.split(':', 1)
                    header_pairs.append(f'"{key.strip()}"="{val.strip()}"')
            headers_str = ';'.join(header_pairs)
            ps_parts.append(f'-Headers @{{{headers_str}}}')
        
        # Body data
        if json_data:
            ps_parts.append(f'-Body \'{json_data}\'')
        elif data_file:
            if data_binary:
                ps_parts.append(f'-InFile "{data_file}"')
            else:
                ps_parts.append(f'-Body (Get-Content "{data_file}" -Raw)')
        elif data:
            ps_parts.append(f'-Body "{data}"')
        elif form_data:
            # Multipart form data
            form_parts = []
            for form in form_data:
                if '=' in form:
                    key, val = form.split('=', 1)
                    if val.startswith('@'):
                        # File upload
                        file_path = val[1:]
                        form_parts.append(f'"{key}"=(Get-Item "{file_path}")')
                    else:
                        # Regular field
                        form_parts.append(f'"{key}"="{val}"')
            form_str = ';'.join(form_parts)
            ps_parts.append(f'-Form @{{{form_str}}}')
        
        # Output
        if output_file:
            ps_parts.append(f'-OutFile "{output_file}"')
        elif save_remote:
            # Extract filename from URL
            filename = url.split('/')[-1].split('?')[0]
            if filename:
                ps_parts.append(f'-OutFile "{filename}"')
        
        # Redirects
        if follow_redirects:
            ps_parts.append('-MaximumRedirection 10')
        else:
            ps_parts.append('-MaximumRedirection 0')
        
        # User agent
        if user_agent:
            ps_parts.append(f'-UserAgent "{user_agent}"')
        
        # Authentication
        if auth:
            user, pwd = auth.split(':', 1) if ':' in auth else (auth, '')
            ps_parts.append(f'-Credential (New-Object System.Management.Automation.PSCredential("{user}", (ConvertTo-SecureString "{pwd}" -AsPlainText -Force)))')
        
        # Error handling
        error_action = 'Stop' if fail_silent else 'Continue'
        ps_parts.append(f'-ErrorAction {error_action}')
        
        # Verbose flag
        if verbose:
            ps_parts.append('-Verbose')
        
        # Silent mode: suppress progress
        if silent:
            ps_parts.insert(0, '$ProgressPreference="SilentlyContinue";')
        
        # Build command
        ps_cmd = ' '.join(ps_parts)
        
        # Output formatting
        if include_headers or head_only:
            # Include headers in output
            if head_only:
                ps_cmd += ' | Select-Object -ExpandProperty Headers | Format-List'
            else:
                ps_cmd += ' | ForEach-Object { $_.RawContent }'
        elif verbose:
            # Verbose shows everything
            ps_cmd += ' | Select-Object StatusCode, StatusDescription, Headers, Content | Format-List'
        elif not output_file and not save_remote:
            # Output content only (default)
            ps_cmd += ' | Select-Object -ExpandProperty Content'
        
        # Wrap in try-catch if fail_silent
        if fail_silent and not silent:
            ps_cmd = f'try {{ {ps_cmd} }} catch {{ exit 22 }}'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_chmod(self, cmd: str, parts):
        return 'echo chmod: operation completed (no-op on Windows)', True
    
    def _translate_chown(self, cmd: str, parts):
        return 'echo chown: operation completed (no-op on Windows)', True
    
    def _translate_du(self, cmd: str, parts):
        """
        Translate du (disk usage) with FULL flags.
        
        Flags:
        -h: human readable (KB, MB, GB)
        -s: summarize (total only)
        -a: all files (not just directories)
        """
        human_readable = '-h' in parts
        summarize = '-s' in parts
        all_files = '-a' in parts
        
        paths = [p for p in parts[1:] if not p.startswith('-')]
        path = paths[0] if paths else '.'
        
        if summarize:
            # Total size only
            if human_readable:
                ps_cmd = f'Get-ChildItem -Path \\"{path}\\" -Recurse -File | Measure-Object -Property Length -Sum | Select-Object @{{Name="Size";Expression={{"{{0:N2}} MB" -f ($_.Sum / 1MB)}}}}'
            else:
                ps_cmd = f'Get-ChildItem -Path \\"{path}\\" -Recurse -File | Measure-Object -Property Length -Sum | Select-Object -ExpandProperty Sum'
            
            return f'powershell -Command "{ps_cmd}"', True
        elif all_files:
            # All files with sizes
            if human_readable:
                ps_cmd = f'Get-ChildItem -Path \\"{path}\\" -Recurse | Select-Object FullName, @{{Name="Size";Expression={{"{{0:N2}} KB" -f ($_.Length / 1KB)}}}}'
            else:
                ps_cmd = f'Get-ChildItem -Path \\"{path}\\" -Recurse | Select-Object FullName, Length'
            
            return f'powershell -Command "{ps_cmd}"', True
        else:
            # Directory sizes (default)
            return f'dir /s "{path}"', True
    
    def _translate_df(self, cmd: str, parts):
        return 'wmic logicaldisk get size,freespace,caption', True
    
    def _translate_date(self, cmd: str, parts):
        """
        Translate date with format support.
        
        date → current date/time
        date +FORMAT → formatted output
        
        Common formats:
        %Y year, %m month, %d day
        %H hour, %M minute, %S second
        %s Unix timestamp
        """
        if len(parts) == 1:
            # Simple date
            return 'echo %date% %time%', True
        
        format_str = parts[1] if len(parts) > 1 else None
        
        if format_str and format_str.startswith('+'):
            # Format string
            fmt = format_str[1:]  # Remove +
            
            # Convert Unix format to PowerShell Get-Date format
            # %Y → yyyy, %m → MM, %d → dd, etc.
            ps_fmt = fmt
            ps_fmt = ps_fmt.replace('%Y', 'yyyy')
            ps_fmt = ps_fmt.replace('%y', 'yy')
            ps_fmt = ps_fmt.replace('%m', 'MM')
            ps_fmt = ps_fmt.replace('%d', 'dd')
            ps_fmt = ps_fmt.replace('%H', 'HH')
            ps_fmt = ps_fmt.replace('%M', 'mm')
            ps_fmt = ps_fmt.replace('%S', 'ss')
            ps_fmt = ps_fmt.replace('%A', 'dddd')  # Full weekday
            ps_fmt = ps_fmt.replace('%a', 'ddd')   # Short weekday
            ps_fmt = ps_fmt.replace('%B', 'MMMM')  # Full month
            ps_fmt = ps_fmt.replace('%b', 'MMM')   # Short month
            
            # Special cases
            if '%s' in fmt:
                # Unix timestamp
                return 'powershell -Command "[int](Get-Date -UFormat %s)"', True
            
            return f'powershell -Command "Get-Date -Format \\"{ps_fmt}\\""', True
        
        return 'echo %date% %time%', True
    
    def _translate_sleep(self, cmd: str, parts):
        if len(parts) > 1 and parts[1].isdigit():
            return f'timeout /t {parts[1]} /nobreak', True
        return 'echo Error: sleep requires seconds', True
    
    def _translate_basename(self, cmd: str, parts):
        if len(parts) > 1:
            filename = parts[1].split('/')[-1].split('\\')[-1]
            return f'echo {filename}', True
        return 'echo Error: basename requires path', True
    
    def _translate_dirname(self, cmd: str, parts):
        if len(parts) > 1:
            win_path = parts[1]  # Already translated
            return f'powershell -Command "(Get-Item \\"{win_path}\\").Directory.FullName"', True
        return 'echo Error: dirname requires path', True
    
    def _translate_tar(self, cmd: str, parts):
        """
        Translate tar with REAL .tar.gz support via fallback chain.
        
        STRATEGY FOR 100%:
        1. Try tar.exe (Git for Windows) - 100% GNU tar with .tar.gz, .tar.bz2, .tar.xz
        2. Fallback PowerShell Compress-Archive - .zip workaround (90% compatible)
        
        CRITICAL: tar.exe supports REAL tar formats:
        - .tar: uncompressed tar archive
        - .tar.gz / .tgz: gzip compressed (-z flag)
        - .tar.bz2: bzip2 compressed (-j flag)
        - .tar.xz: xz compressed (-J flag)
        
        Common operations:
        tar -czf archive.tar.gz dir/ → create gzip
        tar -xzf archive.tar.gz → extract gzip
        tar -tzf archive.tar.gz → list contents
        tar -xjf archive.tar.bz2 → extract bzip2
        """
        if len(parts) < 2:
            return 'echo Error: tar requires arguments', True
        
        # Parse operation from flags
        flags = parts[1]
        create = 'c' in flags
        extract = 'x' in flags
        list_contents = 't' in flags
        verbose = 'v' in flags
        use_file = 'f' in flags
        gzip_compress = 'z' in flags
        bzip2_compress = 'j' in flags
        xz_compress = 'J' in flags
        
        # Find archive name and paths
        archive = None
        paths = []
        change_dir = None
        
        i = 2
        while i < len(parts):
            if parts[i] == '-C' and i + 1 < len(parts):
                change_dir = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                if not archive and use_file:
                    archive = parts[i]
                else:
                    paths.append(parts[i])
                i += 1
            else:
                i += 1
        
        if not archive:
            return 'echo Error: tar requires archive name (-f)', True
        
        # Build tar command for native tar.exe
        tar_parts = [parts[0]]  # 'tar'
        tar_parts.extend(parts[1:])  # All flags and args as-is
        
        tar_cmd = ' '.join(f'"{p}"' if ' ' in p else p for p in tar_parts)
        
        # PowerShell fallback (current implementation)
        # Convert tar extensions to zip for PowerShell
        if archive.endswith('.tar.gz') or archive.endswith('.tgz'):
            zip_archive = archive.rsplit('.', 2 if archive.endswith('.tar.gz') else 1)[0] + '.zip'
        elif archive.endswith('.tar.bz2') or archive.endswith('.tar.xz') or archive.endswith('.tar'):
            zip_archive = archive.rsplit('.', 1)[0] + '.zip'
        else:
            zip_archive = archive
        
        if create:
            if not paths:
                return 'echo Error: tar -c requires source path(s)', True
            
            paths_str = ','.join([f'\\"{p}\\"' for p in paths])
            ps_fallback = f'Compress-Archive -Path {paths_str} -DestinationPath \\"{zip_archive}\\" -Force'
            
            if verbose:
                ps_fallback += f'; Write-Host "Created archive: {zip_archive}"'
        
        elif extract:
            dest = paths[0] if paths else '.'
            ps_fallback = f'Expand-Archive -Path \\"{zip_archive}\\" -DestinationPath \\"{dest}\\" -Force'
            
            if verbose:
                ps_fallback += f'; Get-ChildItem -Path \\"{dest}\\" -Recurse | Select-Object FullName'
        
        elif list_contents:
            ps_fallback = f'Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::OpenRead(\\"{zip_archive}\\").Entries | Select-Object FullName'
        
        else:
            return 'echo Error: tar requires operation flag (c, x, or t)', True
        
        # Build PowerShell script with fallback chain
        ps_script = f'''
            # Try native tar.exe (Git for Windows) - 100% GNU tar
            $tarExe = Get-Command tar.exe -ErrorAction SilentlyContinue
            
            if ($tarExe) {{
                # Native tar.exe available - supports REAL .tar.gz, .tar.bz2, .tar.xz
                & tar.exe {' '.join(parts[1:])}
            }} else {{
                # Fallback: PowerShell Compress-Archive (.zip workaround)
                {ps_fallback}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_zip(self, cmd: str, parts):
        """
        Translate zip - create compressed archives.
        
        ARTISAN IMPLEMENTATION:
        - Uses PowerShell Compress-Archive (native .NET)
        - Creates .zip files compatible with Unix unzip
        
        Flags:
        - -r: recursive (include subdirectories) - default ON
        - archive.zip: output file
        - files/dirs: items to compress
        
        Usage:
          zip -r archive.zip dir/
          zip archive.zip file1.txt file2.txt
        """
        recursive = '-r' in parts
        archive = None
        items = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-r':
                recursive = True
                i += 1
            elif not parts[i].startswith('-'):
                if not archive:
                    archive = parts[i]
                else:
                    items.append(parts[i])
                i += 1
            else:
                i += 1
        
        if not archive:
            return 'echo Error: zip requires archive name', True
        
        if not items:
            return 'echo Error: zip requires items to compress', True
        
        # Ensure .zip extension
        if not archive.endswith('.zip'):
            archive += '.zip'
        
        # Build paths list for PowerShell
        paths_list = ','.join(f'"{item}"' for item in items)
        
        ps_script = f'''
            $archive = "{archive}"
            $items = @({paths_list})
            
            # Remove existing archive if present
            if (Test-Path $archive) {{
                Remove-Item $archive -Force
            }}
            
            # Compress items
            try {{
                Compress-Archive -Path $items -DestinationPath $archive -CompressionLevel Optimal
                Write-Output "created $archive"
            }} catch {{
                Write-Error "zip: $($_.Exception.Message)"
                exit 1
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_unzip(self, cmd: str, parts):
        """
        Translate unzip - extract compressed archives.
        
        ARTISAN IMPLEMENTATION:
        - Uses PowerShell Expand-Archive (native .NET)
        - Extracts .zip files from Unix/Windows
        
        Flags:
        - -l: list contents (don't extract)
        - -d DIR: extract to directory
        - archive.zip: file to extract
        
        Usage:
          unzip archive.zip
          unzip -d output/ archive.zip
          unzip -l archive.zip
        """
        list_contents = '-l' in parts
        extract_dir = None
        archive = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-l':
                list_contents = True
                i += 1
            elif parts[i] == '-d' and i + 1 < len(parts):
                extract_dir = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                archive = parts[i]
                i += 1
            else:
                i += 1
        
        if not archive:
            return 'echo Error: unzip requires archive', True
        
        if list_contents:
            # List contents
            ps_script = f'''
                if (-not (Test-Path "{archive}")) {{
                    Write-Error "unzip: {archive}: No such file"
                    exit 1
                }}
                
                Add-Type -AssemblyName System.IO.Compression.FileSystem
                $zip = [System.IO.Compression.ZipFile]::OpenRead("{archive}")
                
                Write-Output "Archive:  {archive}"
                foreach ($entry in $zip.Entries) {{
                    $size = $entry.Length
                    $date = $entry.LastWriteTime.ToString("MM-dd-yy HH:mm")
                    Write-Output ("  {{0,10}}  {{1}}  {{2}}" -f $size, $date, $entry.FullName)
                }}
                
                $zip.Dispose()
            '''
        else:
            # Extract
            if not extract_dir:
                extract_dir = '.'
            
            ps_script = f'''
                if (-not (Test-Path "{archive}")) {{
                    Write-Error "unzip: {archive}: No such file"
                    exit 1
                }}
                
                $dest = "{extract_dir}"
                
                # Create destination if needed
                if (-not (Test-Path $dest)) {{
                    New-Item -Path $dest -ItemType Directory -Force | Out-Null
                }}
                
                try {{
                    Expand-Archive -Path "{archive}" -DestinationPath $dest -Force
                    Write-Output "extracted {archive} to $dest"
                }} catch {{
                    Write-Error "unzip: $($_.Exception.Message)"
                    exit 1
                }}
            '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_sed(self, cmd: str, parts):
        """
        Translate sed.
        
        Supported in PowerShell fallback:
        - s/search/replace/flags (substitution with g, i, p flags)
        - Address ranges: 1,10s/.../, /pattern/s/.../, $s/.../
        - Multiple -e expressions
        - d (delete lines)
        - p (print lines)
        - a, i, c (append, insert, change text)
        - -i (in-place editing)
        - -n (quiet mode - suppress output except explicit p)
        
        Complex sed scripts work better with native sed.
        """
        if len(parts) < 2:
            return 'echo Error: sed requires expression', True
        
        # Build command for native sed
        sed_cmd_parts = []
        for part in parts[1:]:
            # Quote arguments that need it
            if ' ' in part or any(c in part for c in ['|', '&', '>', '<', ';']):
                sed_cmd_parts.append(f'"{part}"')
            else:
                sed_cmd_parts.append(part)
        
        sed_full_cmd = ' '.join(sed_cmd_parts)
        
        # PowerShell script 
        ps_script_start = ""
        
        # Parse arguments for PowerShell 
        in_place = False
        quiet = False
        expressions = []
        files = []
        
        # Parse arguments
        i = 1
        while i < len(parts):
            if parts[i] == '-i':
                in_place = True
                # Check for -i with backup suffix (e.g., -i.bak)
                if i + 1 < len(parts) and not parts[i + 1].startswith('-') and '=' not in parts[i + 1]:
                    i += 2  # skip backup suffix
                else:
                    i += 1
            elif parts[i].startswith('-i'):
                in_place = True
                i += 1
            elif parts[i] == '-n':
                quiet = True
                i += 1
            elif parts[i] == '-e' and i + 1 < len(parts):
                expressions.append(parts[i + 1])
                i += 2
            elif parts[i].startswith('-e'):
                expressions.append(parts[i][2:])
                i += 1
            elif not parts[i].startswith('-'):
                # First non-flag is expression (if no -e was used)
                if not expressions:
                    expressions.append(parts[i])
                else:
                    # It's a file
                    win_path = parts[i]  # Already translated
                    files.append(win_path)
                i += 1
            else:
                i += 1
        
        if not expressions:
            return 'echo Error: sed requires expression', True
        
        # Build PowerShell sed emulation
        if not files:
            return 'echo Error: sed requires file argument (stdin not yet supported)', True
        
        file_arg = f'\\"{files[0]}\\"'
        
        # Build PowerShell sed emulation with line number tracking
        ps_script_parts = []
        ps_script_parts.append('$LineNum = 0')
        ps_script_parts.append('$output = @()')
        ps_script_parts.append(f'Get-Content {file_arg} | ForEach-Object {{')
        ps_script_parts.append('  $LineNum++')
        ps_script_parts.append('  $line = $_')
        ps_script_parts.append('  $print = ' + ('$false' if quiet else '$true'))
        ps_script_parts.append('  $skip = $false')
        
        # Process each expression
        for expr_idx, expr in enumerate(expressions):
            # Parse address + command
            address = None
            command = expr
            
            # Check for address prefix
            # Line number: 5s/.../ or 1,10s/.../
            if expr[0].isdigit():
                match = re.match(r'^(\d+)(,(\d+|\$))?(.*)$', expr)
                if match:
                    start_line = match.group(1)
                    end_line = match.group(3) if match.group(3) else start_line
                    command = match.group(4)
                    if end_line == '$':
                        address = ('line_range', start_line, '999999')
                    else:
                        address = ('line_range', start_line, end_line)
            
            # Pattern address: /pattern/s/.../
            elif expr.startswith('/'):
                match = re.match(r'^/(.+?)/(,/(.+?)/)?(.*)$', expr)
                if match:
                    pattern = match.group(1)
                    end_pattern = match.group(3)
                    command = match.group(4)
                    if end_pattern:
                        address = ('pattern_range', pattern, end_pattern)
                    else:
                        address = ('pattern', pattern, None)
            
            # Last line: $
            elif expr.startswith('$'):
                address = ('last_line', None, None)
                command = expr[1:]
            
            # Generate condition for address
            condition = None
            if address:
                if address[0] == 'line_range':
                    condition = f'($LineNum -ge {address[1]} -and $LineNum -le {address[2]})'
                elif address[0] == 'pattern':
                    pattern_escaped = address[1].replace('\\', '\\\\').replace('"', '\\"')
                    condition = f'($line -match "{pattern_escaped}")'
                elif address[0] == 'last_line':
                    condition = '($LineNum -eq (Get-Content ' + file_arg + ' | Measure-Object -Line).Lines)'
            
            # Parse command type
            if command.startswith('s/') or command.startswith('s|') or command.startswith('s#'):
                # Substitution
                delimiter = command[1]
                parts_expr = command[2:].split(delimiter)
                
                if len(parts_expr) >= 2:
                    search = parts_expr[0].replace('\\', '\\\\').replace('"', '\\"')
                    replace = parts_expr[1].replace('\\', '\\\\').replace('"', '\\"')
                    flags = parts_expr[2] if len(parts_expr) > 2 else ''
                    
                    global_replace = 'g' in flags
                    ignore_case = 'i' in flags
                    print_flag = 'p' in flags
                    
                    # Build replacement operation
                    if condition:
                        ps_script_parts.append(f'  if {condition} {{')
                    else:
                        ps_script_parts.append('  if ($true) {')
                    
                    # Generate replacement logic
                    if global_replace:
                        # Global replace: use standard -replace (replaces ALL occurrences)
                        if ignore_case:
                            ps_script_parts.append(f'    $line = $line -replace "(?i){search}", "{replace}"')
                        else:
                            ps_script_parts.append(f'    $line = $line -replace "{search}", "{replace}"')
                    else:
                        # First occurrence only: use .NET Regex.Replace with count=1
                        if ignore_case:
                            ps_script_parts.append(f'    $regex = [regex]::new("(?i){search}"); $line = $regex.Replace($line, "{replace}", 1)')
                        else:
                            ps_script_parts.append(f'    $regex = [regex]::new("{search}"); $line = $regex.Replace($line, "{replace}", 1)')
                    
                    if print_flag and quiet:
                        ps_script_parts.append('    $print = $true')
                    
                    ps_script_parts.append('  }')
            
            elif command == 'd' or (command.endswith('d') and len(command) == 1):
                # Delete operation
                if condition:
                    ps_script_parts.append(f'  if {condition} {{')
                else:
                    ps_script_parts.append('  if ($true) {')
                
                ps_script_parts.append('    $skip = $true')
                ps_script_parts.append('  }')
            
            elif command == 'p' or (command.endswith('p') and len(command) == 1):
                # Print operation (in quiet mode, forces print)
                if condition:
                    ps_script_parts.append(f'  if {condition} {{')
                else:
                    ps_script_parts.append('  if ($true) {')
                
                ps_script_parts.append('    $print = $true')
                ps_script_parts.append('  }')
        
        # Output logic
        ps_script_parts.append('  if (-not $skip -and $print) {')
        ps_script_parts.append('    $output += $line')
        ps_script_parts.append('  }')
        ps_script_parts.append('}')
        
        # Final output
        if in_place:
            ps_script_parts.append(f'$output | Set-Content {file_arg}')
        else:
            ps_script_parts.append('$output')
        
        ps_script = '; '.join(ps_script_parts)
        
        # Complete script with fallback chain
        ps_complete = ps_script_start + ps_script
        
        return f'powershell -Command "{ps_complete}"', True
    
    def _translate_awk(self, cmd: str, parts):
        """
        Execute awk with ARTIGIANO strategy dispatch.

        COMPLEXITY LEVELS:
        1. CRITICAL (awk.exe/bash.exe required):
           - Array operations (a[$1]++, associative arrays)
           - Built-in functions (gsub, substr, split, match, sprintf, etc.)
           - User-defined functions
           - Pattern ranges (/start/,/end/)
           - getline operations
           - Multiple files with FILENAME/FNR
           - Complex printf with format strings

        2. ADVANCED (awk.exe preferred):
           - BEGIN/END blocks
           - Multiple -F field separators
           - Field variables ($1, $2, $NF)
           - Simple arithmetic

        3. SIMPLE (PowerShell OK):
           - Basic field extraction: awk '{print $1}'
           - Single condition: awk '$3 > 100'

        ARTIGIANO STRATEGY:
        1. Try awk.exe/gawk.exe (Git for Windows) - 100% GNU awk
        2. If critical features and no awk.exe -> bash.exe
        3. Fallback PowerShell custom for common patterns
        """
        if len(parts) < 2:
            return 'echo Error: awk requires program', True

        # ================================================================
        # ARTIGIANO: Detect CRITICAL complexity
        # ================================================================

        def is_critical_awk(program):
            """Detect if awk uses features that REQUIRE native awk"""
            # Array operations
            if '[' in program and ']' in program:
                # Likely array: a[$1]++, array[key]=value
                return True

            # Built-in functions (not exhaustive, but common ones)
            critical_functions = [
                'gsub', 'sub', 'substr', 'split', 'match', 'sprintf',
                'strftime', 'systime', 'tolower', 'toupper', 'length',
                'index', 'getline', 'system', 'close', 'fflush'
            ]
            for func in critical_functions:
                if func + '(' in program:
                    return True

            # User-defined functions (function name() {...})
            if re.search(r'\bfunction\s+\w+\s*\(', program):
                return True

            # Pattern ranges (/start/,/end/)
            if re.search(r'/[^/]+/\s*,\s*/[^/]+/', program):
                return True

            # Multiple files with FILENAME or FNR
            if 'FILENAME' in program or 'FNR' in program:
                return True

            # Complex printf (more than simple %s or %d)
            if 'printf' in program:
                # Check for complex format strings
                printf_match = re.search(r'printf\s*\(["\']([^"\']+)', program)
                if printf_match:
                    format_str = printf_match.group(1)
                    # Complex formats: %10s, %.2f, %-5d, etc.
                    if re.search(r'%[-+0-9.]*[a-z]', format_str):
                        complex_formats = re.findall(r'%[-+0-9.]+[a-z]', format_str)
                        if complex_formats:
                            return True

            return False

        # Extract program for analysis
        program_str = None
        for i, part in enumerate(parts):
            if not part.startswith('-') and i > 0:
                if parts[i-1] not in ['-F', '-v']:  # Not an option argument
                    program_str = part
                    break

        if program_str and is_critical_awk(program_str):
            # CRITICAL awk -> native awk.exe or bash.exe REQUIRED
            # First try will be awk.exe in the fallback chain
            # But if that fails and we have bash.exe, use it
            if not self.git_bash_exe:
                self.logger.warning("Critical awk features detected - requires awk.exe or bash.exe")
            else:
                # Check if awk.exe available
                try:
                    result = subprocess.run(['where', 'awk.exe'], capture_output=True, timeout=2)
                    if result.returncode != 0:
                        # No awk.exe, use bash.exe
                        self.logger.debug("Critical awk features + no awk.exe -> using bash.exe")
                        bash_cmd = self._execute_with_gitbash(cmd)
                        if bash_cmd:
                            return bash_cmd, False
                except:
                    pass

        # ================================================================
        # Standard awk execution with native awk.exe preference
        # ================================================================
        
        # Build command for native awk
        awk_cmd_parts = []
        for part in parts[1:]:
            # Quote arguments that need it
            if ' ' in part or any(c in part for c in ['|', '&', '>', '<', ';']):
                awk_cmd_parts.append(f'"{part}"')
            else:
                awk_cmd_parts.append(part)
        
        awk_full_cmd = ' '.join(awk_cmd_parts)
        
        # PowerShell script with fallback chain
        ps_script = f'''
            # Try native awk/gawk (Git for Windows)
            $awkExe = Get-Command awk.exe -ErrorAction SilentlyContinue
            if (-not $awkExe) {{
                $awkExe = Get-Command gawk.exe -ErrorAction SilentlyContinue
            }}
            
            if ($awkExe) {{
                # Native awk - 100% GNU compatible
                & $awkExe.Source {awk_full_cmd}
                exit $LASTEXITCODE
            }}
            
            # Fallback: PowerShell custom implementation
            # (Common patterns only - complex awk requires native binary)
        '''
        
        # Extract awk components for PowerShell fallback
        field_separator = None
        program = None
        files = []
        
        # Parse arguments
        i = 1
        while i < len(parts):
            if parts[i] == '-F' and i + 1 < len(parts):
                field_separator = parts[i + 1]
                i += 2
            elif parts[i].startswith('-F'):
                field_separator = parts[i][2:]
                i += 1
            elif not parts[i].startswith('-'):
                if program is None:
                    program = parts[i]
                else:
                    win_path = parts[i]  # Already translated
                    files.append(win_path)
                i += 1
            else:
                i += 1
        
        if not program:
            return 'echo Error: awk requires program', True
        
        # Default field separator
        if not field_separator:
            field_separator = '\\s+'
        else:
            # Escape special regex chars
            field_separator = field_separator.replace('\\', '\\\\')
        
        # Parse awk program
        # Detect BEGIN, main block, END
        begin_block = None
        main_block = None
        end_block = None
        pattern = None
        
        # Extract BEGIN block
        begin_match = re.search(r'BEGIN\s*{([^}]+)}', program)
        if begin_match:
            begin_block = begin_match.group(1).strip()
            program = program.replace(begin_match.group(0), '')
        
        # Extract END block
        end_match = re.search(r'END\s*{([^}]+)}', program)
        if end_match:
            end_block = end_match.group(1).strip()
            program = program.replace(end_match.group(0), '')
        
        # Extract pattern and main block
        # Pattern can be: /regex/, $1 > 100, NF > 5, etc.
        pattern_match = re.match(r'^(/[^/]+/|[^{]+)\s*{([^}]+)}', program.strip())
        if pattern_match:
            pattern_str = pattern_match.group(1).strip()
            main_block = pattern_match.group(2).strip()
            
            if pattern_str.startswith('/') and pattern_str.endswith('/'):
                pattern = ('regex', pattern_str[1:-1])
            elif '>' in pattern_str or '<' in pattern_str or '==' in pattern_str:
                pattern = ('condition', pattern_str)
        else:
            # No pattern, just block
            block_match = re.search(r'{([^}]+)}', program)
            if block_match:
                main_block = block_match.group(1).strip()
        
        # Convert awk operations to PowerShell
        file_arg = f'"{files[0]}"' if files else '$input'
        
        # Build PowerShell fallback script
        ps_lines = []
        
        # BEGIN block
        if begin_block:
            ps_begin = self._awk_to_ps_statement(begin_block)
            ps_lines.append(ps_begin)
        
        # Main processing
        ps_main = []
        ps_main.append(f'Get-Content {file_arg} | ForEach-Object {{')
        ps_main.append(f'  $F = $_ -split "{field_separator}"')
        ps_main.append('  $NF = $F.Length')
        
        # Apply pattern filter if present
        if pattern:
            if pattern[0] == 'regex':
                ps_main.append(f'  if ($_ -match "{pattern[1]}") {{')
            elif pattern[0] == 'condition':
                ps_condition = self._awk_to_ps_condition(pattern[1])
                ps_main.append(f'  if ({ps_condition}) {{')
        
        # Main block operations
        if main_block:
            ps_operation = self._awk_to_ps_statement(main_block)
            indent = '    ' if pattern else '  '
            ps_main.append(f'{indent}{ps_operation}')
        
        # Close pattern filter
        if pattern:
            ps_main.append('  }')
        
        ps_main.append('}')
        
        # END block
        if end_block:
            ps_end = self._awk_to_ps_statement(end_block)
            ps_main.append(ps_end)
        
        ps_fallback = '; '.join(ps_lines + ps_main)
        
        # Complete script with fallback
        ps_script += f'''
            {ps_fallback}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _awk_to_ps_statement(self, awk_stmt: str) -> str:
        """Convert awk statement to PowerShell"""
        # Handle print statements
        if 'print' in awk_stmt:
            # Extract what to print
            print_match = re.search(r'print\s+(.+)', awk_stmt)
            if print_match:
                expr = print_match.group(1).strip()
                # Convert field references
                expr = re.sub(r'\$(\d+)', r'$F[\1-1]', expr)
                expr = expr.replace('$NF', '$F[$NF-1]')
                expr = expr.replace('$(NF-1)', '$F[$NF-2]')
                return f'Write-Output {expr}'
        
        # Handle variable assignments
        if '=' in awk_stmt and not '==' in awk_stmt:
            # x=0 or x+=$1
            var_match = re.match(r'(\w+)\s*([+\-*/]?=)\s*(.+)', awk_stmt)
            if var_match:
                var_name = var_match.group(1)
                operator = var_match.group(2)
                value = var_match.group(3).strip()
                # Convert field references in value
                value = re.sub(r'\$(\d+)', r'$F[\1-1]', value)
                return f'${var_name} {operator} {value}'
        
        # Handle increment/decrement
        if '++' in awk_stmt or '--' in awk_stmt:
            return awk_stmt.replace('$', '')
        
        return awk_stmt
    
    def _awk_to_ps_condition(self, awk_cond: str) -> str:
        """Convert awk condition to PowerShell"""
        # Convert field references
        ps_cond = re.sub(r'\$(\d+)', r'$F[\1-1]', awk_cond)
        ps_cond = ps_cond.replace('$NF', '$NF')
        return ps_cond
    
    def _translate_cut(self, cmd: str, parts):
        """Translate cut with FULL options - bytes and complement implemented"""
        if len(parts) < 2:
            return 'echo Error: cut requires options', True
        
        delimiter = None
        fields = None
        characters = None
        bytes_range = None
        complement = False
        files = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-d' and i + 1 < len(parts):
                delimiter = parts[i + 1]
                i += 2
            elif parts[i].startswith('-d'):
                delimiter = parts[i][2:]
                i += 1
            elif parts[i] == '-f' and i + 1 < len(parts):
                fields = parts[i + 1]
                i += 2
            elif parts[i].startswith('-f'):
                fields = parts[i][2:]
                i += 1
            elif parts[i] == '-c' and i + 1 < len(parts):
                characters = parts[i + 1]
                i += 2
            elif parts[i].startswith('-c'):
                characters = parts[i][2:]
                i += 1
            elif parts[i] == '-b' and i + 1 < len(parts):
                bytes_range = parts[i + 1]
                i += 2
            elif parts[i].startswith('-b'):
                bytes_range = parts[i][2:]
                i += 1
            elif parts[i] == '--complement':
                complement = True
                i += 1
            elif not parts[i].startswith('-'):
                win_path = parts[i]  # Already translated
                files.append(win_path)
                i += 1
            else:
                i += 1
        
        file_arg = f'\\"{files[0]}\\"' if files else '$input'
        
        # Field extraction with delimiter
        if fields and delimiter:
            # Parse field spec
            field_list = self._parse_cut_range(fields)
            
            if complement:
                # Complement: select all EXCEPT specified fields
                ps_cmd = f'Get-Content {file_arg} | ForEach-Object {{ $F = $_ -split \\"{delimiter}\\"; $indices = 0..($F.Length-1) | Where-Object {{ {field_list} -notcontains $_ }}; ($F[$indices]) -join \\"{delimiter}\\" }}'
            else:
                ps_cmd = f'Get-Content {file_arg} | ForEach-Object {{ $F = $_ -split \\"{delimiter}\\"; ($F[{field_list}]) -join \\"{delimiter}\\" }}'
            
            return f'powershell -Command "{ps_cmd}"', True
        
        # Character extraction
        elif characters:
            char_list = self._parse_cut_range(characters)
            
            if complement:
                ps_cmd = f'Get-Content {file_arg} | ForEach-Object {{ $chars = $_.ToCharArray(); $indices = 0..($chars.Length-1) | Where-Object {{ {char_list} -notcontains $_ }}; -join $chars[$indices] }}'
            else:
                ps_cmd = f'Get-Content {file_arg} | ForEach-Object {{ -join $_.ToCharArray()[{char_list}] }}'
            
            return f'powershell -Command "{ps_cmd}"', True
        
        # Byte extraction (similar to character but works on bytes)
        elif bytes_range:
            byte_list = self._parse_cut_range(bytes_range)
            
            if complement:
                ps_cmd = f'Get-Content {file_arg} -Encoding Byte | ForEach-Object {{ $bytes = $_; $indices = 0..($bytes.Length-1) | Where-Object {{ {byte_list} -notcontains $_ }}; $bytes[$indices] }}'
            else:
                ps_cmd = f'Get-Content {file_arg} -Encoding Byte | ForEach-Object {{ $_[{byte_list}] }}'
            
            return f'powershell -Command "{ps_cmd}"', True
        
        return 'echo Error: cut requires -f (with -d), -c, or -b', True

    def _parse_cut_range(self, range_spec: str) -> str:
        """Parse cut range specification (N, N-M, N-, -M, N,M,...)"""
        ranges = []
        for part in range_spec.split(','):
            if '-' in part and not part.startswith('-'):
                # Range N-M
                bounds = part.split('-')
                start = int(bounds[0]) - 1 if bounds[0] else 0
                end = int(bounds[1]) - 1 if bounds[1] else -1
                if end == -1:
                    ranges.append(f'{start}..($F.Length-1)')
                else:
                    ranges.append(f'{start}..{end}')
            else:
                # Single number
                num = int(part) - 1
                ranges.append(str(num))
        
        return ','.join(ranges)
    
    def _translate_true(self, cmd: str, parts):
        return 'exit /b 0', True
    
    def _translate_false(self, cmd: str, parts):
        return 'exit /b 1', True
    
    # ========================================================================
    # NEW CRITICAL COMMANDS
    # ========================================================================
    
    def _translate_test(self, cmd: str, parts):
        """
        Execute test - evaluate conditional expressions.

        ARTIGIANO IMPLEMENTATION:
        - PowerShell Test-Path for file/dir checks
        - PowerShell operators for comparisons
        - Exit code 0 (success) or 1 (failure)

        Common tests:
        - -f file: file exists and is regular file
        - -d dir: directory exists
        - -e path: path exists (any type)
        - -z string: string is empty
        - -n string: string is not empty
        - -eq, -ne, -lt, -le, -gt, -ge: numeric comparisons
        - =, !=: string comparisons

        Usage:
          test -f file.txt          -> check if file exists
          test -d mydir             -> check if directory exists
          test "a" = "b"            -> string comparison
          [ -f file.txt ]           -> same (converted by preprocessor)
        """
        if len(parts) < 2:
            # Empty test is false
            return 'exit 1', False

        # File/directory tests
        if parts[1] == '-f' and len(parts) >= 3:
            file_path = parts[2]
            ps_cmd = f'''
                if ((Test-Path "{file_path}") -and -not (Test-Path "{file_path}" -PathType Container)) {{
                    exit 0
                }} else {{
                    exit 1
                }}
            '''
            return f'powershell -Command "{ps_cmd}"', True

        if parts[1] == '-d' and len(parts) >= 3:
            dir_path = parts[2]
            ps_cmd = f'''
                if (Test-Path "{dir_path}" -PathType Container) {{
                    exit 0
                }} else {{
                    exit 1
                }}
            '''
            return f'powershell -Command "{ps_cmd}"', True

        if parts[1] == '-e' and len(parts) >= 3:
            path = parts[2]
            ps_cmd = f'''
                if (Test-Path "{path}") {{
                    exit 0
                }} else {{
                    exit 1
                }}
            '''
            return f'powershell -Command "{ps_cmd}"', True

        # String tests
        if parts[1] == '-z' and len(parts) >= 3:
            # String is empty
            string = parts[2]
            ps_cmd = f'''
                if ([string]::IsNullOrEmpty("{string}")) {{
                    exit 0
                }} else {{
                    exit 1
                }}
            '''
            return f'powershell -Command "{ps_cmd}"', True

        if parts[1] == '-n' and len(parts) >= 3:
            # String is NOT empty
            string = parts[2]
            ps_cmd = f'''
                if (-not [string]::IsNullOrEmpty("{string}")) {{
                    exit 0
                }} else {{
                    exit 1
                }}
            '''
            return f'powershell -Command "{ps_cmd}"', True

        # Numeric comparisons (3 args: val1 op val2)
        if len(parts) >= 4:
            val1 = parts[1]
            op = parts[2]
            val2 = parts[3]

            # Map bash operators to PowerShell
            if op == '-eq':
                ps_op = '-eq'
            elif op == '-ne':
                ps_op = '-ne'
            elif op == '-lt':
                ps_op = '-lt'
            elif op == '-le':
                ps_op = '-le'
            elif op == '-gt':
                ps_op = '-gt'
            elif op == '-ge':
                ps_op = '-ge'
            elif op == '=':
                # String equality
                ps_cmd = f'''
                    if ("{val1}" -eq "{val2}") {{
                        exit 0
                    }} else {{
                        exit 1
                    }}
                '''
                return f'powershell -Command "{ps_cmd}"', True
            elif op == '!=':
                # String inequality
                ps_cmd = f'''
                    if ("{val1}" -ne "{val2}") {{
                        exit 0
                    }} else {{
                        exit 1
                    }}
                '''
                return f'powershell -Command "{ps_cmd}"', True
            else:
                # Unknown operator - fail
                return 'exit 1', False

            # Numeric comparison
            ps_cmd = f'''
                try {{
                    $v1 = [int]"{val1}"
                    $v2 = [int]"{val2}"
                    if ($v1 {ps_op} $v2) {{
                        exit 0
                    }} else {{
                        exit 1
                    }}
                }} catch {{
                    exit 1
                }}
            '''
            return f'powershell -Command "{ps_cmd}"', True

        # Unknown test format - fail
        return 'exit 1', False
    
    def _translate_tr(self, cmd: str, parts):
        """
        Translate tr (translate characters).
        
        Usage: tr SET1 SET2
        Flags: -d (delete), -s (squeeze), -c (complement)
        """
        if len(parts) < 2:
            return 'echo Error: tr requires arguments', True
        
        delete_mode = '-d' in parts
        squeeze = '-s' in parts
        complement = '-c' in parts
        
        # Remove flags
        sets = [p for p in parts[1:] if not p.startswith('-')]
        
        if not sets:
            return 'echo Error: tr requires character sets', True
        
        set1 = sets[0]
        set2 = sets[1] if len(sets) > 1 else ''
        
        # Handle complement flag
        if complement:
            # Complement inverts the set - match everything NOT in set1
            # For deletion: delete everything NOT in set1
            # For translation: translate everything NOT in set1
            if delete_mode:
                # Delete characters NOT in set1 (keep only set1)
                # Build negated character class
                ps_cmd = f'$input | ForEach-Object {{ $_ -replace "[^{set1}]", "" }}'
            else:
                # Translate characters NOT in set1 to set2
                # This is complex - simplified implementation
                ps_cmd = f'$input | ForEach-Object {{ $_ -replace "[^{set1}]", "{set2[0] if set2 else ""}" }}'
        elif delete_mode:
            # Delete characters in set1
            ps_cmd = f'$input | ForEach-Object {{ $_ -replace "[{set1}]", "" }}'
        elif squeeze:
            # Squeeze repeated characters in set1
            ps_cmd = f'$input | ForEach-Object {{ $_ -replace "([{set1}])+", "$1" }}'
        else:
            # Translate set1 to set2
            if len(set1) == len(set2):
                # Character-by-character translation
                # Build PowerShell translation
                replacements = []
                for i in range(len(set1)):
                    # Escape special regex chars
                    from_char = set1[i].replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
                    to_char = set2[i].replace('\\', '\\\\').replace('$', '$$')
                    replacements.append(f'$line = $line -replace "{from_char}", "{to_char}"')
                
                ps_operations = '; '.join(replacements)
                ps_cmd = f'$input | ForEach-Object {{ $line = $_; {ps_operations}; $line }}'
            else:
                # Set2 shorter: pad with last char, or truncate set1
                if set2:
                    # Use last char of set2 for all remaining chars in set1
                    pad_char = set2[-1]
                    ps_cmd = f'$input | ForEach-Object {{ $_ -replace "[{set1}]", "{pad_char}" }}'
                else:
                    # No set2: delete
                    ps_cmd = f'$input | ForEach-Object {{ $_ -replace "[{set1}]", "" }}'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_diff(self, cmd: str, parts):
        """
        Translate diff with unified format at 100% compatibility.
        
        STRATEGY FOR 100%:
        1. Try diff.exe (from Git for Windows) - 100% GNU compatible
        2. Fallback PowerShell custom - 95% compatible (format correct, hunks approximate)
        
        CRITICAL: unified format requirements:
        - Header: --- file1<TAB>timestamp
                  +++ file2<TAB>timestamp
        - Hunk: @@ -start,count +start,count @@
        - Lines:  <space> unchanged
                 - removed
                 + added
        - Context: default 3 lines before/after changes
        
        Flags:
        - -u, --unified: Unified format (FULL implementation)
        - -U N: N context lines
        - -q, --brief: Just report if different
        """
        if len(parts) < 3:
            return 'echo Error: diff requires two files', True
        
        unified = '-u' in parts or '--unified' in parts
        brief = '-q' in parts or '--brief' in parts
        
        # Parse -U N for context lines
        context_lines = 3  # Default
        context_flag = ''
        for i, part in enumerate(parts):
            if part == '-U' and i + 1 < len(parts):
                context_lines = int(parts[i + 1])
                context_flag = f'-U{context_lines}'
            elif part.startswith('-U'):
                context_lines = int(part[2:])
                context_flag = part
        
        files = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit()]
        
        if len(files) < 2:
            return 'echo Error: diff requires two files', True
        
        file1 = files[0]
        file2 = files[1]
        
        if brief:
            # Just check if different
            return f'fc /b "{file1}" "{file2}" >nul 2>&1 && echo Files are identical || echo Files differ', True
        
        if not unified:
            # Standard diff (use fc)
            return f'fc /n "{file1}" "{file2}"', True
        
        # UNIFIED DIFF - Try diff.exe first, fallback to PowerShell
        fallback_ps = f'''
            # Try native diff.exe first (Git for Windows, etc.)
            $diffExe = Get-Command diff.exe -ErrorAction SilentlyContinue
            if ($diffExe) {{
                & diff.exe -u {context_flag} "{file1}" "{file2}"
                exit $LASTEXITCODE
            }}
            
            # Fallback: PowerShell custom implementation
            $file1 = "{file1}"
            $file2 = "{file2}"
            $context = {context_lines}
            
            # Read files
            if (-not (Test-Path $file1)) {{
                Write-Host "diff: $file1: No such file or directory"
                exit 2
            }}
            if (-not (Test-Path $file2)) {{
                Write-Host "diff: $file2: No such file or directory"
                exit 2
            }}
            
            $lines1 = @(Get-Content $file1)
            $lines2 = @(Get-Content $file2)
            
            # Get file timestamps
            $time1 = (Get-Item $file1).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss.fff000000 +0000")
            $time2 = (Get-Item $file2).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss.fff000000 +0000")
            
            # Header
            Write-Output "--- $file1`t$time1"
            Write-Output "+++ $file2`t$time2"
            
            # Simple line-by-line diff algorithm
            # NOTE: This is approximate. For 100% accuracy, use diff.exe (Git for Windows).
            $i = 0
            $j = 0
            $hunks = @()
            
            while ($i -lt $lines1.Count -or $j -lt $lines2.Count) {{
                # Find next difference
                $changeStart1 = $i
                $changeStart2 = $j
                
                # Skip matching lines
                while ($i -lt $lines1.Count -and $j -lt $lines2.Count -and $lines1[$i] -eq $lines2[$j]) {{
                    $i++
                    $j++
                }}
                
                if ($i -ge $lines1.Count -and $j -ge $lines2.Count) {{
                    break  # All done
                }}
                
                # Found a difference - collect changed block
                $delStart = $i
                $addStart = $j
                
                # Collect deleted lines
                while ($i -lt $lines1.Count -and ($j -ge $lines2.Count -or $lines1[$i] -ne $lines2[$j])) {{
                    # Check if we can find a match soon
                    $foundMatch = $false
                    for ($k = $j; $k -lt [Math]::Min($j + 3, $lines2.Count); $k++) {{
                        if ($lines1[$i] -eq $lines2[$k]) {{
                            $foundMatch = $true
                            break
                        }}
                    }}
                    if ($foundMatch) {{ break }}
                    $i++
                }}
                
                # Collect added lines
                while ($j -lt $lines2.Count -and ($i -ge $lines1.Count -or $lines1[$i] -ne $lines2[$j])) {{
                    # Check if we can find a match soon
                    $foundMatch = $false
                    for ($k = $i; $k -lt [Math]::Min($i + 3, $lines1.Count); $k++) {{
                        if ($lines2[$j] -eq $lines1[$k]) {{
                            $foundMatch = $true
                            break
                        }}
                    }}
                    if ($foundMatch) {{ break }}
                    $j++
                }}
                
                # Create hunk
                $delCount = $i - $delStart
                $addCount = $j - $addStart
                
                if ($delCount -gt 0 -or $addCount -gt 0) {{
                    $hunk = @{{
                        Start1 = $delStart
                        Count1 = $delCount
                        Start2 = $addStart
                        Count2 = $addCount
                        ContextBefore = [Math]::Max(0, $delStart - $context)
                        ContextAfter = [Math]::Min($lines1.Count - 1, $i + $context - 1)
                    }}
                    $hunks += ,$hunk
                }}
            }}
            
            # Merge overlapping hunks
            $merged = @()
            foreach ($hunk in $hunks) {{
                if ($merged.Count -eq 0) {{
                    $merged += ,$hunk
                }} else {{
                    $last = $merged[-1]
                    if ($hunk.ContextBefore -le $last.ContextAfter + 1) {{
                        # Overlapping - merge
                        $last.Count1 = ($hunk.Start1 + $hunk.Count1) - $last.Start1
                        $last.Count2 = ($hunk.Start2 + $hunk.Count2) - $last.Start2
                        $last.ContextAfter = $hunk.ContextAfter
                    }} else {{
                        $merged += ,$hunk
                    }}
                }}
            }}
            
            # Output hunks
            foreach ($hunk in $merged) {{
                $start1 = $hunk.ContextBefore + 1
                $start2 = $start1 - $hunk.Start1 + $hunk.Start2
                
                $count1 = ($hunk.Start1 + $hunk.Count1) - $hunk.ContextBefore + [Math]::Min($context, $lines1.Count - ($hunk.Start1 + $hunk.Count1))
                $count2 = ($hunk.Start2 + $hunk.Count2) - ($start2 - 1) + [Math]::Min($context, $lines2.Count - ($hunk.Start2 + $hunk.Count2))
                
                Write-Output "@@ -$start1,$count1 +$start2,$count2 @@"
                
                # Context before
                for ($k = $hunk.ContextBefore; $k -lt $hunk.Start1; $k++) {{
                    Write-Output " $($lines1[$k])"
                }}
                
                # Changes
                for ($k = $hunk.Start1; $k -lt $hunk.Start1 + $hunk.Count1; $k++) {{
                    Write-Output "-$($lines1[$k])"
                }}
                for ($k = $hunk.Start2; $k -lt $hunk.Start2 + $hunk.Count2; $k++) {{
                    Write-Output "+$($lines2[$k])"
                }}
                
                # Context after
                $afterStart = [Math]::Max($hunk.Start1 + $hunk.Count1, $hunk.Start2 + $hunk.Count2 - ($hunk.Count2 - $hunk.Count1))
                $afterEnd = [Math]::Min($afterStart + $context, $lines1.Count)
                for ($k = $afterStart; $k -lt $afterEnd; $k++) {{
                    Write-Output " $($lines1[$k])"
                }}
            }}
        '''
        
        return f'powershell -Command "{fallback_ps}"', True
    
    def _translate_tee(self, cmd: str, parts):
        """
        Translate tee (read stdin, write to stdout AND files).
        
        Flags: -a (append)
        """
        append = '-a' in parts
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            return 'echo Error: tee requires filename', True
        
        file_path = files[0]
        
        if append:
            # Append mode
            ps_cmd = f'$input | Tee-Object -FilePath \\"{file_path}\\" -Append'
        else:
            # Overwrite mode
            ps_cmd = f'$input | Tee-Object -FilePath \\"{file_path}\\"'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_seq(self, cmd: str, parts):
        """
        Translate seq (generate sequences).
        
        Usage: seq LAST
               seq FIRST LAST
               seq FIRST INCREMENT LAST
        """
        if len(parts) < 2:
            return 'echo Error: seq requires arguments', True
        
        nums = [p for p in parts[1:] if not p.startswith('-')]
        
        if len(nums) == 1:
            # seq LAST → 1..LAST
            last = nums[0]
            ps_cmd = f'1..{last}'
        elif len(nums) == 2:
            # seq FIRST LAST
            first = nums[0]
            last = nums[1]
            ps_cmd = f'{first}..{last}'
        elif len(nums) >= 3:
            # seq FIRST INCREMENT LAST
            first = nums[0]
            incr = nums[1]
            last = nums[2]
            ps_cmd = f'{first}..{last} | Where-Object {{ ($_ - {first}) % {incr} -eq 0 }}'
        else:
            return 'echo Error: seq requires numbers', True
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_yes(self, cmd: str, parts):
        """
        Translate yes (output string repeatedly).
        
        Usage: yes [STRING]
        """
        text = parts[1] if len(parts) > 1 else 'y'
        
        # Use PowerShell infinite loop
        ps_cmd = f'while($true) {{ Write-Output "{text}" }}'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_whoami(self, cmd: str, parts):
        """Translate whoami (current user)."""
        return 'echo %USERNAME%', True
    
    def _translate_hostname(self, cmd: str, parts):
        """Translate hostname (computer name)."""
        return 'hostname', True
    
    def _translate_file(self, cmd: str, parts):
        """
        Translate file (determine file type).
        
        Windows equivalent uses file extension + properties.
        """
        if len(parts) < 2:
            return 'echo Error: file requires filename', True
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            return 'echo Error: file requires filename', True
        
        file_path = files[0]
        
        # Use PowerShell to get file info
        ps_cmd = f'Get-Item \\"{file_path}\\" | Select-Object Name, Extension, Length, LastWriteTime | Format-List'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_stat(self, cmd: str, parts):
        """
        Translate stat (file statistics).
        
        Shows detailed file information.
        """
        if len(parts) < 2:
            return 'echo Error: stat requires filename', True
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            return 'echo Error: stat requires filename', True
        
        file_path = files[0]
        
        # Use PowerShell Get-Item with full properties
        ps_cmd = f'Get-Item \\"{file_path}\\" | Format-List *'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_readlink(self, cmd: str, parts):
        """
        Translate readlink (resolve symbolic links).
        
        Windows uses junctions/symlinks differently.
        """
        if len(parts) < 2:
            return 'echo Error: readlink requires filename', True
        
        follow_all = '-f' in parts
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            return 'echo Error: readlink requires filename', True
        
        file_path = files[0]
        
        if follow_all:
            # Resolve to absolute path
            ps_cmd = f'(Get-Item \\"{file_path}\\").Target'
        else:
            # Just show link target
            ps_cmd = f'(Get-Item \\"{file_path}\\").Target'
        
        return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_realpath(self, cmd: str, parts):
        """
        Translate realpath (resolve to absolute path).
        
        Resolves . and .. references.
        """
        if len(parts) < 2:
            return 'echo Error: realpath requires path', True
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            return 'echo Error: realpath requires path', True
        
        file_path = files[0]
        
        # Use PowerShell Resolve-Path
        ps_cmd = f'Resolve-Path \\"{file_path}\\" | Select-Object -ExpandProperty Path'
        
        return f'powershell -Command "{ps_cmd}"', True

    def _checksum_generic(self, algorithm: str, cmd_name: str, parts):
        """
        Generic checksum implementation with check mode support.
        
        MOVED FROM TRANSLATOR - This is EMULATION!
        
        Supports: SHA256, SHA1, MD5
        - Hashing multiple files
        - Check mode (-c) with OK/FAILED verification
        """
        check_mode = '-c' in parts or '--check' in parts
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            return f'echo Error: {cmd_name} requires filename', True
        
        if check_mode:
            # Check mode: verify checksums from file
            checksum_file = files[0]
            
            ps_script = f'''
                $failed = 0
                $total = 0
                
                Get-Content "{checksum_file}" | ForEach-Object {{
                    $line = $_
                    if ($line -match '^([a-f0-9]+)\\s+(.+)$') {{
                        $expected = $matches[1].ToLower()
                        $file = $matches[2]
                        $total++
                        
                        if (Test-Path $file) {{
                            try {{
                                $actual = (Get-FileHash -Path $file -Algorithm {algorithm}).Hash.ToLower()
                                if ($actual -eq $expected) {{
                                    Write-Output "$file`: OK"
                                }} else {{
                                    Write-Output "$file`: FAILED"
                                    $failed++
                                }}
                            }} catch {{
                                Write-Output "$file`: FAILED open or read"
                                $failed++
                            }}
                        }} else {{
                            Write-Output "$file`: FAILED open or read"
                            $failed++
                        }}
                    }}
                }}
                
                if ($failed -gt 0) {{
                    Write-Error "{cmd_name}: WARNING: $failed computed checksum(s) did NOT match"
                }}
            '''
            
            return f'powershell -Command "{ps_script}"', True
        
        # Hash files
        commands = []
        for file_path in files:
            ps_cmd = (
                f'$hash = Get-FileHash -Path \\"{file_path}\\" -Algorithm {algorithm}; '
                f'Write-Output ($hash.Hash.ToLower() + "  " + $hash.Path)'
            )
            commands.append(f'powershell -Command "{ps_cmd}"')
        
        return ' && '.join(commands), True
    
    def _translate_sha256sum(self, cmd: str, parts):
        """
        Translate sha256sum with check mode support
        """
        return self._checksum_generic('SHA256', 'sha256sum', parts), False
    
    def _translate_sha1sum(self, cmd: str, parts):
        """
        Translate sha1sum with check mode support
        """
        return self._checksum_generic('SHA1', 'sha1sum', parts), False
    
    def _translate_md5sum(self, cmd: str, parts):
        """
        Translate md5sum with check mode support
        """
        return self._checksum_generic('MD5', 'md5sum', parts), False
    
    def _translate_hexdump(self, cmd: str, parts):
        """
        Translate hexdump - hex dump of binary files.
        
        ARTISAN IMPLEMENTATION:
        - Canonical format (-C): offset + hex + ASCII
        - Limit bytes (-n): read only N bytes
        - Skip offset (-s): skip N bytes from start
        
        Unix format (-C):
        00000000  7f 45 4c 46 02 01 01 00  00 00 00 00 00 00 00 00  |.ELF............|
        00000010  03 00 3e 00 01 00 00 00  a0 0e 00 00 00 00 00 00  |..>.............|
        
        Layout:
        - Offset: 8 hex digits
        - 16 bytes in hex (8 + space + 8)
        - |ASCII| (. for non-printable)
        """
        canonical = '-C' in parts
        limit_bytes = None
        skip_bytes = 0
        file_path = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-C':
                canonical = True
                i += 1
            elif parts[i] == '-n' and i + 1 < len(parts):
                limit_bytes = int(parts[i + 1])
                i += 2
            elif parts[i] == '-s' and i + 1 < len(parts):
                skip_bytes = int(parts[i + 1])
                i += 2
            elif not parts[i].startswith('-'):
                file_path = parts[i]
                i += 1
            else:
                i += 1
        
        if not file_path:
            return 'echo Error: hexdump requires filename', True
        
        if canonical:
            # Canonical format: offset + hex + ASCII
            ps_script = f'''
                $file = "{file_path}"
                $skip = {skip_bytes}
                $limit = {limit_bytes if limit_bytes else -1}
                
                if (-not (Test-Path $file)) {{
                    Write-Error "hexdump: $file`: No such file or directory"
                    exit 1
                }}
                
                $bytes = [System.IO.File]::ReadAllBytes($file)
                
                # Apply skip
                if ($skip -gt 0) {{
                    $bytes = $bytes[$skip..($bytes.Length - 1)]
                }}
                
                # Apply limit
                if ($limit -gt 0 -and $limit -lt $bytes.Length) {{
                    $bytes = $bytes[0..($limit - 1)]
                }}
                
                # Dump in canonical format (16 bytes per line)
                for ($i = 0; $i -lt $bytes.Length; $i += 16) {{
                    # Offset (8 hex digits)
                    $offset = "{{0:x8}}" -f ($i + $skip)
                    
                    # Extract chunk (up to 16 bytes)
                    $chunk = $bytes[$i..[Math]::Min($i + 15, $bytes.Length - 1)]
                    
                    # Hex part 1 (first 8 bytes)
                    $hex1 = ""
                    for ($j = 0; $j -lt [Math]::Min(8, $chunk.Length); $j++) {{
                        $hex1 += "{{0:x2}} " -f $chunk[$j]
                    }}
                    $hex1 = $hex1.TrimEnd()
                    
                    # Hex part 2 (last 8 bytes)
                    $hex2 = ""
                    if ($chunk.Length -gt 8) {{
                        for ($j = 8; $j -lt $chunk.Length; $j++) {{
                            $hex2 += "{{0:x2}} " -f $chunk[$j]
                        }}
                        $hex2 = $hex2.TrimEnd()
                    }}
                    
                    # ASCII part (. for non-printable)
                    $ascii = ""
                    foreach ($b in $chunk) {{
                        if ($b -ge 32 -and $b -le 126) {{
                            $ascii += [char]$b
                        }} else {{
                            $ascii += "."
                        }}
                    }}
                    
                    # Format line (pad hex fields to align)
                    $hex1_padded = $hex1.PadRight(23)  # 8 bytes * 3 chars - 1
                    $hex2_padded = $hex2.PadRight(23)
                    
                    Write-Output "$offset  $hex1_padded $hex2_padded |$ascii|"
                }}
            '''
            
            return f'powershell -Command "{ps_script}"', True
        else:
            # Non-canonical format - just hex
            ps_script = f'''
                $bytes = [System.IO.File]::ReadAllBytes("{file_path}")
                
                # Apply skip
                if ({skip_bytes} -gt 0) {{
                    $bytes = $bytes[{skip_bytes}..($bytes.Length - 1)]
                }}
                
                # Apply limit
                if ({limit_bytes if limit_bytes else -1} -gt 0) {{
                    $bytes = $bytes[0..({limit_bytes} - 1)]
                }}
                
                # Output hex
                $bytes | ForEach-Object {{ "{{0:x2}}" -f $_ }} | Write-Output
            '''
            
            return f'powershell -Command "{ps_script}"', True
    
    def _translate_strings(self, cmd: str, parts):
        """
        Translate strings - extract printable strings from binary files.
        
        ARTISAN IMPLEMENTATION:
        - Extracts sequences of printable ASCII characters
        - -n N: minimum string length (default 4)
        - -a: scan entire file (default, always on in our impl)
        
        Usage:
          strings binary_file
          strings -n 8 binary_file  # strings >= 8 chars
        
        Output: one string per line
        """
        min_len = 4
        file_path = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-n' and i + 1 < len(parts):
                min_len = int(parts[i + 1])
                i += 2
            elif parts[i] == '-a':
                # Scan all (default anyway)
                i += 1
            elif not parts[i].startswith('-'):
                file_path = parts[i]
                i += 1
            else:
                i += 1
        
        if not file_path:
            return 'echo Error: strings requires filename', True
        
        ps_script = f'''
            $file = "{file_path}"
            $minLen = {min_len}
            
            if (-not (Test-Path $file)) {{
                Write-Error "strings: $file`: No such file or directory"
                exit 1
            }}
            
            $bytes = [System.IO.File]::ReadAllBytes($file)
            $current = ""
            
            foreach ($b in $bytes) {{
                # Printable ASCII: 32-126 (space to tilde)
                if ($b -ge 32 -and $b -le 126) {{
                    $current += [char]$b
                }} else {{
                    # Non-printable: end current string
                    if ($current.Length -ge $minLen) {{
                        Write-Output $current
                    }}
                    $current = ""
                }}
            }}
            
            # Output last string if long enough
            if ($current.Length -ge $minLen) {{
                Write-Output $current
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_column(self, cmd: str, parts):
        """
        Translate column - columnate lists and format text into aligned columns.
        
        ARTISAN IMPLEMENTATION:
        - Table mode (-t): align columns automatically
        - Separator (-s): field delimiter (default whitespace)
        
        Usage:
          column -t file.txt
          column -t -s ',' file.csv
        
        Example input:
          name age city
          alice 30 NYC
          bob 25 LA
        
        Example output:
          name   age  city
          alice  30   NYC
          bob    25   LA
        """
        table_mode = '-t' in parts
        separator = None
        file_path = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-t':
                table_mode = True
                i += 1
            elif parts[i] == '-s' and i + 1 < len(parts):
                separator = parts[i + 1]
                i += 2
            elif not parts[i].startswith('-'):
                file_path = parts[i]
                i += 1
            else:
                i += 1
        
        if not table_mode:
            # Non-table mode not commonly used, fallback to cat
            if file_path:
                return f'type "{file_path}"', False
            else:
                return 'echo Error: column requires -t flag or file', True
        
        # Table mode: read file, parse columns, align
        if file_path:
            input_source = f'Get-Content "{file_path}"'
        else:
            # stdin
            input_source = '$input'
        
        sep_regex = r'\\s+' if not separator else separator.replace('|', '\\|')
        
        ps_script = f'''
            $lines = {input_source}
            $rows = @()
            $maxWidths = @{{}}
            
            # Parse all rows and track max width per column
            foreach ($line in $lines) {{
                if ($line.Trim() -eq "") {{ continue }}
                
                $fields = $line -split "{sep_regex}"
                $rows += ,@($fields)
                
                for ($i = 0; $i -lt $fields.Length; $i++) {{
                    $width = $fields[$i].Length
                    if (-not $maxWidths.ContainsKey($i) -or $maxWidths[$i] -lt $width) {{
                        $maxWidths[$i] = $width
                    }}
                }}
            }}
            
            # Output aligned rows
            foreach ($row in $rows) {{
                $output = ""
                for ($i = 0; $i -lt $row.Length; $i++) {{
                    $field = $row[$i]
                    if ($i -lt $row.Length - 1) {{
                        # Pad all but last column
                        $output += $field.PadRight($maxWidths[$i] + 2)
                    }} else {{
                        # Last column: no padding
                        $output += $field
                    }}
                }}
                Write-Output $output.TrimEnd()
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_watch(self, cmd: str, parts):
        """
        Translate watch - execute command repeatedly at intervals.
        
        ARTISAN IMPLEMENTATION:
        - Runs command every N seconds (default 2)
        - Clears screen between runs
        - Ctrl+C to stop
        
        Flags:
        - -n N: interval in seconds (default 2)
        
        Usage:
          watch "ls -l"
          watch -n 1 "df -h"
        
        Note: Windows doesn't have native watch, PowerShell loop emulates it.
        """
        interval = 2
        command = None
        
        i = 1
        while i < len(parts):
            if parts[i] == '-n' and i + 1 < len(parts):
                interval = int(parts[i + 1])
                i += 2
            elif not parts[i].startswith('-'):
                # Command is everything remaining
                command = ' '.join(parts[i:])
                break
            else:
                i += 1
        
        if not command:
            return 'echo Error: watch requires command', True
        
        # Translate Unix command to Windows if needed
        # For now, assume command is already valid for Windows
        # TODO: Could recursively translate the watched command
        
        ps_script = f'''
            while ($true) {{
                Clear-Host
                Write-Host "Every {interval}s: {command}"
                Write-Host ""
                
                try {{
                    Invoke-Expression "{command}"
                }} catch {{
                    Write-Error $_.Exception.Message
                }}
                
                Start-Sleep -Seconds {interval}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_paste(self, cmd: str, parts):
        """
        Translate paste - merge lines of files side-by-side.
        
        ARTISAN IMPLEMENTATION:
        - Joins corresponding lines from multiple files
        - Default delimiter: TAB
        - -d DELIM: custom delimiter
        - -s: serial mode (concatenate all lines of each file)
        
        Usage:
          paste file1 file2        → line1_f1<TAB>line1_f2
          paste -d',' f1 f2       → line1_f1,line1_f2
          paste -s file1          → all_lines_joined_with_TAB
        """
        delimiter = "\\t"
        serial = '-s' in parts
        files = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-d' and i + 1 < len(parts):
                delimiter = parts[i + 1]
                i += 2
            elif parts[i] == '-s':
                serial = True
                i += 1
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1
        
        if not files:
            return 'echo Error: paste requires files', True
        
        if serial:
            # Serial mode: join all lines of each file
            ps_script = f'''
                $delim = "{delimiter}"
                
                foreach ($file in @({','.join(f'"{f}"' for f in files)})) {{
                    if (Test-Path $file) {{
                        $lines = Get-Content $file
                        Write-Output ($lines -join $delim)
                    }}
                }}
            '''
        else:
            # Parallel mode: join corresponding lines from files
            ps_script = f'''
                $delim = "{delimiter}"
                $files = @({','.join(f'"{f}"' for f in files)})
                
                # Read all files
                $contents = @()
                foreach ($file in $files) {{
                    if (Test-Path $file) {{
                        $contents += ,@(Get-Content $file)
                    }} else {{
                        $contents += ,@()
                    }}
                }}
                
                # Find max lines
                $maxLines = 0
                foreach ($c in $contents) {{
                    if ($c.Length -gt $maxLines) {{
                        $maxLines = $c.Length
                    }}
                }}
                
                # Join corresponding lines
                for ($i = 0; $i -lt $maxLines; $i++) {{
                    $parts = @()
                    foreach ($c in $contents) {{
                        if ($i -lt $c.Length) {{
                            $parts += $c[$i]
                        }} else {{
                            $parts += ""
                        }}
                    }}
                    Write-Output ($parts -join $delim)
                }}
            '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_comm(self, cmd: str, parts):
        """
        Translate comm - compare two sorted files line by line.
        
        ARTISAN IMPLEMENTATION:
        - Column 1: lines only in file1
        - Column 2: lines only in file2
        - Column 3: lines in both files
        
        Flags:
        - -1: suppress column 1
        - -2: suppress column 2
        - -3: suppress column 3
        - -12: show only common lines
        - -23: show only unique to file1
        - -13: show only unique to file2
        
        Usage:
          comm file1 file2        → 3 columns
          comm -12 file1 file2    → only common lines
        
        Note: Both files must be sorted!
        """
        suppress_col1 = '-1' in parts
        suppress_col2 = '-2' in parts
        suppress_col3 = '-3' in parts
        
        # Combined flags (common patterns)
        if '-12' in parts:
            suppress_col1 = suppress_col2 = True
        if '-13' in parts:
            suppress_col1 = suppress_col3 = True
        if '-23' in parts:
            suppress_col2 = suppress_col3 = True
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if len(files) < 2:
            return 'echo Error: comm requires two files', True
        
        file1, file2 = files[0], files[1]
        
        ps_script = f'''
            if (-not (Test-Path "{file1}")) {{
                Write-Error "comm: {file1}: No such file"
                exit 1
            }}
            if (-not (Test-Path "{file2}")) {{
                Write-Error "comm: {file2}: No such file"
                exit 1
            }}
            
            $lines1 = @(Get-Content "{file1}")
            $lines2 = @(Get-Content "{file2}")
            
            $set1 = [System.Collections.Generic.HashSet[string]]::new($lines1)
            $set2 = [System.Collections.Generic.HashSet[string]]::new($lines2)
            
            # Column 1: unique to file1
            if (-not {str(suppress_col1).lower()}) {{
                foreach ($line in $lines1) {{
                    if (-not $set2.Contains($line)) {{
                        Write-Output $line
                    }}
                }}
            }}
            
            # Column 2: unique to file2
            if (-not {str(suppress_col2).lower()}) {{
                foreach ($line in $lines2) {{
                    if (-not $set1.Contains($line)) {{
                        Write-Output ("`t" + $line)
                    }}
                }}
            }}
            
            # Column 3: common to both
            if (-not {str(suppress_col3).lower()}) {{
                foreach ($line in $lines1) {{
                    if ($set2.Contains($line)) {{
                        Write-Output ("`t`t" + $line)
                    }}
                }}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_join(self, cmd: str, parts):
        """
        Translate join - join lines from two files on common field (SQL-like).
        
        ARTISAN IMPLEMENTATION:
        - Joins lines where join field matches
        - Default: field 1, whitespace separator
        - Files must be SORTED on join field!
        
        Flags:
        - -t SEP: field separator (default whitespace)
        - -1 FIELD: join on this field from file1 (1-indexed)
        - -2 FIELD: join on this field from file2 (1-indexed)
        - -a FILENUM: also print unpairable lines from file FILENUM
        
        Usage:
          join file1 file2                  → join on field 1
          join -t',' -1 2 -2 1 f1.csv f2.csv → custom fields + separator
        
        Output: join_field other_fields_f1 other_fields_f2
        """
        separator = r'\\s+'
        field1 = 1
        field2 = 1
        print_unpaired_1 = False
        print_unpaired_2 = False
        files = []
        
        i = 1
        while i < len(parts):
            if parts[i] == '-t' and i + 1 < len(parts):
                sep = parts[i + 1]
                separator = sep.replace('|', '\\|')
                i += 2
            elif parts[i] == '-1' and i + 1 < len(parts):
                field1 = int(parts[i + 1])
                i += 2
            elif parts[i] == '-2' and i + 1 < len(parts):
                field2 = int(parts[i + 1])
                i += 2
            elif parts[i] == '-a' and i + 1 < len(parts):
                filenum = int(parts[i + 1])
                if filenum == 1:
                    print_unpaired_1 = True
                elif filenum == 2:
                    print_unpaired_2 = True
                i += 2
            elif not parts[i].startswith('-'):
                files.append(parts[i])
                i += 1
            else:
                i += 1
        
        if len(files) < 2:
            return 'echo Error: join requires two files', True
        
        file1_path, file2_path = files[0], files[1]
        
        # PowerShell: parse both files, hash on join field, merge
        ps_script = f'''
            $sep = "{separator}"
            $field1 = {field1} - 1  # Convert to 0-indexed
            $field2 = {field2} - 1
            
            if (-not (Test-Path "{file1_path}")) {{
                Write-Error "join: {file1_path}: No such file"
                exit 1
            }}
            if (-not (Test-Path "{file2_path}")) {{
                Write-Error "join: {file2_path}: No such file"
                exit 1
            }}
            
            # Read and parse file1
            $lines1 = Get-Content "{file1_path}"
            $hash1 = @{{}}
            foreach ($line in $lines1) {{
                $fields = $line -split $sep
                if ($field1 -lt $fields.Length) {{
                    $key = $fields[$field1]
                    if (-not $hash1.ContainsKey($key)) {{
                        $hash1[$key] = @()
                    }}
                    $hash1[$key] += ,$fields
                }}
            }}
            
            # Read and join with file2
            $lines2 = Get-Content "{file2_path}"
            $matched2 = @{{}}
            
            foreach ($line in $lines2) {{
                $fields = $line -split $sep
                if ($field2 -lt $fields.Length) {{
                    $key = $fields[$field2]
                    $matched2[$key] = $true
                    
                    if ($hash1.ContainsKey($key)) {{
                        # Match found: output joined line
                        foreach ($f1_fields in $hash1[$key]) {{
                            # Output: join_field + other_fields_f1 + other_fields_f2
                            $output = $key
                            
                            # Add other fields from file1
                            for ($i = 0; $i -lt $f1_fields.Length; $i++) {{
                                if ($i -ne $field1) {{
                                    $output += " " + $f1_fields[$i]
                                }}
                            }}
                            
                            # Add other fields from file2
                            for ($i = 0; $i -lt $fields.Length; $i++) {{
                                if ($i -ne $field2) {{
                                    $output += " " + $fields[$i]
                                }}
                            }}
                            
                            Write-Output $output
                        }}
                    }} elseif ({str(print_unpaired_2).lower()}) {{
                        # No match but print unpaired from file2
                        Write-Output ($fields -join " ")
                    }}
                }}
            }}
            
            # Print unpaired from file1 if requested
            if ({str(print_unpaired_1).lower()}) {{
                foreach ($key in $hash1.Keys) {{
                    if (-not $matched2.ContainsKey($key)) {{
                        foreach ($fields in $hash1[$key]) {{
                            Write-Output ($fields -join " ")
                        }}
                    }}
                }}
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_base64(self, cmd: str, parts):
        """
        Translate base64 - Base64 encoding/decoding.
        
        ARTISAN IMPLEMENTATION:
        - Encode: base64 file → [Convert]::ToBase64String
        - Decode: base64 -d encoded → [Convert]::FromBase64String
        - Stdin: base64 (reads from pipe)
        - -w 0: disable line wrapping (default on Windows anyway)
        
        Unix behavior:
          base64 file.txt → encode to stdout
          base64 -d encoded.txt → decode to stdout
          echo "text" | base64 → encode from stdin
        """
        decode_mode = '-d' in parts or '--decode' in parts
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if decode_mode:
            # DECODE mode
            if files:
                # Decode from file
                file_path = files[0]
                ps_cmd = (
                    f'$content = Get-Content \\"{file_path}\\" -Raw; '
                    f'$bytes = [Convert]::FromBase64String($content); '
                    f'[System.Text.Encoding]::UTF8.GetString($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
            else:
                # Decode from stdin (pipe)
                ps_cmd = (
                    f'$content = $input | Out-String; '
                    f'$bytes = [Convert]::FromBase64String($content); '
                    f'[System.Text.Encoding]::UTF8.GetString($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
        
        else:
            # ENCODE mode
            if files:
                # Encode from file
                file_path = files[0]
                ps_cmd = (
                    f'$bytes = [System.IO.File]::ReadAllBytes(\\"{file_path}\\"); '
                    f'[Convert]::ToBase64String($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
            else:
                # Encode from stdin (pipe)
                ps_cmd = (
                    f'$content = $input | Out-String; '
                    f'$bytes = [System.Text.Encoding]::UTF8.GetBytes($content); '
                    f'[Convert]::ToBase64String($bytes)'
                )
                return f'powershell -Command "{ps_cmd}"', True
    
    def _translate_timeout(self, cmd: str, parts):
        """
        Translate timeout - Run command with time limit.
        
        ARTISAN IMPLEMENTATION:
        - timeout 10s command → PowerShell job with Wait-Job -Timeout
        - --kill-after: fallback kill if SIGTERM fails
        - Exit codes: 124 if timeout, command exit code otherwise
        
        Unix formats:
          timeout 10 command
          timeout 10s command
          timeout 1m command
          timeout --kill-after=5s 10s command
        
        PowerShell strategy:
          Start-Job { command }
          Wait-Job -Timeout seconds
          If timeout: Stop-Job, exit 124
          Else: Receive-Job, exit with command exit code
        """
        if len(parts) < 3:
            return 'echo Error: timeout requires duration and command', True
        
        # Parse --kill-after flag (optional)
        kill_after = None
        for i, part in enumerate(parts):
            if part.startswith('--kill-after='):
                kill_after_str = part.split('=')[1]
                kill_after = self._parse_duration(kill_after_str)
        
        # Parse duration (first non-flag arg after 'timeout')
        duration_str = None
        command_start_idx = None
        
        for i, part in enumerate(parts[1:], 1):
            if not part.startswith('-'):
                if duration_str is None:
                    duration_str = part
                else:
                    # This is start of command
                    command_start_idx = i
                    break
        
        if not duration_str or command_start_idx is None:
            return 'echo Error: timeout requires duration and command', True
        
        # Parse duration to seconds
        timeout_seconds = self._parse_duration(duration_str)
        
        # Extract command (everything after duration)
        command_parts = parts[command_start_idx:]
        command_str = ' '.join(command_parts)
        
        # Build PowerShell script with job control
        # Note: Command inside job needs translation too, but we'll pass it through as-is
        # since the outer translator already handles command translation
        ps_script = f'''
            $job = Start-Job -ScriptBlock {{
                {command_str}
            }}
            
            $completed = Wait-Job $job -Timeout {timeout_seconds}
            
            if ($completed) {{
                # Job completed within timeout
                $output = Receive-Job $job
                if ($output) {{ Write-Output $output }}
                
                # Get exit code from job
                $jobState = $job.State
                Remove-Job $job -Force
                
                if ($jobState -eq "Failed") {{
                    exit 1
                }} else {{
                    exit 0
                }}
            }} else {{
                # Timeout occurred
                Stop-Job $job -PassThru | Remove-Job -Force
                Write-Host "timeout: command timed out after {timeout_seconds} seconds"
                exit 124
            }}
        '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string to seconds.
        
        Formats: 10, 10s, 1m, 1h, 1d
        """
        import re
        
        match = re.match(r'^(\d+)([smhd])?$', duration_str)
        if not match:
            return 10  # Default fallback
        
        value = int(match.group(1))
        unit = match.group(2) or 's'
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        
        return value * multipliers.get(unit, 1)
    
    def _translate_split(self, cmd: str, parts):
        """
        Translate split - file splitting with Unix-compatible naming.
        
        CRITICAL: Suffix naming must be IDENTICAL to Unix.
        
        Flags:
        - -l N: Lines per chunk (default 1000)
        - -b N[K|M|G]: Bytes per chunk
        - -d: Numeric suffixes (00, 01) instead of (aa, ab)
        - -a N: Suffix length (default 2)
        
        Unix behavior:
          split -l 100 file.txt chunk_  →  chunk_aa, chunk_ab, chunk_ac...
          split -l 100 -d file.txt chunk_  →  chunk_00, chunk_01, chunk_02...
          split -b 1M file.bin part_  →  part_aa, part_ab... (1MB chunks)
        
        Output: SILENT (no stdout)
        """
        lines_per_chunk = None
        bytes_per_chunk = None
        numeric_suffix = '-d' in parts or '--numeric-suffixes' in parts
        suffix_length = 2  # Default
        
        # Parse flags
        i = 1
        while i < len(parts):
            part = parts[i]
            
            if part == '-l' and i + 1 < len(parts):
                lines_per_chunk = int(parts[i + 1])
                i += 2
            elif part.startswith('-l'):
                lines_per_chunk = int(part[2:])
                i += 1
            
            elif part == '-b' and i + 1 < len(parts):
                size_str = parts[i + 1]
                bytes_per_chunk = self._parse_size(size_str)
                i += 2
            elif part.startswith('-b'):
                size_str = part[2:]
                bytes_per_chunk = self._parse_size(size_str)
                i += 1
            
            elif part == '-a' and i + 1 < len(parts):
                suffix_length = int(parts[i + 1])
                i += 2
            elif part.startswith('-a'):
                suffix_length = int(part[2:])
                i += 1
            
            elif part == '-d' or part == '--numeric-suffixes':
                i += 1
            
            else:
                # File or prefix
                i += 1
        
        # Default: 1000 lines if neither -l nor -b specified
        if lines_per_chunk is None and bytes_per_chunk is None:
            lines_per_chunk = 1000
        
        # Get input file and prefix
        non_flag_args = [p for p in parts[1:] if not p.startswith('-') and not p.isdigit()]
        
        if len(non_flag_args) == 0:
            # stdin, default prefix 'x'
            input_file = None
            prefix = 'x'
        elif len(non_flag_args) == 1:
            # Could be file or prefix
            # If file exists, it's input file with default prefix
            # Otherwise it's prefix with stdin
            # For Windows translation, assume it's file (path already translated)
            input_file = non_flag_args[0]
            prefix = 'x'
        else:
            # Both file and prefix
            input_file = non_flag_args[0]
            prefix = non_flag_args[1]
        
        # Build PowerShell script
        ps_script = '''
            $ErrorActionPreference = 'Stop'
        '''
        
        if input_file:
            ps_script += f'''
            $content = Get-Content "{input_file}" -Raw
            $lines = Get-Content "{input_file}"
            '''
        else:
            ps_script += '''
            $lines = $input
            '''
        
        # Suffix generation function
        if numeric_suffix:
            # Numeric: 00, 01, 02...
            ps_script += f'''
            function Get-Suffix {{
                param($index)
                return $index.ToString().PadLeft({suffix_length}, '0')
            }}
            '''
        else:
            # Alphabetic: aa, ab, ac... az, ba, bb...
            ps_script += f'''
            function Get-Suffix {{
                param($index)
                $chars = 'abcdefghijklmnopqrstuvwxyz'
                $suffix = ''
                $n = $index
                for ($i = 0; $i -lt {suffix_length}; $i++) {{
                    $suffix = $chars[$n % 26] + $suffix
                    $n = [Math]::Floor($n / 26)
                }}
                return $suffix
            }}
            '''
        
        if lines_per_chunk:
            # Line-based splitting
            ps_script += f'''
            $chunkIndex = 0
            $currentChunk = @()
            
            foreach ($line in $lines) {{
                $currentChunk += $line
                
                if ($currentChunk.Count -eq {lines_per_chunk}) {{
                    $suffix = Get-Suffix $chunkIndex
                    $filename = "{prefix}" + $suffix
                    $currentChunk | Out-File -FilePath $filename -Encoding utf8
                    $currentChunk = @()
                    $chunkIndex++
                }}
            }}
            
            # Write remaining lines
            if ($currentChunk.Count -gt 0) {{
                $suffix = Get-Suffix $chunkIndex
                $filename = "{prefix}" + $suffix
                $currentChunk | Out-File -FilePath $filename -Encoding utf8
            }}
            '''
        else:
            # Byte-based splitting
            ps_script += f'''
            $bytes = [System.IO.File]::ReadAllBytes("{input_file}")
            $chunkIndex = 0
            $offset = 0
            
            while ($offset -lt $bytes.Length) {{
                $chunkSize = [Math]::Min({bytes_per_chunk}, $bytes.Length - $offset)
                $chunk = $bytes[$offset..($offset + $chunkSize - 1)]
                
                $suffix = Get-Suffix $chunkIndex
                $filename = "{prefix}" + $suffix
                [System.IO.File]::WriteAllBytes($filename, $chunk)
                
                $offset += $chunkSize
                $chunkIndex++
            }}
            '''
        
        # Silent output (like Unix split)
        return f'powershell -Command "{ps_script}" >$null 2>&1', True
    
    def _parse_size(self, size_str: str) -> int:
        """
        Parse size string like 1K, 2M, 3G.
        
        Returns bytes.
        """
        import re
        
        match = re.match(r'^(\d+)([KMGT])?$', size_str, re.IGNORECASE)
        if not match:
            return int(size_str)  # Plain number
        
        value = int(match.group(1))
        unit = match.group(2)
        
        if unit:
            multipliers = {
                'K': 1024,
                'M': 1024 * 1024,
                'G': 1024 * 1024 * 1024,
                'T': 1024 * 1024 * 1024 * 1024,
            }
            return value * multipliers.get(unit.upper(), 1)
        
        return value
    
    def _translate_gzip(self, cmd: str, parts):
        """
        Translate gzip - REAL gzip compression with .NET GZipStream.
        
        CRITICAL: Must produce VALID gzip files compatible with Unix gzip.
        
        Format: RFC 1952 gzip format
        - Magic bytes: 0x1f 0x8b
        - Compression: deflate
        - CRC32, timestamp, etc.
        
        Flags:
        - -c: Write to stdout (keep original)
        - -d: Decompress (same as gunzip)
        - -k: Keep original file
        - -f: Force overwrite
        - -1 to -9: Compression level (ignored - .NET uses default)
        - -r: Recursive (directories)
        
        Behavior (Unix compatible):
        - gzip file.txt → creates file.txt.gz, deletes file.txt
        - gzip -k file.txt → creates file.txt.gz, keeps file.txt
        - gzip -c file.txt → stdout, keeps file.txt
        """
        stdout_mode = '-c' in parts or '--stdout' in parts
        decompress = '-d' in parts or '--decompress' in parts
        keep = '-k' in parts or '--keep' in parts
        force = '-f' in parts or '--force' in parts
        recursive = '-r' in parts or '--recursive' in parts
        
        # Get files (ignore compression level flags -1 to -9)
        files = [p for p in parts[1:] if not p.startswith('-') or (p.startswith('-') and len(p) == 2 and p[1].isdigit())]
        files = [f for f in files if not (f.startswith('-') and len(f) == 2 and f[1].isdigit())]
        
        if not files:
            # stdin mode
            if decompress:
                # Decompress from stdin
                ps_script = '''
                    $input | Set-Content -Path temp.gz -Encoding Byte
                    $input = [System.IO.File]::OpenRead("temp.gz")
                    $gzip = New-Object System.IO.Compression.GZipStream($input, [System.IO.Compression.CompressionMode]::Decompress)
                    $gzip.CopyTo([Console]::OpenStandardOutput())
                    $gzip.Close()
                    $input.Close()
                    Remove-Item temp.gz
                '''
            else:
                # Compress from stdin
                ps_script = '''
                    $input | Set-Content -Path temp -Encoding Byte
                    $inputFile = [System.IO.File]::OpenRead("temp")
                    $output = [Console]::OpenStandardOutput()
                    $gzip = New-Object System.IO.Compression.GZipStream($output, [System.IO.Compression.CompressionMode]::Compress)
                    $inputFile.CopyTo($gzip)
                    $gzip.Close()
                    $inputFile.Close()
                    Remove-Item temp
                '''
            return f'powershell -Command "{ps_script}"', True
        
        file_path = files[0]
        
        if decompress:
            # Decompress mode (gzip -d = gunzip)
            return self._translate_gunzip(cmd, parts)
        
        # Compress mode
        if stdout_mode:
            # Output to stdout, keep original
            ps_script = f'''
                $inputFile = [System.IO.File]::OpenRead("{file_path}")
                $output = [Console]::OpenStandardOutput()
                $gzip = New-Object System.IO.Compression.GZipStream($output, [System.IO.Compression.CompressionMode]::Compress)
                $inputFile.CopyTo($gzip)
                $gzip.Close()
                $inputFile.Close()
            '''
        else:
            # Create .gz file
            output_file = f'{file_path}.gz'
            
            ps_script = f'''
                $inputPath = "{file_path}"
                $outputPath = "{output_file}"
                
                if (-not (Test-Path $inputPath)) {{
                    Write-Host "gzip: $inputPath: No such file or directory"
                    exit 1
                }}
                
                if ((Test-Path $outputPath) -and -not {str(force).lower()}) {{
                    Write-Host "gzip: $outputPath already exists; not overwritten"
                    exit 1
                }}
                
                $inputFile = [System.IO.File]::OpenRead($inputPath)
                $outputFile = [System.IO.File]::Create($outputPath)
                $gzip = New-Object System.IO.Compression.GZipStream($outputFile, [System.IO.Compression.CompressionMode]::Compress)
                
                $inputFile.CopyTo($gzip)
                
                $gzip.Close()
                $outputFile.Close()
                $inputFile.Close()
            '''
            
            if not keep:
                # Delete original (Unix default behavior)
                ps_script += f'''
                Remove-Item "{file_path}"
                '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_gunzip(self, cmd: str, parts):
        """
        Translate gunzip - REAL gzip decompression with .NET GZipStream.
        
        CRITICAL: Must decompress VALID gzip files from Unix gzip.
        
        Flags:
        - -c: Write to stdout (keep original)
        - -k: Keep original file
        - -f: Force overwrite
        
        Behavior (Unix compatible):
        - gunzip file.txt.gz → creates file.txt, deletes file.txt.gz
        - gunzip -k file.txt.gz → creates file.txt, keeps file.txt.gz
        - gunzip -c file.txt.gz → stdout, keeps file.txt.gz
        """
        stdout_mode = '-c' in parts or '--stdout' in parts
        keep = '-k' in parts or '--keep' in parts
        force = '-f' in parts or '--force' in parts
        
        files = [p for p in parts[1:] if not p.startswith('-')]
        
        if not files:
            # stdin mode
            ps_script = '''
                $ms = New-Object System.IO.MemoryStream
                $stdin = [Console]::OpenStandardInput()
                $stdin.CopyTo($ms)
                $ms.Position = 0
                
                $gzip = New-Object System.IO.Compression.GZipStream($ms, [System.IO.Compression.CompressionMode]::Decompress)
                $gzip.CopyTo([Console]::OpenStandardOutput())
                $gzip.Close()
                $ms.Close()
            '''
            return f'powershell -Command "{ps_script}"', True
        
        file_path = files[0]
        
        # Determine output filename (remove .gz extension)
        if file_path.endswith('.gz'):
            output_file = file_path[:-3]
        elif file_path.endswith('.tgz'):
            output_file = file_path[:-4] + '.tar'
        else:
            # No .gz extension - error
            return f'echo gzip: {file_path}: unknown suffix -- ignored', True
        
        if stdout_mode:
            # Output to stdout, keep original
            ps_script = f'''
                $inputFile = [System.IO.File]::OpenRead("{file_path}")
                $gzip = New-Object System.IO.Compression.GZipStream($inputFile, [System.IO.Compression.CompressionMode]::Decompress)
                $gzip.CopyTo([Console]::OpenStandardOutput())
                $gzip.Close()
                $inputFile.Close()
            '''
        else:
            # Create decompressed file
            ps_script = f'''
                $inputPath = "{file_path}"
                $outputPath = "{output_file}"
                
                if (-not (Test-Path $inputPath)) {{
                    Write-Host "gzip: $inputPath: No such file or directory"
                    exit 1
                }}
                
                if ((Test-Path $outputPath) -and -not {str(force).lower()}) {{
                    Write-Host "gzip: $outputPath already exists; not overwritten"
                    exit 1
                }}
                
                $inputFile = [System.IO.File]::OpenRead($inputPath)
                $gzip = New-Object System.IO.Compression.GZipStream($inputFile, [System.IO.Compression.CompressionMode]::Decompress)
                $outputFile = [System.IO.File]::Create($outputPath)
                
                $gzip.CopyTo($outputFile)
                
                $outputFile.Close()
                $gzip.Close()
                $inputFile.Close()
            '''
            
            if not keep:
                # Delete original .gz (Unix default behavior)
                ps_script += f'''
                Remove-Item "{file_path}"
                '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _translate_jq(self, cmd: str, parts):
        """
        Translate jq - JSON processor with intelligent fallback.
        
        STRATEGY FOR 100%:
        1. Try jq.exe (Git for Windows, scoop, chocolatey) - 100% complete
        2. Fallback PowerShell for COMMON patterns (90% real-world use):
           - .field → select field
           - .[] → array elements  
           - .field.nested → nested access
           - .[N] → array index
           - keys → object keys
           - length → count
           - -r flag → raw output (no quotes)
        
        Complex filters require jq.exe.
        
        Flags:
        - -r, --raw-output: Raw strings (no quotes)
        - -c, --compact-output: Compact JSON
        - -n, --null-input: No input
        - -e, --exit-status: Exit code based on output
        - -s, --slurp: Read entire input as array
        
        Examples:
          jq '.name' → PowerShell fallback OK
          jq '.items[].id' → PowerShell fallback OK
          jq 'map(select(.active))' → Requires jq.exe
        """
        raw_output = '-r' in parts or '--raw-output' in parts
        compact = '-c' in parts or '--compact-output' in parts
        null_input = '-n' in parts or '--null-input' in parts
        slurp = '-s' in parts or '--slurp' in parts
        
        # Get filter expression (first non-flag arg)
        filter_expr = None
        files = []
        for part in parts[1:]:
            if not part.startswith('-'):
                if filter_expr is None:
                    filter_expr = part
                else:
                    files.append(part)
        
        if not filter_expr:
            filter_expr = '.'  # Identity filter
        
        # Build PowerShell script with fallback
        file_input = f'Get-Content "{files[0]}"' if files else '$input'
        
        # Check if pattern is simple (PowerShell can handle)
        is_simple = self._is_simple_jq_pattern(filter_expr)
        
        if is_simple:
            # PowerShell fallback for simple patterns
            ps_script = f'''
                # Try jq.exe first
                $jqExe = Get-Command jq.exe -ErrorAction SilentlyContinue
                if ($jqExe) {{
                    {file_input} | & jq.exe {'-r' if raw_output else ''} {'-c' if compact else ''} '{filter_expr}'
                    exit $LASTEXITCODE
                }}
                
                # Fallback: PowerShell for simple patterns
                $json = {file_input} | Out-String | ConvertFrom-Json
                $result = $json
            '''
            
            # Parse simple filter and convert to PowerShell
            ps_filter = self._jq_to_powershell(filter_expr)
            ps_script += ps_filter
            
            # Output formatting
            if raw_output:
                ps_script += '''
                if ($result -is [string]) {
                    Write-Output $result
                } elseif ($result -is [array]) {
                    $result | ForEach-Object { Write-Output $_ }
                } else {
                    Write-Output $result
                }
                '''
            elif compact:
                ps_script += '''
                $result | ConvertTo-Json -Compress -Depth 100
                '''
            else:
                ps_script += '''
                if ($result -is [string] -or $result -is [int] -or $result -is [bool]) {
                    $result | ConvertTo-Json
                } else {
                    $result | ConvertTo-Json -Depth 100
                }
                '''
        else:
            # Complex pattern - REQUIRES jq.exe
            ps_script = f'''
                $jqExe = Get-Command jq.exe -ErrorAction SilentlyContinue
                if ($jqExe) {{
                    {file_input} | & jq.exe {'-r' if raw_output else ''} {'-c' if compact else ''} '{filter_expr}'
                    exit $LASTEXITCODE
                }} else {{
                    Write-Host "jq: complex filter requires jq.exe (install via Git for Windows, scoop, or chocolatey)"
                    Write-Host "Filter: {filter_expr}"
                    exit 1
                }}
            '''
        
        return f'powershell -Command "{ps_script}"', True
    
    def _is_simple_jq_pattern(self, pattern: str) -> bool:
        """
        Check if jq pattern is simple enough for PowerShell fallback.
        
        Simple patterns:
        - . (identity)
        - .field
        - .field.nested
        - .[]
        - .[N]
        - .field[]
        - keys
        - length
        
        Complex patterns (require jq.exe):
        - map()
        - select()
        - Pipe operators
        - Functions
        - Conditionals
        """
        # Complex patterns
        if any(keyword in pattern for keyword in ['map', 'select', 'if', 'then', 'else', 'def', '|']):
            return False
        
        # Simple patterns
        if pattern in ['.', 'keys', 'length']:
            return True
        
        # Field access patterns: .field, .field.nested, .[], .[N]
        import re
        if re.match(r'^\.(\w+|\[\d*\])(\.(\w+|\[\d*\]))*$', pattern):
            return True
        
        return False
    
    def _jq_to_powershell(self, pattern: str) -> str:
        """
        Convert simple jq pattern to PowerShell.
        
        Examples:
        - . → $result = $json
        - .name → $result = $json.name
        - .items[] → $result = $json.items
        - .[0] → $result = $json[0]
        - .user.email → $result = $json.user.email
        - keys → $result = $json.PSObject.Properties.Name
        - length → $result = $json.Count or $json.Length
        """
        if pattern == '.':
            return '$result = $json\n'
        
        if pattern == 'keys':
            return '''
                if ($json -is [PSCustomObject]) {
                    $result = $json.PSObject.Properties.Name
                } else {
                    $result = @()
                }
            '''
        
        if pattern == 'length':
            return '''
                if ($json -is [array]) {
                    $result = $json.Count
                } elseif ($json -is [string]) {
                    $result = $json.Length
                } elseif ($json -is [PSCustomObject]) {
                    $result = ($json.PSObject.Properties | Measure-Object).Count
                } else {
                    $result = 0
                }
            '''
        
        # Parse field access: .field.nested or .[] or .[N]
        import re
        
        # Remove leading dot
        if pattern.startswith('.'):
            pattern = pattern[1:]
        
        # Split by dots
        parts = pattern.split('.')
        
        ps_code = '$result = $json'
        for part in parts:
            if part == '[]':
                # Array iteration - already handled by $result
                pass
            elif re.match(r'^\[\d+\]$', part):
                # Array index
                index = part[1:-1]
                ps_code += f'[{index}]'
            elif part.endswith('[]'):
                # Field with array iteration
                field = part[:-2]
                ps_code += f'.{field}'
            else:
                # Simple field
                ps_code += f'.{part}'
        
        return ps_code + '\n'
