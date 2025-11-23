# GAP ANALYSIS - GptHandler vs ClaudeHandler

## STATO ATTUALE

### ✅ GÀ COMPLETO
- `GptStreamingProcessor` - Accumula tool_calls, emette eventi
- `process_stream()` - Loop SSE con processor
- Basic response handling
- Simulation mode (mock)

### ❌ MANCANTE
1. **Tool Use Support**
   - `supports_tools()` → False
   - `prepare_payload()` vuoto (no tools conversion)
   - Nessuna tool execution
   - Nessun multi-call loop

2. **Event-based Tool Registry Access**
   - Non implementato (come ClaudeHandler)

---

## FORMATO OPENAI vs ANTHROPIC

### Tools Definition

**Anthropic** (quello che abbiamo):
```json
{
  "name": "get_weather",
  "description": "Get weather info",
  "input_schema": {
    "type": "object",
    "properties": {"location": {"type": "string"}},
    "required": ["location"]
  }
}
```

**OpenAI** (quello che serve):
```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather info",
    "parameters": {
      "type": "object",
      "properties": {"location": {"type": "string"}},
      "required": ["location"]
    }
  }
}
```

**Conversione**: `input_schema` → `parameters`, wrap in `{"type": "function", "function": {...}}`

---

## CONTINUATION FORMAT

Dopo tool execution, aggiungere a messages:

```json
[
  ...previous messages...,
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"location\": \"Paris\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "Sunny, 20°C"
  }
]
```

---

## IMPLEMENTAZIONE NECESSARIA

### 1. prepare_payload() - Tool Conversion

```python
def prepare_payload(self, payload: Dict) -> None:
    # Request tools via event
    tool_definitions = self._request_tool_definitions()
    
    if tool_definitions:
        # Convert Anthropic → OpenAI format
        payload['tools'] = [
            self._convert_tool_definition(td) 
            for td in tool_definitions
        ]
```

### 2. _convert_tool_definition()

```python
def _convert_tool_definition(self, anthropic_tool: Dict) -> Dict:
    return {
        "type": "function",
        "function": {
            "name": anthropic_tool["name"],
            "description": anthropic_tool.get("description", ""),
            "parameters": anthropic_tool.get("input_schema", {})
        }
    }
```

### 3. process_stream() - Check Tool Calls

```python
# Dopo processor.update_response(standard_response)

if processor.has_tool_calls():
    return self._handle_tool_calls(
        processor.get_tool_calls(),
        standard_response,
        context
    )
```

### 4. _handle_tool_calls() - Execute & Continue

```python
def _handle_tool_calls(self, tool_calls, standard_response, context):
    # Execute each tool
    tool_results = []
    for tc in tool_calls:
        tool_id = tc['id']
        func_name = tc['function']['name']
        arguments = json.loads(tc['function']['arguments'])
        
        # Execute via event_system (come ClaudeHandler)
        result = self._execute_tool_via_event(func_name, arguments)
        
        # Emit result
        context.emit_stream_output([{
            'type': 'tool_result',
            'tool_name': func_name,
            'tool_id': tool_id,
            'tool_result': result
        }])
        
        # Build result message
        tool_results.append({
            "role": "tool",
            "tool_call_id": tool_id,
            "content": result
        })
    
    # Build continuation
    continuation_payload = self._build_continuation_payload(
        context.original_payload,
        standard_response,
        tool_results
    )
    
    # Make request
    continue_request = StreamingRequest(
        request_id=str(uuid.uuid4()),
        payload=continuation_payload,
        progress_callback=None
    )
    
    return context.make_request(continue_request)
```

### 5. _build_continuation_payload()

```python
def _build_continuation_payload(self, original_payload, 
                                assistant_response, tool_results):
    payload = copy.deepcopy(original_payload)
    
    # Add assistant message with tool_calls
    assistant_msg = {
        "role": "assistant",
        "content": assistant_response['choices'][0]['message'].get('content'),
        "tool_calls": assistant_response['choices'][0]['message']['tool_calls']
    }
    payload['messages'].append(assistant_msg)
    
    # Add tool results
    for result in tool_results:
        payload['messages'].append(result)
    
    return payload
```

### 6. Event-based Tool Execution

```python
def _execute_tool_via_event(self, tool_name, tool_input):
    # Reset flags
    self._tool_execution_response = None
    self._tool_execution_received = False
    
    # Emit request
    self.event_system.emit_event('execute_tool_request', {
        'tool_name': tool_name,
        'tool_input': tool_input
    })
    
    # Wait for response
    max_wait = 30.0  # Tools possono essere lenti
    elapsed = 0.0
    sleep_interval = 0.01
    
    while not self._tool_execution_received and elapsed < max_wait:
        time.sleep(sleep_interval)
        self.event_system.emit_event('gui_update_request', {})
        elapsed += sleep_interval
    
    if not self._tool_execution_received:
        return f"ERROR: Timeout executing {tool_name}"
    
    return self._tool_execution_response
```

---

## MODIFICHE DA FARE

1. **GptHandler.__init__** - Aggiungere event subscriptions
2. **GptHandler.prepare_payload()** - Tool conversion
3. **GptHandler.process_stream()** - Check tool_calls dopo finalize
4. **GptHandler._handle_tool_calls()** - Nuovo metodo
5. **GptHandler._execute_tool_via_event()** - Nuovo metodo
6. **GptHandler._build_continuation_payload()** - Nuovo metodo
7. **GptHandler._convert_tool_definition()** - Nuovo metodo
8. **GptHandler.supports_tools()** - Cambiare a True

---

## MULTI-CALL LOOP (Opzionale)

Se GPT ritorna tool_calls nella continuation, loop:

```python
max_iterations = 5
iteration = 0

while has_tool_calls and iteration < max_iterations:
    iteration += 1
    # Execute tools
    # Build continuation
    # Make request
    # Check new tool_calls
```

---

## TOOL REGISTRY EVENTS

Servono **2 nuovi eventi** per execution:

**Request**: `execute_tool_request`
```python
{
    'tool_name': 'web_search',
    'tool_input': {'query': 'weather Paris'}
}
```

**Response**: `tool_execution_response`
```python
{
    'result': 'Sunny, 20°C'
}
```

---

## PRIORITÀ

1. **HIGH**: Tool conversion + prepare_payload
2. **HIGH**: Tool execution via events
3. **HIGH**: Single continuation (no loop)
4. **MEDIUM**: Multi-call loop
5. **LOW**: Error handling raffinato

---

## STIMA TEMPO

- Tool conversion: 30 min
- Event-based execution: 1 ora
- Continuation build: 1 ora
- Testing: 1 ora
- Multi-call loop: 30 min (opzionale)

**TOTALE**: ~3.5-4 ore
