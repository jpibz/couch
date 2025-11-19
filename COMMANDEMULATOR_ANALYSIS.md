# CommandEmulator - Analisi Completa command_map

## 1. command_map ESATTO DAL CODICE (unix_translator.py:362-448)

```python
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
```

**TOTALE in command_map: 70 comandi Unix**

---

## 2. TUTTI I METODI _translate_* REALI (ordine alfabetico)

| Metodo | Linee REALI | In command_map? | Note |
|--------|-------------|-----------------|------|
| `_translate_awk` | 172 | ✓ | HEAVY (>= 100) |
| `_translate_base64` | 58 | ✓ | QUICK |
| `_translate_basename` | 6 | ✓ | QUICK |
| `_translate_cat` | 63 | ✓ | QUICK |
| `_translate_cd` | 6 | ✓ | QUICK |
| `_translate_chmod` | 3 | ✓ | QUICK |
| `_translate_chown` | 3 | ✓ | QUICK |
| `_translate_column` | 95 | ✓ | QUICK |
| `_translate_comm` | 88 | ✓ | QUICK |
| `_translate_cp` | 72 | ✓ | QUICK |
| `_translate_curl` | 239 | ✓ | HEAVY (>= 100) |
| `_translate_cut` | 87 | ✓ | QUICK |
| `_translate_date` | 46 | ✓ | QUICK |
| `_translate_df` | 3 | ✓ | QUICK |
| `_translate_diff` | 212 | ✓ | HEAVY (>= 100) |
| `_translate_dirname` | 6 | ✓ | QUICK |
| `_translate_du` | 36 | ✓ | QUICK |
| `_translate_echo` | 37 | ✓ | QUICK |
| `_translate_env` | 15 | ✓ | QUICK |
| `_translate_export` | 19 | ✓ | QUICK |
| `_translate_false` | 7 | ✓ | QUICK |
| `_translate_file` | 21 | ✓ | QUICK |
| `_translate_find` | 24 | ✓ | QUICK |
| `_translate_grep` | 124 | ✓ | HEAVY (>= 100) |
| `_translate_gunzip` | 92 | ✓ | QUICK |
| `_translate_gzip` | 115 | ✓ | HEAVY (>= 100) |
| `_translate_head` | 51 | ✓ | QUICK |
| `_translate_hexdump` | 131 | ✓ | HEAVY (>= 100) |
| `_translate_hostname` | 4 | ✓ | QUICK |
| `_translate_join` | 140 | ✓ | HEAVY (>= 100) |
| `_translate_jq` | 111 | ✓ | HEAVY (>= 100) |
| `_translate_kill` | 8 | ✓ | QUICK |
| `_translate_ln` | 124 | ✓ | HEAVY (>= 100) |
| `_translate_ls` | 75 | ✓ | QUICK |
| `_translate_md5sum` | 9 | ✓ | QUICK |
| `_translate_mkdir` | 9 | ✓ | QUICK |
| `_translate_mv` | 11 | ✓ | QUICK |
| `_translate_paste` | 88 | ✓ | QUICK |
| `_translate_printenv` | 15 | ✓ | QUICK |
| `_translate_ps` | 3 | ✓ | QUICK |
| `_translate_pwd` | 3 | ✓ | QUICK |
| `_translate_readlink` | 26 | ✓ | QUICK |
| `_translate_realpath` | 21 | ✓ | QUICK |
| `_translate_rm` | 58 | ✓ | QUICK |
| `_translate_sed` | 233 | ✓ | HEAVY (>= 100) |
| `_translate_seq` | 33 | ✓ | QUICK |
| `_translate_sha1sum` | 9 | ✓ | QUICK |
| `_translate_sha256sum` | 9 | ✓ | QUICK |
| `_translate_sleep` | 5 | ✓ | QUICK |
| `_translate_sort` | 190 | ✓ | HEAVY (>= 100) |
| `_translate_split` | 170 | ✓ | HEAVY (>= 100) |
| `_translate_stat` | 21 | ✓ | QUICK |
| `_translate_strings` | 68 | ✓ | QUICK |
| `_translate_tail` | 56 | ✓ | QUICK |
| `_translate_tar` | 110 | ✓ | HEAVY (>= 100) |
| `_translate_tee` | 23 | ✓ | QUICK |
| `_translate_test` | 75 | ✓ | QUICK |
| `_translate_timeout` | 88 | ✓ | QUICK |
| `_translate_touch` | 26 | ✓ | QUICK |
| `_translate_tr` | 68 | ✓ | QUICK |
| `_translate_true` | 3 | ✓ | QUICK |
| `_translate_uniq` | 161 | ✓ | HEAVY (>= 100) |
| `_translate_unix_paths_to_windows` | 20 | ❌ | **UTILITY - non Unix command** |
| `_translate_unzip` | 88 | ✓ | QUICK |
| `_translate_watch` | 58 | ✓ | QUICK |
| `_translate_wc` | 34 | ✓ | QUICK |
| `_translate_wget` | 16 | ✓ | QUICK |
| `_translate_which` | 5 | ✓ | QUICK |
| `_translate_whoami` | 4 | ✓ | QUICK |
| `_translate_windows_paths_to_unix` | 21 | ❌ | **UTILITY - non Unix command** |
| `_translate_yes` | 13 | ✓ | QUICK |
| `_translate_zip` | 69 | ✓ | QUICK |

