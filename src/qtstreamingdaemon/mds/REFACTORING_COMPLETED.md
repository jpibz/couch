# REFACTORING COMPLETATO - QtStreamingDaemon Agent-Agnostic

## Data: 22 Nov 2025

## OBIETTIVO RAGGIUNTO

Il daemon `QtStreamingDaemon` è ora **completamente agent-agnostic**. Non sa che esistono più agenti (Claude, GPT, ecc.) e non interpreta nulla di agent-specific.

---

## MODIFICHE ESEGUITE

### 1. streaming_types.py

#### StreamingRequest
- **RIMOSSO**: `extended_mode: bool = False`
- Il daemon non deve sapere se l'handler sta usando "extended mode"

#### StreamContext
- **RIMOSSI**: 
  - `max_extended_calls: int = 10`
  - `total_extended_budget: int = 50000`
- I budget limits sono ora gestiti INTERNAMENTE dall'handler

---

### 2. streaming_daemon_refactored.py

#### StreamingConfig
- **RIMOSSI parametri agent-specific**:
  - `max_extended_calls`
  - `extended_token_budget_per_call`
  - `total_extended_budget`
  - `extended_depth_shallow_max`
  - `extended_depth_deep_min`

#### StreamingMetrics
- **RIMOSSI campi agent-specific**:
  - `total_extended_tokens`
  - `extended_calls_total`
  - `extended_sessions_total`
  - `avg_extended_calls_per_session`
- **MODIFICATO**: `update_request_complete()` - rimosso parametro `extended_calls`

#### DetailedProgress
- **RIMOSSI**:
  - `extended_calls_completed`
  - `current_extended_depth`

#### QtStreamingDaemon
- **RIMOSSI instance variables**:
  - `self.max_extended_calls`
  - `self.total_extended_budget`
- **MODIFICATO** `_process_streaming_request()`:
  - `prepare_payload()` non ritorna più un valore
  - Rimosso `request.extended_mode = extended_mode_enabled`
  - Rimosso `extended_mode_enabled` da debug info
- **MODIFICATO** `_create_stream_context()`:
  - Rimossi `max_extended_calls` e `total_extended_budget`
- **RINOMINATO**: `extended_calls_completed` → `multi_call_count` in progress data
- **RIMOSSO**: `extended_tokens` dalle metrics update
- **AGGIORNATA** docstring per riflettere agent-agnostic design

---

### 3. agent_streaming_handler.py

#### BaseAgentHandler (ABC)
- **MODIFICATO** `prepare_payload()`: signature → `None` invece di `bool`

#### ClaudeHandler
- **AGGIUNTA config interna**:
  ```python
  self._max_thinking_calls = 8
  self._thinking_token_budget_per_call = 20000
  self._total_thinking_budget = 100000
  self._thinking_depth_shallow_max = 800
  self._thinking_depth_deep_min = 2000
  self._thinking_calls_count = 0
  self._thinking_tokens_used = 0
  self._thinking_enabled = False  # Set in prepare_payload()
  ```
- **MODIFICATO** `prepare_payload()`:
  - Ritorna `None` invece di `bool`
  - Salva `self._thinking_enabled` internamente
- **MODIFICATO** `_should_stop_thinking()`:
  - Usa `self._max_thinking_calls` invece di `context.max_extended_calls`
  - Usa `self._total_thinking_budget` invece di `context.total_extended_budget`
- **RIMOSSO** `extended_mode=True` dalla creazione di `StreamingRequest`

#### GptHandler
- **MODIFICATO** `prepare_payload()`: ritorna `None` invece di `False`

#### AgentStreamingHandler (Facade)
- **MODIFICATO** `prepare_payload()`: non ritorna più un valore

---

## VERIFICA FINALE

```bash
# Test: Zero riferimenti agent-specific nel daemon
grep -n "extended\|thinking\|claude\|Claude\|gpt\|Gpt" streaming_daemon_refactored.py
# Risultato: ZERO (esclusi commenti di documentazione)
```

---

## ARCHITETTURA FINALE

```
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 1: QtStreamingDaemon                                    │
│                                                                 │
│ • NON SA che esistono più agenti                               │
│ • Conosce SOLO "agent_handler" come se fosse l'unico agente    │
│ • NON interpreta MAI cosa ritornano i metodi dell'handler      │
│ • NON conosce: thinking, extended_mode, budgets, signatures    │
│ • Gestisce: streaming HTTP, retry, pause/resume, abort,        │
│   compressione generica, metrics generiche                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ usa SOLO
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 2: AgentStreamingHandler (FACADE PURA)                  │
│                                                                 │
│ • SA che esistono più modelli                                  │
│ • Istanzia l'handler corretto in base a config                 │
│ • NON SA NULLA di thinking, tools, signatures, budgets, ecc.   │
│ • È SOLO: __init__ + delegation pura a self._impl              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ delega a
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ LIVELLO 3: ClaudeHandler / GptHandler                           │
│                                                                 │
│ • SANNO TUTTO della loro logica specifica                      │
│ • ClaudeHandler: thinking, signatures, redacted, budgets       │
│   - _max_thinking_calls, _total_thinking_budget (INTERNI)      │
│   - _should_stop_thinking() usa limiti INTERNI                 │
│ • GptHandler: function calling, sua logica specifica           │
└─────────────────────────────────────────────────────────────────┘
```

---

## PRINCIPIO FONDAMENTALE

> **Il daemon è come un autista di taxi.**
> 
> L'autista sa guidare, sa la strada, sa gestire il traffico.
> NON sa chi è il passeggero, cosa fa nella vita, perché va in quel posto.
> 
> Il passeggero (handler) dice "portami qui" e l'autista esegue.
> L'autista non chiede "ma sei un dottore? hai fretta?".
> 
> Se il passeggero ha bisogno di fermarsi 3 volte, lo dice lui.
> L'autista non ha un "limite fermate per dottori".

---

## FILE MODIFICATI

1. `streaming_types.py` - Rimossi campi agent-specific
2. `streaming_daemon_refactored.py` - Rimosso tutto ciò che è agent-aware
3. `agent_streaming_handler.py` - Aggiunta config/tracking interno a ClaudeHandler
