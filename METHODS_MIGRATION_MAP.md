# METHODS MIGRATION MAP - Tracciamento Spostamenti

**Data**: 2025-11-18
**Scopo**: Documentare tutti i metodi spostati da BashToolExecutor alle classi target

---

## MIGRATION 1: Preprocessing Methods → CommandExecutor

**Commit**: 660ebd9 - refactor: Complete method migration from BashToolExecutor
**Righe migrate**: 982 righe
**Metodi totali**: 14

### Metodi inseriti in CommandExecutor:

1. **_expand_braces** (72 righe)
   - Include closure: `expand_single_brace`
   - Espande pattern brace: {1..10}, {a..z}, {a,b,c}

2. **_process_heredocs** (179 righe)
   - Processa heredocs (<<EOF)
   - Gestisce variable expansion in heredocs
   - **TESTMODE support**: Simula output realistico

3. **_process_substitution** (104 righe)
   - Include closures: `replace_input_substitution`, `replace_output_substitution`
   - Gestisce <(cmd) e >(cmd)
   - **TESTMODE support**: Simula process substitution

4. **_process_command_substitution_recursive** (100 righe)
   - Include closure: `find_substitutions`
   - Gestisce $(cmd) ricorsivamente

5. **_translate_substitution_content** (99 righe)
   - Include closure: `is_complex_substitution`
   - Traduce contenuto substitution

