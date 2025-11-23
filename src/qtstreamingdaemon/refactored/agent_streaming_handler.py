"""
AgentStreamingHandler - Gestione streaming agent-specific.

ITERAZIONE #3: Full process_stream() implementation
    - ClaudeHandler.process_stream() - loop SSE + tool execution + multi-call
    - GptHandler.process_stream() - loop SSE semplice
    - StreamContext per passare dipendenze
    - StreamResult come output

STRUTTURA:
    AgentStreamingHandler (Wrapper/Facade)
        └── _impl: BaseAgentHandler
                ├── ClaudeHandler (con StreamingProcessor)
                └── GptHandler

INVARIANTE: Il daemon usa SEMPRE AgentStreamingHandler con firma IDENTICA.
            Il daemon chiama process_stream() e riceve StreamResult.
"""

import time
import json
import gc
import copy
import uuid
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from streaming_types import (
    StreamEvent, 
    StreamEventType,
    ContentBlockType,
    ContentBlock,
    StreamingState,
    StreamingRequest,
    StreamContext,
    StreamResult
)
from streaming_processors import StreamingProcessor, GptStreamingProcessor, ContentBlockPool


# ═══════════════════════════════════════════════════════════════════════════════
# BASE HANDLER - Contratto interno (il daemon NON vede questa classe)
# ═══════════════════════════════════════════════════════════════════════════════

class BaseAgentHandler(ABC):
    """
    Contratto interno per handler agent-specific.
    
    NOTA: Questa è una classe INTERNA. Il daemon NON la vede.
          Il daemon usa solo AgentStreamingHandler.
    """
    
    def __init__(self, event_system, logger):
        self.event_system = event_system
        self.logger = logger
    
    @abstractmethod
    def init_response(self) -> Dict:
        """Initialize response structure"""
        pass
    
    @abstractmethod
    def create_error_response(self, error_message: str) -> Dict:
        """Create error response"""
        pass
    
    @abstractmethod
    def parse_sse_event(self, data: Dict, is_multi_call_session: bool = False) -> Optional[StreamEvent]:
        """Parse SSE event"""
        pass
    
    @abstractmethod
    def update_response_from_event(self, standard_response: Dict, data: Dict) -> None:
        """Update response from SSE event"""
        pass
    
    @abstractmethod
    def append_abort_message(self, standard_response: Dict, message: str) -> None:
        """Append abort message to response"""
        pass
    
    @abstractmethod
    def finalize_response_simple(self, standard_response: Dict) -> None:
        """Simple finalization"""
        pass
    
    @abstractmethod
    def process_chunk(self, data: Dict, standard_response: Dict, first_chunk: bool) -> tuple[bool, Optional[str]]:
        """Process single SSE chunk"""
        pass
    
    @abstractmethod
    def supports_thinking(self) -> bool:
        pass
    
    @abstractmethod
    def supports_tools(self) -> bool:
        pass
    
    @abstractmethod
    def supports_streaming_processor(self) -> bool:
        pass
    
    @abstractmethod
    def get_agent_name(self) -> str:
        pass
    
    @abstractmethod
    def prepare_payload(self, payload: Dict) -> None:
        """
        Prepare payload per streaming - agent-specific.
        
        L'handler decide internamente se servono tools e li prende da self.tool_registry.
        """
        pass
    
    @abstractmethod
    def create_simulation_payload(self) -> Dict:
        """
        Create simulation/test payload - agent-specific.
        
        Returns:
            Dict: Payload minimo valido per questo agent
        """
        pass
    
    @abstractmethod
    def get_uncompressible_content_types(self) -> List[str]:
        """
        Get content types that should NEVER be compressed.
        
        Returns:
            List[str]: Content type names to preserve
        """
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # SIMULATION MODE - Agent gestisce tutto internamente
    # ═══════════════════════════════════════════════════════════════
    
    @abstractmethod
    def toggle_simulation_mode(self, enabled: bool, tool_registry=None) -> None:
        """
        Toggle simulation mode - agent gestisce TUTTO internamente.
        
        Args:
            enabled: True per attivare, False per disattivare
            tool_registry: Registry per accesso ai tool (opzionale)
        
        NOTE: L'agent sa cosa fare per la sua simulazione specifica.
              Il daemon NON sa come funziona la simulazione.
        """
        pass
    
    @abstractmethod
    def is_simulation_enabled(self) -> bool:
        """Check se simulation mode è attivo."""
        pass
    
    @abstractmethod
    def get_simulation_response(self):
        """
        Get simulation response iterator.
        
        Returns:
            Object che implementa iter_lines() per simulare streaming
        """
        pass
    
    @abstractmethod
    def configure_simulation_for_payload(self, payload: Dict) -> None:
        """
        Configure simulation based on prepared payload.
        
        Called after prepare_payload() to adjust simulation config
        based on what tools/features are in the payload.
        
        Args:
            payload: The prepared payload
        """
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # PAYLOAD FEATURE OPERATIONS - Astratti per modifiche debug
    # ═══════════════════════════════════════════════════════════════
    
    @abstractmethod
    def modify_payload_feature_data(self, modified_data: Any,
                                    context: StreamContext) -> Dict:
        """
        Modify payload feature data (es. tool result) - NO execution.
        
        ITERAZIONE #5: content_blocks NON passato - handler usa stato interno.
        
        Args:
            modified_data: The modified data (es. tool result string)
            context: Stream context
        
        Returns:
            Dict: Rebuilt continuation payload
        """
        pass
    
    @abstractmethod
    def recalculate_payload_feature_data(self, feature_name: str,
                                         modified_input: Any,
                                         context: StreamContext) -> tuple:
        """
        Recalculate payload feature data (es. re-execute tool).
        
        ITERAZIONE #5: content_blocks NON passato - handler usa stato interno.
        
        Args:
            feature_name: Name of feature to recalculate (es. tool name)
            modified_input: Modified input for recalculation
            context: Stream context
        
        Returns:
            tuple: (result, success, continuation_payload)
        """
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # SESSION STATE - Gestito internamente dall'handler (ITERAZIONE #5)
    # ═══════════════════════════════════════════════════════════════
    
    @abstractmethod
    def has_active_session(self) -> bool:
        """Check se c'è una sessione attiva con content blocks."""
        pass
    
    @abstractmethod
    def get_session_info(self) -> Dict:
        """
        Get session info per debug panel.
        
        Returns:
            Dict con info generiche (no strutture agent-specific)
        """
        pass
    
    @abstractmethod
    def reset_session(self) -> None:
        """Reset session state."""
        pass
    
    @abstractmethod
    def compress_payload(self, payload: Dict, max_context: int, 
                        max_tokens: int) -> Dict:
        """
        Compress payload per rispettare limiti token.
        
        Agent-specific: ogni agent sa come comprimere il suo formato.
        
        Args:
            payload: Payload da comprimere
            max_context: Max context window
            max_tokens: Max tokens per risposta
        
        Returns:
            Dict: Payload compresso
        """
        pass
    
    @abstractmethod
    def process_stream(self, response, request: StreamingRequest, 
                       standard_response: Dict, context: StreamContext) -> StreamResult:
        """
        Process complete stream from HTTP response.
        
        CORE METHOD - Contiene TUTTO il processing:
        - Loop SSE lines
        - Parsing eventi
        - Tool execution (Claude)
        - Multi-call continuation (Claude)
        - Error analysis
        - Finalization
        
        Args:
            response: HTTP response object (iter_lines capable)
            request: StreamingRequest con state e metadata
            standard_response: Dict da popolare con la risposta
            context: StreamContext con tutte le dipendenze
        
        Returns:
            StreamResult con esito del processing
        """
        pass
    
    def _emit_event_simple(self, event_type: str, text: str = '', block_index: Optional[int] = None):
        """Emit simple event via event_system - comune a tutti gli handler"""
        event_data = {
            'type': event_type,
            'block_index': block_index
        }
        if text:
            event_data['text'] = text
        
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [event_data]
        })


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE HANDLER - Implementazione Claude-specific
# ═══════════════════════════════════════════════════════════════════════════════

