# CommandEmulator - Analisi OUTPUT Comandi

## Metodologia CORRETTA

**ERRORE PRECEDENTE**: Classificazione basata su line count del metodo Python
**METRICA CORRETTA**: Classificazione basata su OUTPUT PowerShell/CMD generato

---

## Analisi Sistematica in 3 Passaggi

### PASSAGGIO 1: Analisi Return Statements Automatica
- Estratti tutti i return da ogni metodo `_translate_*`
- Contati: `powershell` usage, pipeline `|`, variabili `$`
- Classificazione preliminare

### PASSAGGIO 2: Verifica Comandi Semplici
- Analizzati return dei comandi non classificati al passaggio 1
- Identificati CMD 1:1 semplici

### PASSAGGIO 3: Analisi Condizionali
- Comandi con multipli return analizzati per complessità output
- Verificato se usano SEMPRE PowerShell o solo condizionalmente

---

## CLASSIFICAZIONE FINALE - 70 Comandi Unix

### ✅ TIER 1: CMD 1:1 Nativo (22 comandi) - **QUICK**

Comandi che traducono a **semplici comandi CMD/Windows** senza PowerShell:

```
basename    → echo {filename}
cd          → cd /d "path"
chmod       → echo (no-op on Windows)
chown       → echo (no-op on Windows)
cp          → copy /y "src" "dst"
df          → wmic logicaldisk
env         → set | echo %VAR%
export      → set VAR=value
false       → exit /b 1
hostname    → hostname
kill        → taskkill /pid
mkdir       → mkdir dirname
mv          → move /y "src" "dst"
printenv    → set | echo %VAR%
ps          → tasklist
pwd         → cd
rm          → del /del tree (multiple commands)
sleep       → timeout /t N
true        → exit /b 0
wget        → curl -o/-O (maps to curl)
which       → where command
whoami      → echo %USERNAME%
```

**CARATTERISTICHE:**
- Esecuzione CMD diretta, nessun PowerShell
- Instant execution
- Nessuna pipeline
- **SEMPRE QUICK**

---

### ✅ TIER 2: PowerShell Cmdlet Singolo (5 comandi) - **QUICK**

Comandi che traducono a **singolo cmdlet PowerShell** senza pipeline:

```
dirname     → powershell -Command "(Get-Item).Directory.FullName"
find        → Get-ChildItem -Recurse
md5sum      → Get-FileHash -Algorithm MD5
sha1sum     → Get-FileHash -Algorithm SHA1
sha256sum   → Get-FileHash -Algorithm SHA256
```

**CARATTERISTICHE:**
- Singolo cmdlet PowerShell
- NO pipeline
- NO variabili `$`
- **SEMPRE QUICK**

---

### ⚠️ TIER 3: PowerShell Condizionale (16 comandi) - **DIPENDE**

Comandi che usano PowerShell **SOLO PER FLAGS COMPLESSI**, altrimenti CMD:

```
base64      → PS solo per encode/decode
cat         → type (simple) | PS pipeline (con -n/-b flags)
cut         → PS con field selection
date        → echo %date% (simple) | PS per Unix timestamp
diff        → fc (simple) | PS per unified format
echo        → echo (simple) | PS per -n/-e flags
grep        → findstr (simple) | PS Select-String (complesso)
head        → type/more (simple) | PS Get-Content con -n
ln          → mklink (simple) | PS per symbolic/hard
sed         → PS con regex replace
tail        → type (simple) | PS Get-Content -Tail
tar         → tar.exe (se disponibile) | PS per compress/extract
test        → if exist (simple) | PS Test-Path per -f/-d/-x
wc          → find /c (lines only) | PS Measure-Object (full)
```

**CARATTERISTICHE:**
- **Casi semplici**: CMD diretto → QUICK
- **Casi complessi**: PowerShell → potenzialmente SLOW
- Dipende dai FLAG usati

**ESEMPIO:**
```bash
cat file.txt           → type file.txt (QUICK)
cat -n file.txt        → PS pipeline con line numbering (MEDIUM)
```

---

### ✗ TIER 4: PowerShell Pipeline Semplice (20 comandi) - **MEDIUM**

Comandi che generano **PowerShell con pipeline breve** (1-3 pipe):

