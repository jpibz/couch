# PREPROCESSING METHODS DESTINATION ANALYSIS

## Analisi Dettagliata - Destinazione 42 Metodi Preprocessing/Expansion/Control

**Data**: 2025-11-18
**Contesto**: Questi metodi sono attualmente duplicati tra BashToolExecutor e CommandTranslator
**Problema**: Nell'architettura finale, nessuna di queste due classi è la destinazione corretta

---

## DECISIONE ARCHITETTURALE

### ⚠️ MANCA UNA CLASSE NELL'ARCHITETTURA FINALE

Analizzando i 42 metodi di preprocessing, variable expansion e control structures, emerge che:

1. **NON appartengono a BashToolExecutor** - deve essere thin coordinator MCP
2. **NON appartengono a CommandTranslator** - sarà eliminata
3. **NON appartengono ai Translators** (Simple/Emulative/Pipeline) - traducono comandi, non processano sintassi bash
4. **NON appartengono a CommandExecutor** - thin orchestration layer
5. **NON appartengono a PipelineStrategy** - analizza pipeline, non processa sintassi
6. **NON appartengono a ExecuteUnixSingleCommand** - esegue comandi singoli

### ✅ SOLUZIONE: Creare Nuova Classe **BashPreprocessor**

**Nuova classe nell'architettura finale**:

```
BashPreprocessor
│
├─ Preprocessing (14 metodi)
│  └─ Heredocs, substitution, command grouping, etc.
│
├─ Variable Expansion (20 metodi)
│  └─ ${var}, $(()), ${var:-default}, brace expansion, etc.
│
└─ Control Structures (8 metodi)
   └─ if/for/while conversion, test commands
```

**Responsabilità**:
- Processare sintassi bash PRIMA dell'esecuzione
- Espandere variabili bash
- Convertire control structures bash → PowerShell
- Gestire command/process substitution

**Posizione nel flusso**:

```
BashToolExecutor.execute(raw_command)
  ↓
  🆕 BashPreprocessor.preprocess(raw_command)
     - Variable expansion
     - Heredocs & substitution
     - Control structures conversion
  ↓
CommandExecutor.execute(preprocessed_command)
  ↓
PipelineStrategy.analyze_pipeline()
  ↓
ExecuteUnixSingleCommand
```

---

## DETTAGLIO MAPPING - 42 METODI

### CATEGORIA 1: PREPROCESSING (14 metodi) → BashPreprocessor

| # | Metodo | Presente In | Destinazione Finale | Sub-categoria |
|---|--------|-------------|-------------------|---------------|
| 1 | `_adapt_for_powershell` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Bash→PS Conversion |
| 2 | `_bash_to_powershell` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Bash→PS Conversion |
| 3 | `_cleanup_temp_files` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Utility |
| 4 | `_needs_powershell` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Decision Helper |
| 5 | `_preprocess_test_commands` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Test Preprocessing |
| 6 | `_process_command_grouping` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Command Grouping |
| 7 | `_process_command_substitution_recursive` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Substitution |
| 8 | `_process_escape_sequences` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Escape Sequences |
| 9 | `_process_find_exec` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Find -exec |
| 10 | `_process_heredocs` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Heredocs |
| 11 | `_process_subshell` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Subshells |
| 12 | `_process_substitution` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Process Substitution |
| 13 | `_process_xargs` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Xargs |
| 14 | `_translate_substitution_content` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Substitution Content |

**Rationale**:
- Tutti questi metodi processano sintassi bash PRIMA dell'esecuzione
- Gestiscono costrutti bash-specific (heredocs, substitution, grouping)
- Devono operare sul comando RAW prima che arrivi a CommandExecutor
- BashPreprocessor è la classe dedicata a questo preprocessing

**Note Speciali**:
- `_needs_powershell`: Decision helper che determina se comando richiede PowerShell. Potrebbe andare in PipelineStrategy, ma per YAGNI resta in BashPreprocessor dove ha accesso al context del preprocessing.

---

### CATEGORIA 2: VARIABLE EXPANSION (20 metodi) → BashPreprocessor

