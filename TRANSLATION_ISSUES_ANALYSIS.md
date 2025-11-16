# TRANSLATION ISSUES - SYSTEMATIC ANALYSIS

Analysis of 37 real-world bash commands showing translation problems.

## 🔴 CRITICAL ISSUE #1: Command Substitution Not Executed

### Problem
`$(command)` is NOT executed - the command string is used literally.

### Examples
```bash
# Test: grep -r "import" $(find . -name "*.py")
# Expected: Execute find, use results as args to grep
# Actual: grep -r "import" . -name "*.py"
#         ↑ "find" removed, args used literally!

# Test: wc -l $(find . -name "*.py" -type f)
# Expected: Execute find, count lines in all .py files
# Actual: find /c /v "" "."
#         ↑ Completely wrong!

# Test: echo "Files: $(find . -type f -name "*.py" | wc -l)"
# Expected: Execute find|wc, echo the count
# Actual: echo "Files: . -type f -name "*.py" | echo Error: wc..."
#         ↑ find not executed, wc wrong
```

### Root Cause
Command substitution `$(...)` is being processed but the inner command is NOT executed.
The command string inside $() is being treated as literal text.

### Impact
**CRITICAL** - This breaks ALL dynamic command construction patterns Claude uses.

---

## 🔴 CRITICAL ISSUE #2: Pipeline Commands Translated to Errors

### Problem
`head`, `tail`, `wc` in pipelines → translated to "echo Error: requires filename"

### Examples
```bash
# Test: git log --oneline | head -20 | awk '{print $1}'
# Translated: git log --oneline | echo Error: head requires filename | awk...

# Test: grep 'ERROR' log.txt | wc -l
# Translated: grep 'ERROR' log.txt | echo Error: wc requires filename

# Test: find ... | tail -1
# Translated: find ... | echo Error: tail requires filename
```

### Root Cause
head/tail/wc translation logic checks for filename arguments.
In pipelines, they receive stdin, not files.
But translator doesn't recognize pipeline context.

### Impact
**CRITICAL** - Breaks ALL pipelines with head/tail/wc (extremely common).

---

## 🔴 CRITICAL ISSUE #3: Process Substitution Broken

### Problem
`<(command)` loses parentheses, becomes `< command`

### Examples
```bash
# Test: diff <(git show HEAD:file) <(cat file)
# Translated: diff < git show HEAD:file < cat file
#             ↑ Lost parentheses! Wrong syntax!

# Test: comm -12 <(sort file1) <(sort file2)
# Translated: comm -12 < sort file1 < sort file2
#             ↑ Becomes stdin redirect, not process substitution!
```

### Root Cause
Process substitution `<(...)` is being parsed as input redirect `<`.
The parentheses and command execution are lost.

### Impact
**HIGH** - Breaks file comparison workflows Claude uses.

---

## 🟡 ISSUE #4: find -exec → Get-ChildItem (Unknown Command)

### Problem
`find ... -exec` translates to PowerShell `Get-ChildItem` but then fails.

### Examples
```bash
# Test: find . -name "*.py" -exec grep -l "class" {} \;
# Translated: Get-ChildItem . -Recurse | ForEach-Object { grep -l "class" $_.FullName }
# Warning: Unknown command: Get-ChildItem - passing through
# Final: cmd /c Get-ChildItem...
#        ↑ Get-ChildItem doesn't work in cmd!
```

### Root Cause
1. Translator correctly converts find → Get-ChildItem (PowerShell)
2. But then passes to `cmd /c` instead of `powershell -Command`
3. Get-ChildItem is PowerShell-only, fails in cmd

### Impact
**HIGH** - Breaks ALL find -exec patterns (very common).

---

## 🟡 ISSUE #5: Heredoc Variable Expansion

### Problem
Heredocs with unquoted delimiters should expand variables, but don't.

### Examples
```bash
# Test: cat <<EOF
#       HOME is: $HOME
#       EOF
# Expected: Expand $HOME to actual path
# Actual: Writes literal "$HOME"
# Warning: "bash.exe not available - writing LITERAL content"
```

### Root Cause
Variable expansion in heredocs requires bash execution.
Without bash.exe, falls back to literal content.

### Impact
**MEDIUM** - Breaks heredoc templating (less common).

---

## 🟡 ISSUE #6: grep -o Flag Lost

### Problem
`grep -o` (only matching) loses the -o flag in translation.

### Examples
```bash
# Test: echo "Total: $(grep -o "def [a-z_]*" file.py | wc -l)"
# Translated: echo "Total: -o "def [a-z_]*" file.py | ..."
#             ↑ -o flag became literal text!
```

### Root Cause
grep translation doesn't handle -o flag correctly.

### Impact
**MEDIUM** - Breaks pattern extraction workflows.

---

## 📊 ISSUE PRIORITY

### 🔴 P0 - MUST FIX (Breaks core Claude workflows)
1. **Command substitution not executed** - $(find ...) → literal
2. **Pipeline head/tail/wc errors** - | head → echo Error
3. **Process substitution broken** - <(cmd) → < cmd

### 🟡 P1 - SHOULD FIX (Common use cases)
4. **find -exec → wrong shell** - Get-ChildItem in cmd
5. **Heredoc expansion** - Variables not expanded
6. **grep -o flag** - Lost in translation

---

## 🎯 FIX STRATEGY

### Fix #1: Command Substitution Execution
**Location**: Command preprocessing, before translation
**Action**:
1. Detect `$(...)`
2. Extract inner command
3. Execute it (in testmode: simulate with placeholder)
4. Replace `$(...)` with result

### Fix #2: Pipeline Context Detection
**Location**: head/tail/wc translation
**Action**:
1. Check if command is in pipeline (detect `|` before)
2. If in pipeline: use stdin version (PowerShell: `Select-Object`)
3. If standalone: use file version

### Fix #3: Process Substitution Support
**Location**: Command preprocessing
**Action**:
1. Detect `<(...)`
2. Create temp file path
3. Execute command, write to temp file
4. Replace `<(...)` with temp file path

### Fix #4: Shell Selection for PowerShell Commands
**Location**: Execution strategy
**Action**:
1. Detect PowerShell-specific commands (Get-ChildItem, etc.)
2. Use `powershell -Command` instead of `cmd /c`

### Fix #5: Heredoc Variable Expansion
**Location**: Heredoc processing
**Action**:
1. Detect unquoted delimiter
2. Expand variables before writing temp file
3. Use environment variables from self.env

### Fix #6: grep -o Support
**Location**: grep translation
**Action**:
1. Parse -o flag
2. Use PowerShell: `Select-String | ForEach-Object { $_.Matches.Value }`

---

## 📈 EXPECTED IMPROVEMENT

After fixes:
- Command substitution: ✓ Executed properly
- Pipeline commands: ✓ Correct stdin handling
- Process substitution: ✓ Temp file mechanism
- find -exec: ✓ Correct PowerShell execution
- Heredoc expansion: ✓ Variables expanded
- grep -o: ✓ Flag handled

**Estimated pass rate after fixes: 90%+** (from current translation issues)
