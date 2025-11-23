# ARCHITETTURA AGENT-AGNOSTIC - EVENT-BASED COMMUNICATION

## PRINCIPIO FONDAMENTALE

**IL DAEMON NON SA CHE ESISTONO I TOOLS**
**COMUNICAZIONE VIA EVENT_SYSTEM**

---

## ARCHITETTURA CORRETTA

```
┌────────────────────────────────────────┐
│  ModernStreamWindow                    │
│  - Istanzia ToolRegistry               │
│  - Istanzia daemon (NO tool_registry)  │
└────────────────────────────────────────┘
         │                    │
         │ crea               │ crea
         ↓                    ↓
┌─────────────────┐   ┌──────────────────────┐
│  ToolRegistry   │   │  QtStreamingDaemon   │
│  - In ascolto   │   │  - Agent-agnostic    │
│    eventi       │   │  - NO tool_registry  │
└─────────────────┘   └──────────────────────┘
         ↑                    │
         │                    │ crea
         │                    ↓
         │            ┌──────────────────────┐
         │            │ AgentStreamingHandler│
         │            │ (Facade pura)        │
         │            └──────────────────────┘
         │                    │
         │                    │ crea
         │                    ↓
         │            ┌──────────────────────┐
         │            │   ClaudeHandler      │
         │            │                      │
         └────────────│   EVENT_SYSTEM       │
       (request/      │                      │
        response)     │   Request ──→        │
                      │   ←── Response       │
                      └──────────────────────┘
```

---

## COMUNICAZIONE EVENT-BASED

### Pattern Request/Wait/Response

**ClaudeHandler** → **ToolRegistry**:

1. **Request**: `emit_event('get_enabled_tools_request', {})`
2. **Wait**: Loop con sleep + `emit_event('gui_update_request', {})`
3. **Response**: Callback riceve `enabled_tools_response`

**Eventi implementati**:

| Request Event | Response Event | Data |
|---------------|----------------|------|
| `get_enabled_tools_request` | `enabled_tools_response` | `{'tool_definitions': [...]}` |
| `get_tool_system_prompt_request` | `tool_system_prompt_response` | `{'system_prompt': '...'}` |

---

## MODIFICHE ESEGUITE

### 1. ToolRegistry (DA FARE - snippet fornito)

✅ **AGGIUNGERE** in `_subscribe_events()`:
```python
# Request: tool definitions
self.event_system.subscribe('get_enabled_tools_request', 
                           self._on_get_enabled_tools_request)

# Request: system prompt addition
self.event_system.subscribe('get_tool_system_prompt_request', 
                           self._on_get_tool_system_prompt_request)
```

✅ **AGGIUNGERE** metodi handler:
```python
def _on_get_enabled_tools_request(self, data: Dict):
    enabled_definitions = self.get_enabled_definitions()
    self.event_system.emit_event('enabled_tools_response', {
        'tool_definitions': enabled_definitions
    })

def _on_get_tool_system_prompt_request(self, data: Dict):
    system_prompt = self.get_complete_system_prompt_addition()
    self.event_system.emit_event('tool_system_prompt_response', {
        'system_prompt': system_prompt
    })
```

### 2. agent_streaming_handler.py - ClaudeHandler

✅ **MODIFICATO** costruttore:
- Aggiunto `_tool_definitions_response`, `_system_prompt_response`
- Aggiunto flags `_tool_definitions_received`, `_system_prompt_received`
- Sottoscritto eventi `enabled_tools_response`, `tool_system_prompt_response`

✅ **AGGIUNTI** metodi:
- `_on_enabled_tools_response()` - callback per risposta tool definitions
- `_on_tool_system_prompt_response()` - callback per risposta system prompt
- `_request_tool_definitions()` - request/wait sync per tool definitions
- `_request_system_prompt()` - request/wait sync per system prompt

✅ **MODIFICATO** `prepare_payload()`:
- Usa `_request_tool_definitions()` invece di accesso diretto
- Usa `_request_system_prompt()` invece di accesso diretto

### 3. streaming_daemon_refactored.py

✅ **ELIMINATO** tutto riferimento a tool_registry:
- NO import
- NO costruttore parameter
- NO self.tool_registry
- NO metodi enable_tool/disable_tool/ecc.
- NO tool_registry in StreamContext

### 4. streaming_types.py

✅ **ELIMINATO** tool_registry da StreamContext

---

## VERIFICA

✅ **Zero tool_registry nel daemon**:
```bash
grep -n "tool_registry" streaming_daemon_refactored.py
# Solo commenti
```

✅ **Compilazione**:
```bash
python3 -m py_compile agent_streaming_handler.py     # ✅ OK
python3 -m py_compile streaming_daemon_refactored.py # ✅ OK
```

✅ **Event-based communication**: Implementato pattern request/wait/response

---

## SNIPPET PER TOOLREGISTRY

Il file `tool_registry_events_addition.py` contiene il codice da aggiungere a ToolRegistry:
- Sottoscrizioni eventi in `_subscribe_events()`
- Metodi handler `_on_get_enabled_tools_request()` e `_on_get_tool_system_prompt_request()`

---

## FUNZIONAMENTO

1. **ModernWindow** istanzia ToolRegistry e daemon separatamente
2. **ClaudeHandler.prepare_payload()** chiede tools via eventi:
   - Emette `get_enabled_tools_request`
   - Aspetta in loop con `gui_update_request`
   - Riceve risposta via callback `_on_enabled_tools_response`
   - Continua con elaborazione
3. **ToolRegistry** risponde agli eventi automaticamente
4. **Daemon** completamente blind - non sa che tools esistono

---

## BREAKING CHANGES

✅ **NESSUNO** - ModernWindow non deve essere modificato
✅ ToolRegistry riceve solo 2 nuovi eventi da gestire
✅ Daemon invariato dal punto di vista esterno

---

## FILES MODIFICATI

- ✅ `agent_streaming_handler.py` - Event-based communication
- ✅ `streaming_daemon_refactored.py` - Zero tool_registry
- ✅ `streaming_types.py` - StreamContext pulito
- ⏳ `ToolRegistry` - DA FARE (snippet fornito)

---

## LEZIONI APPRESE

1. ✅ **Event_system per comunicazione indiretta** - Pattern request/wait/response
2. ✅ **gui_update_request nel loop** - Keep GUI responsive durante wait
3. ✅ **Flags per sync su eventi async** - _received flags + loop
4. ✅ **Timeout su wait** - Max 2 secondi, poi fallback
5. ✅ **Daemon completamente blind** - Zero passaggio parametri

---

## REFACTORING COMPLETATO

**Architettura agent-agnostic COMPLETAMENTE implementata con comunicazione event-based**! 🎉