```
du          → PS Get-ChildItem | Measure-Object
file        → PS Get-Item | Select properties
ls          → dir (simple) | PS Get-ChildItem | Format (con -l/-h)
readlink    → PS Get-Item -ItemType SymbolicLink
realpath    → PS Resolve-Path
seq         → PS 1..N
stat        → PS Get-Item | Select Mode, Length, LastWriteTime
tee         → PS Get-Content | Tee-Object
timeout     → PS Start-Sleep con timeout logic
touch       → PS New-Item/Set-ItemProperty
watch       → PS loop con sleep
yes         → PS infinite loop Write-Host
zip         → PS Compress-Archive
unzip       → PS Expand-Archive
```

**CARATTERISTICHE:**
- PowerShell con 1-3 pipeline stages
- Logica semplice, poche variabili
- **MEDIUM complexity**

---

### ✗✗ TIER 5: PowerShell COMPLESSO (14 comandi) - **HEAVY**

Comandi che generano **PowerShell con logica complessa**:

```
awk         → PS con $-variables, foreach, field processing (172 lines, $:20)
column      → PS con formatting loops ($:45)
comm        → PS con array comparison ($:21)
curl        → PS Invoke-WebRequest con options (239 lines)
gunzip      → PS con stream decompression ($:33)
gzip        → PS con stream compression ($:41)
hexdump     → PS con byte-level processing ($:75)
join        → PS con field join logic ($:72)
jq          → PS JSON parsing con nested objects ($:22)
paste       → PS con column merging ($:38)
sort        → PS Sort-Object con custom fields ($:48)
split       → PS con file splitting logic ($:67)
strings     → PS con byte filtering ($:20)
tr          → PS character translation (68 lines)
uniq        → PS Group-Object con counting ($:54)
```

**CARATTERISTICHE:**
- PowerShell con 3+ pipeline stages
- Logica complessa: loops, variabili `$`, foreach
- Field processing, byte manipulation
- **HEAVY, meglio Bash Git se disponibile**

---

## METRICHE SUMMARY

| Tier | Count | Type | Performance | Use Case |
|------|-------|------|-------------|----------|
| **TIER 1** | 22 | CMD 1:1 | **Instant** | Sempre CommandEmulator |
| **TIER 2** | 5 | PS Cmdlet | **Very Fast** | Sempre CommandEmulator |
| **TIER 3** | 16 | Conditional | **Depends** | CommandEmulator se simple flags |
| **TIER 4** | 20 | PS Pipeline | **Medium** | CommandEmulator se < 3 pipes |
| **TIER 5** | 14 | PS Complex | **Slow** | **Preferire Bash Git** |

**TOTALE: 70 comandi**

---

## CLASSIFICAZIONE CORRETTA per quick_commands

### QUICK COMMANDS = TIER 1 + TIER 2 = 27 comandi

**Sempre veloci, nessuna condizione:**

```python
self.quick_commands = {
    # TIER 1: CMD 1:1 (22)
    'basename', 'cd', 'chmod', 'chown', 'cp', 'df', 'env', 'export',
    'false', 'hostname', 'kill', 'mkdir', 'mv', 'printenv', 'ps',
    'pwd', 'rm', 'sleep', 'true', 'wget', 'which', 'whoami',

    # TIER 2: PS Cmdlet singolo (5)
    'dirname', 'find', 'md5sum', 'sha1sum', 'sha256sum'
}
```

### CONDITIONAL MEDIUM = TIER 3 + TIER 4 = 36 comandi

**Possono essere quick O medium, dipende dai flag:**

```python
# Questi NON vanno in quick_commands perché potrebbero essere slow
# Gestiti caso per caso da ExecuteUnixSingleCommand
```

Comandi: base64, cat, cut, date, diff, echo, grep, head, ln, sed, tail, tar, test, wc, du, file, ls, readlink, realpath, seq, stat, tee, timeout, touch, watch, yes, zip, unzip

### HEAVY = TIER 5 = 14 comandi

**Sempre preferire Bash Git se disponibile:**

Comandi: awk, column, comm, curl, gunzip, gzip, hexdump, join, jq, paste, sort, split, strings, tr, uniq

---

## CONCLUSIONE

La classificazione precedente era ERRATA:
- **56 "quick"** basato su line count metodo Python ❌
- **27 "quick"** basato su OUTPUT effettivo ✓

**FATTORE CRITICO IDENTIFICATO:**
- `ls` (75 line metodo) → CONDITIONAL (dir O PS pipeline) → NON sempre quick
- `grep` (124 line metodo) → CONDITIONAL (findstr O PS pipeline) → NON sempre quick
- Molti comandi TIER 3/4 erano classificati "quick" erroneamente

**LA METRICA CORRETTA È OUTPUT, NON LINE COUNT DEL METODO.**

---

*Analisi basata su ispezione REALE dei return statements e output generato*
*Data: 2025-11-19*
