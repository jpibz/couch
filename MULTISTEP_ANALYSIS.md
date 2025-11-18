# ANALISI METODI MULTISTEP

## DEFINIZIONE MULTISTEP
Un metodo è MULTISTEP se:
1. Chiama executor (execute_cmd/execute_bash/execute_powershell/subprocess.run)
2. USA il risultato (stdout/stderr/returncode) per fare ALTRO (step successivo)

## CLASSI ANALIZZATE

---

## 1. CommandExecutor (bash_tool_executor.py) ✅ COMPLETATO

**PATTERN IDENTIFICATO:** Tutti i metodi `_execute_*` sono **TRANSLATOR**, non EXECUTOR:
- Parsano comando Unix
- Traducono in PowerShell/CMD
- Ritornano `Tuple[str, bool]` (comando tradotto + flag)
- **NON eseguono** subprocess
- **NON usano** risultati per step successivi

| Line | Method | MULTISTEP | Note |
|------|--------|-----------|------|
| 967 | `__init__` | FALSE | Inizializzazione |
| 1018 | `single_executor` | FALSE | Property getter |
| 1054 | `execute` | FALSE | Esegue ma ritorna direttamente |
| 1133 | `execute_bash` | FALSE | Strategia, non execution |
| 1215 | `_detect_native_binaries` | FALSE | Detection binari |
| 1243 | `_execute_with_gitbash` | FALSE | Wrapper comando |
| 1264 | `_windows_to_gitbash_paths` | FALSE | Conversione paths |
| 1286 | `_get_execution_map` | FALSE | Ritorna dict |
| 1347 | `_execute_find` | FALSE | Translator |
| 1743 | `_execute_curl` | FALSE | Translator |
| 1983 | `_checksum_generic` | FALSE | Translator |
| 2036 | `_execute_sha256sum` | FALSE | Translator |
| 2039 | `_execute_sha1sum` | FALSE | Translator |
| 2042 | `_execute_md5sum` | FALSE | Translator |
| 2051 | `_execute_ln` | FALSE | Translator |
| 2178 | `_parse_find_size` | FALSE | Parser helper |
| 2207 | `_execute_join` | FALSE | Translator |
| 2350 | `_execute_diff` | FALSE | Translator |
| 2565 | `_execute_awk` | FALSE | Translator |
| 2825 | `_awk_to_ps_statement` | FALSE | Conversion helper |
| 2857 | `_awk_to_ps_condition` | FALSE | Conversion helper |
| 2867 | `_execute_sort` | FALSE | Translator |
| 3060 | `_execute_uniq` | FALSE | Translator |
| 3224 | `_execute_grep` | FALSE | Translator |
| 3351 | `_execute_tar` | FALSE | Translator |
| 3464 | `_execute_hexdump` | FALSE | Translator |
| 3598 | `_execute_gzip` | FALSE | Translator |
| 3716 | `_execute_split` | FALSE | Translator |
| 3886 | `_parse_size` | FALSE | Parser helper |
| 3915 | `_execute_jq` | FALSE | Translator |
| 4026 | `_is_simple_jq_pattern` | FALSE | Pattern matcher |
| 4062 | `_jq_to_powershell` | FALSE | Conversion helper |
| 4137 | `_execute_timeout` | FALSE | Translator |
| 4225 | `_parse_duration` | FALSE | Parser helper |
| 4252 | `_execute_sed` | FALSE | Translator |
| 4537 | `_execute_strings` | FALSE | Translator |
| 4607 | `_execute_base64` | FALSE | Translator |
| 4667 | `_execute_gunzip` | FALSE | Translator |
| 4761 | `_execute_column` | FALSE | Translator |
| 4858 | `_execute_unzip` | FALSE | Translator |
| 4948 | `_execute_watch` | FALSE | Translator |
| 5006 | `_execute_paste` | FALSE | Translator |
| 5094 | `_execute_comm` | FALSE | Translator |
| 5184 | `_execute_wget` | FALSE | Translator |
| 5231 | `_execute_head` | FALSE | Translator |
| 5348 | `_execute_tail` | FALSE | Translator |
| 5500 | `_execute_cat` | FALSE | Translator |
| 5692 | `_execute_wc` | FALSE | Translator |
| 5944 | `_execute_test` | FALSE | Translator |
| 6093 | `_execute_zip` | FALSE | Translator |