6. **_expand_variables** (243 righe)
   - Include 13 closures:
     - `expand_arithmetic`, `expand_default`, `expand_assign`
     - `expand_length`, `expand_remove_prefix`, `expand_remove_suffix`
     - `expand_substitution`, `expand_case`, `expand_simple_brace`
     - `expand_simple_var`
   - Gestisce: ${var:-default}, ~/path, $((expr)), ${var#pattern}, etc.

7. **_preprocess_test_commands** (30 righe)
   - Converte [ expr ] → test expr

8. **_expand_aliases** (29 righe)
   - Espande alias comuni (ll, la, l)

9. **_process_subshell** (28 righe)
   - Include closure: `remove_subshell`
   - Gestisce (command)

10. **_process_command_grouping** (22 righe)
    - Include closure: `expand_grouping`
    - Gestisce { cmd1; cmd2; }

11. **_process_xargs** (27 righe)
    - Trasforma pattern xargs

12. **_process_find_exec** (27 righe)
    - Trasforma find ... -exec

13. **_process_escape_sequences** (14 righe)
    - Gestisce escape sequences

14. **_cleanup_temp_files** (10 righe)
    - Cleanup file temporanei

**Note**:
- Tutti i metodi hanno **TESTMODE support** (dove applicabile)
- Closures interne mantenute con i parent methods
- Indentazione preservata

---

## MIGRATION 2: Control Structure Methods → ExecuteUnixSingleCommand

**Commit**: 660ebd9 - refactor: Complete method migration from BashToolExecutor
**Righe migrate**: 280 righe
**Metodi totali**: 6

### Metodi inseriti in ExecuteUnixSingleCommand:

1. **_has_control_structures** (5 righe)
   - Detecta if/for/while/case/function/until

2. **_convert_control_structures_to_script** (32 righe)
   - Crea temp PowerShell script (.ps1)

3. **_bash_to_powershell** (105 righe)
   - Include 3 closures:
     - `convert_for`: for loops → PowerShell foreach
     - `convert_while`: while loops → PowerShell while
     - `convert_if`: if statements → PowerShell if
   - Conversione bash control structures → PowerShell

4. **_convert_test_to_powershell** (40 righe)
   - Converte test conditions bash → PowerShell
   - File tests: -f, -d, -e → Test-Path
   - String comparisons: =, != → -eq, -ne

5. **_needs_powershell** (53 righe)
   - Detecta se serve PowerShell vs cmd.exe
   - Cerca cmdlets, $(..  .), backticks, etc.

6. **_adapt_for_powershell** (35 righe)
   - Adatta comando per esecuzione PowerShell
   - Converte backticks → $()
   - Converte /dev/null → $null

**Note**:
- Metodi gestiscono traduzione semantica bash→PowerShell
- Non preprocessing sintattico, ma script translation

---

## MIGRATION 3: Setup/Detection Methods → CommandExecutor

**Commit**: 80e9229 - refactor: Move setup/detection methods from BashToolExecutor to CommandExecutor
**Righe migrate**: 140 righe
**Metodi totali**: 4

### Metodi inseriti in CommandExecutor:

1. **_detect_git_bash** (36 righe)
   - Detecta Git Bash executable
   - Locations: Program Files, PATH
   - Restituisce: Optional[str]

2. **_detect_system_python** (36 righe)
   - Detecta Python system
   - FAIL FAST se mancante
   - Disabilita tool se Python non trovato

3. **_setup_virtual_env** (48 righe)
   - Setup virtual environment
   - Crea BASH_TOOL_ENV se mancante
   - BLOCKING at initialization (accettabile)

4. **_setup_environment** (20 righe)
   - Setup environment variables
   - UTF-8 encoding, PYTHONIOENCODING, PYTHONUNBUFFERED
   - Virtual env PATH setup

**Note**:
- Metodi di configurazione ambiente esecuzione
- Appartengono a CommandExecutor (non BashToolExecutor)

---

## TOTALI MIGRAZIONE

| Migrazione | Destinazione | Metodi | Righe | Commit |
|------------|--------------|--------|-------|--------|
| Preprocessing | CommandExecutor | 14 | 982 | 660ebd9 |
| Control Structures | ExecuteUnixSingleCommand | 6 | 280 | 660ebd9 |
| Setup/Detection | CommandExecutor | 4 | 140 | 80e9229 |
| **TOTALE** | - | **24** | **1,402** | - |

---

## TODO: Verifiche Post-Migrazione

### Verifiche da fare:

1. **Firme metodi**:
   - [ ] Verificare firme metodi in CommandExecutor
   - [ ] Verificare firme metodi in ExecuteUnixSingleCommand
   - [ ] Aggiungere parametri mancanti (scratch_dir, TESTMODE, etc.)

2. **Chiamate metodi**:
   - [ ] Aggiornare chiamate in BashToolExecutor
   - [ ] `self._process_heredocs()` → `self.command_executor._process_heredocs()`
   - [ ] `self._needs_powershell()` → `self.command_executor.single_executor._needs_powershell()`

3. **Dipendenze**:
   - [ ] Verificare accesso a `self.scratch_dir` in CommandExecutor
   - [ ] Verificare accesso a `self.TESTMODE` in CommandExecutor
   - [ ] Verificare accesso a `self.git_bash_exe` in ExecuteUnixSingleCommand

4. **__init__ methods**:
   - [ ] Estendere CommandExecutor.__init__ con parametri necessari
   - [ ] Estendere ExecuteUnixSingleCommand.__init__ con parametri necessari

5. **Testing**:
   - [ ] Eseguire test completi
   - [ ] Verificare preprocessing methods
   - [ ] Verificare control structure methods
   - [ ] Verificare setup methods

---

## RISULTATO FINALE

**BashToolExecutor**:
- Prima: ~50 metodi, ~8,000 righe
- Dopo: ~26 metodi, ~6,600 righe
- **Riduzione**: -1,402 righe (-24 metodi)
- **Status**: Thin coordinator (come progettato)

**CommandExecutor**:
- Guadagnati: 18 metodi (14 preprocessing + 4 setup)
- **Nuove capabilities**: Preprocessing + Environment setup

**ExecuteUnixSingleCommand**:
- Guadagnati: 6 metodi (control structures)
- **Nuove capabilities**: Bash→PowerShell script translation

---

**Fine del documento**
