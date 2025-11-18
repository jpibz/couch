Analyzing methods... (this may take a minute)

Processed 9 methods...
Processed 19 methods...
Processed 29 methods...
Processed 39 methods...
Processed 49 methods...
Processed 59 methods...
Processed 69 methods...
Processed 79 methods...
Processed 89 methods...
Processed 99 methods...
Processed 109 methods...
Processed 119 methods...

Generating table...

# ANALISI DETTAGLIATA METODI - 3 CLASSI PRINCIPALI

**TOTALE METODI:** 125

## LEGENDA COLONNE

- **#**: Numero progressivo
- **Metodo**: Nome del metodo
- **Classe**: Classe di appartenenza
- **Vis**: Visibilità (pub=public, priv=private)
- **Lines**: Numero righe di codice
- **Subprocess**: Usa chiamate subprocess (Yes/No)
- **Type**: Tipo traduzione (solo CommandTranslator)
  - **Core**: Logica centrale (parsing, dispatch)
  - **Simple**: Traduzione semplice 1:1
  - **Sim**: Simulazione/Workaround complesso
  - **Pipe**: Gestione pipeline/redirect/operators
  - **Help**: Metodo helper/utility

---

| # | Metodo | Classe | Vis | Lines | Subprocess | Type |
|---|--------|--------|-----|-------|------------|------|
| 1 | `__init__` | PathTranslator | pub | 16 | No |  |
| 2 | `get_workspace_root` | PathTranslator | pub | 9 | No |  |
| 3 | `get_tool_scratch_directory` | PathTranslator | pub | 17 | No |  |
| 4 | `get_claude_home_unix` | PathTranslator | pub | 11 | No |  |
| 5 | `get_claude_home_windows` | PathTranslator | pub | 11 | No |  |
| 6 | `get_uploads_directory_unix` | PathTranslator | pub | 9 | No |  |
| 7 | `get_uploads_directory_windows` | PathTranslator | pub | 11 | No |  |
| 8 | `get_outputs_directory_unix` | PathTranslator | pub | 9 | No |  |
| 9 | `get_outputs_directory_windows` | PathTranslator | pub | 11 | No |  |
| 10 | `to_windows` | PathTranslator | pub | 46 | No |  |
| 11 | `to_unix` | PathTranslator | pub | 47 | No |  |
| 12 | `ensure_directories_exist` | PathTranslator | pub | 15 | No |  |
| 13 | `translate_paths_in_string` | PathTranslator | pub | 28 | No |  |
| 14 | `_translate_unix_paths_to_windows` | PathTranslator | priv | 20 | No |  |
| 15 | `_translate_windows_paths_to_unix` | PathTranslator | priv | 20 | No |  |
| 16 | `__init__` | CommandTranslator | pub | 104 | No | Core |
| 17 | `translate` | CommandTranslator | pub | 100 | No | Core |
| 18 | `_parse_command_structure` | CommandTranslator | priv | 88 | No | Core |
| 19 | `_translate_single_command` | CommandTranslator | priv | 49 | No | Core |
| 20 | `_translate_ls` | CommandTranslator | priv | 75 | No | Pipe |
| 21 | `_translate_cat` | CommandTranslator | priv | 63 | No | Pipe |
| 22 | `_translate_echo` | CommandTranslator | priv | 37 | No | Sim |
| 23 | `_translate_pwd` | CommandTranslator | priv | 3 | No | Simple |
| 24 | `_translate_cd` | CommandTranslator | priv | 6 | No | Simple |
| 25 | `_translate_mkdir` | CommandTranslator | priv | 9 | No | Simple |
| 26 | `_translate_rm` | CommandTranslator | priv | 58 | No | Pipe |
| 27 | `_translate_cp` | CommandTranslator | priv | 72 | No | Sim |
| 28 | `_translate_mv` | CommandTranslator | priv | 11 | No | Simple |
| 29 | `_translate_touch` | CommandTranslator | priv | 26 | No | Pipe |
| 30 | `_translate_ln` | CommandTranslator | priv | 124 | No | Pipe |
| 31 | `_translate_grep` | CommandTranslator | priv | 124 | No | Pipe |
| 32 | `_translate_find` | CommandTranslator | priv | 24 | No | Sim |
| 33 | `_translate_which` | CommandTranslator | priv | 5 | No | Simple |
| 34 | `_translate_head` | CommandTranslator | priv | 59 | No | Pipe |
| 35 | `_translate_tail` | CommandTranslator | priv | 67 | No | Pipe |
| 36 | `_translate_wc` | CommandTranslator | priv | 47 | No | Pipe |
| 37 | `_translate_sort` | CommandTranslator | priv | 190 | No | Pipe |
| 38 | `_translate_uniq` | CommandTranslator | priv | 161 | No | Pipe |
| 39 | `_translate_ps` | CommandTranslator | priv | 3 | No | Simple |
| 40 | `_translate_kill` | CommandTranslator | priv | 8 | No | Simple |
| 41 | `_translate_env` | CommandTranslator | priv | 15 | No | Simple |
| 42 | `_translate_printenv` | CommandTranslator | priv | 15 | No | Simple |
| 43 | `_translate_export` | CommandTranslator | priv | 19 | No | Sim |
| 44 | `_translate_wget` | CommandTranslator | priv | 16 | No | Sim |
| 45 | `_translate_curl` | CommandTranslator | priv | 239 | No | Pipe |
| 46 | `_translate_chmod` | CommandTranslator | priv | 3 | No | Simple |
| 47 | `_translate_chown` | CommandTranslator | priv | 3 | No | Simple |
| 48 | `_translate_du` | CommandTranslator | priv | 36 | No | Pipe |
| 49 | `_translate_df` | CommandTranslator | priv | 3 | No | Simple |
| 50 | `_translate_date` | CommandTranslator | priv | 46 | No | Sim |
| 51 | `_translate_sleep` | CommandTranslator | priv | 5 | No | Simple |
| 52 | `_translate_basename` | CommandTranslator | priv | 6 | No | Simple |
| 53 | `_translate_dirname` | CommandTranslator | priv | 6 | No | Simple |
| 54 | `_translate_tar` | CommandTranslator | priv | 110 | No | Pipe |
| 55 | `_translate_zip` | CommandTranslator | priv | 69 | No | Sim |
| 56 | `_translate_unzip` | CommandTranslator | priv | 88 | No | Pipe |
| 57 | `_translate_sed` | CommandTranslator | priv | 233 | No | Pipe |
| 58 | `_translate_awk` | CommandTranslator | priv | 172 | No | Pipe |
| 59 | `_awk_to_ps_statement` | CommandTranslator | priv | 32 | No | Help |
| 60 | `_awk_to_ps_condition` | CommandTranslator | priv | 7 | No | Help |
| 61 | `_translate_cut` | CommandTranslator | priv | 87 | No | Pipe |
| 62 | `_parse_cut_range` | CommandTranslator | priv | 20 | No | Help |
| 63 | `_translate_true` | CommandTranslator | priv | 3 | No | Simple |
| 64 | `_translate_false` | CommandTranslator | priv | 7 | No | Simple |
| 65 | `_translate_test` | CommandTranslator | priv | 75 | No | Sim |
| 66 | `_translate_tr` | CommandTranslator | priv | 68 | No | Pipe |
| 67 | `_translate_diff` | CommandTranslator | priv | 212 | No | Pipe |
| 68 | `_translate_tee` | CommandTranslator | priv | 23 | No | Pipe |
| 69 | `_translate_seq` | CommandTranslator | priv | 33 | No | Pipe |
| 70 | `_translate_yes` | CommandTranslator | priv | 13 | No | Simple |
| 71 | `_translate_whoami` | CommandTranslator | priv | 4 | No | Simple |
| 72 | `_translate_hostname` | CommandTranslator | priv | 4 | No | Simple |
| 73 | `_translate_file` | CommandTranslator | priv | 21 | No | Pipe |
| 74 | `_translate_stat` | CommandTranslator | priv | 21 | No | Pipe |
| 75 | `_translate_readlink` | CommandTranslator | priv | 26 | No | Sim |
| 76 | `_translate_realpath` | CommandTranslator | priv | 21 | No | Pipe |
| 77 | `_translate_sha256sum` | CommandTranslator | priv | 9 | No | Simple |
| 78 | `_translate_sha1sum` | CommandTranslator | priv | 9 | No | Simple |
| 79 | `_translate_md5sum` | CommandTranslator | priv | 9 | No | Simple |
| 80 | `_translate_hexdump` | CommandTranslator | priv | 131 | No | Pipe |
| 81 | `_translate_strings` | CommandTranslator | priv | 68 | No | Sim |
| 82 | `_translate_column` | CommandTranslator | priv | 95 | No | Pipe |
| 83 | `_translate_watch` | CommandTranslator | priv | 58 | No | Sim |
| 84 | `_translate_paste` | CommandTranslator | priv | 88 | No | Sim |
| 85 | `_translate_comm` | CommandTranslator | priv | 88 | No | Sim |
| 86 | `_translate_join` | CommandTranslator | priv | 140 | No | Pipe |
| 87 | `_translate_base64` | CommandTranslator | priv | 58 | No | Pipe |
| 88 | `_translate_timeout` | CommandTranslator | priv | 88 | No | Pipe |
| 89 | `_parse_duration` | CommandTranslator | priv | 24 | No | Help |
| 90 | `_translate_split` | CommandTranslator | priv | 170 | No | Pipe |
| 91 | `_parse_size` | CommandTranslator | priv | 26 | No | Help |
| 92 | `_translate_gzip` | CommandTranslator | priv | 115 | No | Pipe |
| 93 | `_translate_gunzip` | CommandTranslator | priv | 92 | No | Sim |
| 94 | `_translate_jq` | CommandTranslator | priv | 111 | No | Pipe |
| 95 | `_is_simple_jq_pattern` | CommandTranslator | priv | 36 | No | Help |
| 96 | `_jq_to_powershell` | CommandTranslator | priv | 66 | No | Help |
| 97 | `__init__` | BashToolExecutor | pub | 96 | Yes |  |
| 98 | `_detect_git_bash` | BashToolExecutor | priv | 36 | Yes |  |
| 99 | `_detect_system_python` | BashToolExecutor | priv | 36 | Yes |  |
| 100 | `_expand_braces` | BashToolExecutor | priv | 73 | No |  |
| 101 | `_process_heredocs` | BashToolExecutor | priv | 100 | No |  |
| 102 | `_process_substitution` | BashToolExecutor | priv | 96 | Yes |  |
| 103 | `_process_command_substitution_recursive` | BashToolExecutor | priv | 113 | No |  |
| 104 | `_translate_substitution_content` | BashToolExecutor | priv | 46 | No |  |
| 105 | `_expand_variables` | BashToolExecutor | priv | 227 | No |  |
| 106 | `_preprocess_test_commands` | BashToolExecutor | priv | 30 | No |  |
| 107 | `_expand_aliases` | BashToolExecutor | priv | 29 | No |  |
| 108 | `_process_subshell` | BashToolExecutor | priv | 29 | No |  |
| 109 | `_process_command_grouping` | BashToolExecutor | priv | 25 | No |  |
| 110 | `_process_xargs` | BashToolExecutor | priv | 27 | No |  |
| 111 | `_process_find_exec` | BashToolExecutor | priv | 27 | No |  |
| 112 | `_process_escape_sequences` | BashToolExecutor | priv | 14 | No |  |
| 113 | `_has_control_structures` | BashToolExecutor | priv | 5 | No |  |
| 114 | `_convert_control_structures_to_script` | BashToolExecutor | priv | 32 | No |  |
| 115 | `_bash_to_powershell` | BashToolExecutor | priv | 105 | No |  |
| 116 | `_convert_test_to_powershell` | BashToolExecutor | priv | 40 | No |  |
| 117 | `_cleanup_temp_files` | BashToolExecutor | priv | 10 | No |  |
| 118 | `_needs_powershell` | BashToolExecutor | priv | 53 | No |  |
| 119 | `_adapt_for_powershell` | BashToolExecutor | priv | 35 | No |  |
| 120 | `_setup_virtual_env` | BashToolExecutor | priv | 48 | Yes |  |
| 121 | `_process_variable_assignments` | BashToolExecutor | priv | 54 | No |  |
| 122 | `execute` | BashToolExecutor | pub | 171 | Yes |  |
| 123 | `_setup_environment` | BashToolExecutor | priv | 21 | No |  |
| 124 | `_format_result` | BashToolExecutor | priv | 26 | No |  |
| 125 | `get_definition` | BashToolExecutor | pub | 20 | No |  |