**RESULT: 50/50 metodi analizzati - 0 MULTISTEP trovati**

---

## 2. BashToolExecutor (bash_tool_executor.py) ✅ COMPLETATO

**PATTERN IDENTIFICATO:** Solo 2 metodi preprocessing sono MULTISTEP (eseguono + usano output):

| Line | Method | MULTISTEP | DUPLICATO | Note |
|------|--------|-----------|-----------|------|
| 6227 | `__init__` | FALSE | CommandTranslator, CommandExecutor | Inizializzazione |
| 6341 | `_detect_git_bash` | FALSE | - | Detection |
| 6377 | `_detect_system_python` | FALSE | - | Detection |
| 6413 | `_expand_braces` | FALSE | CommandTranslator | Pattern expansion |
| 6483 | `_process_heredocs` | **TRUE** | CommandTranslator (quasi-identico) | ✅ Esegue bash.exe per expand vars → usa stdout |
| 6663 | `_process_substitution` | **TRUE** | CommandTranslator (quasi-identico) | ✅ Esegue comando → usa stdout per temp file |
| 6758 | `_process_command_substitution_recursive` | FALSE | CommandTranslator | Pattern finder |
| 6858 | `_translate_substitution_content` | FALSE | CommandTranslator | Translator |
| 6957 | `_expand_variables` | FALSE | CommandTranslator | Variable expansion |
| 7200 | `_preprocess_test_commands` | FALSE | CommandTranslator | Pattern replace |
| 7230 | `_expand_aliases` | FALSE | CommandTranslator | Alias replace |
| 7259 | `_process_subshell` | FALSE | CommandTranslator | Pattern remove |
| 7287 | `_process_command_grouping` | FALSE | CommandTranslator | Pattern remove |
| 7309 | `_process_xargs` | FALSE | CommandTranslator | Pattern conversion |
| 7336 | `_process_find_exec` | FALSE | CommandTranslator | Pattern conversion |
| 7363 | `_process_escape_sequences` | FALSE | CommandTranslator | Escape handling |
| 7377 | `_has_control_structures` | FALSE | CommandTranslator | Boolean detection |
| 7382 | `_convert_control_structures_to_script` | FALSE | CommandTranslator | Creates script file, no exec |
| 7414 | `_bash_to_powershell` | FALSE | CommandTranslator | Conversion |
| 7519 | `_convert_test_to_powershell` | FALSE | CommandTranslator | Conversion |
| 7559 | `_cleanup_temp_files` | FALSE | CommandTranslator | Cleanup |
| 7569 | `_needs_powershell` | FALSE | CommandTranslator | Boolean detection |
| 7622 | `_adapt_for_powershell` | FALSE | CommandTranslator | Conversion |
| 7657 | `_setup_virtual_env` | FALSE | - | Setup/init |
| 7705 | `execute` | FALSE | CommandExecutor | Delegation, no multi-step |
| 7768 | `_setup_environment` | FALSE | - | Setup dict |
| 7789 | `_format_result` | FALSE | - | Formatting |
| 7823 | `get_definition` | FALSE | - | Returns dict |

**RESULT: 28/28 metodi analizzati - 2 MULTISTEP trovati**
**DUPLICATI: 21/28 metodi sono duplicati in CommandTranslator**

---

## 3. SimpleTranslator (unix_translator.py) ✅ COMPLETATO

**PATTERN IDENTIFICATO:** Tutti i metodi sono **simple 1:1 translators** (ritornano comando tradotto):

| Line | Method | MULTISTEP | Note |
|------|--------|-----------|------|
| 352 | `__init__` | FALSE | Inizializzazione |
| 356 | `_translate_pwd` | FALSE | Simple translator |
| 359 | `_translate_ps` | FALSE | Simple translator |
| 362 | `_translate_chmod` | FALSE | Simple translator |
| 365 | `_translate_chown` | FALSE | Simple translator |
| 368 | `_translate_df` | FALSE | Simple translator |
| 371 | `_translate_true` | FALSE | Simple translator |
| 374 | `_translate_false` | FALSE | Simple translator |
| 381 | `_translate_whoami` | FALSE | Simple translator |
| 385 | `_translate_hostname` | FALSE | Simple translator |
| 389 | `_translate_which` | FALSE | Simple translator |
| 394 | `_translate_sleep` | FALSE | Simple translator |
| 399 | `_translate_cd` | FALSE | Simple translator |
| 405 | `_translate_basename` | FALSE | Simple translator |
| 411 | `_translate_dirname` | FALSE | Simple translator |
| 417 | `_translate_kill` | FALSE | Simple translator |
| 425 | `_translate_mkdir` | FALSE | Simple translator |
| 434 | `_translate_mv` | FALSE | Simple translator |
| 445 | `_translate_yes` | FALSE | Simple translator |
| 458 | `_translate_env` | FALSE | Simple translator |
| 473 | `_translate_printenv` | FALSE | Simple translator |
| 488 | `_translate_export` | FALSE | Simple translator |

