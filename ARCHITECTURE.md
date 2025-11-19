# bash_tool Architecture

Unix command execution on Windows through intelligent translation and emulation.

---

## System Overview

**bash_tool** enables Unix/bash command execution on Windows by combining multiple strategies:
- Path translation (Unix ↔ Windows)
- Command translation (Unix → PowerShell/cmd.exe)
- Native binary detection (grep.exe, awk.exe, etc.)
- Git Bash integration (for complex POSIX operations)
- Security sandbox (workspace containment)

**Core Stats:**
- 73 Unix commands emulated
- 5669 lines of translation code
- 140+ pipeline patterns recognized
- 13 modular components (~8600 lines total)

---

## Architecture Layers

The system is organized in 5 distinct architectural layers:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: API Entry Point                                    │
│ BashToolExecutor - Facade for external API                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ Layer 4: Orchestration                                      │
│ CommandExecutor - Preprocessing + Strategy Coordination     │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
┌────────▼──────┐  ┌──────▼──────┐  ┌──────▼──────────┐
│ Layer 3:      │  │ Layer 3:    │  │ Layer 2:        │
│ MACRO         │  │ MICRO       │  │ Translation     │
│ Strategy      │  │ Strategy    │  │                 │
│               │  │             │  │                 │
│ Pipeline      │  │ Execute     │  │ Command         │
│ Strategy      │  │ Unix        │  │ Emulator        │
│               │  │ Single      │  │                 │
│               │  │ Command     │  │ Path            │
│               │  │             │  │ Translator      │
│               │  │             │  │                 │
│               │  │             │  │ Sandbox         │
│               │  │             │  │ Validator       │
└───────┬───────┘  └──────┬──────┘  └─────────────────┘
        │                 │
        └────────┬────────┘
                 │
┌────────────────▼─────────────────────────────────────────────┐
│ Layer 1: Execution                                           │
│ ExecutionEngine - Single subprocess execution point          │
└──────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

**Layer 5 - API Entry Point:**
- BashToolExecutor: Tool registration, result formatting, high-level orchestration

**Layer 4 - Orchestration:**
- CommandExecutor: Bash preprocessing (expansions, substitutions), strategy dispatch

**Layer 3 - Strategy (MACRO):**
- PipelineStrategy: Analyze entire pipeline, pattern matching (140+ patterns), decide strategy

**Layer 3 - Strategy (MICRO):**
- ExecuteUnixSingleCommand: Single atomic command execution, priority chain

**Layer 2 - Translation:**
- CommandEmulator: Unix→PowerShell translation (73 commands)
- PathTranslator: Unix↔Windows path mapping
- SandboxValidator: Security validation (workspace containment)

**Layer 1 - Execution:**
- ExecutionEngine: Single subprocess point, environment management, capability detection

---

## Component Details

### Entry Point

#### BashToolExecutor
*Location: `src/bash_tool/bash_tool_executor.py` (170 lines)*

Top-level entry point. Thin orchestrator delegating to specialized components.

**Key Responsibilities:**
- Path translation orchestration (Unix → Windows → Unix)
- Security orchestration (sandbox validation)
- Result formatting (bash_tool API contract)
- Timeout management

**Pattern:** Facade

**See docstring for:** DATA FLOW, API CONTRACT, USAGE PATTERN

---

### Orchestration Layer

#### CommandExecutor
*Location: `src/bash_tool/command_executor.py` (1094 lines)*

Central coordinator for preprocessing and execution strategy.

**Key Responsibilities:**
- Bash pattern preprocessing (alias, tilde, variables, command substitution, braces, arithmetic, here-docs)
- Strategic coordination (delegate to PipelineStrategy or ExecuteUnixSingleCommand)
- Recursive execution (command substitution calls execute() recursively)

**Critical Feature:** Preprocessing happens BEFORE translation (enables command substitution)

**Pattern:** Coordinator + Template Method + Recursive

**See docstring for:** PREPROCESSING PIPELINE, RECURSIVE PATTERN, DATA FLOW EXAMPLE

---

### Strategy Layers

#### PipelineStrategy (MACRO)
*Location: `src/bash_tool/pipeline_strategy.py` (346 lines)*

MACRO level analyzer for pipelines and command chains.

