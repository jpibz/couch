# COMPLETE DUPLICATE METHODS ANALYSIS

## Analisi Completa dei Metodi Duplicati - 6 Classi

**Data analisi**: 2025-11-18
**Classi analizzate**: 6
**Totale metodi duplicati**: 122

---

## EXECUTIVE SUMMARY

Dall'analisi delle 6 classi coinvolte nel refactoring sono stati identificati **122 metodi duplicati** presenti in almeno 2 o più classi.

### Classi Analizzate

| # | Classe | File | Totale Metodi |
|---|--------|------|---------------|
| 1 | **BashToolExecutor** | bash_tool_executor.py | 50 |
| 2 | **CommandExecutor** | bash_tool_executor.py | 54 |
| 3 | **CommandTranslator** | unix_translator.py | 127 |
| 4 | **SimpleTranslator** | unix_translator.py | 22 |
| 5 | **EmulativeTranslator** | unix_translator.py | 33 |
| 6 | **PipelineTranslator** | unix_translator.py | 23 |
| | **TOTALE** | | **309 metodi** |

**PathTranslator** è esclusa dall'analisi (fuori scope refactoring).

### Breakdown Duplicazioni

**⚠️ AGGIORNATO: 2025-11-18 - Dopo analisi codice e flusso esecuzione**

| Categoria | Metodi Reali | Pattern Duplicazione | Destinazione Finale (CORRETTA) |
|-----------|--------------|---------------------|--------------------------------|
| **Preprocessing** | 11 | BashToolExecutor ↔ CommandTranslator | **CommandExecutor** (preprocessing generico) |
| **Variable Expansion** | 20 | BashToolExecutor ↔ CommandTranslator | **CommandExecutor** (preprocessing generico) |
| **Control Structures** | 3 (+ 5 closures) | BashToolExecutor ↔ CommandTranslator | **ExecuteUnixSingleCommand/ScriptTranslator** |
| **PowerShell Strategy** | 3 | BashToolExecutor ↔ CommandTranslator | **ExecuteUnixSingleCommand** (2) + EmulativeTranslator (1) |
| **Translation Simple** | 21 | CommandTranslator ↔ SimpleTranslator | SimpleTranslator |
| **Translation Emulative** | 27 | CommandTranslator ↔ EmulativeTranslator | EmulativeTranslator |
| **Translation Pipeline** | 22 | CommandTranslator ↔ PipelineTranslator | PipelineTranslator |
| **Helper Parsing** | 4 | Multi-class (3 classi) | EmulativeTranslator |
| **Helper AWK/JQ** | 4 | Multi-class (3 classi) | EmulativeTranslator |
| **Execution** | 1 | BashToolExecutor ↔ CommandExecutor | Entrambe (ruoli diversi) |
| **Core** | 1 | Tutte le 6 classi | Tutte (__init__) |
| **TOTALE** | **122** (di cui 5 closures, 37 veri) | | |

**Note:**
- I metodi `convert_if`, `convert_for`, `convert_while`, `convert_test`, `convert_double_test` sono **CLOSURE functions** dentro `_bash_to_powershell`, NON metodi standalone
- Totale metodi VERI: 122 - 5 closures = **117 metodi**
- Prime 4 categorie (42 metodi listati): 42 - 5 closures = **37 metodi veri**

---

## CATEGORIA 1: PREPROCESSING (14 metodi)

**Pattern**: BashToolExecutor ↔ CommandTranslator
**Destinazione finale**: 🆕 **BashPreprocessor** (nuova classe da creare)

| # | Metodo | Presente In | Destinazione Finale |
|---|--------|-------------|-------------------|
| 1 | `_adapt_for_powershell` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 2 | `_bash_to_powershell` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 3 | `_cleanup_temp_files` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 4 | `_needs_powershell` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 5 | `_preprocess_test_commands` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 6 | `_process_command_grouping` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 7 | `_process_command_substitution_recursive` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 8 | `_process_escape_sequences` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 9 | `_process_find_exec` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 10 | `_process_heredocs` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 11 | `_process_subshell` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 12 | `_process_substitution` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 13 | `_process_xargs` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 14 | `_translate_substitution_content` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |

**Rationale** (AGGIORNATO):
- ❌ **INCORRETTA destinazione precedente**: Questi metodi NON appartengono a BashToolExecutor (deve essere thin coordinator)
- ✅ **CORRETTA destinazione**: Vanno in NUOVA classe **BashPreprocessor**
- Questi metodi gestiscono preprocessing bash syntax (heredocs, substitution, command grouping)
- **IMPORTANTE**: BashPreprocessor è usata INTERNAMENTE da CommandExecutor, NON da BashToolExecutor
- Flusso: BashToolExecutor → CommandExecutor (usa BashPreprocessor internamente) → PipelineStrategy/ExecuteUnixSingleCommand
- Separazione responsabilità: BashToolExecutor (coordinator) → CommandExecutor (orchestration + preprocessing interno) → Execution

**Azione**:
1. Creare nuova classe `BashPreprocessor` nell'architettura finale
2. Migrare i 14 metodi da BashToolExecutor/CommandTranslator → BashPreprocessor
3. **CommandExecutor** usa `self.preprocessor = BashPreprocessor()` internamente (NON BashToolExecutor!)
4. CommandExecutor chiama `self.preprocessor.preprocess()` all'inizio di `execute()`
5. Eliminare i 14 metodi da BashToolExecutor e CommandTranslator

**Vedi**: `PREPROCESSING_DESTINATION_ANALYSIS.md` per dettagli completi

---

## CATEGORIA 2: VARIABLE EXPANSION (20 metodi)

**Pattern**: BashToolExecutor ↔ CommandTranslator
**Destinazione finale**: 🆕 **BashPreprocessor** (nuova classe da creare)

| # | Metodo | Presente In | Destinazione Finale |
|---|--------|-------------|-------------------|
| 1 | `_expand_aliases` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 2 | `_expand_braces` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 3 | `_expand_variables` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 4 | `expand_arithmetic` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 5 | `expand_assign` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 6 | `expand_case` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 7 | `expand_default` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 8 | `expand_grouping` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 9 | `expand_length` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 10 | `expand_remove_prefix` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 11 | `expand_remove_suffix` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 12 | `expand_simple_brace` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 13 | `expand_simple_var` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 14 | `expand_single_brace` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 15 | `expand_substitution` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 16 | `find_substitutions` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 17 | `is_complex_substitution` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 18 | `remove_subshell` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 19 | `replace_input_substitution` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 20 | `replace_output_substitution` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |

**Rationale** (AGGIORNATO):
- ❌ **INCORRETTA destinazione precedente**: Questi metodi NON appartengono a BashToolExecutor (deve essere thin coordinator)
- ✅ **CORRETTA destinazione**: Vanno in NUOVA classe **BashPreprocessor**
- Variable expansion è preprocessing bash fondamentale (${var}, $((expr)), ${var:-default}, brace expansion, etc.)
- **IMPORTANTE**: BashPreprocessor è usata INTERNAMENTE da CommandExecutor, NON da BashToolExecutor
- Flusso: BashToolExecutor → CommandExecutor (usa BashPreprocessor.preprocess() internamente) → PipelineStrategy/ExecuteUnixSingleCommand

**Pattern bash gestiti**:
- Simple: `$var`, `${var}`
- Default/Assign: `${var:-default}`, `${var:=value}`
- Length/Substring: `${#var}`, `${var:offset:length}`
- Pattern removal: `${var#pattern}`, `${var%pattern}`
- Case conversion: `${var^^}`, `${var,,}`
- Brace expansion: `{a,b,c}`, `{1..10}`
- Arithmetic: `$((expr))`
- Command/Process substitution: `$(cmd)`, `` `cmd` ``, `<(cmd)`, `>(cmd)`

**Azione**:
1. Creare nuova classe `BashPreprocessor` con questi 20 metodi
2. Migrare da BashToolExecutor/CommandTranslator → BashPreprocessor
3. **CommandExecutor** usa BashPreprocessor internamente (NON BashToolExecutor!)
4. Eliminare da BashToolExecutor e CommandTranslator

**Vedi**: `PREPROCESSING_DESTINATION_ANALYSIS.md` per dettagli completi

---

## CATEGORIA 3: CONTROL STRUCTURES (8 metodi)

**Pattern**: BashToolExecutor ↔ CommandTranslator
**Destinazione finale**: 🆕 **BashPreprocessor** (nuova classe da creare)

| # | Metodo | Presente In | Destinazione Finale |
|---|--------|-------------|-------------------|
| 1 | `_convert_control_structures_to_script` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 2 | `_convert_test_to_powershell` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 3 | `_has_control_structures` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 4 | `convert_double_test` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 5 | `convert_for` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 6 | `convert_if` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 7 | `convert_test` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |
| 8 | `convert_while` | BashToolExecutor, CommandTranslator | **🆕 BashPreprocessor** |