**RESULT: 23/23 metodi analizzati - 0 MULTISTEP trovati**

---

## 4. PipelineTranslator (unix_translator.py) ✅ COMPLETATO

**PATTERN IDENTIFICATO:** Tutti i metodi sono **pipeline-aware translators** (ritornano comando tradotto):

| Line | Method | MULTISTEP | Note |
|------|--------|-----------|------|
| 524 | `__init__` | FALSE | Inizializzazione |
| 528 | `_translate_touch` | FALSE | Pipeline translator |
| 554 | `_translate_echo` | FALSE | Pipeline translator |
| 591 | `_translate_wc` | FALSE | Pipeline translator |
| 638 | `_translate_du` | FALSE | Pipeline translator |
| 674 | `_translate_date` | FALSE | Pipeline translator |
| 720 | `_translate_head` | FALSE | Pipeline translator |
| 779 | `_translate_tail` | FALSE | Pipeline translator |
| 846 | `_translate_rm` | FALSE | Pipeline translator |
| 904 | `_translate_cat` | FALSE | Pipeline translator |
| 973 | `_translate_cp` | FALSE | Pipeline translator |
| 1045 | `_translate_ls` | FALSE | Pipeline translator |
| 1120 | `_translate_tee` | FALSE | Pipeline translator |
| 1143 | `_translate_seq` | FALSE | Pipeline translator |
| 1176 | `_translate_file` | FALSE | Pipeline translator |
| 1197 | `_translate_stat` | FALSE | Pipeline translator |
| 1218 | `_translate_readlink` | FALSE | Pipeline translator |
| 1244 | `_translate_realpath` | FALSE | Pipeline translator |
| 1265 | `_translate_tr` | FALSE | Pipeline translator |
| 1333 | `_translate_sha256sum` | FALSE | Pipeline translator |
| 1342 | `_translate_sha1sum` | FALSE | Pipeline translator |
| 1351 | `_translate_md5sum` | FALSE | Pipeline translator |
| 1360 | `_translate_base64` | FALSE | Pipeline translator |

**RESULT: 23/23 metodi analizzati - 0 MULTISTEP trovati**

---

## 5. EmulativeTranslator (unix_translator.py) ✅ COMPLETATO

**PATTERN IDENTIFICATO:** Tutti i metodi sono **complex emulative translators** + helpers (ritornano comando tradotto):

| Line | Method | MULTISTEP | Note |
|------|--------|-----------|------|
| 1435 | `__init__` | FALSE | Inizializzazione |
| 1439 | `_translate_wget` | FALSE | Emulative translator |
| 1455 | `_translate_curl` | FALSE | Emulative translator |
| 1694 | `_translate_sed` | FALSE | Emulative translator |
| 1927 | `_translate_diff` | FALSE | Emulative translator |
| 2139 | `_translate_jq` | FALSE | Emulative translator |
| 2250 | `_translate_awk` | FALSE | Emulative translator |
| 2422 | `_translate_split` | FALSE | Emulative translator |
| 2592 | `_translate_sort` | FALSE | Emulative translator |
| 2782 | `_translate_uniq` | FALSE | Emulative translator |
| 2943 | `_translate_join` | FALSE | Emulative translator |
| 3083 | `_translate_hexdump` | FALSE | Emulative translator |
| 3214 | `_translate_ln` | FALSE | Emulative translator |
| 3338 | `_translate_grep` | FALSE | Emulative translator |
| 3476 | `_translate_gzip` | FALSE | Emulative translator |
| 3591 | `_translate_gunzip` | FALSE | Emulative translator |
| 3683 | `_translate_timeout` | FALSE | Emulative translator |
| 3771 | `_translate_tar` | FALSE | Emulative translator |
| 3881 | `_translate_cut` | FALSE | Emulative translator |
| 3968 | `_translate_strings` | FALSE | Emulative translator |
| 4036 | `_translate_column` | FALSE | Emulative translator |
| 4131 | `_translate_watch` | FALSE | Emulative translator |
| 4189 | `_translate_paste` | FALSE | Emulative translator |
| 4277 | `_translate_comm` | FALSE | Emulative translator |
| 4365 | `_translate_zip` | FALSE | Emulative translator |
| 4434 | `_translate_unzip` | FALSE | Emulative translator |
| 4522 | `_translate_find` | FALSE | Emulative translator |
| 4575 | `_translate_test` | FALSE | Emulative translator |
| 4650 | `_awk_to_ps_statement` | FALSE | Conversion helper |
| 4682 | `_awk_to_ps_condition` | FALSE | Conversion helper |
| 4689 | `_parse_cut_range` | FALSE | Parser helper |
| 4709 | `_parse_duration` | FALSE | Parser helper |

