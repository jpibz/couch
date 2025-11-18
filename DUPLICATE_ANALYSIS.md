# ANALISI DUPLICATI METODI

## SUMMARY

**TOTALE DUPLICATI TROVATI: 107 metodi**

| Coppia Classi | Metodi Comuni | Status |
|---------------|---------------|--------|
| BashToolExecutor ↔ CommandTranslator | 21 | QUASI-IDENTICI (differenza: setup env) |
| SimpleTranslator ↔ CommandTranslator | 22 | DA VERIFICARE |
| PipelineTranslator ↔ CommandTranslator | 23 | DA VERIFICARE |
| EmulativeTranslator ↔ CommandTranslator | 32 | DA VERIFICARE |
| CommandExecutor ↔ BashToolExecutor | 2 | DA VERIFICARE |
| CommandExecutor ↔ CommandTranslator | 7 | DA VERIFICARE |

---

## METODI MULTISTEP - DETTAGLIO DUPLICATI

### 1. _process_heredocs

| Classe | File | Line | Differenza |
|--------|------|------|------------|
| BashToolExecutor | bash_tool_executor.py | 6483 | usa `self._setup_environment()` |
| CommandTranslator | unix_translator.py | 9737 | usa `self._get_default_environment()` |

**STATUS:** ⚠️ QUASI-IDENTICI (170 righe)
- Unica diff: riga 119 → nome metodo setup env diverso

### 2. _process_substitution

| Classe | File | Line | Differenza |
|--------|------|------|------------|
| BashToolExecutor | bash_tool_executor.py | 6663 | usa `self._setup_environment()` |
| CommandTranslator | unix_translator.py | 9907 | usa `self._get_default_environment()` |

**STATUS:** ⚠️ QUASI-IDENTICI (95 righe)
- Unica diff: riga 20 → nome metodo setup env diverso

---

## ALTRI DUPLICATI BashToolExecutor ↔ CommandTranslator (19 metodi)

1. `__init__`
2. `_adapt_for_powershell`
3. `_bash_to_powershell`
4. `_cleanup_temp_files`
5. `_convert_control_structures_to_script`
6. `_convert_test_to_powershell`
7. `_expand_aliases`
8. `_expand_braces`
9. `_expand_variables`
10. `_has_control_structures`
11. `_needs_powershell`
12. `_preprocess_test_commands`
13. `_process_command_grouping`
14. `_process_command_substitution_recursive`
15. `_process_escape_sequences`
16. `_process_find_exec`
17. `_process_subshell`
18. `_process_xargs`
19. `_translate_substitution_content`

**PATTERN:** Preprocessing/conversion logic duplicato

---

## DUPLICATI SimpleTranslator ↔ CommandTranslator (22 metodi)

Tutti i metodi `_translate_*` per comandi semplici:
- pwd, cd, mkdir, rm, mv, chmod, chown, df, basename, dirname, kill, env, printenv, export, whoami, hostname, sleep, true, false, yes, which

**PATTERN:** CommandTranslator ha versione propria di TUTTI i translator

---

## DUPLICATI PipelineTranslator ↔ CommandTranslator (23 metodi)

Tutti i metodi `_translate_*` per comandi pipeline:
- ls, cat, echo, wc, head, tail, rm, cp, touch, tee, seq, file, stat, readlink, realpath, tr, date, du, sha256sum, sha1sum, md5sum, base64

**PATTERN:** CommandTranslator ha versione propria di TUTTI i translator

---

## DUPLICATI EmulativeTranslator ↔ CommandTranslator (32 metodi)

Tutti i metodi `_translate_*` per comandi complessi:
- wget, curl, sed, diff, jq, awk, split, sort, uniq, join, hexdump, ln, grep, gzip, gunzip, timeout, tar, cut, strings, column, watch, paste, comm, zip, unzip, find, test

**PATTERN:** CommandTranslator ha versione propria di TUTTI i translator

---

## DUPLICATI CommandExecutor ↔ Altre Classi

### CommandExecutor ↔ BashToolExecutor (2 metodi)
- `__init__`
- `execute`

### CommandExecutor ↔ CommandTranslator (7 metodi)
- `__init__`
- `_awk_to_ps_statement`
- `_awk_to_ps_condition`
- `_is_simple_jq_pattern`
- `_jq_to_powershell`
- `_parse_duration`
- `_parse_size`

**PATTERN:** Helpers condivisi

---

## CONCLUSIONI

1. **CommandTranslator contiene TUTTI i metodi** delle altre classi translator (Simple/Pipeline/Emulative)
2. **CommandTranslator contiene TUTTI i metodi** preprocessing di BashToolExecutor
3. I metodi sono QUASI-IDENTICI con piccole differenze (es. nome metodo setup)
4. Architettura: **OLD (CommandTranslator monolitico) vs NEW (classi specializzate)**

## ARCHITETTURA

**NUOVO (attuale):**
- BashToolExecutor → preprocessing
- CommandExecutor → strategy + execution
- SimpleTranslator + PipelineTranslator + EmulativeTranslator → translation specializzato
- CommandTranslator → **orchestra i 3 translator** (non fa più traduzione diretta)

**LEGACY (dentro CommandTranslator):**
- CommandTranslator conteneva TUTTO il codice (monolitico)
- Ora è stato decomposto nelle classi specializzate

**IMPLICAZIONE:**
- I metodi in CommandTranslator sono **versioni vecchie/legacy**
- Le versioni **attive** sono in BashToolExecutor e nei 3 Translator
- CommandTranslator dovrebbe solo **delegare** ai translator, non contenere implementazioni