**Rationale** (AGGIORNATO):
- ❌ **INCORRETTA destinazione precedente**: Questi metodi NON appartengono a BashToolExecutor (deve essere thin coordinator)
- ✅ **CORRETTA destinazione**: Vanno in NUOVA classe **BashPreprocessor**
- Control structures bash (if, for, while, test) devono essere convertiti PRIMA dell'esecuzione
- Conversione if/for/while → PowerShell è preprocessing bash syntax
- **IMPORTANTE**: BashPreprocessor è usata INTERNAMENTE da CommandExecutor, NON da BashToolExecutor
- Strettamente correlato a variable expansion (variabili nei loop devono essere espanse)
- Flusso: BashToolExecutor → CommandExecutor (usa BashPreprocessor.preprocess() internamente) → Execution

**Control structures gestiti**:
- `if [ condition ]; then ... fi` → PowerShell if
- `if [[ condition ]]; then ... fi` → PowerShell if (extended test)
- `for var in list; do ... done` → PowerShell foreach
- `while [ condition ]; do ... done` → PowerShell while
- `[ test ]` → `Test-Path`, `-eq`, `-ne`, `-gt`, etc.
- `[[ test ]]` → PowerShell conditional expressions

**Azione**:
1. Creare nuova classe `BashPreprocessor` con questi 8 metodi
2. Migrare da BashToolExecutor/CommandTranslator → BashPreprocessor
3. **CommandExecutor** usa BashPreprocessor internamente (NON BashToolExecutor!)
4. Eliminare da BashToolExecutor e CommandTranslator

**Vedi**: `PREPROCESSING_DESTINATION_ANALYSIS.md` per dettagli completi

---

## CATEGORIA 4: TRANSLATION SIMPLE (21 metodi)

**Pattern**: CommandTranslator ↔ SimpleTranslator
**Destinazione finale**: SimpleTranslator (1:1 translations)

| # | Metodo | Presente In | Destinazione |
|---|--------|-------------|--------------|
| 1 | `_translate_basename` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 2 | `_translate_cd` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 3 | `_translate_chmod` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 4 | `_translate_chown` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 5 | `_translate_df` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 6 | `_translate_dirname` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 7 | `_translate_env` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 8 | `_translate_export` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 9 | `_translate_false` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 10 | `_translate_hostname` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 11 | `_translate_kill` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 12 | `_translate_mkdir` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 13 | `_translate_mv` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 14 | `_translate_printenv` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 15 | `_translate_ps` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 16 | `_translate_pwd` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 17 | `_translate_sleep` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 18 | `_translate_true` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 19 | `_translate_which` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 20 | `_translate_whoami` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |
| 21 | `_translate_yes` | CommandTranslator, SimpleTranslator | **SimpleTranslator** |

**Rationale**:
- Questi sono comandi con traduzione 1:1 (pwd → Get-Location, cd → Set-Location)
- SimpleTranslator è la classe designata per 1:1 translations
- CommandTranslator verrà eliminata
- SimpleTranslator già esiste in unix_translator.py

**Azione**:
1. Verificare che SimpleTranslator abbia implementazioni complete
2. Eliminare da CommandTranslator

---

## CATEGORIA 5: TRANSLATION EMULATIVE (27 metodi)

**Pattern**: CommandTranslator ↔ EmulativeTranslator
**Destinazione finale**: EmulativeTranslator (PowerShell emulation)

| # | Metodo | Presente In | Destinazione |
|---|--------|-------------|--------------|
| 1 | `_translate_awk` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 2 | `_translate_column` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 3 | `_translate_comm` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 4 | `_translate_curl` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 5 | `_translate_cut` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 6 | `_translate_diff` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 7 | `_translate_find` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 8 | `_translate_grep` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 9 | `_translate_gunzip` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 10 | `_translate_gzip` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 11 | `_translate_hexdump` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 12 | `_translate_join` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 13 | `_translate_jq` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 14 | `_translate_ln` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 15 | `_translate_paste` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 16 | `_translate_sed` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 17 | `_translate_sort` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 18 | `_translate_split` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 19 | `_translate_strings` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 20 | `_translate_tar` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 21 | `_translate_test` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 22 | `_translate_timeout` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 23 | `_translate_uniq` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 24 | `_translate_unzip` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 25 | `_translate_watch` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 26 | `_translate_wget` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 27 | `_translate_zip` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |

**Rationale**:
- Comandi complessi che richiedono emulazione con PowerShell
- grep → Select-String, awk → ForEach-Object, sed → -replace
- EmulativeTranslator è la classe designata per emulation
- EmulativeTranslator già esiste in unix_translator.py

**Azione**:
1. Verificare che EmulativeTranslator abbia implementazioni complete
2. Eliminare da CommandTranslator

---

## CATEGORIA 6: TRANSLATION PIPELINE (22 metodi)

**Pattern**: CommandTranslator ↔ PipelineTranslator
**Destinazione finale**: PipelineTranslator (pipeline operators)

| # | Metodo | Presente In | Destinazione |
|---|--------|-------------|--------------|
| 1 | `_translate_base64` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 2 | `_translate_cat` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 3 | `_translate_cp` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 4 | `_translate_date` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 5 | `_translate_du` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 6 | `_translate_echo` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 7 | `_translate_file` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 8 | `_translate_head` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 9 | `_translate_ls` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 10 | `_translate_md5sum` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 11 | `_translate_readlink` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 12 | `_translate_realpath` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 13 | `_translate_rm` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 14 | `_translate_seq` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 15 | `_translate_sha1sum` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 16 | `_translate_sha256sum` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 17 | `_translate_stat` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 18 | `_translate_tail` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 19 | `_translate_tee` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 20 | `_translate_touch` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 21 | `_translate_tr` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |
| 22 | `_translate_wc` | CommandTranslator, PipelineTranslator | **PipelineTranslator** |

**Rationale**:
- Comandi usati frequentemente in pipeline (cat, head, tail, wc, tee)
- Supportano input/output redirection e piping
- PipelineTranslator è la classe designata per pipeline operators
- PipelineTranslator già esiste in unix_translator.py

**Azione**:
1. Verificare che PipelineTranslator abbia implementazioni complete
2. Eliminare da CommandTranslator

---

## CATEGORIA 7: HELPER PARSING (4 metodi)

**Pattern**: Multi-class (2-3 classi)
**Destinazione finale**: EmulativeTranslator (usati principalmente per emulation)

| # | Metodo | Presente In | Destinazione |
|---|--------|-------------|--------------|
| 1 | `_parse_cut_range` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |
| 2 | `_parse_duration` | CommandExecutor, CommandTranslator, **EmulativeTranslator** | **EmulativeTranslator** |
| 3 | `_parse_size` | CommandExecutor, CommandTranslator | **EmulativeTranslator** |
| 4 | `has_flag` | CommandTranslator, EmulativeTranslator | **EmulativeTranslator** |

**Rationale**:
- Helper per parsing input (durate, dimensioni, range, flags)
- Usati principalmente da EmulativeTranslator (_translate_split usa _parse_size, _translate_timeout usa _parse_duration)
- Anche se più "generici", il contesto d'uso è emulation
- Seguendo YAGNI: vanno in EmulativeTranslator (no classe ParsingUtils separata)

**Azione**:
1. Mantenere in EmulativeTranslator
2. Aggiungere _parse_size da CommandExecutor/CommandTranslator
3. Eliminare da CommandExecutor e CommandTranslator

**Note speciali**:
- `_parse_duration` è presente in 3 classi (CommandExecutor, CommandTranslator, EmulativeTranslator)
- EmulativeTranslator è già presente, quindi mantenere lì

---

## CATEGORIA 8: HELPER AWK/JQ (4 metodi)

**Pattern**: Multi-class (2-3 classi)
**Destinazione finale**: EmulativeTranslator (AWK/JQ emulation)

| # | Metodo | Presente In | Destinazione |
|---|--------|-------------|--------------|
| 1 | `_awk_to_ps_condition` | CommandExecutor, CommandTranslator, **EmulativeTranslator** | **EmulativeTranslator** |
| 2 | `_awk_to_ps_statement` | CommandExecutor, CommandTranslator, **EmulativeTranslator** | **EmulativeTranslator** |
| 3 | `_is_simple_jq_pattern` | CommandExecutor, CommandTranslator | **EmulativeTranslator** |
| 4 | `_jq_to_powershell` | CommandExecutor, CommandTranslator | **EmulativeTranslator** |

**Rationale**:
- Helper per convertire awk/jq in PowerShell
- Usati da _translate_awk e _translate_jq in EmulativeTranslator
- EmulativeTranslator già ha _awk_to_ps_statement e _awk_to_ps_condition
- Mancano _is_simple_jq_pattern e _jq_to_powershell