---

## STATISTICHE AGGREGATE

### Per Classe

**PathTranslator (15 metodi):**
- Public: 13, Private: 2
- Lines totali: ~200
- Usa subprocess: 0 metodi
- **Classe semplice, ben focalizzata**

**CommandTranslator (81 metodi) ⚠️ ENORME:**
- Public: 2, Private: 79
- Lines totali: ~4000+
- Usa subprocess: 0 metodi
- **BREAKDOWN PER TIPO:**
  - Core Logic: 4 metodi
  - Simple 1:1: ~25 metodi
  - Simulation/Workaround: ~15 metodi
  - Pipeline/Operators: ~35 metodi
  - Helper: ~6 metodi

**BashToolExecutor (29 metodi):**
- Public: 3, Private: 26
- Lines totali: ~1500
- Usa subprocess: 5 metodi (execute, __init__, _detect_git_bash, _detect_system_python, _setup_virtual_env, _process_substitution)
- **Responsabilità miste: preprocessing + execution**

### Metodi più grandi (>100 righe)

| Metodo | Classe | Lines | Type | Commento |
|--------|--------|-------|------|----------|
| `_expand_variables` | BashToolExecutor | 227 | - | Troppo grande! |
| `_translate_diff` | CommandTranslator | 212 | Pipe | Può essere estratto |
| `execute` | BashToolExecutor | 171 | - | Main entry, potrebbe essere semplificato |
| `_translate_split` | CommandTranslator | 170 | Pipe | Può essere estratto |
| `_translate_join` | CommandTranslator | 140 | Pipe | Può essere estratto |
| `_translate_hexdump` | CommandTranslator | 131 | Pipe | Può essere estratto |
| `_translate_gzip` | CommandTranslator | 115 | Pipe | Può essere estratto |
| `_process_command_substitution_recursive` | BashToolExecutor | 113 | - | Complesso |
| `_translate_jq` | CommandTranslator | 111 | Pipe | Può essere estratto |
| `_bash_to_powershell` | BashToolExecutor | 105 | - | Può essere estratto |