**Key Responsibilities:**
- Analyze entire pipeline structure (pipes, chains, redirections, process substitution)
- Pattern matching (140+ regex patterns)
- Decide execution strategy (BASH_REQUIRED, BASH_PREFERRED, POWERSHELL, SINGLE, FAIL)
- Provide fallback strategies

**Pattern Categories:**
- BASH_REQUIRED (55+ patterns): find|xargs, awk|*, sed|*, process substitution
- BASH_PREFERRED (35+ patterns): sort|uniq, head|tail, grep|sort
- POWERSHELL_OK (10+ patterns): echo|base64, cat|base64

**Pattern:** Strategy + Factory + Pattern Matching

**See docstring for:** STRATEGY TYPES, PATTERN MATCHING, ANALYSIS FLOW

#### ExecuteUnixSingleCommand (MICRO)
*Location: `src/bash_tool/execute_unix_single_command.py` (201 lines)*

MICRO level executor for single atomic commands.

**Execution Priority Chain:**
1. Native Binary (grep.exe, awk.exe) → Best performance
2. Quick Script (< 20 lines PowerShell) → Fast inline
3. Bash Git (if available) → POSIX compatibility
4. Heavy Script (> 20 lines PowerShell) → Full emulation

**Pattern:** Strategy + Chain of Responsibility + Adapter

**See docstring for:** STRATEGY DECISION TREE, STRATEGY RATIONALE

---

### Translation Layer

#### CommandEmulator
*Location: `src/bash_tool/command_emulator.py` (5669 lines)*

Massive translation engine: Unix commands → PowerShell scripts.

**Command Categories:**
- **SIMPLE** (21 commands, < 20 lines): pwd, cd, mkdir, rm, mv, chmod, etc.
- **MEDIUM** (18 commands, 20-100 lines): cat, ls, cp, grep, head, tail, wc, etc.
- **COMPLEX** (34 commands, > 100 lines): curl(239), sed(233), awk(211), diff(212), jq(212), grep(124), etc.

**Total:** 73 Unix commands translated

**Pattern:** Command + Adapter

**See docstring for:** TRANSLATION CATEGORIES, EXAMPLE TRANSLATIONS, SEMANTIC PRESERVATION

#### PathTranslator
*Location: `src/bash_tool/path_translator.py` (320 lines)*

Unix ↔ Windows path translation with virtual filesystem mapping.

**Virtual Unix Structure:**
```
/home/claude              → workspace_root/claude/
/mnt/user-data/uploads    → workspace_root/uploads/
/mnt/user-data/outputs    → workspace_root/outputs/
```

**Pattern:** Translator + Bidirectional Mapping

**See docstring in file for details**

#### SandboxValidator
*Location: `src/bash_tool/sandbox_validator.py` (160 lines)*

Security layer enforcing workspace containment.

**Validation Checks:**
1. Dangerous commands blacklist (format, reg, shutdown, diskpart, etc.)
2. Absolute paths outside workspace
3. Drive access restrictions
4. Restricted commands validation (del, move, copy)

**Pattern:** Validator + Strategy

**See docstring for:** SECURITY MODEL, VALIDATION FLOW

---

### Execution Layer

#### ExecutionEngine
*Location: `src/bash_tool/execution_engine.py` (480 lines)*

Single subprocess execution point for entire system.

**Execution Methods:**
- `execute_bash()` - Via Git Bash (bash.exe -c "command")
- `execute_native()` - Native binary (grep.exe args)
- `execute_powershell()` - PowerShell script
- `execute_cmd()` - cmd.exe command
- `execute_python()` - Python script (with venv support)

**Environment Management:**
- Python venv detection & setup
- Native binary detection (grep.exe, awk.exe, sed.exe, diff.exe, tar.exe, jq.exe)
- Capability caching (self.capabilities dict)

**Pattern:** Facade + Strategy + Singleton (conceptual)

**See docstring for:** EXECUTION METHODS, CAPABILITY DETECTION, WHY SINGLE POINT?

---

### Data Structures

#### PipelineAnalysis (Dataclass)
*Location: `src/bash_tool/pipeline_analysis.py`*

Result of pipeline structural analysis.

**Fields:** has_pipeline, has_chain, has_redirection, has_stderr_redir, has_process_subst, matched_pattern, complexity_level, command_count, command_names

#### ExecutionStrategy (Dataclass)
*Location: `src/bash_tool/execution_strategy.py`*

Execution strategy decision.