class ClaudeHandler(BaseAgentHandler):
    """Handler per Claude API"""
    
    def init_response(self) -> Dict:
        return {
            "id": None,
            "type": "message",
            "role": "assistant",
            "model": None,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0
            }
        }
    
    def create_error_response(self, error_message: str) -> Dict:
        return {
            'type': 'message',
            'role': 'assistant',
            'content': [{
                'type': 'text',
                'text': f'Error: {error_message}'
            }],
            'usage': {'input_tokens': 0, 'output_tokens': 0},
            'error': error_message
        }
    
    def parse_sse_event(self, data: Dict, is_multi_call_session: bool = False) -> Optional[StreamEvent]:
        data_type = data.get('type', '')
        
        try:
            event_type = StreamEventType(data_type)
        except ValueError:
            event_type = StreamEventType.ERROR
        
        if event_type == StreamEventType.MESSAGE_START and not is_multi_call_session:
            self._emit_event_simple('new_stream')
        
        return StreamEvent(
            type=event_type,
            data=data,
            index=data.get('index', ''),
            delta=data.get('delta', ''),
            content_block=data.get('content_block', ''),
            message=data.get('message', ''),
            error=data.get('error', '')
        )
    
    def update_response_from_event(self, standard_response: Dict, data: Dict) -> None:
        data_type = data.get('type')
        
        if data_type == 'message_start':
            message = data.get('message', {})
            
            if not standard_response.get('id'):
                standard_response['id'] = message.get('id')
            if not standard_response.get('model'):
                standard_response['model'] = message.get('model')
            
            usage = message.get('usage', {})
            if usage and not standard_response['usage'].get('input_tokens'):
                standard_response['usage']['input_tokens'] = usage.get('input_tokens', 0)
                        
        elif data_type == 'message_delta':
            delta = data.get('delta', {})
            
            if delta.get('stop_reason'):
                standard_response['stop_reason'] = delta.get('stop_reason')
            
            usage = data.get('usage', {})
            if usage and usage.get('output_tokens'):
                current_output = standard_response['usage'].get('output_tokens', 0)
                standard_response['usage']['output_tokens'] = current_output + usage.get('output_tokens', 0)
    
    def append_abort_message(self, standard_response: Dict, message: str = "\n\n[⛔ Stream aborted by user]") -> None:
        if standard_response.get('content'):
            for block in standard_response['content']:
                if block and block.get('type') == 'text':
                    block['text'] = (block.get('text', '') + message)
                    break
    
    def finalize_response_simple(self, standard_response: Dict) -> None:
        # Claude usa _finalize_claude_response() nel daemon (troppo complesso)
        # Questo metodo è no-op per Claude
        pass
    
    def process_chunk(self, data: Dict, standard_response: Dict, first_chunk: bool) -> tuple[bool, Optional[str]]:
        # Claude usa parse_sse_event + StreamingProcessor nel daemon
        # Questo metodo non è usato per Claude, ma deve esistere per il contratto
        return first_chunk, None
    
    def supports_thinking(self) -> bool:
        return True
    
    def supports_tools(self) -> bool:
        return True
    
    def supports_streaming_processor(self) -> bool:
        return True
    
    def get_agent_name(self) -> str:
        return "Claude"
    
    def prepare_payload(self, payload: Dict) -> None:
        """
        Prepare Claude payload - check thinking + add tools.
        
        REFACTORING: L'handler decide internamente se servono tools.
        Accede a ToolRegistry via EVENT_SYSTEM (pattern request/wait/response).
        """
        thinking_enabled = False
        
        # Check thinking config
        if 'thinking' in payload:
            thinking_config = payload['thinking']
            if isinstance(thinking_config, dict):
                thinking_enabled = thinking_config.get('budget_tokens', 0) > 0
            elif isinstance(thinking_config, bool):
                thinking_enabled = thinking_config
        
        # Add tools if thinking enabled and interleaved mode
        if thinking_enabled:
            headers = payload.get('headers', {})
            interleaved_header = headers.get("anthropic-beta", "")
            if "interleaved-thinking" in interleaved_header:
                # ✅ Request tools via event_system
                tool_definitions = self._request_tool_definitions()
                tools_system_prompt = self._request_system_prompt()
                
                if "tools" not in payload:
                    payload["tools"] = []
                
                # Add each tool definition if not already present
                for tool_def in tool_definitions:
                    tool_name = tool_def['name']
                    if not any(t.get("name") == tool_name for t in payload["tools"]):
                        payload["tools"].append(tool_def)
                
                # Set system prompt for tools
                if tools_system_prompt:
                    payload['system'] = tools_system_prompt
        
        # Save thinking state internamente
        self._thinking_enabled = thinking_enabled
    
    def create_simulation_payload(self) -> Dict:
        """
        Create Claude simulation payload.
        
        SPOSTATO DA: QtStreamingDaemon._on_toggle_simulation_mode
        """
        return {
            'headers': {
                'anthropic-version': '2023-06-01',
                'anthropic-beta': 'interleaved-thinking-20241217',
                'content-type': 'application/json'
            },
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 4096,
            'thinking': {
                'type': 'enabled',
                'budget_tokens': 10000
            },
            'messages': [
                {
                    'role': 'user',
                    'content': 'TEST'
                }
            ]
        }
    
    def get_uncompressible_content_types(self) -> List[str]:
        """
        Claude: thinking blocks have immutable signatures - NEVER compress.
        """
        return ["thinking", "redacted_thinking"]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMULATION MODE - Claude-specific (ITERAZIONE #5)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def __init__(self, event_system, logger):
        super().__init__(event_system, logger)
        # Simulation state - gestito internamente
        self._simulation_enabled = False
        self._simulation_config = None
        self._fake_response = None
        
        # ═══ THINKING STATE ═══
        # Salvato in prepare_payload per uso interno
        self._thinking_enabled = False
        
        # ═══ TOOL REGISTRY ACCESS VIA EVENTS ═══
        # Response data
        self._tool_definitions_response = None
        self._system_prompt_response = None
        # Flags per sync requests
        self._tool_definitions_received = False
        self._system_prompt_received = False
        
        # Subscribe to responses
        self.event_system.subscribe('enabled_tools_response', self._on_enabled_tools_response)
        self.event_system.subscribe('tool_system_prompt_response', self._on_tool_system_prompt_response)
        
        # ═══ SESSION STATE - ITERAZIONE #5 ═══
        # Multi-call tracking - gestito internamente
        self._is_multi_call_session = False
        self._current_content_blocks = None  # List[ContentBlock]
        self._accumulated_content_blocks = []
        self._accumulated_tokens = 0
        self._call_count = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TOOL REGISTRY EVENT HANDLERS - Comunicazione via event_system
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _on_enabled_tools_response(self, data: Dict):
        """
        Handler per risposta tool definitions da ToolRegistry.
        
        Args:
            data: {'tool_definitions': [...]}
        """
        self._tool_definitions_response = data.get('tool_definitions', [])
        self._tool_definitions_received = True
        self.logger.debug(f"Received {len(self._tool_definitions_response)} tool definitions")
    
    def _on_tool_system_prompt_response(self, data: Dict):
        """
        Handler per risposta system prompt da ToolRegistry.
        
        Args:
            data: {'system_prompt': '...'}
        """
        self._system_prompt_response = data.get('system_prompt', '')
        self._system_prompt_received = True
        self.logger.debug(f"Received system prompt ({len(self._system_prompt_response)} chars)")
    
    def _request_tool_definitions(self) -> List[Dict]:
        """
        Request tool definitions da ToolRegistry via event (SYNC).
        
        Returns:
            Lista di tool definitions
        """
        import time
        
        # Reset flag e response
        self._tool_definitions_received = False
        self._tool_definitions_response = None
        
        # Emit request
        self.event_system.emit_event('get_enabled_tools_request', {})
        
        # Wait for response (max 2 seconds)
        max_wait = 2.0
        elapsed = 0.0
        sleep_interval = 0.01
        
        while not self._tool_definitions_received and elapsed < max_wait:
            time.sleep(sleep_interval)
            # Keep GUI responsive
            self.event_system.emit_event('gui_update_request', {})
            elapsed += sleep_interval
        
        if not self._tool_definitions_received:
            self.logger.warning("Timeout waiting for tool definitions")
            return []
        
        return self._tool_definitions_response or []
    
    def _request_system_prompt(self) -> str:
        """
        Request system prompt da ToolRegistry via event (SYNC).
        
        Returns:
            System prompt string
        """
        import time
        
        # Reset flag e response
        self._system_prompt_received = False
        self._system_prompt_response = None
        
        # Emit request
        self.event_system.emit_event('get_tool_system_prompt_request', {})
        
        # Wait for response (max 2 seconds)
        max_wait = 2.0
        elapsed = 0.0
        sleep_interval = 0.01
        
        while not self._system_prompt_received and elapsed < max_wait:
            time.sleep(sleep_interval)
            # Keep GUI responsive
            self.event_system.emit_event('gui_update_request', {})
            elapsed += sleep_interval
        
        if not self._system_prompt_received:
            self.logger.warning("Timeout waiting for system prompt")
            return ""
        
        return self._system_prompt_response or ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMULATION MODE - Claude-specific (ITERAZIONE #5)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def toggle_simulation_mode(self, enabled: bool, tool_registry=None) -> None:
        """
        Toggle simulation mode - Claude gestisce tutto internamente.
        """
        self._simulation_enabled = enabled
        self.logger.info(f"Claude simulation mode: {'ENABLED' if enabled else 'DISABLED'}")
        
        if enabled:
            # Config default per Claude: thinking + text
            self._simulation_config = {
                'include_text': True,
                'include_tool': False,
                'tool_name': None,
                'tool_input': None,
                'timing': 'fast'
            }
            # FakeStreamingResponse verrà creato in configure_simulation_for_payload
        else:
            self._simulation_config = None
            self._fake_response = None
    
    def is_simulation_enabled(self) -> bool:
        return self._simulation_enabled
    
    def get_simulation_response(self):
        """Get fake response iterator for simulation."""
        if self._fake_response:
            self._fake_response._init_turn()
        return self._fake_response
    
    def configure_simulation_for_payload(self, payload: Dict) -> None:
        """
        Configure simulation based on prepared payload.
        
        Se payload ha tools, configura simulation per includere tool call.
        """
        if not self._simulation_enabled or not self._simulation_config:
            return
        
        tools = payload.get('tools', [])
        if tools:
            first_tool_name = tools[0].get('name')
            if first_tool_name:
                self._simulation_config['include_tool'] = True
                self._simulation_config['tool_name'] = first_tool_name
                self.logger.info(f"Simulation configured with tool: {first_tool_name}")
        
        # Create fake response con config aggiornata
        self._fake_response = ClaudeFakeStreamingResponse(self._simulation_config)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAYLOAD FEATURE OPERATIONS - Claude-specific (ITERAZIONE #5)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def modify_payload_feature_data(self, modified_data: Any,
                                    context: StreamContext) -> Dict:
        """
        Modify tool result - rebuild continuation payload.
        
        ITERAZIONE #5: Usa stato interno (_current_content_blocks).
        """
        if not self._current_content_blocks:
            self.logger.error("No current content blocks - cannot modify")
            return {}
        
        # Find tool call
        tool_call = None
        for block in self._current_content_blocks:
            if block.type == ContentBlockType.TOOL_USE:
                tool_call = block
                break
        
        if not tool_call:
            self.logger.error("No tool call found in content blocks")
            return {}
        
        # Rebuild continuation
        return self._build_continue_payload_with_results(
            context.original_payload, self._current_content_blocks,
            tool_call, modified_data, context, replace_last=False
        )
    
    def recalculate_payload_feature_data(self, feature_name: str,
                                         modified_input: Any,
                                         context: StreamContext) -> tuple:
        """
        Re-execute tool and rebuild continuation.
        
        ITERAZIONE #5: Usa stato interno (_current_content_blocks).
        """
        if not self._current_content_blocks:
            self.logger.error("No current content blocks - cannot recalculate")
            return None, False, {}
        
        # Find tool call
        tool_call = None
        for block in self._current_content_blocks:
            if block.type == ContentBlockType.TOOL_USE and block.tool_name == feature_name:
                tool_call = block
                break
        
        if not tool_call:
            self.logger.error(f"Tool call {feature_name} not found")
            return None, False, {}
        
        # Update tool input
        tool_call.tool_input = modified_input
        
        # Execute and rebuild
        return self._execute_tool_and_build_continuation(
            tool_call, self._current_content_blocks, context, replace_last=True
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION STATE METHODS - ITERAZIONE #5
    # ═══════════════════════════════════════════════════════════════════════════
    
    def has_active_session(self) -> bool:
        """Check se c'è una sessione attiva con content blocks."""
        return self._current_content_blocks is not None and len(self._current_content_blocks) > 0
    
    def get_session_info(self) -> Dict:
        """Get session info per debug panel."""
        return {
            'is_multi_call': self._is_multi_call_session,
            'call_count': self._call_count,
            'accumulated_tokens': self._accumulated_tokens,
            'content_blocks_count': len(self._current_content_blocks) if self._current_content_blocks else 0,
            'has_tool_use': any(b.type == ContentBlockType.TOOL_USE for b in (self._current_content_blocks or []))
        }
    
    def reset_session(self) -> None:
        """Reset session state."""
        self._is_multi_call_session = False
        self._current_content_blocks = None
        self._accumulated_content_blocks = []
        self._accumulated_tokens = 0
        self._call_count = 0
        self.logger.debug("Claude session state reset")
    
    def set_current_content_blocks(self, blocks) -> None:
        """Set current content blocks - chiamato dopo process_stream."""
        self._current_content_blocks = blocks
    
    def compress_payload(self, payload: Dict, max_context: int,
                        max_tokens: int) -> Dict:
        """
        Compress Claude payload.
        
        SPOSTATO DA: QtStreamingDaemon._compress_payload_advanced
        TODO: Implementare logica completa
        """
        # Per ora ritorna payload non compresso
        # La logica completa verrà spostata dal daemon
        return payload
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROCESS_STREAM - Main processing method (ITERAZIONE #3)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def process_stream(self, response, request: StreamingRequest, 
                       standard_response: Dict, context: StreamContext) -> StreamResult:
        """
        Process Claude stream con tool execution e multi-call.
        
        COPIATO DA: QtStreamingDaemon._process_claude_stream_with_error_handling
        """
        processor = StreamingProcessor(self.event_system, self.logger)
        chunks_processed = 0
        gui_update_counter = 0
        
        bytes_read = 0
        chunks_received = 0
        stream_started_time = time.time()
        last_successful_chunk_time = time.time()
        has_received_substantial_data = False
        
        stream_outputs_batch = []
        
        try:
            for line in response.iter_lines(decode_unicode=True):
                current_time = time.time()

                # ═══ CHECK PAUSE ═══
                if context.is_paused():
                    context.pause_event.wait()  # Block until resumed
                
                # Immediate abort check
                if chunks_processed % context.abort_check_interval == 0:
                    if context.is_aborted(request.request_id):
                        self.logger.info(f"Stream {request.request_id} aborted mid-processing")
                        
                        # ═══ ADD ABORT NOTICE ═══
                        self.append_abort_message(standard_response)
                        
                        # Finalize e return
                        final_response = self._finalize_response(standard_response, processor, context)
                        request.state = StreamingState.CANCELLED
                        return StreamResult(
                            success=True,
                            partial=True,
                            aborted=True,
                            response=final_response,
                            chunks_received=chunks_received,
                            bytes_read=bytes_read
                        )
                
                # Cancellation check
                if request.state == StreamingState.CANCELLED:
                    self.logger.info("Claude stream cancelled")
                    break
                
                if not line or not line.strip():
                    continue
                
                bytes_read += len(line.encode('utf-8'))
                chunks_received += 1
                last_successful_chunk_time = current_time
                
                if bytes_read > 1000:
                    has_received_substantial_data = True
                
                if current_time - last_successful_chunk_time > 60:
                    self.logger.warning("No data for 60s - stale connection")
                    raise ConnectionError("Stale connection detected")
                
                if line.startswith('data: '):
                    data_str = line[6:]
                    
                    if data_str.strip() == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        event = self.parse_sse_event(data, context.is_multi_call_session)
                        stream_output = processor.process_event(event)
                        if stream_output:
                            stream_outputs_batch.append(stream_output)
                            self.logger.info(f"Stream_output generated: {stream_output}. New outputs batch size: {len(stream_outputs_batch)}. Target flush size: {context.chunk_batch_size} ")

                            if len(stream_outputs_batch) >= context.chunk_batch_size:
                                # Aggiorna GUI batch
                                context.emit_stream_output(stream_outputs_batch)
                                stream_outputs_batch.clear()
                                
                        self.update_response_from_event(standard_response, data)
                        
                        chunks_processed += 1
                        
                        gui_update_counter += 1
                        if gui_update_counter >= context.gui_update_interval:
                            context.emit_gui_update()
                            gui_update_counter = 0
                        
                        if chunks_processed % context.memory_cleanup_interval == 0:
                            gc.collect()
                        
                        if chunks_processed % context.metrics_update_interval == 0:
                            context.emit_metrics_update()
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"JSON decode error: {e}")
                        continue
            
            # Ultimo batch GUI
            if stream_outputs_batch:
                context.emit_stream_output(stream_outputs_batch)
                
            # ═══ FINALIZE ═══
            final_response = self._finalize_response(standard_response, processor, context)
            
            return StreamResult(
                success=True,
                partial=False,
                response=final_response,
                chunks_received=chunks_received,
                bytes_read=bytes_read
            )
            
        except Exception as stream_error:
            stream_duration = time.time() - stream_started_time
            error_context = {
                'bytes_read': bytes_read,
                'chunks_received': chunks_received,
                'chunks_processed': chunks_processed,
                'stream_duration': stream_duration,
                'has_substantial_data': has_received_substantial_data,
                'error_type': type(stream_error).__name__,
                'error_details': str(stream_error)
            }
            
            self.logger.info(f"Stream error context: {error_context}")
            
            should_retry = self._analyze_chunk_error_severity(error_context, stream_error)
            
            if should_retry:
                self.logger.warning("Error analysis: real connection error - will retry")
                return StreamResult(
                    success=False,
                    partial=True,
                    should_retry=True,
                    error=str(stream_error)
                )
            else:
                self.logger.info("Error analysis: normal end-of-stream - processing available data")
                
                if chunks_processed > 0:
                    final_response = self._finalize_response(standard_response, processor, context)
                    
                    # ═══ ADD ERROR NOTICE ═══
                    self.append_abort_message(standard_response, "\n\n[Stream ended unexpectedly but response is complete]")
                    
                    return StreamResult(
                        success=True,
                        partial=True,
                        should_retry=False,
                        response=final_response,
                        chunks_received=chunks_received,
                        bytes_read=bytes_read
                    )
                else:
                    return StreamResult(
                        success=False,
                        partial=True,
                        should_retry=True,
                        error=f"No useful data: {str(stream_error)}"
                    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FINALIZATION & TOOL EXECUTION (Copiati da daemon)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _finalize_response(self, standard_response: Dict, processor: StreamingProcessor,
                          context: StreamContext) -> Dict:
        """
        Finalize response con tool execution e multi-call logic.
        
        COPIATO DA: QtStreamingDaemon._finalize_claude_response
        """
        content_blocks = processor.get_content_blocks()
        self._accumulate_content_blocks(content_blocks, context)
        
        # ═══ CLEANUP: Return blocks to pool ═══
        processor.cleanup()
            
        tool_calls = [b for b in content_blocks if b.type == ContentBlockType.TOOL_USE]
        
        # No tools - finalize normally
        if not tool_calls:
            self._finalize_response_metadata(standard_response, context)
            self._reset_multi_call_session(context)
            return standard_response
        
        # ═══ ALWAYS ONE TOOL PER TURN ═══
        if len(tool_calls) != 1:
            self.logger.error(f"Expected 1 tool call, got {len(tool_calls)} - API contract violation!")
            # Fallback: use first
        
        tool_call = tool_calls[0]
        
        # ═══ CHECK STOP CONDITIONS (solo per think tool) ═══
        if tool_call.tool_name == 'think':
            stop_reason = self._should_stop_thinking(context)
            
            if stop_reason:
                self.logger.warning(f"Stopping think loop: {stop_reason}")
                termination_note = self._create_termination_note(stop_reason, context)
                self._finalize_response_metadata(standard_response, context)
                self._reset_multi_call_session(context)
                return standard_response
        
        # ═══ INITIALIZE MULTI-CALL SESSION ═══
        if not context.is_multi_call_session:
            context.is_multi_call_session = True
            # Clear messages in original_payload for continuation
            if context.original_payload:
                context.original_payload['messages'] = []

        # ═══ EMIT TOOL INPUT EVENT ═══
        context.emit_stream_output([{
            'type': 'tool_input',
            'block_index': tool_call.index,
            'tool_name': tool_call.tool_name,
            'tool_input': tool_call.tool_input
        }])
        
        self.logger.info(f"Generato evento stream_output_batch 'tool_input' per tool {tool_call.tool_name} con input: [{tool_call.tool_input}]")
       
        # ═══ EXECUTE TOOL AND BUILD CONTINUE PAYLOAD ═══
        tool_result, execution_success, continue_payload = self._execute_tool_and_build_continuation(
            tool_call,
            content_blocks,
            context
        )
        
        # ═══ UPDATE TRACKING ═══
        context.call_count += 1
        usage = standard_response.get('usage', {})
        context.accumulated_tokens += usage.get('output_tokens', 0)
        
        # ═══ STEP CHECK ═══
        if context.step_by_step_mode:
            # ═══ EMIT DEBUG INFO ═══
            context.emit_interleaved_info(
                message="Ready to perform next streaming request",
                call_number=context.call_count,
                request_type="continuation",
                tool_call_block={
                    'type': tool_call.type.value,
                    'index': tool_call.index,
                    'tool_name': tool_call.tool_name,
                    'tool_id': tool_call.tool_id,
                    'tool_input': tool_call.tool_input
                },
                tool_result=tool_result,
                tool_execution_success=execution_success,
                continuation_payload=continue_payload,
                messages_count=len(continue_payload.get('messages', [])),
                payload_size_estimate=len(json.dumps(continue_payload))
            )
        
            self.logger.info(f"Step-by-step mode: Pausing before continuation #{context.call_count}")
            return standard_response

        # ═══ RECURSIVE CALL via context.make_request ═══
        continue_request = StreamingRequest(
            request_id=str(uuid.uuid4()),
            payload=continue_payload,
            progress_callback=None,
            extended_mode=True  # Manteniamo thinking mode attivo
        )
        
        result = context.make_request(continue_request)
        
        # Merge result into standard_response se success
        if result.get('success') and result.get('response'):
            # Il result contiene già la risposta finalizzata
            return result['response']
        
        return standard_response
    
    def _execute_tool_and_build_continuation(self, tool_call: ContentBlock, 
                                              content_blocks: List[ContentBlock],
                                              context: StreamContext,
                                              replace_last: bool = False) -> tuple:
        """
        Execute tool AND build continuation.
        
        COPIATO DA: QtStreamingDaemon._execute_tool_and_build_continuation
        """
        tool_name = tool_call.tool_name
        tool_id = tool_call.tool_id
        
        self.logger.info(f"Executing tool: {tool_name} (id: {tool_id})")
        
        # ═══ EXECUTE TOOL ═══
        try:
            tool_result = context.tool_registry.execute_tool(tool_call.tool_name, tool_call.tool_input)
            execution_success = True
        
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            tool_result = f"""
╔═══════════════════════════════════════════════════════════╗
║ ❌ TOOL EXECUTION ERROR                                   ║
╚═══════════════════════════════════════════════════════════╝

Tool: {tool_call.tool_name}
Error: {str(e)}

╚═══════════════════════════════════════════════════════════╝
"""
            execution_success = False

        # Accumulate result (differenziato)
        self._accumulate_tool_result(
            tool_call.tool_name,
            tool_call.tool_id,
            tool_result,
            execution_success,
            context
        )
        
        # ═══ EMIT TOOL RESULT EVENT ═══
        context.emit_stream_output([{
            'type': 'tool_result',
            'block_index': tool_call.index,
            'tool_name': tool_call.tool_name,
            'tool_result': tool_result
        }])
        
        # ═══ BUILD CONTINUATION PAYLOAD ═══
        continue_payload = self._build_continue_payload_with_results(
            context.original_payload,
            content_blocks,
            tool_call,
            tool_result,
            context,
            replace_last=replace_last 
        )
        
        return tool_result, execution_success, continue_payload
    
    def _accumulate_content_blocks(self, content_blocks: List[ContentBlock], context: StreamContext):
        """
        Accumulate content from this call - PRESERVA SIGNATURE.
        
        COPIATO DA: QtStreamingDaemon._accumulate_content_blocks
        """
        for block in content_blocks:
            accumulated_block = {
                "type": block.type.value,
                "content": block.content,
                "call_number": context.call_count,
                "index": block.index
            }
            
            # ↓ CRITICAL: Preserva signature per thinking blocks
            if block.type in [ContentBlockType.THINKING, ContentBlockType.REDACTED_THINKING]:
                if block.signature:
                    accumulated_block["signature"] = block.signature
                    self.logger.debug(f"Accumulated thinking block {block.index} with signature (call {context.call_count})")
                else:
                    self.logger.error(f"CRITICAL: Thinking block {block.index} missing signature in call {context.call_count}")
                
                # For redacted thinking, also preserve encrypted data
                if block.type == ContentBlockType.REDACTED_THINKING:
                    if block.encrypted_data:
                        accumulated_block["encrypted_data"] = block.encrypted_data
                        self.logger.debug(f"Accumulated redacted thinking block {block.index} with encrypted data")
                    else:
                        self.logger.warning(f"Redacted thinking block {block.index} missing encrypted data")
            
            if block.type == ContentBlockType.TOOL_USE:
                accumulated_block["tool_name"] = block.tool_name
                accumulated_block["tool_id"] = block.tool_id
                accumulated_block["tool_input"] = block.tool_input
            
            context.accumulated_content_blocks.append(accumulated_block)

    def _accumulate_tool_result(self, tool_name: str, tool_id: str, 
                                result: str, success: bool, context: StreamContext):
        """
        Accumulate tool result con strategia differenziata.
        
        COPIATO DA: QtStreamingDaemon._accumulate_tool_result
        """
        # ═══ THINK TOOL: Internal Feedback Only ═══
        if tool_name == "think":
            # Save separately per potential debugging
            if not hasattr(self, '_think_results_internal'):
                self._think_results_internal = []
            
            self._think_results_internal.append({
                "call_number": context.call_count,
                "tool_id": tool_id,
                "result": result,
                "success": success,
                "timestamp": time.time()
            })
            
            self.logger.debug(f"Think result saved internally (call {context.call_count})")
            return  # Don't add to main accumulated_content_blocks
        
        # ═══ OPERATIONAL TOOLS: User-Facing Content ═══
        result_block = {
            "type": "tool_result",
            "content": result,
            "tool_use_id": tool_id,
            "tool_name": tool_name,
            "call_number": context.call_count,
            "success": success
        }
        
        context.accumulated_content_blocks.append(result_block)
        self.logger.debug(f"Tool result accumulated: {tool_name} (call {context.call_count})")

    def _validate_thinking_signatures_before_send(self, content_blocks: List[ContentBlock]) -> None:
        """
        Valida che TUTTI i thinking blocks abbiano signature PRIMA di costruire il payload.
        
        CRITICAL: Le API Anthropic RICHIEDONO signature per thinking blocks.
        Meglio fallire qui con errore chiaro che ricevere 400 da API.
        """
        for block in content_blocks:
            if block.type in [ContentBlockType.THINKING, ContentBlockType.REDACTED_THINKING]:
                if not block.signature:
                    error_msg = (
                        f"CRITICAL: Thinking block [{block.index}] type={block.type.value} "
                        f"missing REQUIRED signature. Cannot send to API."
                    )
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Additional validation for redacted thinking
                if block.type == ContentBlockType.REDACTED_THINKING:
                    if not block.encrypted_data:
                        error_msg = (
                            f"CRITICAL: Redacted thinking block [{block.index}] "
                            f"missing encrypted data. Cannot send to API."
                        )
                        self.logger.error(error_msg)
                        raise ValueError(error_msg)
        
        self.logger.debug(f"Signature validation passed for {len(content_blocks)} blocks")

    def _build_continue_payload_with_results(self,
                                             original_payload: Dict,
                                             content_blocks: List[ContentBlock],
                                             tool_call: ContentBlock,
                                             tool_result: str,
                                             context: StreamContext,
                                             replace_last: bool = False) -> Dict:
        """
        Build continuation payload con TUTTA la storia multi-turn.
        
        COPIATO DA: QtStreamingDaemon._build_continue_payload_with_results
        """
        # ═══ VALIDATE SIGNATURES ═══
        # self._validate_thinking_signatures_before_send(content_blocks)
        
        continue_payload = copy.deepcopy(original_payload)
        
        # ═══ RICOSTRUISCI STORIA DA ACCUMULATED_BLOCKS ═══
        turns_history = {}
        
        for accumulated_block in context.accumulated_content_blocks:
            call_num = accumulated_block.get('call_number', 0)
            
            if call_num not in turns_history:
                turns_history[call_num] = {
                    'blocks': [],
                    'tool_result': None
                }
            
            if accumulated_block['type'] == 'tool_result':
                turns_history[call_num]['tool_result'] = accumulated_block
            else:
                turns_history[call_num]['blocks'].append(accumulated_block)
        
        # ═══ RIMUOVI ULTIMO TURNO (evita duplicazione o sostituisci) ═══
        sorted_calls = sorted(turns_history.keys())
        if replace_last and sorted_calls:
            last_call = sorted_calls.pop()
            del turns_history[last_call]
            context.accumulated_content_blocks = [
                b for b in context.accumulated_content_blocks 
                if b.get('call_number', 0) != last_call
            ]
            self.logger.info(f"Replacing last turn (call #{last_call})")

        last_call_num = sorted_calls[-1] if sorted_calls else None
        
        # ═══ AGGIUNGI TURNI PRECEDENTI ═══
        for call_num in sorted_calls:
            turn = turns_history[call_num]
            assistant_content = []
            
            for block_dict in turn['blocks']:
                block_type = block_dict['type']
                
                if block_type == 'thinking':
                    block_content = {
                        "type": "thinking",
                        "thinking": block_dict['content']
                    }
                    if 'signature' in block_dict:
                        block_content["signature"] = block_dict['signature']
                    assistant_content.append(block_content)
                
                elif block_type == 'redacted_thinking':
                    block_content = {"type": "redacted_thinking"}
                    if 'encrypted_data' in block_dict:
                        block_content["data"] = block_dict['encrypted_data']
                    if 'signature' in block_dict:
                        block_content["signature"] = block_dict['signature']
                    assistant_content.append(block_content)
                
                elif block_type == 'text':
                    assistant_content.append({
                        "type": "text",
                        "text": block_dict['content']
                    })
                
                elif block_type == 'tool_use':
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block_dict['tool_id'],
                        "name": block_dict['tool_name'],
                        "input": block_dict['tool_input']
                    })
            
            # Add assistant message
            continue_payload["messages"].append({
                "role": "assistant",
                "content": assistant_content
            })
            
            # Add tool result message
            if turn['tool_result']:
                result_content = turn['tool_result']['content']
                
                continue_payload["messages"].append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": turn['tool_result']['tool_use_id'],
                        "content": result_content
                    }]
                })
    
        return continue_payload

    def _finalize_response_metadata(self, standard_response: Dict, context: StreamContext):
        """
        Assembly intelligente con semantic markup.
        
        COPIATO DA: QtStreamingDaemon._finalize_response_metadata
        """
        # ═══ STEP 1: GROUP BY CALL NUMBER ═══
        calls = {}
        for block in context.accumulated_content_blocks:
            call_num = block.get('call_number', 0)
            if call_num not in calls:
                calls[call_num] = []
            calls[call_num].append(block)
        
        # ═══ STEP 2: BUILD FINAL CONTENT ARRAY ═══
        final_response = []
        final_content = ""
        
        # Process each call sequentially
        for call_num in sorted(calls.keys()):
            call_blocks = calls[call_num]
            
            type_order = {
                'thinking': 0,
                'redacted_thinking': 0,
                'text': 1,
                'tool_use': 2,
                'tool_result': 3
            }
            call_blocks_sorted = sorted(
                call_blocks,
                key=lambda b: type_order.get(b['type'], 99)
            )
            
            for block in call_blocks_sorted:
                block_type = block['type']
                
                if block_type == 'thinking':
                    thinking_text = block['content'] or ''
                    final_content += f"[THINKING]\n{thinking_text}\n[/THINKING]\n\n"
                
                elif block_type == 'redacted_thinking':
                    final_content += "[REDACTED_THINKING]\n(Encrypted reasoning for safety)\n[/REDACTED_THINKING]\n\n"
                
                elif block_type == 'text':
                    final_content += block['content'] or '' 
                    final_content += "\n\n"
                    
                elif block_type == 'tool_use':
                    tool_name = block.get('tool_name', 'unknown')
                    if tool_name != 'think':
                        tool_input_str = json.dumps(block.get('tool_input', {}), indent=2)
                        final_content += f"[TOOL_CALL: {tool_name}]\n{tool_input_str}\n[/TOOL_CALL]\n\n"
                
                elif block_type == 'tool_result':
                    tool_name = block.get('tool_name', 'unknown')
                    result_content = "Tool eseguito con successo"
                    final_content += f"[TOOL_RESULT: {tool_name}]\n{result_content}\n[/TOOL_RESULT]\n\n"
            
            if call_num < max(calls.keys()) if calls else 0:
                separator = f"\n{'═' * 60}\n[Reasoning cycle {call_num + 1} → {call_num + 2}]\n{'═' * 60}\n\n"
                final_content += separator
        
        if final_content:
            integrated_text = ''.join(final_content).strip()
            text_block = {
                "type": "text",
                "text": integrated_text
            }
            final_response.insert(0, text_block)
        
        standard_response['content'] = final_response
        
        if 'type' not in standard_response:
            standard_response['type'] = 'message'
        if 'role' not in standard_response:
            standard_response['role'] = 'assistant'
        
        if 'usage' not in standard_response:
            standard_response['usage'] = {}
            
        standard_response['usage']['output_tokens'] = context.accumulated_tokens
        
        self.logger.info(
            f"Final response assembled: {len(final_content)} chars, "
            f"{len(calls)} reasoning cycles, {context.accumulated_tokens} tokens"
        )

    def _reset_multi_call_session(self, context: StreamContext):
        """Reset multi-call session"""
        context.is_multi_call_session = False
        context.accumulated_content_blocks = []
        context.accumulated_tokens = 0
        context.call_count = 0
    
    def _should_stop_thinking(self, context: StreamContext) -> Optional[str]:
        """
        Determina se fermare multi-call think loop.
        
        COPIATO DA: QtStreamingDaemon._should_stop_thinking
        """
        # Check 1: Max calls reached
        if context.call_count >= context.max_extended_calls:
            return f"Maximum extended cycles reached ({context.max_extended_calls})"
        
        # Check 2: Total token budget exceeded
        if context.accumulated_tokens >= context.total_extended_budget:
            return f"Total extended token budget exceeded ({context.accumulated_tokens}/{context.total_extended_budget})"
        
        # Check 3: Diminishing returns (se thinking diventa ripetitivo)
        if context.call_count >= 3:
            thinking_blocks = [b for b in context.accumulated_content_blocks 
                             if b.get('type') == 'thinking']
            if len(thinking_blocks) >= 2:
                last_thought = thinking_blocks[-1].get('content', '')
                prev_thought = thinking_blocks[-2].get('content', '')
                
                similarity = self._calculate_similarity(last_thought, prev_thought)
                if similarity > 0.7:
                    return f"Thinking appears repetitive (similarity: {similarity:.0%})"
        
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple word-overlap similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_termination_note(self, reason: str, context: StreamContext) -> str:
        """Crea nota informativa per terminazione"""
        return f"""

╔═══════════════════════════════════════════════════════════╗
║ ⚠️  THINKING PROCESS TERMINATED                          ║
╚═══════════════════════════════════════════════════════════╝

Reason: {reason}

Your reasoning across {context.call_count} thinking cycle(s) has been 
recorded and integrated. Proceeding with response formulation based 
on accumulated analysis.

Total thinking tokens used: {context.accumulated_tokens}
"""
    
    def _analyze_chunk_error_severity(self, error_context: Dict, error: Exception) -> bool:
        """
        Analizza se errore è reale o end-of-stream normale.
        
        COPIATO DA: QtStreamingDaemon._analyze_chunk_error_severity
        """
        # === INDICATORI END-OF-STREAM NORMALE ===
        normal_indicators = 0
        
        if error_context['bytes_read'] > 1000 and error_context['chunks_processed'] > 0:
            self.logger.debug("Substantial data - likely normal end")
            normal_indicators += 1
        
        if error_context['stream_duration'] > 5.0:
            self.logger.debug("Reasonable duration - likely normal completion")
            normal_indicators += 1
        
        if error_context['chunks_received'] > 10:
            self.logger.debug("Multiple chunks - likely normal end")
            normal_indicators += 1
        
        if error_context['has_substantial_data']:
            self.logger.debug("Has substantial data - likely complete")
            normal_indicators += 1
        
        # === INDICATORI ERRORE REALE ===
        error_indicators = 0
        
        if error_context['bytes_read'] < 100:
            self.logger.debug("Very little data - likely error")
            error_indicators += 2
        
        if error_context['stream_duration'] < 1.0:
            self.logger.debug("Very short stream - likely error")
            error_indicators += 1
        
        if error_context['chunks_received'] < 3:
            self.logger.debug("Few chunks - likely early error")
            error_indicators += 1
        
        error_keywords = ['connection', 'reset', 'broken', 'refused', 'timeout']
        if any(kw in str(error).lower() for kw in error_keywords):
            self.logger.debug("Error keywords found - connection issue")
            error_indicators += 2
        
        # === DECISIONE ===
        self.logger.info(f"Error analysis: normal={normal_indicators}, error={error_indicators}")
        
        if normal_indicators >= 3:
            return False  # Non retry
        
        if error_indicators >= 3:
            return True  # Retry
        
        if error_context['chunks_processed'] > 0:
            self.logger.info("Ambiguous but have data - treating as normal")
            return False
        else:
            self.logger.info("Ambiguous with no data - treating as error")
            return True