### Uso Subprocess

**Metodi che usano subprocess (5 totali):**
1. `BashToolExecutor.__init__` (96 lines)
2. `BashToolExecutor._detect_git_bash` (36 lines)
3. `BashToolExecutor._detect_system_python` (36 lines)
4. `BashToolExecutor._process_substitution` (96 lines)
5. `BashToolExecutor._setup_virtual_env` (48 lines)
6. `BashToolExecutor.execute` (171 lines)

**OSSERVAZIONE:** Subprocess usato SOLO in BashToolExecutor (corretto per execution layer)

---

## PROBLEMI IDENTIFICATI

### 1. CommandTranslator è TROPPO GRANDE (81 metodi)
- Responsabilità mista: simple translation + simulation + pipeline handling
- Candidati per estrazione:
  - **SimpleTranslator**: 25 metodi simple 1:1 (~500 righe)
  - **SimulationTranslator**: 15 metodi simulation (~1200 righe)
  - **PipelineTranslator**: 35 metodi pipeline (~2000 righe)
  - **TranslationHelpers**: 6 metodi helper (~200 righe)
  - **CoreTranslator**: 4 metodi core (rimangono)

### 2. BashToolExecutor: Responsabilità miste
- Preprocessing (expand braces, variables, heredocs, substitution)
- Execution (subprocess, virtual env, git bash detection)
- Conversion (bash to powershell, control structures)
- Candidati per estrazione:
  - **BashPreprocessor**: metodi _expand_*, _process_* (~600 righe)
  - **PowerShellConverter**: metodi *_powershell, *_test (~200 righe)
  - Rimane: **BashToolExecutor** solo execution logic

### 3. PathTranslator è OK
- Piccolo (15 metodi, ~200 righe)
- Focalizzato (path translation)
- **Non necessita refactoring**

---

## PROPOSTA ARCHITETTURA SCOMPOSTA

```
OLD:
- PathTranslator (15 metodi) ✓ OK
- CommandTranslator (81 metodi) ✗ TROPPO GRANDE
- BashToolExecutor (29 metodi) ⚠️ RESPONSABILITÀ MISTE

NEW:
- PathTranslator (15 metodi) ✓ INVARIATO

- CommandTranslator (4 metodi core) ← ridotto da 81 a 4
  - SimpleTranslator (25 metodi)
  - SimulationTranslator (15 metodi)
  - PipelineTranslator (35 metodi)
  - TranslationHelpers (6 metodi)

- BashToolExecutor (12 metodi) ← ridotto da 29 a 12
  - BashPreprocessor (15 metodi)
  - PowerShellConverter (2 metodi)
```

**RISULTATO:** Da 3 classi (125 metodi) a 8 classi (~15 metodi/classe in media)