**Fields:** strategy_type, can_split, split_points, reason, fallback_strategy

**Helper Methods:** has_fallback(), is_bash_strategy()

#### Constants
*Location: `src/bash_tool/constants.py`*

Command classifications.

**Key Sets:**
- BASH_GIT_UNSUPPORTED_COMMANDS: Commands Git Bash cannot execute (jq, wget, curl, timeout, checksums, zip/unzip, watch)
- GITBASH_PASSTHROUGH_COMMANDS: Commands that should ALWAYS use bash.exe (find, awk, sed, grep, diff, tar, sort, uniq, split, join, comm, paste)

#### ToolExecutor (ABC)
*Location: `src/bash_tool/tool_executor.py`*

Abstract base class for tool executors. Defines interface: execute(), get_definition()

---

## Data Flow Examples

### Example 1: Simple Command (cat file.txt)

```
Input: "cat file.txt"

Flow:
1. BashToolExecutor.execute()
   └→ PathTranslator.translate_paths_in_string() [Unix → Windows]
   └→ SandboxValidator.validate_command() [OK]

2. CommandExecutor.execute()
   └→ No preprocessing needed

3. PipelineStrategy.analyze_pipeline()
   └→ No pipeline, complexity: LOW
   └→ strategy_type: SINGLE

4. ExecuteUnixSingleCommand.execute_single()
   └→ Parse: cmd_name = "cat"
   └→ Check native binary: NO
   └→ Check quick command: YES (< 20 lines)
   └→ CommandEmulator.emulate_command("cat file.txt")
       └→ Returns: "Get-Content file.txt"

5. ExecutionEngine.execute_powershell("Get-Content file.txt")
   └→ subprocess.run(['powershell', '-Command', 'Get-Content file.txt'])

6. Result formatting and path translation back

Result: PowerShell Get-Content execution
```

### Example 2: Native Binary (grep -r pattern .)

```
Input: "grep -r pattern ."

Flow:
1. BashToolExecutor → CommandExecutor → PipelineStrategy
   └→ strategy_type: SINGLE

2. ExecuteUnixSingleCommand.execute_single()
   └→ Parse: cmd_name = "grep"
   └→ Check native: ExecutionEngine.is_available('grep') → TRUE
   └→ Strategy: Native Binary (PRIORITY 1)

3. ExecutionEngine.execute_native('grep', ['-r', 'pattern', '.'])
   └→ subprocess.run(['grep.exe', '-r', 'pattern', '.'])

Result: Native grep.exe execution (best performance, zero translation)
```

### Example 3: Complex Pipeline

```
Input: "find . -type f -name '*.py' | xargs grep -l 'import'"

Flow:
1. BashToolExecutor → CommandExecutor (no preprocessing)

2. PipelineStrategy.analyze_pipeline()
   └→ Detects: has_pipeline=True, command_count=2
   └→ Pattern match: r'find.*\|.*xargs' → BASH_REQUIRED
   └→ Reason: "Pipeline pattern requires bash.exe: find.*\|.*xargs"

3. ExecutionStrategy: strategy_type=BASH_REQUIRED

4. ExecutionEngine.execute_bash(bash_path, command)
   └→ subprocess.run([bash_path, '-c', "find . -type f -name '*.py' | xargs grep -l 'import'"])

Result: Full bash.exe execution (perfect POSIX compatibility)
```

### Example 4: Command Substitution (Recursive)

```
Input: "echo $(ls -la ~/)"

Flow:
1. BashToolExecutor → CommandExecutor

2. CommandExecutor preprocessing:
   └→ STEP 0.1: Expand tilde: "echo $(ls -la /home/claude/)"
   └→ STEP 0.3: Command substitution detected
       └→ Extract: "ls -la /home/claude/"
       └→ RECURSIVE CALL: execute("ls -la /home/claude/")
           └→ PipelineStrategy → ExecuteUnixSingleCommand
           └→ CommandEmulator translates ls
           └→ ExecutionEngine executes
           └→ Returns: "file1\nfile2\nfile3"
       └→ Substitute result: "echo file1 file2 file3"

3. Continue with "echo file1 file2 file3"
   └→ PipelineStrategy: SINGLE
   └→ ExecuteUnixSingleCommand: Quick command
   └→ ExecutionEngine executes

Result: Preprocessed command with substitution applied
```