**Azione**:
1. Mantenere _awk_to_ps_* in EmulativeTranslator
2. Spostare _is_simple_jq_pattern da CommandExecutor/CommandTranslator a EmulativeTranslator
3. Spostare _jq_to_powershell da CommandExecutor/CommandTranslator a EmulativeTranslator
4. Eliminare da CommandExecutor e CommandTranslator

---

## CATEGORIA 9: EXECUTION (1 metodo)

**Pattern**: BashToolExecutor ↔ CommandExecutor
**Destinazione finale**: Entrambe (diverse responsabilità)

| # | Metodo | Presente In | Destinazione |
|---|--------|-------------|--------------|
| 1 | `execute` | BashToolExecutor, CommandExecutor | **ENTRAMBE** (diversi ruoli) |

**Rationale**:
- BashToolExecutor.execute() è il punto di ingresso principale (chiamato da tool MCP)
- CommandExecutor.execute() è il metodo interno per eseguire comandi singoli
- NON sono duplicati funzionali, hanno ruoli diversi
- Non c'è conflitto

**Azione**:
- Nessuna azione necessaria (non sono veri duplicati)

---

## CATEGORIA 10: CORE (1 metodo)

**Pattern**: Tutte le 6 classi
**Destinazione finale**: Tutte (costruttori)

| # | Metodo | Presente In | Destinazione |
|---|--------|-------------|--------------|
| 1 | `__init__` | Tutte e 6 le classi | **TUTTE** (costruttori) |

**Rationale**:
- Ogni classe ha il suo costruttore
- Non sono duplicati funzionali
- Ciascuno inizializza la propria classe

**Azione**:
- Nessuna azione necessaria (non sono veri duplicati)

---

## SUMMARY TABLE - DESTINAZIONE FINALE (AGGIORNATO)

| Categoria | Metodi | Destinazione Finale | Azione |
|-----------|--------|-------------------|---------|
| Preprocessing | 14 | **🆕 BashPreprocessor** (nuova classe) | Creare BashPreprocessor, migrare da BashToolExecutor/CommandTranslator |
| Variable Expansion | 20 | **🆕 BashPreprocessor** (nuova classe) | Creare BashPreprocessor, migrare da BashToolExecutor/CommandTranslator |
| Control Structures | 8 | **🆕 BashPreprocessor** (nuova classe) | Creare BashPreprocessor, migrare da BashToolExecutor/CommandTranslator |
| Translation Simple | 21 | **SimpleTranslator** | Eliminare da CommandTranslator |
| Translation Emulative | 27 | **EmulativeTranslator** | Eliminare da CommandTranslator |
| Translation Pipeline | 22 | **PipelineTranslator** | Eliminare da CommandTranslator |
| Helper Parsing | 4 | **EmulativeTranslator** | Eliminare da CommandExecutor, CommandTranslator |
| Helper AWK/JQ | 4 | **EmulativeTranslator** | Eliminare da CommandExecutor, CommandTranslator |
| Execution | 1 | **Entrambe** | Nessuna (diversi ruoli) |
| Core | 1 | **Tutte** | Nessuna (costruttori) |
| **TOTALE** | **122** | | |

**NOTA IMPORTANTE**: Le prime 3 categorie (42 metodi totali) vanno in una **NUOVA classe BashPreprocessor** che deve essere creata nell'architettura finale. Vedi `PREPROCESSING_DESTINATION_ANALYSIS.md` per dettagli completi.

---

## IMPACT ANALYSIS (AGGIORNATO)

### Metodi da Eliminare/Migrare per Classe

| Classe | Metodi da Eliminare | Destinazione |
|--------|-------------------|--------------|
| **CommandTranslator** | 127 metodi → **ELIMINARE INTERA CLASSE** | Distribuiti tra Simple/Emulative/Pipeline + **BashPreprocessor** |
| **CommandExecutor** | 8 metodi (helper duplicati) | EmulativeTranslator |
| **BashToolExecutor** | **42 metodi (preprocessing/expansion/control)** | **🆕 BashPreprocessor** |
| **🆕 BashPreprocessor** | **NUOVA CLASSE** - riceve 42 metodi | Da BashToolExecutor + CommandTranslator |
| **SimpleTranslator** | 0 (mantiene tutti) | - |
| **EmulativeTranslator** | 0 (mantiene + riceve 12 helper) | - |
| **PipelineTranslator** | 0 (mantiene tutti) | - |

**Nota Importante**: BashPreprocessor è una NUOVA classe che deve essere creata nell'architettura finale per gestire preprocessing bash, variable expansion e control structures.