# ═══════════════════════════════════════════════════════════════════════════════
# GPT HANDLER - Implementazione GPT/OpenAI-specific
# ═══════════════════════════════════════════════════════════════════════════════

class GptHandler(BaseAgentHandler):
    """Handler per GPT/OpenAI API"""
    
    def init_response(self) -> Dict:
        return {
            "id": None,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": None,
            "system_fingerprint": None,  # FIXED: aggiunto system_fingerprint
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': ''
                },
                'finish_reason': None
            }],
            'usage': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        }
    
    def create_error_response(self, error_message: str) -> Dict:
        return {
            'object': 'chat.completion',
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': f'Error: {error_message}'
                },
                'finish_reason': 'stop'
            }],
            'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            'error': error_message
        }
    
    def parse_sse_event(self, data: Dict, is_multi_call_session: bool = False) -> Optional[StreamEvent]:
        # GPT usa processing inline, non StreamEvent
        return None
    
    def update_response_from_event(self, standard_response: Dict, data: Dict) -> None:
        # GPT: update è inline in process_chunk
        pass
    
    def append_abort_message(self, standard_response: Dict, message: str = "\n\n[⛔ Stream aborted by user]") -> None:
        if standard_response.get('choices'):
            standard_response['choices'][0]['message']['content'] += message
    
    def finalize_response_simple(self, standard_response: Dict) -> None:
        if not standard_response['choices']:
            standard_response['choices'] = [{
                'index': 0,
                'message': {'role': 'assistant', 'content': ''},
                'finish_reason': 'stop'
            }]
        elif standard_response['choices'][0].get('finish_reason') is None:
            standard_response['choices'][0]['finish_reason'] = 'stop'
        
        if standard_response['created'] is None:
            standard_response['created'] = int(time.time())
    
    def supports_thinking(self) -> bool:
        return False
    
    def supports_tools(self) -> bool:
        return True  # ✅ IMPLEMENTED
    
    def supports_streaming_processor(self) -> bool:
        return True  # REFACTORING: Ora usa GptStreamingProcessor
    
    def get_agent_name(self) -> str:
        return "GPT"
    
    def prepare_payload(self, payload: Dict) -> None:
        """
        Prepare GPT payload - add tools if available.
        
        REFACTORING: L'handler decide internamente se servono tools.
        Converte da formato Anthropic a formato OpenAI.
        """
        # Request tools via event_system
        tool_definitions = self._request_tool_definitions()
        
        if tool_definitions:
            # Convert Anthropic format → OpenAI format
            payload['tools'] = [
                self._convert_tool_definition(td) 
                for td in tool_definitions
            ]
            self.logger.info(f"Added {len(tool_definitions)} tools to GPT payload")
    
    def _convert_tool_definition(self, anthropic_tool: Dict) -> Dict:
        """
        Convert Anthropic tool definition to OpenAI format.
        
        Anthropic:
            {
                "name": "get_weather",
                "description": "...",
                "input_schema": {...}
            }
        
        OpenAI:
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "...",
                    "parameters": {...}
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
    
    def create_simulation_payload(self) -> Dict:
        """
        Create GPT simulation payload.
        """
        return {
            'headers': {
                'Authorization': 'Bearer TEST',
                'Content-Type': 'application/json'
            },
            'model': 'gpt-4',
            'max_tokens': 4096,
            'messages': [
                {
                    'role': 'user',
                    'content': 'TEST'
                }
            ]
        }
    
    def get_uncompressible_content_types(self) -> List[str]:
        """
        GPT: no special content types to preserve.
        """
        return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMULATION MODE - GPT-specific (ITERAZIONE #5 - MOCK)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def __init__(self, event_system, logger):
        super().__init__(event_system, logger)
        self._simulation_enabled = False
        self._simulation_config = None
        self._fake_response = None
        
        # ═══ TOOL EXECUTION VIA EVENTS ═══
        # Response data
        self._tool_execution_response = None
        # Flag per sync requests
        self._tool_execution_received = False
        
        # Subscribe to tool execution response
        self.event_system.subscribe('tool_execution_response', self._on_tool_execution_response)
        
        # ═══ TOOL REGISTRY ACCESS VIA EVENTS (come ClaudeHandler) ═══
        self._tool_definitions_response = None
        self._tool_definitions_received = False
        
        # Subscribe to tool definitions response
        self.event_system.subscribe('enabled_tools_response', self._on_enabled_tools_response)
        
        # ═══ SESSION STATE - ITERAZIONE #5 (minimal for GPT) ═══
        self._is_multi_call_session = False
        self._call_count = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TOOL REGISTRY/EXECUTION EVENT HANDLERS - Comunicazione via event_system
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _on_tool_execution_response(self, data: Dict):
        """Handler per risposta tool execution da ToolRegistry."""
        self._tool_execution_response = data.get('result', '')
        self._tool_execution_received = True
        self.logger.debug(f"Received tool execution result")
    
    def _on_enabled_tools_response(self, data: Dict):
        """Handler per risposta tool definitions da ToolRegistry."""
        self._tool_definitions_response = data.get('tool_definitions', [])
        self._tool_definitions_received = True
        self.logger.debug(f"Received {len(self._tool_definitions_response)} tool definitions")
    
    def _request_tool_definitions(self) -> List[Dict]:
        """Request tool definitions da ToolRegistry via event (SYNC)."""
        import time
        
        self._tool_definitions_received = False
        self._tool_definitions_response = None
        
        self.event_system.emit_event('get_enabled_tools_request', {})
        
        max_wait = 2.0
        elapsed = 0.0
        sleep_interval = 0.01
        
        while not self._tool_definitions_received and elapsed < max_wait:
            time.sleep(sleep_interval)
            self.event_system.emit_event('gui_update_request', {})
            elapsed += sleep_interval
        
        if not self._tool_definitions_received:
            self.logger.warning("Timeout waiting for tool definitions")
            return []
        
        return self._tool_definitions_response or []
    
    def _execute_tool_via_event(self, tool_name: str, tool_input: Dict) -> str:
        """Execute tool via event_system (SYNC)."""
        import time
        
        self._tool_execution_received = False
        self._tool_execution_response = None
        
        self.event_system.emit_event('execute_tool_request', {
            'tool_name': tool_name,
            'tool_input': tool_input
        })
        
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMULATION MODE - GPT-specific (ITERAZIONE #5 - MOCK)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def toggle_simulation_mode(self, enabled: bool, tool_registry=None) -> None:
        """Toggle simulation mode - GPT mock implementation."""
        self._simulation_enabled = enabled
        self.logger.info(f"GPT simulation mode: {'ENABLED' if enabled else 'DISABLED'}")
        
        if enabled:
            self._simulation_config = {'timing': 'fast'}
            self._fake_response = GptFakeStreamingResponse(self._simulation_config)
        else:
            self._simulation_config = None
            self._fake_response = None
    
    def is_simulation_enabled(self) -> bool:
        return self._simulation_enabled
    
    def get_simulation_response(self):
        """Get fake response iterator for simulation."""
        if self._fake_response:
            self._fake_response._init_turn()
        return self._fake_response
    
    def configure_simulation_for_payload(self, payload: Dict) -> None:
        """GPT: no-op for now (no special config needed)."""
        pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAYLOAD FEATURE OPERATIONS - GPT-specific (ITERAZIONE #5 - NOT IMPLEMENTED)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def modify_payload_feature_data(self, modified_data: Any,
                                    context: StreamContext) -> Dict:
        """GPT: not implemented (no tool support yet)."""
        raise NotImplementedError("GPT does not support payload feature modification yet")
    
    def recalculate_payload_feature_data(self, feature_name: str,
                                         modified_input: Any,
                                         context: StreamContext) -> tuple:
        """GPT: not implemented (no tool support yet)."""
        raise NotImplementedError("GPT does not support payload feature recalculation yet")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION STATE METHODS - GPT-specific (ITERAZIONE #5)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def has_active_session(self) -> bool:
        """GPT: no multi-call sessions (yet)."""
        return False
    
    def get_session_info(self) -> Dict:
        """Get session info per debug panel."""
        return {
            'is_multi_call': self._is_multi_call_session,
            'call_count': self._call_count,
            'accumulated_tokens': 0,
            'content_blocks_count': 0,
            'has_tool_use': False
        }
    
    def reset_session(self) -> None:
        """Reset session state."""
        self._is_multi_call_session = False
        self._call_count = 0
        self.logger.debug("GPT session state reset")
    
    def set_current_content_blocks(self, blocks) -> None:
        """GPT: no-op (no content blocks tracking)."""
        pass
    
    def compress_payload(self, payload: Dict, max_context: int,
                        max_tokens: int) -> Dict:
        """GPT: basic compression (TODO)."""
        return payload
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TOOL EXECUTION - GPT function calling
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _handle_tool_calls(self, tool_calls: List[Dict], 
                           standard_response: Dict,
                           context: StreamContext) -> StreamResult:
        """
        Execute tools e build continuation per GPT.
        
        Args:
            tool_calls: Lista di tool calls da GPT
            standard_response: Response accumulata
            context: Stream context
        
        Returns:
            StreamResult con continuation response
        """
        import uuid
        import json
        import copy
        
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
            
            # Execute tool via event_system
            result = self._execute_tool_via_event(function_name, arguments)
            
            # Emit tool result
            context.emit_stream_output([{
                'type': 'tool_result',
                'tool_name': function_name,
                'tool_id': tool_id,
                'tool_result': result
            }])
            
            # Build result message for continuation
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_id,
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
        
        # Execute continuation via context.make_request
        result = context.make_request(continue_request)
        
        # Return result (StreamResult o Dict a seconda dell'implementazione)
        if isinstance(result, dict):
            # make_request ritorna dict legacy
            if result.get('success') and result.get('response'):
                return StreamResult(
                    success=True,
                    response=result['response'],
                    partial=False
                )
            else:
                return StreamResult(
                    success=False,
                    error=result.get('error', 'Continuation failed'),
                    partial=True
                )
        else:
            # make_request ritorna StreamResult
            return result
    
    def _build_continuation_payload(self, original_payload: Dict,
                                    assistant_response: Dict,
                                    tool_results: List[Dict]) -> Dict:
        """
        Build continuation payload for GPT after tool execution.
        
        OpenAI format:
            messages: [
                ...previous messages...,
                {role: "assistant", content: null, tool_calls: [...]},
                {role: "tool", tool_call_id: "...", content: "..."},
                ...
            ]
        
        Args:
            original_payload: Original request payload
            assistant_response: GPT response with tool_calls
            tool_results: List of tool results to add
        
        Returns:
            New payload for continuation
        """
        import copy
        
        payload = copy.deepcopy(original_payload)
        
        # Add assistant message with tool_calls
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROCESS_STREAM - Main processing method (ITERAZIONE #3)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def process_stream(self, response, request: StreamingRequest, 
                       standard_response: Dict, context: StreamContext) -> StreamResult:
        """
        Process GPT stream usando GptStreamingProcessor.
        
        REFACTORING: Normalizzato - stessa architettura di ClaudeHandler.
        """
        # ═══ INIT PROCESSOR ═══
        processor = GptStreamingProcessor(self.event_system, self.logger)
        
        chunks_processed = 0
        gui_update_counter = 0
        
        bytes_read = 0
        chunks_received = 0
        stream_started_time = time.time()
        has_received_substantial_data = False
        
        try:
            for line in response.iter_lines(decode_unicode=True):
                # Check cancellazione
                if request.state == StreamingState.CANCELLED:
                    self.logger.info("GPT stream cancelled by user")
                    break
                
                if not line or not line.strip():
                    continue
                
                # Tracking
                bytes_read += len(line.encode('utf-8'))
                chunks_received += 1
                
                if bytes_read > 1000:
                    has_received_substantial_data = True
                
                # Parse SSE
                if line.startswith('data: '):
                    data_str = line[6:]
                    
                    if data_str.strip() == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # ═══ USE PROCESSOR ═══
                        stream_output = processor.process_chunk(data)
                        
                        # Emit output if generated
                        if stream_output:
                            context.emit_stream_output([stream_output])
                        
                        chunks_processed += 1
                        
                        # GUI update
                        gui_update_counter += 1
                        if gui_update_counter >= context.gui_update_interval:
                            context.emit_gui_update()
                            gui_update_counter = 0
                        
                        # Memory cleanup
                        if chunks_processed % context.memory_cleanup_interval == 0:
                            gc.collect()
                            
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"JSON decode error: {e}")
                        continue
            
            # ═══ FINALIZE ═══
            # Update response with accumulated data from processor
            processor.update_response(standard_response)
            
            # ═══ CHECK TOOL CALLS ═══
            if processor.has_tool_calls():
                self.logger.info(f"GPT response has {len(processor.get_tool_calls())} tool calls")
                
                # Execute tools and continue
                tool_result = self._handle_tool_calls(
                    processor.get_tool_calls(),
                    standard_response,
                    context
                )
                
                # Cleanup processor before returning
                processor.cleanup()
                
                return tool_result
            
            # Cleanup
            processor.cleanup()
            
            return StreamResult(
                success=True,
                partial=False,
                response=standard_response,
                chunks_received=chunks_received,
                bytes_read=bytes_read
            )
            
        except Exception as stream_error:
            stream_duration = time.time() - stream_started_time
            error_context = {
                'bytes_read': bytes_read,
                'chunks_received': chunks_received,
                'chunks_processed': chunks_processed,
                'stream_duration': stream_duration,
                'has_substantial_data': has_received_substantial_data,
                'error_type': type(stream_error).__name__,
                'error_details': str(stream_error)
            }
            
            should_retry = self._analyze_chunk_error_severity(error_context, stream_error)
            
            if should_retry:
                return StreamResult(
                    success=False,
                    partial=True,
                    should_retry=True,
                    error=str(stream_error)
                )
            else:
                # Use partial data
                if chunks_processed > 0:
                    # Update response with what we have
                    processor.update_response(standard_response)
                    processor.cleanup()
                    
                    self.append_abort_message(standard_response, 
                                            "\n\n[Stream ended unexpectedly but response is complete]")
                    
                    return StreamResult(
                        success=True,
                        partial=True,
                        should_retry=False,
                        response=standard_response,
                        chunks_received=chunks_received,
                        bytes_read=bytes_read
                    )
                else:
                    return StreamResult(
                        success=False,
                        partial=True,
                        should_retry=True,
                        error=str(stream_error)
                    )
    
    def _analyze_chunk_error_severity(self, error_context: Dict, error: Exception) -> bool:
        """
        Analizza se errore è reale o end-of-stream normale.
        
        COPIATO DA: ClaudeHandler._analyze_chunk_error_severity (identico)
        """
        normal_indicators = 0
        
        if error_context['bytes_read'] > 1000 and error_context['chunks_processed'] > 0:
            normal_indicators += 1
        if error_context['stream_duration'] > 5.0:
            normal_indicators += 1
        if error_context['chunks_received'] > 10:
            normal_indicators += 1
        if error_context['has_substantial_data']:
            normal_indicators += 1
        
        error_indicators = 0
        
        if error_context['bytes_read'] < 100:
            error_indicators += 2
        if error_context['stream_duration'] < 1.0:
            error_indicators += 1
        if error_context['chunks_received'] < 3:
            error_indicators += 1
        
        error_keywords = ['connection', 'reset', 'broken', 'refused', 'timeout']
        if any(kw in str(error).lower() for kw in error_keywords):
            error_indicators += 2
        
        if normal_indicators >= 3:
            return False
        if error_indicators >= 3:
            return True
        if error_context['chunks_processed'] > 0:
            return False
        else:
            return True


# ═══════════════════════════════════════════════════════════════════════════════
# FAKE STREAMING RESPONSE - Agent-specific simulation (ITERAZIONE #5)
# ═══════════════════════════════════════════════════════════════════════════════

class ClaudeFakeStreamingResponse:
    """
    Fake streaming response per Claude simulation.
    
    Simula le risposte SSE di Claude per testing senza API call.
    SPOSTATO DA: fake_streaming_response.py
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'include_text': True,
            'include_tool': False,
            'tool_name': None,
            'tool_input': None,
            'timing': 'fast'
        }
        self._lines = []
        self._current_index = 0
    
    def _init_turn(self):
        """Initialize a new turn - generate SSE lines."""
        self._lines = self._generate_sse_lines()
        self._current_index = 0
    
    def _generate_sse_lines(self) -> List[str]:
        """Generate SSE event lines based on config."""
        lines = []
        
        # Message start
        lines.append('data: {"type":"message_start","message":{"id":"msg_sim_' + str(uuid.uuid4())[:8] + '","type":"message","role":"assistant","model":"claude-sonnet-4-20250514-simulation","content":[],"stop_reason":null,"usage":{"input_tokens":100,"output_tokens":0}}}')
        
        block_index = 0
        
        # Thinking block (always for Claude simulation with thinking)
        lines.append(f'data: {{"type":"content_block_start","index":{block_index},"content_block":{{"type":"thinking","thinking":""}}}}')
        lines.append(f'data: {{"type":"content_block_delta","index":{block_index},"delta":{{"type":"thinking_delta","thinking":"Let me think about this..."}}}}')
        lines.append(f'data: {{"type":"content_block_delta","index":{block_index},"delta":{{"type":"thinking_delta","thinking":" This is simulated thinking."}}}}')
        lines.append(f'data: {{"type":"content_block_stop","index":{block_index}}}')
        block_index += 1
        
        # Text block
        if self.config.get('include_text', True):
            lines.append(f'data: {{"type":"content_block_start","index":{block_index},"content_block":{{"type":"text","text":""}}}}')
            lines.append(f'data: {{"type":"content_block_delta","index":{block_index},"delta":{{"type":"text_delta","text":"This is a simulated response"}}}}')
            lines.append(f'data: {{"type":"content_block_delta","index":{block_index},"delta":{{"type":"text_delta","text":" from Claude."}}}}')
            lines.append(f'data: {{"type":"content_block_stop","index":{block_index}}}')
            block_index += 1
        
        # Tool use block
        if self.config.get('include_tool', False):
            tool_name = self.config.get('tool_name', 'test_tool')
            tool_input = self.config.get('tool_input') or {'param': 'test_value'}
            tool_id = f"toolu_sim_{str(uuid.uuid4())[:8]}"
            
            lines.append(f'data: {{"type":"content_block_start","index":{block_index},"content_block":{{"type":"tool_use","id":"{tool_id}","name":"{tool_name}","input":{{}}}}}}')
            lines.append(f'data: {{"type":"content_block_delta","index":{block_index},"delta":{{"type":"input_json_delta","partial_json":"{json.dumps(tool_input)}"}}}}')
            lines.append(f'data: {{"type":"content_block_stop","index":{block_index}}}')
            block_index += 1
        
        # Message delta with stop reason
        stop_reason = "tool_use" if self.config.get('include_tool', False) else "end_turn"
        lines.append(f'data: {{"type":"message_delta","delta":{{"stop_reason":"{stop_reason}"}},"usage":{{"output_tokens":150}}}}')
        
        # Message stop
        lines.append('data: {"type":"message_stop"}')
        
        return lines
    
    def iter_lines(self, decode_unicode=True):
        """Iterate over simulated SSE lines."""
        delay = 0.01 if self.config.get('timing') == 'fast' else 0.1
        
        for line in self._lines:
            time.sleep(delay)
            yield line