---

## Design Patterns

### Architectural Patterns

**Layered Architecture**
- 5 distinct layers with clear separation of concerns
- Each layer depends only on layers below
- Enables independent testing and evolution

**Facade Pattern** (BashToolExecutor)
- Simple interface hiding complex subsystem
- Delegates to specialized components

**Strategy Pattern** (Multiple locations)
- PipelineStrategy: Different strategies based on pipeline characteristics
- ExecuteUnixSingleCommand: Different execution strategies for single commands
- ExecutionEngine: Different execution methods (bash, native, powershell, cmd, python)

**Chain of Responsibility** (ExecuteUnixSingleCommand)
- Try execution strategies in priority order
- Native Binary → Quick Script → Bash Git → Heavy Script

**Template Method** (CommandExecutor.execute(), BashToolExecutor.execute())
- Fixed orchestration pipeline with variable steps

**Factory Pattern** (PipelineStrategy)
- Creates ExecutionStrategy objects based on analysis

**Command Pattern** (CommandEmulator)
- Each Unix command has dedicated translator method
- 73 commands in command_map

**Adapter Pattern** (CommandEmulator)
- Adapts Unix command semantics to PowerShell

**Recursive Pattern** (CommandExecutor)
- execute() can call itself for command substitution

**Coordinator Pattern** (CommandExecutor)
- Orchestrates multiple specialized components

---

## Key Architectural Decisions

### 1. Why Single ExecutionEngine?

**Decision:** All subprocess calls go through ExecutionEngine (no direct subprocess.run() elsewhere)

**Rationale:**
- **Test mode:** Switch test/production in ONE place
- **Logging:** All executions visible in centralized logs
- **Metrics:** Count execution types (bash vs native vs powershell)
- **Environment:** Virtual environment activation in ONE place
- **Error handling:** Consistent subprocess error management

**Benefit:** Single point of truth for execution environment

### 2. Why Unified CommandEmulator?

**Before:** 3 separate classes (SimpleTranslator, PipelineTranslator, EmulativeTranslator)
- Separated by "line count" (< 20, 20-100, > 100)
- No conceptual difference (all emulate Unix commands)

**After:** Single CommandEmulator with 73 commands in one command_map

**Rationale:**
- Separation was arbitrary (not architectural)
- All translators do same thing: Unix → PowerShell
- Unified method: emulate_command()

**Benefit:** Eliminates artificial separation, clearer architecture

### 3. Why Separate MACRO/MICRO Strategy?

**MACRO (PipelineStrategy):**
- Analyzes ENTIRE pipeline structure
- Pattern matches complex scenarios
- Decides if bash.exe required

**MICRO (ExecuteUnixSingleCommand):**
- Handles SINGLE atomic command
- Priority chain: Native → Quick → Bash → Heavy
- Tactical decisions

**Rationale:**
- Different levels of decision-making
- Pipeline analysis ≠ single command execution
- Separation of concerns

**Benefit:** Clear responsibility boundaries, easier testing

### 4. Why Preprocessing Before Translation?

**Decision:** CommandExecutor does all bash preprocessing BEFORE translation/execution

**Rationale:**
- Command substitution needs to EXECUTE first, THEN substitute result
- Brace expansion creates multiple commands to translate
- Variable expansion must use bash semantics
- Tilde expansion needs Unix home directory concept

**Example:** `echo $(ls ~/)`
1. Expand tilde: `echo $(ls /home/claude/)`
2. Execute substitution: execute("ls /home/claude/") → "file1 file2"
3. Substitute: `echo file1 file2`
4. Translate and execute

**Benefit:** Correct bash semantics, enables recursive execution

### 5. Why 140+ Pipeline Patterns?

**Decision:** PipelineStrategy contains 140+ regex patterns for common pipeline scenarios

**Rationale:**
- Real-world pipelines follow common patterns
- Pattern matching faster than generic analysis
- Can optimize per-pattern (some REQUIRE bash, some work in PowerShell)
- Provides fallback strategies per pattern

**Categories:**
- 55+ BASH_REQUIRED patterns (find|xargs, process substitution, etc.)
- 35+ BASH_PREFERRED patterns (sort|uniq, head|tail)
- 10+ POWERSHELL_OK patterns (simple transformations)

**Benefit:** Intelligent strategy selection, optimal performance/compatibility balance

---