**TOTALE metodi: 72**
- **70 comandi Unix** (tutti in command_map ✓)
- **2 utility** (unix_paths_to_windows, windows_paths_to_unix) - correttamente ESCLUSI da command_map

---

## 3. CONFRONTO E VERIFICA

### ✅ COMMAND_MAP È COMPLETO

```
Metodi Unix _translate_*:         70
Comandi in command_map:           70
Differenza:                        0
```

### ✅ TUTTI I 70 COMANDI UNIX SONO MAPPATI

Nessun comando Unix mancante da command_map.

### ✅ UTILITY CORRETTAMENTE ESCLUSE

I 2 metodi utility (`unix_paths_to_windows`, `windows_paths_to_unix`) sono correttamente **NON inclusi** in command_map perché non sono comandi Unix, ma funzioni di supporto per path translation.

---

## 4. DISCREPANZE NEI LINE COUNT DOCUMENTATI

### ❌ ERRORI NEI COMMENTI command_map

| Comando | Line count DOCUMENTATO | Line count REALE | Differenza |
|---------|----------------------|-----------------|------------|
| `jq` | 212 lines | 111 lines | **-101 lines ❌** |
| `awk` | 211 lines | 172 lines | **-39 lines ❌** |
| `split` | 196 lines | 170 lines | **-26 lines ❌** |
| `timeout` | 112 lines | 88 lines | **-24 lines ❌** |
| `cut` | 107 lines | 87 lines | **-20 lines ❌** |

### ✓ CORRETTI (campione verificato)

| Comando | Documentato | Reale | Match |
|---------|------------|-------|-------|
| `pwd` | 3 | 3 | ✓ |
| `ls` | 75 | 75 | ✓ |
| `cat` | 63 | 63 | ✓ |
| `grep` | 124 | 124 | ✓ |
| `curl` | 239 | 239 | ✓ |
| `sed` | 233 | 233 | ✓ |

---

## 5. RESOCONTO FINALE

### ✅ POSITIVO

1. **command_map è COMPLETO**: Tutti i 70 comandi Unix sono mappati
2. **Nessun comando mancante**: Tutti i _translate_* Unix sono in command_map
3. **Utility correttamente escluse**: unix_paths_to_windows e windows_paths_to_unix NON sono in command_map (corretto)
4. **Struttura corretta**: Ogni 'cmd' → self._translate_cmd è corretto

### ❌ DA CORREGGERE

**I COMMENTI "# X lines" in command_map sono IMPRECISI per 5 comandi:**
- `jq`: documentato 212, reale 111 (-101)
- `awk`: documentato 211, reale 172 (-39)
- `split`: documentato 196, reale 170 (-26)
- `timeout`: documentato 112, reale 88 (-24)
- `cut`: documentato 107, reale 87 (-20)

**NOTA**: Questi errori nei commenti NON influenzano la funzionalità del codice, sono solo documentazione imprecisa. Il mapping funziona correttamente.

---

## 6. VERIFICA quick_commands

### Distribuzione REALE (con line count corretti):

```
< 20 lines:    25 comandi (very simple)
20-49 lines:   12 comandi (simple)
50-99 lines:   19 comandi (medium)
>= 100 lines:  14 comandi (heavy)
```

### quick_commands dovrebbe contenere < 100 lines = 56 comandi

**VERIFICA ATTUALE**: quick_commands = 56 comandi ✓ CORRETTO

---

## CONCLUSIONE

**command_map è FUNZIONALMENTE COMPLETO E CORRETTO.**

L'unico problema sono i commenti imprecisi per 5 comandi (jq, awk, split, timeout, cut), ma questo non influisce sulla funzionalità perché il mapping Python `'cmd': self._translate_cmd` è corretto.

La discrepanza nei line count documentati probabilmente deriva da:
- Refactoring successivi che hanno ridotto il codice
- Commenti non aggiornati dopo ottimizzazioni
- Conteggio iniziale errato

**Raccomandazione**: Opzionalmente correggere i 5 commenti errati per accuratezza documentale.