class GptFakeStreamingResponse:
    """
    Fake streaming response per GPT simulation.
    
    MOCK - implementazione minima per architettura.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {'timing': 'fast'}
        self._lines = []
        self._current_index = 0
    
    def _init_turn(self):
        """Initialize a new turn."""
        self._lines = self._generate_sse_lines()
        self._current_index = 0
    
    def _generate_sse_lines(self) -> List[str]:
        """Generate SSE event lines for GPT format."""
        lines = []
        
        # GPT format SSE
        lines.append('data: {"id":"chatcmpl-sim","object":"chat.completion.chunk","model":"gpt-4-simulation","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}')
        lines.append('data: {"id":"chatcmpl-sim","object":"chat.completion.chunk","model":"gpt-4-simulation","choices":[{"index":0,"delta":{"content":"This is "},"finish_reason":null}]}')
        lines.append('data: {"id":"chatcmpl-sim","object":"chat.completion.chunk","model":"gpt-4-simulation","choices":[{"index":0,"delta":{"content":"simulated GPT output."},"finish_reason":null}]}')
        lines.append('data: {"id":"chatcmpl-sim","object":"chat.completion.chunk","model":"gpt-4-simulation","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}')
        lines.append('data: [DONE]')
        
        return lines
    
    def iter_lines(self, decode_unicode=True):
        """Iterate over simulated SSE lines."""
        delay = 0.01 if self.config.get('timing') == 'fast' else 0.1
        
        for line in self._lines:
            time.sleep(delay)
            yield line


# ═══════════════════════════════════════════════════════════════════════════════
# HUGGINGFACE HANDLER - OpenAI-compatible API
# ═══════════════════════════════════════════════════════════════════════════════

class HfHandler(BaseAgentHandler):
    """
    Handler per HuggingFace Inference API (OpenAI-compatible).
    
    FORMATO SSE: Identico a OpenAI (riusa GptStreamingProcessor).
    
    DIFFERENZE vs GPT:
    - Headers: Authorization: Bearer hf_... (non sk_...)
    - Endpoint: Da models_config (es. https://router.huggingface.co/v1/chat/completions)
    - Model names: meta-llama/Llama-3.1-8B-Instruct (non gpt-4)
    - Provider parameter: {"provider": "auto" | "hf-inference" | ...}
    - Tool support: Dipende dal modello (Llama 3.1+, Hermes, Mistral Instruct)
    
    RIUSA da GptHandler:
    - init_response() - IDENTICO
    - create_error_response() - IDENTICO
    - process_stream() - USA GptStreamingProcessor
    - _handle_tool_calls() - IDENTICO
    - _build_continuation_payload() - IDENTICO
    - _convert_tool_definition() - IDENTICO
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESPONSE STRUCTURE - Identico a GPT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def init_response(self) -> Dict:
        return {
            "id": None,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": None,
            "system_fingerprint": None,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': ''
                },
                'finish_reason': None
            }],
            'usage': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        }
    
    def create_error_response(self, error_message: str) -> Dict:
        return {
            'object': 'chat.completion',
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': f'Error: {error_message}'
                },
                'finish_reason': 'stop'
            }],
            'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            'error': error_message
        }
    
    def parse_sse_event(self, data: Dict, is_multi_call_session: bool = False) -> Optional[StreamEvent]:
        # HF usa processing inline come GPT
        return None
    
    def update_response_from_event(self, standard_response: Dict, data: Dict) -> None:
        # HF: update è inline in process_chunk
        pass
    
    def append_abort_message(self, standard_response: Dict, message: str = "\n\n[⛔ Stream aborted by user]") -> None:
        if standard_response.get('choices'):
            standard_response['choices'][0]['message']['content'] += message
    
    def finalize_response_simple(self, standard_response: Dict) -> None:
        if not standard_response['choices']:
            standard_response['choices'] = [{
                'index': 0,
                'message': {'role': 'assistant', 'content': ''},
                'finish_reason': 'stop'
            }]
        elif standard_response['choices'][0].get('finish_reason') is None:
            standard_response['choices'][0]['finish_reason'] = 'stop'
        
        if standard_response['created'] is None:
            standard_response['created'] = int(time.time())
    
    def supports_thinking(self) -> bool:
        return False
    
    def supports_tools(self) -> bool:
        """
        HuggingFace: Tool support dipende dal modello.
        
        MODELS CON TOOL SUPPORT:
        - meta-llama/Llama-3.1-* (tutte le varianti)
        - NousResearch/Hermes-* (tutte le versioni)
        - mistralai/Mistral-*-Instruct-* (con Instruct)
        - Qwen/Qwen2.*
        
        DEFAULT: Assume tool support (safe - l'API rifiuterà se non supportato)
        """
        # Per ora return True - il model specifico viene validato in prepare_payload
        return True
    
    def supports_streaming_processor(self) -> bool:
        return True  # Usa GptStreamingProcessor (formato identico)
    
    def get_agent_name(self) -> str:
        return "HuggingFace"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAYLOAD PREPARATION - HF-specific
    # ═══════════════════════════════════════════════════════════════════════════
    
    def prepare_payload(self, payload: Dict) -> None:
        """
        Prepare HuggingFace payload.
        
        DIFFERENZE vs GPT:
        1. Provider parameter (opzionale): {"provider": "auto"}
        2. Model validation per tool support
        3. Tools in formato OpenAI (come GPT)
        
        HEADERS e API_URL: Passati dall'esterno (come GPT).
        """
        # Request tools via event_system (come GPT)
        tool_definitions = self._request_tool_definitions()
        
        if tool_definitions:
            # Valida model per tool support
            model = payload.get('model', '')
            if not self._model_supports_tools(model):
                self.logger.warning(
                    f"Model '{model}' may not support tool calls. "
                    f"Supported: Llama-3.1, Hermes, Mistral-Instruct, Qwen2"
                )
            
            # Convert Anthropic format → OpenAI format (identico a GPT)
            payload['tools'] = [
                self._convert_tool_definition(td) 
                for td in tool_definitions
            ]
            self.logger.info(f"Added {len(tool_definitions)} tools to HuggingFace payload")
        
        # Provider parameter (opzionale - HF lo inferisce automaticamente)
        if 'provider' not in payload:
            payload['provider'] = 'auto'  # Let HF choose best provider
    
    def _model_supports_tools(self, model: str) -> bool:
        """
        Check se il modello supporta tool calls.
        
        Returns:
            True se il modello supporta tools, False altrimenti
        """
        model_lower = model.lower()
        
        # Llama 3.1+ support
        if 'llama-3.1' in model_lower or 'llama-3-1' in model_lower:
            return True
        
        # Hermes support
        if 'hermes' in model_lower:
            return True
        
        # Mistral Instruct support
        if 'mistral' in model_lower and 'instruct' in model_lower:
            return True
        
        # Qwen2 support
        if 'qwen2' in model_lower or 'qwen-2' in model_lower:
            return True
        
        # Default: assume NO tool support (conservative)
        return False
    
    def _convert_tool_definition(self, anthropic_tool: Dict) -> Dict:
        """
        Convert Anthropic tool definition to OpenAI format.
        IDENTICO a GptHandler - HF usa stesso formato.
        """
        return {
            "type": "function",
            "function": {
                "name": anthropic_tool["name"],
                "description": anthropic_tool.get("description", ""),
                "parameters": anthropic_tool.get("input_schema", {})
            }
        }
    
    def create_simulation_payload(self) -> Dict:
        """
        Create HuggingFace simulation payload.
        """
        return {
            'headers': {
                'Authorization': 'Bearer hf_TEST',
                'Content-Type': 'application/json'
            },
            'model': 'meta-llama/Llama-3.1-8B-Instruct',
            'provider': 'auto',
            'max_tokens': 4096,
            'messages': [
                {
                    'role': 'user',
                    'content': 'TEST'
                }
            ]
        }
    
    def get_uncompressible_content_types(self) -> List[str]:
        """
        HuggingFace: no special content types to preserve.
        """
        return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONSTRUCTOR & EVENT HANDLERS - Identico a GptHandler
    # ═══════════════════════════════════════════════════════════════════════════
    
    def __init__(self, event_system, logger):
        super().__init__(event_system, logger)
        self._simulation_enabled = False
        self._simulation_config = None
        self._fake_response = None
        
        # ═══ TOOL EXECUTION VIA EVENTS ═══
        self._tool_execution_response = None
        self._tool_execution_received = False
        
        self.event_system.subscribe('tool_execution_response', self._on_tool_execution_response)
        
        # ═══ TOOL REGISTRY ACCESS VIA EVENTS ═══
        self._tool_definitions_response = None
        self._tool_definitions_received = False
        
        self.event_system.subscribe('enabled_tools_response', self._on_enabled_tools_response)
        
        # ═══ SESSION STATE ═══
        self._is_multi_call_session = False
        self._call_count = 0
    
    def _on_tool_execution_response(self, data: Dict):
        """Handler per risposta tool execution da ToolRegistry."""
        self._tool_execution_response = data.get('result', '')
        self._tool_execution_received = True
        self.logger.debug(f"Received tool execution result")
    
    def _on_enabled_tools_response(self, data: Dict):
        """Handler per risposta tool definitions da ToolRegistry."""
        self._tool_definitions_response = data.get('tool_definitions', [])
        self._tool_definitions_received = True
        self.logger.debug(f"Received {len(self._tool_definitions_response)} tool definitions")
    
    def _request_tool_definitions(self) -> List[Dict]:
        """Request tool definitions da ToolRegistry via event (SYNC)."""
        import time
        
        self._tool_definitions_received = False
        self._tool_definitions_response = None
        
        # Emit request
        self.event_system.emit_event('get_enabled_tools_request', {})
        
        # Wait for response (max 2 seconds)
        timeout = 2.0
        elapsed = 0.0
        sleep_interval = 0.05
        
        while not self._tool_definitions_received and elapsed < timeout:
            self.event_system.emit_event('gui_update_request', {})
            time.sleep(sleep_interval)
            elapsed += sleep_interval
        
        if not self._tool_definitions_received:
            self.logger.warning("Timeout waiting for tool definitions - proceeding without tools")
            return []
        
        return self._tool_definitions_response or []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STREAMING - Riusa GptStreamingProcessor (formato identico)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def process_stream(self, response, request: StreamingRequest, 
                      standard_response: Dict, context: StreamContext) -> StreamResult:
        """
        Process HuggingFace streaming response.
        USA GptStreamingProcessor - formato SSE identico a OpenAI!
        """
        from streaming_processors import GptStreamingProcessor
        
        processor = GptStreamingProcessor(
            standard_response=standard_response,
            context=context,
            logger=self.logger
        )
        
        return processor.process_response(response, request)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TOOL CALLS - Identico a GptHandler
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _handle_tool_calls(self, tool_calls: List[Dict], 
                          original_payload: Dict,
                          accumulated_messages: List[Dict],
                          context: StreamContext) -> Optional[Dict]:
        """
        Handle tool calls execution and continuation.
        IDENTICO a GptHandler - formato tool calls uguale.
        """
        import json
        
        self.logger.info(f"Handling {len(tool_calls)} tool calls")
        
        # Build tool results
        tool_results = []
        
        for tool_call in tool_calls:
            tool_id = tool_call.get('id')
            function_data = tool_call.get('function', {})
            tool_name = function_data.get('name')
            
            try:
                arguments = function_data.get('arguments', '{}')
                if isinstance(arguments, str):
                    tool_input = json.loads(arguments)
                else:
                    tool_input = arguments
            except json.JSONDecodeError:
                tool_input = {}
                self.logger.error(f"Failed to parse tool arguments for {tool_name}")
            
            self.logger.info(f"Executing tool: {tool_name}")
            
            # Execute via event_system
            self._tool_execution_received = False
            self._tool_execution_response = None
            
            self.event_system.emit_event('tool_execution_request', {
                'tool_name': tool_name,
                'tool_input': tool_input,
                'tool_use_id': tool_id
            })
            
            # Wait for response
            timeout = 30.0
            elapsed = 0.0
            sleep_interval = 0.1
            
            while not self._tool_execution_received and elapsed < timeout:
                context.emit_gui_update()
                import time
                time.sleep(sleep_interval)
                elapsed += sleep_interval
                
                if context.is_aborted(request_id="current"):
                    self.logger.warning("Tool execution aborted")
                    return None
            
            if not self._tool_execution_received:
                result_content = f"Error: Tool execution timeout for {tool_name}"
            else:
                result_content = self._tool_execution_response or "Tool executed successfully"
            
            # OpenAI format tool result
            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result_content
            })
        
        # Build continuation payload
        continuation_payload = self._build_continuation_payload(
            original_payload,
            accumulated_messages,
            tool_calls,
            tool_results
        )
        
        return continuation_payload
    
    def _build_continuation_payload(self, original_payload: Dict,
                                   accumulated_messages: List[Dict],
                                   tool_calls: List[Dict],
                                   tool_results: List[Dict]) -> Dict:
        """
        Build continuation payload dopo tool execution.
        IDENTICO a GptHandler - formato messaggi uguale.
        """
        new_payload = original_payload.copy()
        
        # Reconstruct messages
        messages = new_payload.get('messages', []).copy()
        
        # Add assistant message con tool_calls
        assistant_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls
        }
        messages.append(assistant_message)
        
        # Add tool results
        messages.extend(tool_results)
        
        new_payload['messages'] = messages
        
        return new_payload
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMULATION MODE - Per testing
    # ═══════════════════════════════════════════════════════════════════════════
    
    def is_simulation_enabled(self) -> bool:
        return self._simulation_enabled
    
    def enable_simulation(self, config: Dict = None):
        self._simulation_enabled = True
        self._simulation_config = config or {}
        self.logger.info("HuggingFace simulation mode ENABLED")
    
    def disable_simulation(self):
        self._simulation_enabled = False
        self._simulation_config = None
        self._fake_response = None
        self.logger.info("HuggingFace simulation mode DISABLED")
    
    def configure_simulation_for_payload(self, payload: Dict):
        """Configure simulation basandosi sul payload corrente."""
        if not self._simulation_enabled:
            return
        
        # Import lazy per evitare circular imports
        from hf_fake_streaming_response import HfFakeStreamingResponse
        
        # Create fake response con config
        self._fake_response = HfFakeStreamingResponse(self._simulation_config)
        self.logger.info("Created HuggingFace fake streaming response")
    
    def get_simulation_response(self):
        """Get fake response per simulation mode."""
        if not self._fake_response:
            from hf_fake_streaming_response import HfFakeStreamingResponse
            self._fake_response = HfFakeStreamingResponse(self._simulation_config or {})
        
        return self._fake_response


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT STREAMING HANDLER - Wrapper/Facade (il daemon usa SOLO questa classe)
# ═══════════════════════════════════════════════════════════════════════════════