**RESULT: 32/32 metodi analizzati - 0 MULTISTEP trovati**

---

## 6. CommandTranslator (unix_translator.py) ✅ COMPLETATO

**PATTERN IDENTIFICATO:** Stesso pattern BashToolExecutor - 2 metodi preprocessing MULTISTEP, resto translator/helpers:

| Line | Method | MULTISTEP | Note |
|------|--------|-----------|------|
| 4751 | `__init__` | FALSE | Inizializzazione |
| 4847 | `preprocess_command` | FALSE | Chiamasub-metodi, no exec diretta |
| 4897 | `execute_command` | FALSE | Delegation wrapper |
| 4937 | `translate` | FALSE | Dispatcher |
| 5037 | `_parse_command_structure` | FALSE | Parser |
| 5146 | `_translate_single_command` | FALSE | Dispatcher |
| 5204 | `_translate_ls` | FALSE | Translator |
| 5279 | `_translate_cat` | FALSE | Translator |
| 5348 | `_translate_echo` | FALSE | Translator |
| 5385 | `_translate_pwd` | FALSE | Translator |
| 5388 | `_translate_cd` | FALSE | Translator |
| 5394 | `_translate_mkdir` | FALSE | Translator |
| 5403 | `_translate_rm` | FALSE | Translator |
| 5461 | `_translate_cp` | FALSE | Translator |
| 5533 | `_translate_mv` | FALSE | Translator |
| 5544 | `_translate_touch` | FALSE | Translator |
| 5570 | `_translate_ln` | FALSE | Translator |
| 5694 | `_translate_grep` | FALSE | Translator |
| 5832 | `_translate_find` | FALSE | Translator |
| 5885 | `_translate_which` | FALSE | Translator |
| 5890 | `_translate_head` | FALSE | Translator |
| 5949 | `_translate_tail` | FALSE | Translator |
| 6016 | `_translate_wc` | FALSE | Translator |
| 6063 | `_translate_sort` | FALSE | Translator |
| 6253 | `_translate_uniq` | FALSE | Translator |
| 6414 | `_translate_ps` | FALSE | Translator |
| 6417 | `_translate_kill` | FALSE | Translator |
| 6425 | `_translate_env` | FALSE | Translator |
| 6440 | `_translate_printenv` | FALSE | Translator |
| 6455 | `_translate_export` | FALSE | Translator |
| 6474 | `_translate_wget` | FALSE | Translator |
| 6490 | `_translate_curl` | FALSE | Translator |
| 6729 | `_translate_chmod` | FALSE | Translator |
| 6732 | `_translate_chown` | FALSE | Translator |
| 6735 | `_translate_du` | FALSE | Translator |
| 6771 | `_translate_df` | FALSE | Translator |
| 6774 | `_translate_date` | FALSE | Translator |
| 6820 | `_translate_sleep` | FALSE | Translator |
| 6825 | `_translate_basename` | FALSE | Translator |
| 6831 | `_translate_dirname` | FALSE | Translator |
| 6837 | `_translate_tar` | FALSE | Translator |
| 6947 | `_translate_zip` | FALSE | Translator |
| 7016 | `_translate_unzip` | FALSE | Translator |
| 7104 | `_translate_sed` | FALSE | Translator |
| 7337 | `_translate_awk` | FALSE | Translator |
| 7509 | `_awk_to_ps_statement` | FALSE | Helper |
| 7541 | `_awk_to_ps_condition` | FALSE | Helper |
| 7548 | `_translate_cut` | FALSE | Translator |
| 7635 | `_parse_cut_range` | FALSE | Helper |
| 7655 | `_translate_true` | FALSE | Translator |
| 7658 | `_translate_false` | FALSE | Translator |
| 7665 | `_translate_test` | FALSE | Translator |
| 7740 | `_translate_tr` | FALSE | Translator |
| 7808 | `_translate_diff` | FALSE | Translator |
| 8020 | `_translate_tee` | FALSE | Translator |
| 8043 | `_translate_seq` | FALSE | Translator |
| 8076 | `_translate_yes` | FALSE | Translator |
| 8089 | `_translate_whoami` | FALSE | Translator |
| 8093 | `_translate_hostname` | FALSE | Translator |
| 8097 | `_translate_file` | FALSE | Translator |
| 8118 | `_translate_stat` | FALSE | Translator |
| 8139 | `_translate_readlink` | FALSE | Translator |
| 8165 | `_translate_realpath` | FALSE | Translator |
| 8186 | `_translate_sha256sum` | FALSE | Translator |
| 8195 | `_translate_sha1sum` | FALSE | Translator |
| 8204 | `_translate_md5sum` | FALSE | Translator |
| 8213 | `_translate_hexdump` | FALSE | Translator |
| 8344 | `_translate_strings` | FALSE | Translator |
| 8412 | `_translate_column` | FALSE | Translator |
| 8507 | `_translate_watch` | FALSE | Translator |
| 8565 | `_translate_paste` | FALSE | Translator |
| 8653 | `_translate_comm` | FALSE | Translator |
| 8741 | `_translate_join` | FALSE | Translator |
| 8881 | `_translate_base64` | FALSE | Translator |
| 8939 | `_translate_timeout` | FALSE | Translator |
| 9027 | `_parse_duration` | FALSE | Helper |
| 9051 | `_translate_split` | FALSE | Translator |
| 9221 | `_parse_size` | FALSE | Helper |
| 9247 | `_translate_gzip` | FALSE | Translator |
| 9362 | `_translate_gunzip` | FALSE | Translator |
| 9454 | `_translate_jq` | FALSE | Translator |
| 9565 | `_is_simple_jq_pattern` | FALSE | Helper |
| 9601 | `_jq_to_powershell` | FALSE | Helper |
| 9667 | `_expand_braces` | FALSE | Pattern expansion |
| 9737 | `_process_heredocs` | **TRUE** | ✅ Esegue bash.exe per expand → usa stdout |
| 9907 | `_process_substitution` | **TRUE** | ✅ Esegue comando → usa stdout per temp file |
| 10002 | `_process_command_substitution_recursive` | FALSE | Pattern finder |
| 10102 | `_translate_substitution_content` | FALSE | Translator |
| 10201 | `_expand_variables` | FALSE | Variable expansion |
| 10444 | `_preprocess_test_commands` | FALSE | Pattern replace |
| 10474 | `_expand_aliases` | FALSE | Alias replace |
| 10503 | `_process_subshell` | FALSE | Pattern remove |
| 10531 | `_process_command_grouping` | FALSE | Pattern remove |
| 10553 | `_process_xargs` | FALSE | Pattern conversion |
| 10580 | `_process_find_exec` | FALSE | Pattern conversion |
| 10607 | `_process_escape_sequences` | FALSE | Escape handling |
| 10621 | `_has_control_structures` | FALSE | Boolean detection |
| 10626 | `_convert_control_structures_to_script` | FALSE | Creates script, no exec |
| 10658 | `_bash_to_powershell` | FALSE | Conversion |
| 10763 | `_convert_test_to_powershell` | FALSE | Conversion |
| 10803 | `_cleanup_temp_files` | FALSE | Cleanup |
| 10813 | `_needs_powershell` | FALSE | Boolean detection |
| 10866 | `_adapt_for_powershell` | FALSE | Conversion |
| 10902 | `_get_default_environment` | FALSE | Setup dict |