## System Metrics

### Code Organization

| Component | Lines | Description |
|-----------|-------|-------------|
| CommandEmulator | 5669 | Unix→PowerShell translator (73 commands) |
| CommandExecutor | 1094 | Preprocessing + orchestration |
| ExecutionEngine | 480 | Subprocess management |
| PipelineStrategy | 346 | MACRO pipeline analysis |
| PathTranslator | 320 | Unix↔Windows path mapping |
| ExecuteUnixSingleCommand | 201 | MICRO single command |
| BashToolExecutor | 170 | API entry point |
| SandboxValidator | 160 | Security validation |
| **Total** | **~8600** | 13 modular components |

### Command Coverage

| Category | Count | Lines/Cmd | Examples |
|----------|-------|-----------|----------|
| SIMPLE | 21 | < 20 | pwd, cd, mkdir, rm, mv, chmod |
| MEDIUM | 18 | 20-100 | cat, ls, cp, grep, head, tail, wc |
| COMPLEX | 34 | > 100 | curl, sed, awk, diff, jq, find |
| **Total** | **73** | - | Full Unix command suite |

### Strategy Distribution

| Strategy Type | Use Case | Execution Method |
|---------------|----------|------------------|
| BASH_REQUIRED | Process substitution, complex pipelines | bash.exe (perfect compatibility) |
| BASH_PREFERRED | Multi-stage text processing | bash.exe with PowerShell fallback |
| NATIVE | Binary available (grep.exe, awk.exe) | Direct binary (best performance) |
| POWERSHELL | Simple commands, emulated commands | PowerShell script |

---

## Testing Strategy

### Component Testing

Each layer can be tested independently:

**Layer 1 (ExecutionEngine):**
- Test mode: Commands logged, not executed
- Capability detection mocked
- Environment setup isolated

**Layer 2 (Translation):**
- CommandEmulator: 73 command translators testable independently
- PathTranslator: Bidirectional translation tests
- SandboxValidator: Security boundary tests

**Layer 3 (Strategy):**
- PipelineStrategy: Pattern matching tests (140+ patterns)
- ExecuteUnixSingleCommand: Priority chain tests

**Layer 4 (Orchestration):**
- CommandExecutor: Preprocessing tests (expansions, substitutions)
- Integration with strategy layers

**Layer 5 (API):**
- BashToolExecutor: End-to-end API contract tests

### Test Mode

All components support `test_mode=True`:
- ExecutionEngine: Logs commands without executing
- Returns mock CompletedProcess
- Capabilities all set to True
- Enables fast unit testing without subprocess overhead

---

## Future Enhancements

### Pipeline Splitting (HYBRID Strategy)

Currently, entire pipelines execute as one unit. Future optimization:

```python
# Current: "find . | grep TODO | wc -l" → bash.exe (entire pipeline)

# Future: Split at | boundaries
#   Part 1: "find ." → bash.exe or native find
#   Part 2: "grep TODO" → native grep.exe or PowerShell
#   Part 3: "wc -l" → PowerShell
#   Pipe results between parts
```

**Benefit:** Hybrid execution using best method per command

### Dynamic Fallback Learning

Track success rates per strategy:
- If BASH_PREFERRED consistently fails → switch to BASH_REQUIRED
- If PowerShell emulation works well → prefer over bash.exe
- Adapt to environment capabilities

### Performance Profiling

Instrument ExecutionEngine to track:
- Execution time per strategy type
- Translation overhead
- Subprocess spawn time
- Cache translation results for repeated commands

---

## Documentation Map

**This file (ARCHITECTURE.md):** High-level architecture overview

**In-code docstrings:** Detailed implementation documentation (source of truth)
- `bash_tool_executor.py`: API contract, DATA FLOW
- `command_executor.py`: Preprocessing pipeline, recursive execution
- `pipeline_strategy.py`: Strategy types, pattern matching
- `execute_unix_single_command.py`: Priority chain, strategy rationale
- `command_emulator.py`: Translation categories, semantic preservation
- `execution_engine.py`: Execution methods, capability detection
- `path_translator.py`: Virtual filesystem mapping
- `sandbox_validator.py`: Security model, validation flow

**For implementation details, see in-code docstrings in `src/bash_tool/`**

---

*Last updated: 2025-11-19*
*Architecture corresponds to refactored modular structure (13 components)*