### Lines of Code Impact

Stima riduzione duplicazioni (da verificare con analisi dettagliata):

| Categoria | Lines Estimate | Occorrenze | Lines Eliminate |
|-----------|---------------|------------|-----------------|
| Preprocessing | ~1500 | 2x | ~1500 |
| Variable Expansion | ~2000 | 2x | ~2000 |
| Control Structures | ~800 | 2x | ~800 |
| Translation Simple | ~500 | 2x | ~500 |
| Translation Emulative | ~3000 | 2x | ~3000 |
| Translation Pipeline | ~2000 | 2x | ~2000 |
| Helper Parsing | ~100 | 2-3x | ~150 |
| Helper AWK/JQ | ~150 | 2-3x | ~200 |
| **TOTALE** | | | **~10,150 lines** |

**Nota**: Stime conservative. L'analisi effettiva potrebbe rivelare maggiori risparmi.

---

## MIGRATION PLAN

### Phase 1: Verify Translators Have Complete Implementations ✅

**Obiettivo**: Verificare che SimpleTranslator, EmulativeTranslator, PipelineTranslator abbiano tutte le implementazioni

**Checklist**:
- [ ] SimpleTranslator ha tutti i 21 metodi _translate_*
- [ ] EmulativeTranslator ha tutti i 27 metodi _translate_* + 8 helper
- [ ] PipelineTranslator ha tutti i 22 metodi _translate_*
- [ ] Test unitari per ogni translator

### Phase 2: Move Helper Methods to EmulativeTranslator 🔄

**Obiettivo**: Spostare i 12 helper da CommandExecutor/CommandTranslator a EmulativeTranslator

**Metodi da spostare**:
1. _parse_size (da CommandExecutor, CommandTranslator)
2. _is_simple_jq_pattern (da CommandExecutor, CommandTranslator)
3. _jq_to_powershell (da CommandExecutor, CommandTranslator)

(Altri già presenti in EmulativeTranslator)

**Steps**:
1. Copiare implementazioni da CommandExecutor a EmulativeTranslator
2. Update CommandExecutor per delegare a EmulativeTranslator
3. Eliminare metodi duplicati da CommandExecutor
4. Test unitari e integration tests

### Phase 3: Update CommandExecutor to Use Translators 🔄

**Obiettivo**: CommandExecutor usa Translators invece di implementazioni interne

**Pattern**:
```python
# BEFORE
class CommandExecutor:
    def _execute_awk(self, command, parts):
        # Implementazione inline con helper duplicati
        statement = self._awk_to_ps_statement(...)
        ...

# AFTER
class CommandExecutor:
    def __init__(self):
        self.emulative = EmulativeTranslator()

    def _execute_awk(self, command, parts):
        # Delega a EmulativeTranslator
        return self.emulative._translate_awk(command, parts)
```

### Phase 4: Verify BashToolExecutor Has Complete Preprocessing ✅

**Obiettivo**: Verificare che BashToolExecutor abbia tutte le implementazioni preprocessing

**Checklist**:
- [ ] Tutti i 14 metodi preprocessing presenti
- [ ] Tutti i 20 metodi variable expansion presenti
- [ ] Tutti gli 8 metodi control structures presenti
- [ ] Test completi per preprocessing

### Phase 5: Eliminate CommandTranslator ⚠️ **FINALE**

**Obiettivo**: Eliminare completamente CommandTranslator

**Pre-requisiti**:
- ✅ Tutti i metodi migrati a Simple/Emulative/Pipeline/BashToolExecutor
- ✅ Tutti i chiamanti aggiornati
- ✅ Tutti i test passano

**Steps**:
1. Rimuovere file unix_translator.py (CommandTranslator class)
2. Rimuovere import di CommandTranslator
3. Update references in documentation
4. Final test suite run
5. Celebration! 🎉

---

## TESTING STRATEGY

### Unit Tests per Translator

Ogni translator deve avere test isolati:

```python
# test_simple_translator.py
def test_translate_pwd():
    translator = SimpleTranslator()
    result = translator._translate_pwd("pwd", ["pwd"])
    assert result == "Get-Location"

# test_emulative_translator.py
def test_translate_awk():
    translator = EmulativeTranslator()
    result = translator._translate_awk("awk '{print $1}' file", ...)
    assert "ForEach-Object" in result
    assert "$_.Split()[0]" in result

def test_parse_size():
    translator = EmulativeTranslator()
    assert translator._parse_size("10M") == 10485760
    assert translator._parse_size("1G") == 1073741824

# test_pipeline_translator.py
def test_translate_cat():
    translator = PipelineTranslator()
    result = translator._translate_cat("cat file.txt", ...)
    assert "Get-Content" in result
```