class AgentStreamingHandler:
    """
    Wrapper/Facade per streaming agent-specific.
    
    ARCHITETTURA: Il daemon usa SOLO questa classe.
                  NON SA quale agente c'è dietro.
                  La conoscenza è CONFINATA qui.
    
    USAGE (ITERAZIONE #4):
        handler = AgentStreamingHandler(models_config.SELECTED_CONF, event_system, logger)
        response = handler.init_response()
        ...
    """
    
    def __init__(self, model_config: str, event_system, logger):
        """
        Args:
            model_config: Stringa configurazione modello (es. 'ANTHROPIC_CLAUDE_SONNET')
            event_system: EventSystem per emettere eventi
            logger: Logger instance
        
        NOTE: La decisione su quale handler usare è CONFINATA QUI.
              Il daemon NON sa quale agente c'è dietro.
        """
        # ═══ LA CONOSCENZA DELL'AGENTE È CONFINATA QUI ═══
        model_config_str = str(model_config).upper()
        
        if 'CLAUDE' in model_config_str:
            self._impl = ClaudeHandler(event_system, logger)
        elif 'HUGGINGFACE' in model_config_str or 'HF_' in model_config_str:
            self._impl = HfHandler(event_system, logger)
        else:
            # Default: GPT/OpenAI
            self._impl = GptHandler(event_system, logger)
        
        # Store per internal use (NON esposto al daemon)
        self._model_config = model_config
        self.event_system = event_system
        self.logger = logger
    
    # ═══════════════════════════════════════════════════════════════
    # DELEGAZIONE - Tutti i metodi delegano a self._impl
    # ═══════════════════════════════════════════════════════════════
    
    def init_response(self) -> Dict:
        """Initialize response structure"""
        return self._impl.init_response()
    
    def create_error_response(self, error_message: str) -> Dict:
        """Create error response"""
        return self._impl.create_error_response(error_message)
    
    def parse_sse_event(self, data: Dict, is_multi_call_session: bool = False) -> Optional[StreamEvent]:
        """Parse SSE event"""
        return self._impl.parse_sse_event(data, is_multi_call_session)
    
    def update_response_from_event(self, standard_response: Dict, data: Dict) -> None:
        """Update response from SSE event"""
        return self._impl.update_response_from_event(standard_response, data)
    
    def append_abort_message(self, standard_response: Dict, message: str = "\n\n[⛔ Stream aborted by user]") -> None:
        """Append abort message to response"""
        return self._impl.append_abort_message(standard_response, message)
    
    def append_error_message(self, standard_response: Dict, message: str = "\n\n[Stream ended unexpectedly but response is complete]") -> None:
        """Append error message (alias di append_abort_message)"""
        return self._impl.append_abort_message(standard_response, message)
    
    def finalize_response_simple(self, standard_response: Dict) -> None:
        """Simple finalization"""
        return self._impl.finalize_response_simple(standard_response)
    
    def process_gpt_chunk(self, data: Dict, standard_response: Dict, first_chunk: bool) -> tuple[bool, Optional[str]]:
        """
        Process single chunk.
        
        NOTE: Manteniamo il nome process_gpt_chunk per backward compatibility
              con il daemon. Internamente delega a process_chunk dell'impl.
        """
        return self._impl.process_chunk(data, standard_response, first_chunk)
    
    # ═══════════════════════════════════════════════════════════════
    # CAPABILITIES - Delegati
    # ═══════════════════════════════════════════════════════════════
    
    def supports_thinking(self) -> bool:
        return self._impl.supports_thinking()
    
    def supports_tools(self) -> bool:
        return self._impl.supports_tools()
    
    def supports_streaming_processor(self) -> bool:
        return self._impl.supports_streaming_processor()
    
    def get_agent_name(self) -> str:
        return self._impl.get_agent_name()
    
    # ═══════════════════════════════════════════════════════════════
    # PROCESS_STREAM - MAIN METHOD (ITERAZIONE #3)
    # ═══════════════════════════════════════════════════════════════
    
    def process_stream(self, response, request: StreamingRequest, 
                       standard_response: Dict, context: StreamContext) -> StreamResult:
        """
        Process complete stream - DELEGA a impl.
        
        Questo è il CORE METHOD che il daemon chiama.
        Sostituisce sia _process_claude_stream che _process_gpt_stream.
        """
        return self._impl.process_stream(response, request, standard_response, context)
    
    # ═══════════════════════════════════════════════════════════════
    # DEBUG/CONTINUATION METHODS - ITERAZIONE #5
    # ═══════════════════════════════════════════════════════════════
    # 
    # I vecchi metodi build_continue_payload_with_results e
    # execute_tool_and_build_continuation sono stati RIMOSSI.
    # 
    # Ora il daemon usa i nuovi metodi generici:
    # - modify_payload_feature_data()
    # - recalculate_payload_feature_data()
    #
    # Questi delegano internamente ai metodi _build_continue_payload_with_results
    # e _execute_tool_and_build_continuation degli handler specifici.
    # ═══════════════════════════════════════════════════════════════
    
    # ═══════════════════════════════════════════════════════════════
    # PAYLOAD PREPARATION - Agent-specific (ITERAZIONE #4)
    # ═══════════════════════════════════════════════════════════════
    
    def prepare_payload(self, payload: Dict) -> None:
        """
        Prepare payload per streaming - agent-specific.
        
        REFACTORING: L'handler decide internamente se servono tools
        e li prende direttamente da tool_registry.
        
        Gestisce:
        - Check thinking mode (se supportato)
        - Aggiunta tool definitions nel formato corretto per l'agent
        - Modifica system prompt se necessario
        
        Args:
            payload: Payload da preparare (MODIFICATO in place)
        """
        self._impl.prepare_payload(payload)
    
    def create_simulation_payload(self) -> Dict:
        """
        Create simulation/test payload - agent-specific.
        
        Returns:
            Dict: Payload minimo valido per questo agent
        """
        return self._impl.create_simulation_payload()
    
    def get_uncompressible_content_types(self) -> List[str]:
        """
        Get content types that should NEVER be compressed.
        
        Returns:
            List[str]: Content type names to preserve (e.g., ["thinking", "redacted_thinking"])
        
        NOTE: Used by daemon compression logic to know what to preserve.
        """
        return self._impl.get_uncompressible_content_types()
    
    # ═══════════════════════════════════════════════════════════════
    # SIMULATION MODE - ITERAZIONE #5
    # ═══════════════════════════════════════════════════════════════
    
    def toggle_simulation_mode(self, enabled: bool) -> None:
        """
        Toggle simulation mode - daemon passa SOLO il boolean.
        
        L'agent handler gestisce TUTTO internamente:
        - Crea FakeStreamingResponse appropriato
        - Configura parametri specifici dell'agent
        - Il daemon NON sa come funziona la simulazione
        """
        # tool_registry può essere passato se necessario in futuro
        return self._impl.toggle_simulation_mode(enabled, tool_registry=None)
    
    def is_simulation_enabled(self) -> bool:
        """Check se simulation mode è attivo."""
        return self._impl.is_simulation_enabled()
    
    def get_simulation_response(self):
        """
        Get simulation response iterator.
        
        Returns:
            Object che implementa iter_lines() per simulare streaming
        """
        return self._impl.get_simulation_response()
    
    def configure_simulation_for_payload(self, payload: Dict) -> None:
        """
        Configure simulation based on prepared payload.
        
        Called after prepare_payload() quando simulation è attivo.
        """
        return self._impl.configure_simulation_for_payload(payload)
    
    # ═══════════════════════════════════════════════════════════════
    # PAYLOAD FEATURE OPERATIONS - ITERAZIONE #5
    # ═══════════════════════════════════════════════════════════════
    
    def modify_payload_feature_data(self, modified_data: Any,
                                    context: StreamContext) -> Dict:
        """
        Modify payload feature data (es. tool result) - NO execution.
        
        ITERAZIONE #5: Senza content_blocks - handler usa stato interno.
        
        Returns:
            Dict: Rebuilt continuation payload
        """
        return self._impl.modify_payload_feature_data(modified_data, context)
    
    def recalculate_payload_feature_data(self, feature_name: str,
                                         modified_input: Any,
                                         context: StreamContext) -> tuple:
        """
        Recalculate payload feature data (es. re-execute tool).
        
        ITERAZIONE #5: Senza content_blocks - handler usa stato interno.
        
        Returns:
            tuple: (result, success, continuation_payload)
        """
        return self._impl.recalculate_payload_feature_data(
            feature_name, modified_input, context
        )
    
    # ═══════════════════════════════════════════════════════════════
    # SESSION STATE - ITERAZIONE #5
    # ═══════════════════════════════════════════════════════════════
    
    def has_active_session(self) -> bool:
        """Check se c'è una sessione attiva."""
        return self._impl.has_active_session()
    
    def get_session_info(self) -> Dict:
        """Get session info per debug panel (struttura generica)."""
        return self._impl.get_session_info()
    
    def reset_session(self) -> None:
        """Reset session state."""
        return self._impl.reset_session()
    
    def set_current_content_blocks(self, blocks) -> None:
        """Set current content blocks - chiamato dopo process_stream."""
        return self._impl.set_current_content_blocks(blocks)
    
    def compress_payload(self, payload: Dict, max_context: int,
                        max_tokens: int) -> Dict:
        """
        Compress payload per rispettare limiti token.
        
        Agent-specific compression.
        """
        return self._impl.compress_payload(payload, max_context, max_tokens)


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE VALIDATOR - Utility class (invariata)
# ═══════════════════════════════════════════════════════════════════════════════

