# ANALISI METODI - 3 CLASSI PRINCIPALI (CORRETTA)

**TOTALE METODI:** 155

## CLASSI ANALIZZATE

1. **CommandTranslator** (81 metodi) - unix_translator.py
2. **CommandExecutor** (45 metodi) - bash_tool_executor.py  
3. **BashToolExecutor** (29 metodi) - bash_tool_executor.py

**PathTranslator NON incluso** (fuori scope analisi decomposizione)

---

## FILE GENERATI

### 📊 METHOD_ANALYSIS.csv
**Formato CSV** - Apribile in Excel/Google Sheets/LibreOffice Calc

**Colonne pre-popolate:**
- Num: Numero progressivo
- Method: Nome metodo
- Class: Classe appartenenza
- Visibility: public/private
- Lines: Righe codice
- Uses_Subprocess: Yes/No
- Translation_Type: Core/Simple/Sim/Pipe/Help

**Colonne EDITABILI (per tua analisi):**
- Category: Categoria funzionale
- Extract_To: Nome nuova classe per estrazione
- Notes: Note varie

---

## STATISTICHE RAPIDE

### CommandTranslator (81 metodi) ⚠️ TROPPO GRANDE
- Public: 2, Private: 79
- Lines totali: ~4000+
- Subprocess: NO (0 metodi)
- **Breakdown per tipo:**
  - Core Logic: 4 metodi
  - Simple 1:1: ~25 metodi
  - Simulation: ~15 metodi
  - Pipeline/Operators: ~35 metodi
  - Helper: ~6 metodi

### CommandExecutor (45 metodi) ⚠️ GRANDE
- Public: 1, Private: 44
- Lines totali: ~2500+
- Subprocess: da analizzare
- **Responsabilità:** Execution strategies + command-specific executors

### BashToolExecutor (29 metodi) ⚠️ RESPONSABILITÀ MISTE
- Public: 3, Private: 26
- Lines totali: ~1500
- Subprocess: 6 metodi (execute, __init__, _detect_git_bash, _detect_system_python, _setup_virtual_env, _process_substitution)
- **Responsabilità miste:** preprocessing + execution + conversion

---

## PROSSIMI STEP

1. **Analizza CSV in Excel/Sheets**
2. **Popola colonne Category/Extract_To**
3. **Identifica gruppi coesi di metodi**
4. **Proponi decomposizione**

