# ROADMAP - Completare Tool Use Support per GPT

## STATO ATTUALE

✅ **GptStreamingProcessor** - COMPLETO
- Accumula tool_calls incrementalmente
- Emette eventi `tool_start`
- Metodo `get_tool_calls()` ritorna lista completa
- Metodo `has_tool_calls()` per check

❌ **GptHandler** - Tool execution NON implementata
- Processor pronto, ma handler non esegue i tool
- Nessun loop multi-call
- `supports_tools()` → False

---

## STEP 1 - Abilitare Tool Use Base

### 1.1 Modificare `supports_tools()`

```python
def supports_tools(self) -> bool:
    return True  # CHANGED: Now supported
```

### 1.2 Modificare `prepare_payload()`

```python
def prepare_payload(self, payload: Dict, tool_definitions: List[Dict],
                    tools_system_prompt: str) -> None:
    """
    Prepare GPT payload - add tools if provided.
    """
    if tool_definitions:
        # Convert Anthropic format to OpenAI format
        payload['tools'] = [
            self._convert_tool_definition(td) for td in tool_definitions
        ]
```

### 1.3 Aggiungere `_convert_tool_definition()`

```python
def _convert_tool_definition(self, anthropic_tool: Dict) -> Dict:
    """
    Convert Anthropic tool definition to OpenAI format.
    
    Anthropic:
        {
            "name": "get_weather",
            "description": "Get weather...",
            "input_schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    
    OpenAI:
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather...",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }
    """
    return {
        "type": "function",
        "function": {
            "name": anthropic_tool["name"],
            "description": anthropic_tool.get("description", ""),
            "parameters": anthropic_tool.get("input_schema", {})
        }
    }
```

---

## STEP 2 - Implementare Tool Execution

### 2.1 Modificare `process_stream()` per check tool calls

```python
def process_stream(self, response, request: StreamingRequest, 
                   standard_response: Dict, context: StreamContext) -> StreamResult:
    processor = GptStreamingProcessor(self.event_system, self.logger)
    
    # ... existing loop ...
    
    # ═══ FINALIZE ═══
    processor.update_response(standard_response)
    
    # ═══ CHECK TOOL CALLS ═══
    if processor.has_tool_calls():
        self.logger.info(f"GPT response has {len(processor.get_tool_calls())} tool calls")
        
        # Execute tools and continue
        return self._handle_tool_calls(
            processor.get_tool_calls(),
            standard_response,
            context
        )
    
    processor.cleanup()
    return StreamResult(success=True, response=standard_response, ...)
```

### 2.2 Implementare `_handle_tool_calls()`

```python
def _handle_tool_calls(self, tool_calls: List[Dict], 
                       standard_response: Dict,
                       context: StreamContext) -> StreamResult:
    """
    Execute tools e build continuation.
    
    Simile a ClaudeHandler._finalize_claude_response() ma per GPT format.
    """
    # Build tool results
    tool_results = []
    
    for tool_call in tool_calls:
        tool_id = tool_call['id']
        function_name = tool_call['function']['name']
        
        # Parse arguments
        try:
            arguments = json.loads(tool_call['function']['arguments'])
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid tool arguments JSON: {e}")
            arguments = {}
        
        # Execute tool
        try:
            result = context.tool_registry.execute_tool(function_name, arguments)
            success = True
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            result = f"Error: {str(e)}"
            success = False
        
        # Emit tool result
        context.emit_stream_output([{
            'type': 'tool_result',
            'tool_name': function_name,
            'tool_id': tool_id,
            'tool_result': result
        }])
        
        # Build result for continuation
        tool_results.append({
            "tool_call_id": tool_id,
            "role": "tool",
            "name": function_name,
            "content": result
        })
    
    # Build continuation payload
    continuation_payload = self._build_continuation_payload(
        context.original_payload,
        standard_response,
        tool_results
    )
    
    # Make continuation request
    continue_request = StreamingRequest(
        request_id=str(uuid.uuid4()),
        payload=continuation_payload,
        progress_callback=None
    )
    
    result = context.make_request(continue_request)
    
    if result.get('success') and result.get('response'):
        return result['response']
    
    return standard_response
```

### 2.3 Implementare `_build_continuation_payload()`