### Integration Tests

Verificare che l'intero flusso funzioni:

```python
# test_command_executor_integration.py
def test_execute_awk_uses_emulative():
    executor = CommandExecutor()
    result = executor.execute_bash("awk '{print $1}' file", ...)
    # Verifica che usa EmulativeTranslator
    assert "ForEach-Object" in result.command

def test_execute_pwd_uses_simple():
    executor = CommandExecutor()
    result = executor.execute_bash("pwd", ...)
    # Verifica che usa SimpleTranslator
    assert "Get-Location" in result.command
```

### Regression Tests

Eseguire full test suite dopo ogni phase:

```bash
pytest tests/ -v --cov=couch --cov-report=html
```

---

## RISK ANALYSIS

### High Risk

1. **CommandTranslator Elimination**
   - Risk: Breaking changes se ci sono riferimenti non trovati
   - Mitigation: Grep completo per "CommandTranslator", run full test suite

2. **Helper Method Migration**
   - Risk: Comportamento leggermente diverso tra implementazioni duplicate
   - Mitigation: Test A/B comparison prima di eliminare

### Medium Risk

3. **Integration Complexity**
   - Risk: CommandExecutor → Translator delegation può introdurre bug
   - Mitigation: Integration tests completi, gradual rollout

4. **Performance Impact**
   - Risk: Extra layer di delegation può rallentare esecuzione
   - Mitigation: Benchmark prima/dopo, ottimizzazione se necessario

### Low Risk

5. **Test Coverage Gaps**
   - Risk: Eliminazione codice non testato può nascondere bug
   - Mitigation: Aumentare coverage prima di eliminare

---

## NEXT STEPS IMMEDIATE

1. **Verify Current State**
   - [ ] Check che SimpleTranslator, EmulativeTranslator, PipelineTranslator esistano
   - [ ] Check che abbiano le implementazioni complete
   - [ ] Run existing tests

2. **Create Detailed Migration Plan**
   - [ ] Prioritize helper methods migration
   - [ ] Create tracking issue/PR per phase
   - [ ] Setup CI/CD per verificare non-regression

3. **Start Phase 2**
   - [ ] Move _is_simple_jq_pattern e _jq_to_powershell a EmulativeTranslator
   - [ ] Move _parse_size a EmulativeTranslator
   - [ ] Update CommandExecutor delegation
   - [ ] Test & merge

---

## APPENDIX A: COMPLETE METHOD LIST BY CLASS

### BashToolExecutor (50 methods)
```
__init__, _adapt_for_powershell, _bash_to_powershell, _cleanup_temp_files,
_convert_control_structures_to_script, _convert_test_to_powershell,
_detect_git_bash, _detect_system_python, _expand_aliases, _expand_braces,
_expand_variables, _format_result, _has_control_structures, _needs_powershell,
_preprocess_test_commands, _process_command_grouping,
_process_command_substitution_recursive, _process_escape_sequences,
_process_find_exec, _process_heredocs, _process_subshell, _process_substitution,
_process_xargs, _setup_environment, _setup_virtual_env,
_translate_substitution_content, convert_double_test, convert_for, convert_if,
convert_test, convert_while, execute, expand_arithmetic, expand_assign,
expand_case, expand_default, expand_grouping, expand_length,
expand_remove_prefix, expand_remove_suffix, expand_simple_brace,
expand_simple_var, expand_single_brace, expand_substitution, find_substitutions,
get_definition, is_complex_substitution, remove_subshell,
replace_input_substitution, replace_output_substitution
```

### CommandExecutor (54 methods)
```
__init__, _awk_to_ps_condition, _awk_to_ps_statement, _checksum_generic,
_detect_native_binaries, _execute_awk, _execute_base64, _execute_cat,
_execute_column, _execute_comm, _execute_curl, _execute_diff, _execute_find,
_execute_grep, _execute_gunzip, _execute_gzip, _execute_head, _execute_hexdump,
_execute_join, _execute_jq, _execute_ln, _execute_md5sum, _execute_paste,
_execute_sed, _execute_sha1sum, _execute_sha256sum, _execute_sort,
_execute_split, _execute_strings, _execute_tail, _execute_tar, _execute_test,
_execute_timeout, _execute_uniq, _execute_unzip, _execute_watch, _execute_wc,
_execute_wget, _execute_with_gitbash, _execute_zip, _get_execution_map,
_is_simple_jq_pattern, _jq_to_powershell, _parse_duration, _parse_find_size,
_parse_size, _windows_to_gitbash_paths, convert_path, execute, execute_bash,
is_complex_exec, is_critical_awk, is_critical_sed, single_executor
```