class ResponseValidator:
    """
    Valida response per consistency/completeness.
    
    NOTE: Metodi statici, non dipendono dall'handler.
    """
    
    @staticmethod
    def validate_claude_response(response: Dict) -> tuple[bool, list]:
        """Valida risposta Claude"""
        issues = []
        
        if 'id' not in response or not response['id']:
            issues.append("Missing response ID")
        
        if 'content' not in response:
            issues.append("Missing content field")
        elif not isinstance(response['content'], list):
            issues.append("Content is not list")
        elif len(response['content']) == 0:
            issues.append("Content is empty")
        
        if 'content' in response and isinstance(response['content'], list):
            for i, block in enumerate(response['content']):
                if block is None:
                    issues.append(f"Content block {i} is None")
                    continue
                
                block_type = block.get('type')
                if not block_type:
                    issues.append(f"Block {i} missing type")
                
                if block_type == 'text' and 'text' not in block:
                    issues.append(f"Text block {i} missing text field")
                
                if block_type == 'tool_use':
                    if 'name' not in block:
                        issues.append(f"Tool use block {i} missing name")
                    if 'id' not in block:
                        issues.append(f"Tool use block {i} missing id")
        
        if 'usage' in response:
            usage = response['usage']
            if usage.get('output_tokens', 0) == 0 and len(response.get('content', [])) > 0:
                issues.append("Has content but 0 output tokens (suspicious)")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_gpt_response(response: Dict) -> tuple[bool, list]:
        """Valida risposta GPT"""
        issues = []
        
        if 'id' not in response or not response['id']:
            issues.append("Missing response ID")
        
        if 'choices' not in response:
            issues.append("Missing choices field")
        elif not isinstance(response['choices'], list):
            issues.append("Choices is not list")
        elif len(response['choices']) == 0:
            issues.append("Choices is empty")
        else:
            choice = response['choices'][0]
            if 'message' not in choice:
                issues.append("Choice missing message")
            elif 'content' not in choice.get('message', {}):
                issues.append("Message missing content")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def sanitize_claude_response(response: Dict) -> Dict:
        """Sanitize Claude response"""
        sanitized = response.copy()
        
        if 'content' in sanitized and isinstance(sanitized['content'], list):
            sanitized['content'] = [b for b in sanitized['content'] if b is not None]
        
        if 'usage' not in sanitized:
            sanitized['usage'] = {'input_tokens': 0, 'output_tokens': 0}
        
        if 'type' not in sanitized:
            sanitized['type'] = 'message'
        if 'role' not in sanitized:
            sanitized['role'] = 'assistant'
        
        return sanitized
    
    @staticmethod
    def sanitize_gpt_response(response: Dict) -> Dict:
        """Sanitize GPT response"""
        sanitized = response.copy()
        
        if 'choices' not in sanitized or not sanitized['choices']:
            sanitized['choices'] = [{
                'index': 0,
                'message': {'role': 'assistant', 'content': ''},
                'finish_reason': 'stop'
            }]
        
        if 'usage' not in sanitized:
            sanitized['usage'] = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        
        return sanitized
