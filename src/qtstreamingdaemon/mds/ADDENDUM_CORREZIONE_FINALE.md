# ADDENDUM - Correzione Finale Architettura Agent-Agnostic

## PROBLEMA IDENTIFICATO

Il daemon ha ancora **DUE VIOLAZIONI** dell'architettura agent-agnostic:

### Violazione #1: Daemon conosce tool_registry
```python
# QtStreamingDaemon.__init__
self.tool_registry = ToolRegistry(...)  # ❌ SBAGLIATO
```

### Violazione #2: Daemon passa tools a prepare_payload()
```python
# QtStreamingDaemon._process_streaming_request
tool_definitions = self.tool_registry.get_enabled_definitions()  # ❌
tools_system_prompt = self.tool_registry.get_complete_system_prompt_addition()  # ❌
self.agent_handler.prepare_payload(payload, tool_definitions, tools_system_prompt)  # ❌
```

**PERCHÉ È SBAGLIATO**:
- Il daemon NON deve sapere che esistono i tools
- Il daemon NON deve estrarre tool definitions
- Il daemon NON deve passare nulla oltre al payload

---

## ARCHITETTURA CORRETTA - 3 LIVELLI

```
DAEMON (Layer 1)
  ↓ conosce solo
  agent_handler (come se fosse l'unico agente nell'universo)
  ↓ chiama
  agent_handler.prepare_payload(payload)  ← SOLO payload, nient'altro

AGENT HANDLER (Layer 2 - Facade)
  ↓ sa che esistono più modelli
  ↓ istanzia handler corretto
  ↓ delega
  self._impl.prepare_payload(payload)

CLAUDE/GPT HANDLER (Layer 3)
  ↓ ha tool_registry nel costruttore
  ↓ decide TUTTO internamente
  def prepare_payload(self, payload):
      if needs_tools():
          tools = self.tool_registry.get_enabled_definitions()
          payload['tools'] = tools
```

---

## PRINCIPIO FONDAMENTALE

**DAEMON**:
- Non sa che esistono AGENT (plurale)
- Non sa che esistono TOOLS
- Non sa che esiste THINKING
- Conosce SOLO agent_handler (singolare, come unico interlocutore)

**AGENT HANDLER** (Facade):
- SA che esistono più modelli
- Istanzia handler corretto
- NON SA logiche interne (tools, thinking, ecc.)
- È SOLO wrapper puro

**CLAUDE/GPT HANDLER**:
- SA TUTTO della propria logica
- HA accesso diretto a tool_registry
- DECIDE internamente cosa fare

---

## MODIFICHE DA FARE

### 1. Spostare tool_registry

**DA**: `QtStreamingDaemon.__init__`
```python
self.tool_registry = ToolRegistry(...)  # ❌ Rimuovere
```

**A**: `AgentStreamingHandler.__init__`
```python
def __init__(self, config, event_system, logger, tool_registry):
    self.tool_registry = tool_registry
    # Passa a handler specifico
    if is_claude:
        self._impl = ClaudeHandler(event_system, logger, tool_registry)
    else:
        self._impl = GptHandler(event_system, logger, tool_registry)
```

### 2. Handler specifici ricevono tool_registry

```python
class ClaudeHandler(BaseAgentHandler):
    def __init__(self, event_system, logger, tool_registry):
        super().__init__(event_system, logger)
        self.tool_registry = tool_registry  # ✅ Accesso diretto
```

### 3. Modificare prepare_payload signature

**PRIMA**:
```python
def prepare_payload(self, payload: Dict, tool_definitions: List[Dict],
                    tools_system_prompt: str) -> None:
```

**DOPO**:
```python
def prepare_payload(self, payload: Dict) -> None:
    # Handler decide internamente se servono tools
    if self._check_thinking_enabled(payload):
        if self._is_interleaved_mode(payload):
            tools = self.tool_registry.get_enabled_definitions()  # ✅ Prende direttamente
            payload['tools'] = tools
```

### 4. Daemon chiama solo con payload

```python
# QtStreamingDaemon._process_streaming_request
self.agent_handler.prepare_payload(request.payload)  # ✅ SOLO payload
```

### 5. Daemon istanzia AgentStreamingHandler con tool_registry

```python
# QtStreamingDaemon.__init__
self.tool_registry = ToolRegistry(...)  # Istanzia per passarlo

# QtStreamingDaemon._process_streaming_request
self.agent_handler = AgentStreamingHandler(
    models_config.SELECTED_CONF, 
    self.event_system, 
    self.logger,
    self.tool_registry  # ✅ Passa a facade
)
```

---

## FILE DA MODIFICARE

1. **streaming_daemon_refactored.py**
   - Rimuovere `tool_definitions` e `tools_system_prompt` da prepare_payload call
   - Passare `tool_registry` al costruttore di AgentStreamingHandler

2. **agent_streaming_handler.py**
   - `BaseAgentHandler.__init__`: aggiungere parametro `tool_registry`
   - `ClaudeHandler.__init__`: ricevere e salvare `tool_registry`
   - `GptHandler.__init__`: ricevere e salvare `tool_registry`
   - `prepare_payload()`: rimuovere parametri `tool_definitions` e `tools_system_prompt`
   - `ClaudeHandler.prepare_payload()`: prendere tools direttamente da `self.tool_registry`
   - `AgentStreamingHandler.__init__`: ricevere `tool_registry` e passarlo a `_impl`

---

## RISULTATO FINALE

✅ **Daemon completamente agent-agnostic**
- Non sa di tools
- Non sa di thinking
- Non sa di multi-model
- Conosce solo agent_handler

✅ **Facade pulita**
- Solo wrapper
- Nessuna logica interna

✅ **Handler autonomi**
- Accesso diretto a dipendenze
- Decidono tutto internamente