**RESULT: 113/113 metodi analizzati - 2 MULTISTEP trovati**

---

## SUMMARY ✅ ANALISI COMPLETA

**TOTALE METODI ANALIZZATI: 269**

| Classe | Totale Metodi | MULTISTEP | Percentuale |
|--------|---------------|-----------|-------------|
| CommandExecutor | 50 | 0 | 0% |
| BashToolExecutor | 28 | 2 | 7.1% |
| SimpleTranslator | 23 | 0 | 0% |
| PipelineTranslator | 23 | 0 | 0% |
| EmulativeTranslator | 32 | 0 | 0% |
| CommandTranslator | 113 | 2 | 1.8% |
| **TOTALE** | **269** | **4** | **1.5%** |

---

## METODI MULTISTEP IDENTIFICATI (4 totali)

### BashToolExecutor (2 metodi)
1. **`_process_heredocs`** (line 6483)
   - Esegue bash.exe per espandere variabili nel heredoc
   - Usa stdout per creare contenuto heredoc (step successivo)

2. **`_process_substitution`** (line 6663)
   - Esegue comando per process substitution `<(cmd)`
   - Usa stdout per creare temp file (step successivo)

### CommandTranslator (2 metodi - duplicati)
3. **`_process_heredocs`** (line 9737)
   - Identico a BashToolExecutor._process_heredocs