### CommandTranslator (127 methods) → TO BE ELIMINATED
```
(Full list available in /tmp/all_methods.txt)
```

---

## APPENDIX B: FINAL CORRECTED DISTRIBUTION (37 METHODS)

**⚠️ DECISIONE FINALE - Basata su lettura codice effettivo**
**Data:** 2025-11-18

Dopo analisi approfondita del flusso di esecuzione nel codice, la distribuzione corretta dei primi 42 metodi (di cui 37 reali) è:

### CommandExecutor: 28 metodi - PREPROCESSING GENERICO

**A. Heredocs e Process Substitution (5):**
- `_process_heredocs`, `_process_substitution`, `_process_command_substitution_recursive`
- `_translate_substitution_content`, `find_substitutions`

**B. Subshell e Command Grouping (2):**
- `_process_subshell`, `_process_command_grouping`

**C. Preprocessing Patterns (4):**
- `_process_xargs`, `_process_find_exec`, `_process_escape_sequences`
- `_preprocess_test_commands`

**D. Variable Expansion (20):**
- `_expand_variables` (orchestrator), `_expand_aliases`, `_expand_braces`
- `expand_simple_var`, `expand_default`, `expand_assign`, `expand_length`
- `expand_remove_prefix`, `expand_remove_suffix`, `expand_case`
- `expand_substitution`, `expand_arithmetic`
- `expand_simple_brace`, `expand_single_brace`, `expand_grouping`
- `is_complex_substitution`, `remove_subshell`
- `replace_input_substitution`, `replace_output_substitution`

**E. Cleanup (1):**
- `_cleanup_temp_files`

**Totale: 28 metodi**

---

### ExecuteUnixSingleCommand: 8 metodi - SCRIPT TRANSLATION

**NUOVO COMPONENTE: ScriptTranslator**

**A. Control Structures Detection & Conversion (4):**
- `_has_control_structures` - Detecta if/for/while/case
- `_convert_control_structures_to_script` - Crea file .ps1
- `_bash_to_powershell` - Core conversion bash→PowerShell
- `_convert_test_to_powershell` - Converte test conditions

**B. PowerShell Strategy Decision (2):**
- `_needs_powershell` - Detecta se serve PowerShell vs cmd.exe
- `_adapt_for_powershell` - Adatta comando per PowerShell

**Note:** I metodi `convert_if`, `convert_for`, `convert_while`, `convert_test`, `convert_double_test` sono **CLOSURE functions** dentro `_bash_to_powershell`, NON metodi standalone.

**Totale: 8 metodi**
*(Di cui 1 metodo `_adapt_for_powershell` potrebbe essere spostato in EmulativeTranslator)*

---

### EmulativeTranslator: 0-1 metodo

- `_adapt_for_powershell` (opzionale, se non in ExecuteUnixSingleCommand)

---

### MOTIVAZIONE CHIAVE

**Perché bash→PowerShell va in ExecuteUnixSingleCommand, NON in CommandExecutor?**

1. **`_bash_to_powershell` è TRADUZIONE, non preprocessing:**
   - Preprocessing: `$var` → valore (testuale)
   - Traduzione: `if...; then...; fi` → `If (...) { ... }` (semantica)

2. **Parallelo con altri Translators:**
   - SimpleTranslator: `pwd` → `Get-Location`
   - EmulativeTranslator: `sed` → PowerShell emulation
   - PipelineTranslator: `|` → pipeline operators
   - **ScriptTranslator**: `if/for/while` → PowerShell script

3. **ExecuteUnixSingleCommand gestisce strategie di ESECUZIONE:**
   - Non solo comandi "atomici" ma "unità di esecuzione" (comando o script)

**Vedi:** `FINAL_37_METHODS_DISTRIBUTION.md` per analisi completa

---

*Document created: 2025-11-18*
*Last updated: 2025-11-18 (after code flow analysis)*
*Analysis based on: bash_tool_executor.py, unix_translator.py*
*Total duplicate methods identified: 122 (117 real methods, 5 closures)*
*Recommendation: Eliminate CommandTranslator entirely, distribute methods to specialized classes*