```python
def _build_continuation_payload(self, original_payload: Dict,
                                assistant_response: Dict,
                                tool_results: List[Dict]) -> Dict:
    """
    Build continuation payload for GPT after tool execution.
    
    GPT format:
        messages: [
            ...previous messages...,
            {role: "assistant", content: null, tool_calls: [...]},
            {role: "tool", tool_call_id: "...", content: "..."},
            {role: "tool", tool_call_id: "...", content: "..."}
        ]
    """
    payload = copy.deepcopy(original_payload)
    
    # Add assistant message with tool calls
    assistant_message = {
        "role": "assistant",
        "content": assistant_response['choices'][0]['message'].get('content'),
        "tool_calls": assistant_response['choices'][0]['message'].get('tool_calls', [])
    }
    
    payload['messages'].append(assistant_message)
    
    # Add tool results
    for tool_result in tool_results:
        payload['messages'].append(tool_result)
    
    return payload
```

---

## STEP 3 - Multi-call Loop (Opzionale)

Se GPT ritorna tool_calls nella continuation response, ripetere il loop.

```python
def _handle_tool_calls(self, tool_calls, standard_response, context):
    """With multi-call support"""
    
    max_iterations = 5  # Internal limit
    iteration = 0
    
    current_response = standard_response
    current_tool_calls = tool_calls
    
    while current_tool_calls and iteration < max_iterations:
        iteration += 1
        self.logger.info(f"Tool iteration {iteration}/{max_iterations}")
        
        # Execute tools
        tool_results = self._execute_tools(current_tool_calls, context)
        
        # Build continuation
        continuation_payload = self._build_continuation_payload(
            context.original_payload, current_response, tool_results
        )
        
        # Make request
        continue_request = StreamingRequest(
            request_id=str(uuid.uuid4()),
            payload=continuation_payload,
            progress_callback=None
        )
        
        result = context.make_request(continue_request)
        
        if not result.get('success'):
            break
        
        current_response = result['response']
        
        # Check if new tool calls
        new_tool_calls = current_response['choices'][0]['message'].get('tool_calls')
        if not new_tool_calls:
            break
        
        current_tool_calls = new_tool_calls
    
    return current_response
```

---

## TESTING PLAN

### Test 1 - Single Tool Call
```python
payload = {
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
    "tools": [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    }]
}
```

**Expected**:
1. GPT ritorna tool_call
2. GptStreamingProcessor accumula
3. GptHandler esegue tool
4. Continuation request con result
5. GPT ritorna risposta finale

### Test 2 - Multiple Tool Calls
```python
# User asks something requiring 2+ tools
# GPT returns multiple tool_calls in single response
```

**Expected**:
1. Processor accumula tutti i tool_calls
2. Handler esegue tutti
3. Continuation con tutti i results
4. GPT ritorna risposta finale

### Test 3 - Multi-iteration
```python
# User asks complex question
# GPT needs multiple rounds (tool → response → tool → response)
```

**Expected**:
1. First tool call → execute → continue
2. Second tool call → execute → continue
3. Final response

---

## FILE DA MODIFICARE

1. **agent_streaming_handler.py** - GptHandler
   - `supports_tools()` → True
   - `prepare_payload()` + tool conversion
   - `process_stream()` + tool check
   - `_handle_tool_calls()` (nuovo)
   - `_execute_tools()` (nuovo)
   - `_build_continuation_payload()` (nuovo)

---

## SFORZO STIMATO

- **STEP 1** (prepare payload): ~30 min
- **STEP 2** (tool execution): ~2 ore
- **STEP 3** (multi-call loop): ~1 ora
- **Testing**: ~1 ora

**TOTALE**: ~4.5 ore

---

## COMPATIBILITÀ

✅ **Backward compatible** - Se nessun tool definito, comportamento invariato
✅ **Format compatible** - Anthropic tools convertiti a OpenAI format
✅ **Architecture aligned** - Stesso pattern di ClaudeHandler

---

## QUANDO COMPLETARE

**OPZIONE A**: Subito (chiudere completamente il gap)
**OPZIONE B**: Dopo testing architettura attuale
**OPZIONE C**: On-demand quando serve tool use GPT

**RACCOMANDAZIONE**: Opzione B
- Test architettura attuale prima
- Poi aggiungere tool use quando stabile