4. **`_process_substitution`** (line 9907)
   - Identico a BashToolExecutor._process_substitution

---

## PATTERN IDENTIFICATI

### FALSE (Non MULTISTEP)
- **Translators** (`_translate_*`, `_execute_*`): Parsano + traducono → ritornano stringa
- **Helpers** (`_parse_*`, `_*_to_*`): Conversioni, parsing, helpers
- **Detection** (`_detect_*`, `_has_*`, `_needs_*`): Boolean/detection
- **Setup/Init** (`__init__`, `_setup_*`): Inizializzazione
- **Dispatchers** (`execute`, `translate`): Delegano ma non sono multistep
- **Pattern ops** (`_expand_*`, `_process_subshell`, ecc.): Pattern manipulation

### TRUE (MULTISTEP)
- **`_process_heredocs`**: Esegue bash.exe → usa stdout per step 2
- **`_process_substitution`**: Esegue comando → usa stdout per step 2

---

## ANALISI DUPLICATI

**TOTALE DUPLICATI: 107 metodi su 269 (39.8%)**

### Pattern Architetturale Identificato

**CommandTranslator è LEGACY/MONOLITICO:**
- Contiene versioni vecchie di TUTTI i metodi preprocessing (da BashToolExecutor)
- Contiene versioni vecchie di TUTTI i _translate_* (da Simple/Pipeline/Emulative Translator)
- Dovrebbe solo **delegare** ai translator specializzati, non contenere implementazioni

**Architettura ATTUALE (refactored):**
1. **BashToolExecutor** → preprocessing (versioni ATTIVE)
2. **CommandExecutor** → strategy + execution
3. **SimpleTranslator + PipelineTranslator + EmulativeTranslator** → translation (versioni ATTIVE)
4. **CommandTranslator** → orchestra i 3 translator (delega, non implementa)

**Duplicati principali:**
- BashToolExecutor ↔ CommandTranslator: 21 metodi (preprocessing)
- SimpleTranslator ↔ CommandTranslator: 22 metodi (_translate_* semplici)
- PipelineTranslator ↔ CommandTranslator: 23 metodi (_translate_* pipeline)
- EmulativeTranslator ↔ CommandTranslator: 32 metodi (_translate_* complessi)

**Status duplicati MULTISTEP:**
- `_process_heredocs`: quasi-identici (solo diff: `_setup_environment()` vs `_get_default_environment()`)
- `_process_substitution`: quasi-identici (solo diff: `_setup_environment()` vs `_get_default_environment()`)

Vedi **DUPLICATE_ANALYSIS.md** per dettagli completi.

---

## CONCLUSIONE

Solo **4 metodi su 269** (1.5%) sono MULTISTEP e necessitano del workaround testmode AS IF.

Tutti e 4 sono metodi preprocessing che:
1. Eseguono comando via executor
2. Usano lo stdout per processare step successivo

**AZIONE NECESSARIA:**
1. Aggiungere testmode workaround AS IF a questi 4 metodi:
   - BashToolExecutor._process_heredocs (line 6483) ← ATTIVO
   - BashToolExecutor._process_substitution (line 6663) ← ATTIVO
   - CommandTranslator._process_heredocs (line 9737) ← LEGACY
   - CommandTranslator._process_substitution (line 9907) ← LEGACY

2. **PRIORITÀ:** Modificare SOLO le versioni in BashToolExecutor (attive).
   Le versioni in CommandTranslator sono legacy e potrebbero essere rimosse in futuro.