| # | Metodo | Presente In | Destinazione Finale | Type |
|---|--------|-------------|-------------------|------|
| 1 | `_expand_aliases` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Alias Expansion |
| 2 | `_expand_braces` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Brace Expansion |
| 3 | `_expand_variables` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Main Variable Expansion |
| 4 | `expand_arithmetic` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | $((expr)) |
| 5 | `expand_assign` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | ${var:=value} |
| 6 | `expand_case` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | ${var^^}, ${var,,} |
| 7 | `expand_default` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | ${var:-default} |
| 8 | `expand_grouping` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | {...} grouping |
| 9 | `expand_length` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | ${#var} |
| 10 | `expand_remove_prefix` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | ${var#pattern} |
| 11 | `expand_remove_suffix` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | ${var%pattern} |
| 12 | `expand_simple_brace` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | {a,b,c} |
| 13 | `expand_simple_var` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | $var, ${var} |
| 14 | `expand_single_brace` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | {1..10} |
| 15 | `expand_substitution` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | $(cmd) substitution |
| 16 | `find_substitutions` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Find $() and `` |
| 17 | `is_complex_substitution` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Detect complex cases |
| 18 | `remove_subshell` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Remove subshell syntax |
| 19 | `replace_input_substitution` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Replace <() |
| 20 | `replace_output_substitution` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Replace >() |

**Rationale**:
- Variable expansion è preprocessing bash fondamentale
- Deve avvenire PRIMA che il comando venga analizzato da PipelineStrategy
- Tutti questi metodi sono strettamente correlati (variable/parameter expansion bash)
- BashPreprocessor centralizza tutta la logica di expansion

**Pattern Bash gestiti**:
- Simple: `$var`, `${var}`
- Default: `${var:-default}`, `${var:=value}`
- Length: `${#var}`
- Substring: `${var:offset:length}`
- Pattern removal: `${var#pattern}`, `${var%pattern}`
- Case conversion: `${var^^}`, `${var,,}`
- Brace expansion: `{a,b,c}`, `{1..10}`
- Arithmetic: `$((expr))`
- Command substitution: `$(cmd)`, `` `cmd` ``
- Process substitution: `<(cmd)`, `>(cmd)`

---

### CATEGORIA 3: CONTROL STRUCTURES (8 metodi) → BashPreprocessor

| # | Metodo | Presente In | Destinazione Finale | Converte |
|---|--------|-------------|-------------------|----------|
| 1 | `_convert_control_structures_to_script` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | if/for/while → script |
| 2 | `_convert_test_to_powershell` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | [ test ] → PowerShell |
| 3 | `_has_control_structures` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | Detect if/for/while |
| 4 | `convert_double_test` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | [[ ]] → PowerShell |
| 5 | `convert_for` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | for loop → PS |
| 6 | `convert_if` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | if/then/else → PS |
| 7 | `convert_test` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | [ test ] → PS |
| 8 | `convert_while` | BashToolExecutor, CommandTranslator | **BashPreprocessor** | while loop → PS |

**Rationale**:
- Control structures bash devono essere convertiti PRIMA dell'esecuzione
- Conversione if/for/while → PowerShell è preprocessing
- Strettamente correlato a variable expansion (le variabili nei loop devono essere espanse)
- BashPreprocessor gestisce tutta la sintassi bash

**Control Structures gestiti**:
- `if [ condition ]; then ... fi`
- `if [[ condition ]]; then ... fi`
- `for var in list; do ... done`
- `while [ condition ]; do ... done`
- `[ test ]` → `Test-Path`, `-eq`, ecc.
- `[[ test ]]` → PowerShell conditional expressions

---

## ARCHITETTURA FINALE AGGIORNATA

```
🆕 BashPreprocessor (42 metodi)
 │
 ├─ Preprocessing (14)
 ├─ Variable Expansion (20)
 └─ Control Structures (8)

BashToolExecutor (thin coordinator)
 │
 ├─ BashPreprocessor (delega preprocessing)
 │
 └─ CommandExecutor (delega execution)
     │
     ├─ PipelineStrategy (analisi pipeline)
     ├─ ExecuteUnixSingleCommand (esecuzione)
     │
     └─ Translators (3 classi)
         ├─ SimpleTranslator
         ├─ EmulativeTranslator
         └─ PipelineTranslator
```

---

## FLUSSO ESECUZIONE AGGIORNATO

```
1. BashToolExecutor.execute(raw_command)
   │
   ├─ Receive command from MCP tool
   └─ Setup environment

2. 🆕 BashPreprocessor.preprocess(raw_command)
   │
   ├─ Variable expansion (${var}, $(()), etc.)
   ├─ Heredocs processing (<<EOF)
   ├─ Command/process substitution ($(cmd), <(), >())
   ├─ Control structures conversion (if/for/while → PS)
   ├─ Brace expansion ({a,b,c}, {1..10})
   └─ Return preprocessed_command

3. CommandExecutor.execute(preprocessed_command)
   │
   ├─ PipelineStrategy.analyze_pipeline()
   └─ ExecuteUnixSingleCommand or bash.exe

4. Result formatting & return
```

---

## IMPLEMENTAZIONE PROPOSTA

### Classe BashPreprocessor

```python
class BashPreprocessor:
    """
    Preprocessa sintassi bash PRIMA dell'esecuzione.

    Responsabilità:
    - Variable expansion (${var}, $(()), etc.)
    - Heredocs & command substitution
    - Process substitution (<(), >())
    - Control structures conversion (if/for/while)
    - Brace expansion
    - Escape sequences

    NON fa:
    - Esecuzione comandi (delega a CommandExecutor)
    - Traduzione comandi Unix (delega a Translators)
    - Analisi pipeline (delega a PipelineStrategy)
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.temp_files = []

    def preprocess(self, command: str, env: dict = None) -> str:
        """
        Preprocessa comando bash.

        Pipeline:
        1. Process heredocs
        2. Expand variables
        3. Process substitution (command & process)
        4. Expand braces
        5. Convert control structures
        6. Process escape sequences

        Returns:
            Preprocessed command ready for execution
        """
        # Step 1: Heredocs
        command = self._process_heredocs(command)

        # Step 2: Variable expansion
        command = self._expand_variables(command, env)

        # Step 3: Command/process substitution
        command = self._process_substitution(command)

        # Step 4: Brace expansion
        command = self._expand_braces(command)

        # Step 5: Control structures
        if self._has_control_structures(command):
            command = self._convert_control_structures_to_script(command)

        # Step 6: Escape sequences
        command = self._process_escape_sequences(command)

        return command

    # === PREPROCESSING METHODS (14) ===
    def _process_heredocs(self, command): ...
    def _process_substitution(self, command): ...
    def _process_command_substitution_recursive(self, command): ...
    def _translate_substitution_content(self, content): ...
    def _process_subshell(self, command): ...
    def _process_command_grouping(self, command): ...
    def _process_xargs(self, command): ...
    def _process_find_exec(self, command): ...
    def _process_escape_sequences(self, command): ...
    def _preprocess_test_commands(self, command): ...
    def _cleanup_temp_files(self): ...
    def _needs_powershell(self, command): ...
    def _adapt_for_powershell(self, command): ...
    def _bash_to_powershell(self, command): ...

    # === VARIABLE EXPANSION METHODS (20) ===
    def _expand_variables(self, command, env): ...
    def _expand_aliases(self, command): ...
    def _expand_braces(self, command): ...
    def expand_simple_var(self, match, env): ...
    def expand_default(self, var, default, env): ...
    def expand_assign(self, var, value, env): ...
    def expand_length(self, var, env): ...
    def expand_remove_prefix(self, var, pattern, env): ...
    def expand_remove_suffix(self, var, pattern, env): ...
    def expand_case(self, var, op, env): ...
    def expand_substitution(self, command, env): ...
    def expand_arithmetic(self, expr): ...
    def expand_simple_brace(self, pattern): ...
    def expand_single_brace(self, start, end): ...
    def expand_grouping(self, items): ...
    def find_substitutions(self, command): ...
    def is_complex_substitution(self, command): ...
    def remove_subshell(self, command): ...
    def replace_input_substitution(self, command): ...
    def replace_output_substitution(self, command): ...

    # === CONTROL STRUCTURES METHODS (8) ===
    def _has_control_structures(self, command): ...
    def _convert_control_structures_to_script(self, command): ...
    def _convert_test_to_powershell(self, test_expr): ...
    def convert_if(self, command): ...
    def convert_for(self, command): ...
    def convert_while(self, command): ...
    def convert_test(self, test_expr): ...
    def convert_double_test(self, test_expr): ...
```

### Integrazione in BashToolExecutor

```python
class BashToolExecutor:
    def __init__(self):
        # Preprocessing
        self.preprocessor = BashPreprocessor(logger=self.logger)

        # Execution
        self.executor = CommandExecutor(...)

    def execute(self, command, timeout=None, cwd=None, env=None):
        """Execute bash command with preprocessing."""

        # Step 1: Preprocess bash syntax
        preprocessed_command = self.preprocessor.preprocess(command, env)

        # Step 2: Execute preprocessed command
        result = self.executor.execute(
            preprocessed_command,
            timeout=timeout,
            cwd=cwd,
            env=env
        )

        # Step 3: Cleanup
        self.preprocessor._cleanup_temp_files()

        return result
```

---

## ALTERNATIVE CONSIDERATE

### Alternativa A: Suddivisione in 3 classi

```
BashVariableExpander (20 metodi)
BashSyntaxProcessor (14 metodi)
BashControlConverter (8 metodi)
```

**PRO**: Separazione responsabilità più fine
**CONTRO**: Più classi da gestire, overhead di coordinamento
**DECISIONE**: NO (YAGNI - You Aren't Gonna Need It)

### Alternativa B: Distribuire tra classi esistenti

**Opzione**: Mettere in PipelineStrategy, ExecuteUnixSingleCommand, etc.
**PROBLEMA**: Questi metodi non appartengono a quelle classi
**DECISIONE**: NO (viola Single Responsibility Principle)

### Alternativa C: Lasciare in BashToolExecutor

**PROBLEMA**: BashToolExecutor deve essere thin coordinator, non classe monolitica
**DECISIONE**: NO

---

## MIGRATION PLAN

### Phase 1: Creare BashPreprocessor ✅

**Steps**:
1. Creare file `bash_preprocessor.py`
2. Creare skeleton classe BashPreprocessor
3. Definire interfaccia pubblica: `preprocess(command, env)`

### Phase 2: Migrare metodi da BashToolExecutor 🔄

**Steps**:
1. Copiare 42 metodi da BashToolExecutor → BashPreprocessor
2. Verificare dipendenze (logger, temp_files, etc.)
3. Adattare signatures se necessario
4. Unit tests per BashPreprocessor

### Phase 3: Integrare in BashToolExecutor 🔄

**Steps**:
1. Aggiungere `self.preprocessor = BashPreprocessor()` in `__init__`
2. Chiamare `self.preprocessor.preprocess()` in `execute()`
3. Rimuovere chiamate ai metodi deprecati
4. Integration tests

### Phase 4: Rimuovere metodi duplicati 🔄

**Steps**:
1. Eliminare 42 metodi da BashToolExecutor
2. Eliminare da CommandTranslator (quando verrà rimossa)
3. Verificare che tutti i test passino
4. Code review

---

## SUMMARY

**DECISIONE FINALE**: Creare nuova classe **BashPreprocessor** con tutti i 42 metodi

| Categoria | Metodi | Destinazione |
|-----------|--------|--------------|
| Preprocessing | 14 | **BashPreprocessor** |
| Variable Expansion | 20 | **BashPreprocessor** |
| Control Structures | 8 | **BashPreprocessor** |
| **TOTALE** | **42** | **BashPreprocessor** |

**Rationale**:
- ✅ Separazione responsabilità (preprocessing vs execution vs translation)
- ✅ Single source of truth per bash syntax processing
- ✅ Testabilità (unit test isolati per preprocessing)
- ✅ Manutenibilità (tutti i metodi bash syntax in una classe)
- ✅ YAGNI (una classe invece di 3)

**Next Steps**:
1. Update COMPLETE_DUPLICATE_METHODS_ANALYSIS.md
2. Create BashPreprocessor class
3. Migrate methods
4. Integration

---

*Documento creato: 2025-11-18*
*Analisi: 42 metodi preprocessing/expansion/control*
*Decisione: Creare BashPreprocessor come nuova classe nell'architettura finale*
