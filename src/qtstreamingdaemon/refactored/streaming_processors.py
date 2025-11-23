"""
streaming_processors.py - Processor per streaming events.

ITERAZIONE #3: Estratto da streaming_daemon.py
SCOPO: Contenere i processor per ogni agent type

Contiene:
    - ContentBlockPool (memory management per ContentBlock)
    - StreamingProcessor (Claude-specific SSE processing)
    - GptStreamingProcessor (GPT/OpenAI-specific SSE processing)
"""

import json
import copy
import logging
import tiktoken
from collections import deque
from typing import Dict, List, Optional, Any

from streaming_types import (
    ContentBlockType,
    StreamEventType,
    StreamEvent,
    ContentBlock
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT BLOCK POOL - Memory management
# ═══════════════════════════════════════════════════════════════════════════════

class ContentBlockPool:
    """
    Object pool per ContentBlock per ridurre GC pressure durante streaming.
    
    Durante streaming intenso, la creazione continua di ContentBlock objects
    causa GC overhead. Pool permette riuso.
    """
    
    def __init__(self, initial_size: int = 50, max_size: int = 200):
        self.available: deque[ContentBlock] = deque()
        self.max_size = max_size
        self.created_count = 0
        self.reused_count = 0
        
        # Pre-populate pool
        for _ in range(initial_size):
            self.available.append(self._create_new())
    
    def _create_new(self) -> ContentBlock:
        """Create new ContentBlock."""
        self.created_count += 1
        return ContentBlock(
            type=ContentBlockType.TEXT,  # Default, will be reset
            content="",
            index=None
        )
    
    def acquire(self, block_type: ContentBlockType, index: int) -> ContentBlock:
        """
        Acquire ContentBlock from pool (or create new if empty).
        """
        if self.available:
            block = self.available.popleft()
            self.reused_count += 1
        else:
            block = self._create_new()
        
        # Reset state
        block.type = block_type
        block.content = ""
        block.encrypted_data = None
        block.tool_name = None
        block.tool_id = None
        block.tool_input = None
        block.signature = None
        block.index = index
        
        return block
    
    def release(self, block: ContentBlock):
        """
        Release ContentBlock back to pool.
        """
        if len(self.available) < self.max_size:
            # Clear sensitive data before returning to pool
            block.content = ""
            block.encrypted_data = None
            block.tool_input = None
            block.signature = None
            
            self.available.append(block)
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        return {
            'available': len(self.available),
            'created': self.created_count,
            'reused': self.reused_count,
            'reuse_rate': (self.reused_count / max(1, self.created_count)) * 100
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMING PROCESSOR - Claude-specific SSE processing
# ═══════════════════════════════════════════════════════════════════════════════

class StreamingProcessor:
    """
    Streaming processor che usa EventSystem invece di callbacks.
    Gestisce parsing completo eventi SSE e conversione in eventi per GUI.
    """
    
    def __init__(self, event_system, logger=None):
        self.event_system = event_system
        self.logger = logger or logging.getLogger(__name__)
        self.content_blocks: Dict[int, ContentBlock] = {}
        self.blocks_created = 0
        
        # ═══ ADD: Object pool ═══
        self.block_pool = ContentBlockPool(initial_size=20, max_size=100)
        
        self.current_message: Dict[str, Any] = {}
        self.is_complete = False
        self.error_occurred = False
        
    def process_event(self, event: StreamEvent) -> Optional[dict]:
        """Process a single streaming event and emit to EventSystem"""
        try:
            if event.type == StreamEventType.MESSAGE_START:
                self.current_message = event.message or {}
                
            elif event.type == StreamEventType.CONTENT_BLOCK_START:
                return self._handle_block_start(event)
                
            elif event.type == StreamEventType.CONTENT_BLOCK_DELTA:
                return self._handle_block_delta(event)
                
            elif event.type == StreamEventType.CONTENT_BLOCK_STOP:
                return self._handle_block_stop(event)
                
            elif event.type == StreamEventType.MESSAGE_STOP:
                self.is_complete = True
                return self._to_stream_output('stream_finished', None)
                
            elif event.type == StreamEventType.ERROR:
                self.error_occurred = True
                self.logger.error(f"Streaming error: {event.error}")
                
        except Exception as e:
            self.logger.error(f"Error processing stream event: {e}")
            self.error_occurred = True
        
        return None
    
    def _handle_block_start(self, event: StreamEvent) -> None:
        """Handle content block start - USE POOL"""
        block_data = event.content_block or {}
        index = event.index or 0
        block_type_str = block_data.get('type', 'text')
        stream_output = None
        
        try:
            block_type = ContentBlockType(block_type_str)
        except ValueError:
            block_type = ContentBlockType.TEXT
        
        # ═══ USE POOL instead of creating new ═══
        block = self.block_pool.acquire(block_type, index)
        
        if block_type == ContentBlockType.THINKING:
            signature = block_data.get('signature', None)
            block.signature = signature
            if signature:
                self.logger.debug(f"Thinking block {index} started with signature: {signature}")
            stream_output = self._to_stream_output('thinking_start', index, redacted=False)
            
        elif block_type == ContentBlockType.REDACTED_THINKING:
            block.encrypted_data = block_data.get('data', '')
            signature = block_data.get('signature')
            block.signature = signature
            if signature:
                self.logger.debug(f"Thinking block {index} started with signature: {signature}")
            block.signature = None
            stream_output = self._to_stream_output('thinking_start', index, redacted=True)
            
        elif block_type == ContentBlockType.TEXT:
            stream_output = self._to_stream_output('text_start', index)
            
        elif block_type == ContentBlockType.TOOL_USE:
            block.tool_name = block_data.get('name')
            block.tool_id = block_data.get('id')
            block.tool_input = {}
            block.accumulated_json_delta = None
            stream_output = self._to_stream_output('tool_start', index, 
                           tool_name=block_data.get('name', ''),
                           tool_id=block_data.get('id', ''))
        
        self.content_blocks[index] = block
        self.blocks_created += 1
        
        return stream_output

    def _handle_block_delta(self, event: StreamEvent) -> None:
        """
        Handle content block delta.
        
        VERIFIED: Gestione redacted_thinking è corretta.
        """
        index = event.index or 0
        delta = event.delta or {}
        
        if index not in self.content_blocks:
            return
        
        block = self.content_blocks[index]
        delta_type = delta.get('type', '')
        
        if block.type in [ContentBlockType.THINKING, ContentBlockType.REDACTED_THINKING]:
            if delta_type == 'thinking_delta':
                if block.type == ContentBlockType.THINKING:
                    # Normal thinking - accumulate plaintext
                    text_delta = delta.get('thinking', '')
                    block.content += text_delta
                    
                    try:
                        encoding = tiktoken.get_encoding("cl100k_base")
                        token_count = len(encoding.encode(text_delta))
                    except:
                        token_count = len(text_delta) // 4  # Fallback estimate
                    
                    signature = delta.get('signature', None)
                    if signature:
                        self.logger.debug(f"Thinking delta block {index} has signature: {signature}")
                        block.signature = signature
            
                    return self._to_stream_output('thinking_content', index, text=text_delta, token_count=token_count)
                    
                else:  # REDACTED
                    # ↓ VERIFIED: Accumulate in encrypted_data (correct)
                    encrypted_delta = delta.get('data', '')
                    if encrypted_delta:
                        block.encrypted_data = (block.encrypted_data or '') + encrypted_delta
                        self.logger.debug(f"Accumulated encrypted data for redacted block {index}: +{len(encrypted_delta)} bytes")
                    # Don't emit content (è encrypted)
            
            elif delta_type == 'signature_delta':
                # ═══ CRITICAL FIX: Capture signature for continuity ═══
                signature_delta = delta.get('signature', '')
                if signature_delta:
                    # Accumulate signature (può arrivare in chunks)
                    if block.signature is None:
                        block.signature = signature_delta
                    else:
                        block.signature += signature_delta
                    
                    self.logger.debug(f"Signature delta captured for thinking block {index} (+{len(signature_delta)} chars)")
                    
                    # Log when signature complete (euristico - se > 100 chars probabilmente completo)
                    if len(block.signature) > 100:
                        self.logger.info(f"Thinking block {index} signature complete ({len(block.signature)} chars)")
                
        elif block.type == ContentBlockType.TEXT:
            if delta_type == 'text_delta':
                text_delta = delta.get('text', '')
                block.content += text_delta
                
                try:
                    encoding = tiktoken.get_encoding("cl100k_base")
                    token_count = len(encoding.encode(text_delta))
                except:
                    token_count = len(text_delta) // 4  # Fallback estimate
                        
                return self._to_stream_output('text_content', index, text=text_delta, token_count=token_count)
                
        elif block.type == ContentBlockType.TOOL_USE:
            if delta_type == 'input_json_delta':
                partial_json = delta.get('partial_json', '')
                
                if block.accumulated_json_delta is None:
                    block.accumulated_json_delta = partial_json
                else:
                    block.accumulated_json_delta += partial_json
                
                self.logger.debug(f"Tool use delta block 'partial_json' received: {partial_json}")
                    
                try:
                    block.tool_input = json.loads(block.accumulated_json_delta)
                except json.JSONDecodeError:
                    pass
        
                return None
            
                return self._to_stream_output('tool_input_progress', index,
                               tool_id=block.tool_id,
                               partial_input=partial_json)
    
    def _handle_block_stop(self, event: StreamEvent) -> Optional[ContentBlock]:
        """Handle content block stop"""
        index = event.index or 0
        if index not in self.content_blocks:
            return None
        
        block = self.content_blocks[index]
        
        if block.type in [ContentBlockType.THINKING, ContentBlockType.REDACTED_THINKING]:
            return self._to_stream_output('thinking_end', index)
            
        elif block.type == ContentBlockType.TEXT:
            pass  # Text end - no specific event needed
            
        elif block.type == ContentBlockType.TOOL_USE:
            self.logger.info(f"Tool block stop reached. Tool name: {block.tool_name}, tool input: {block.tool_input}")            
            pass  # Evento tool_input in QtStreamingDaemon._finalize_claude_response
        
        return None
    
    def _to_stream_output(self, event_type: str, block_index: Optional[int], **kwargs):
        """Emit event to EventSystem"""
        event_data = {
            'type': event_type,
            'block_index': block_index
        }
        event_data.update(kwargs)

        return event_data 
    
    def get_content_blocks(self) -> List[ContentBlock]:
        """Get all content blocks in order"""
        return [copy.deepcopy(self.content_blocks[i]) for i in sorted(self.content_blocks.keys())]

    def cleanup(self):
        """
        Cleanup and return blocks to pool.
        
        NUOVO METODO - chiamare alla fine del processing.
        """
        for block in self.content_blocks.values():
            self.block_pool.release(block)
        
        self.content_blocks.clear()
        
        # Log pool stats
        stats = self.block_pool.get_stats()
        self.logger.debug(f"Block pool stats: {stats}")


# ═══════════════════════════════════════════════════════════════════════════════
# GPT STREAMING PROCESSOR - GPT/OpenAI-specific SSE processing
# ═══════════════════════════════════════════════════════════════════════════════

class GptStreamingProcessor:
    """
    Streaming processor per GPT/OpenAI.
    
    ARCHITETTURA: Stessa struttura di StreamingProcessor (Claude) per normalizzare
    il processing tra diversi provider.
    
    GPT SSE Events:
        - First chunk: id, model, role='assistant'
        - Content deltas: choices[0].delta.content
        - Tool call deltas: choices[0].delta.tool_calls[index]
        - Finish: choices[0].finish_reason = 'stop' | 'tool_calls'
        - Usage: solo ultimo chunk con stream_options={"include_usage": True}
    """
    
    def __init__(self, event_system, logger=None):
        self.event_system = event_system
        self.logger = logger or logging.getLogger(__name__)
        
        # Content accumulation
        self.content = ""
        self.tool_calls: Dict[int, Dict] = {}  # index -> {id, name, arguments}
        
        # State
        self.message_started = False
        self.is_complete = False
        self.finish_reason = None
        self.error_occurred = False
        
        # Metadata (from first chunk)
        self.message_id = None
        self.model = None
        self.created = None
        self.system_fingerprint = None  # FIXED: aggiunto system_fingerprint
    
    def process_chunk(self, data: Dict) -> Optional[Dict]:
        """
        Process a single GPT SSE chunk and return stream output.
        
        Args:
            data: Parsed JSON from SSE line
            
        Returns:
            Stream output dict or None
        """
        try:
            # Validate chunk type
            if data.get('object') != 'chat.completion.chunk':
                return None
            
            # First chunk - capture metadata
            if not self.message_started:
                self.message_id = data.get('id')
                self.model = data.get('model')
                self.created = data.get('created')
                self.system_fingerprint = data.get('system_fingerprint')  # FIXED: cattura system_fingerprint
                self.message_started = True
                return self._to_stream_output('new_stream', None)
            
            # Process choices
            choices = data.get('choices', [])
            if not choices:
                # Last chunk with usage only (no choices)
                usage = data.get('usage')
                if usage:
                    return self._to_stream_output('usage_update', None, usage=usage)
                return None
            
            choice = choices[0]
            delta = choice.get('delta', {})
            finish_reason = choice.get('finish_reason')
            
            # Content delta
            content_delta = delta.get('content')
            if content_delta:
                self.content += content_delta
                
                try:
                    encoding = tiktoken.get_encoding("cl100k_base")
                    token_count = len(encoding.encode(content_delta))
                except:
                    token_count = len(content_delta) // 4
                
                return self._to_stream_output('text_content', 0, 
                                              text=content_delta, 
                                              token_count=token_count)
            
            # Tool call deltas
            tool_calls_delta = delta.get('tool_calls')
            if tool_calls_delta:
                return self._process_tool_call_delta(tool_calls_delta)
            
            # Finish reason
            if finish_reason:
                self.finish_reason = finish_reason
                self.is_complete = True
                return self._to_stream_output('stream_finished', None, 
                                              finish_reason=finish_reason)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing GPT chunk: {e}")
            self.error_occurred = True
            return None
    
    def _process_tool_call_delta(self, tool_calls_delta: List[Dict]) -> Optional[Dict]:
        """
        Process tool_calls delta from GPT.
        
        GPT tool calls arrivano incrementali:
        - Prima: {index, id, function: {name, arguments: ""}}
        - Poi: {index, function: {arguments: "{"}}
        - Poi: {index, function: {arguments: "param"}}
        - ...
        """
        for tc_delta in tool_calls_delta:
            index = tc_delta.get('index', 0)
            
            # Initialize tool call if new
            if index not in self.tool_calls:
                self.tool_calls[index] = {
                    'id': tc_delta.get('id'),
                    'type': tc_delta.get('type', 'function'),
                    'function': {
                        'name': None,
                        'arguments': ''
                    }
                }
                
                # Emit tool_start
                func = tc_delta.get('function', {})
                if func.get('name'):
                    self.tool_calls[index]['function']['name'] = func['name']
                    return self._to_stream_output('tool_start', index,
                                                  tool_name=func['name'],
                                                  tool_id=tc_delta.get('id', ''))
            
            # Update existing tool call
            tc = self.tool_calls[index]
            
            # Update id if present
            if tc_delta.get('id'):
                tc['id'] = tc_delta['id']
            
            # Update function
            func_delta = tc_delta.get('function', {})
            if func_delta.get('name'):
                tc['function']['name'] = func_delta['name']
            
            # Accumulate arguments
            if func_delta.get('arguments'):
                tc['function']['arguments'] += func_delta['arguments']
        
        return None  # Tool deltas don't emit output until complete
    
    def _to_stream_output(self, event_type: str, block_index: Optional[int], **kwargs) -> Dict:
        """Create stream output dict"""
        event_data = {
            'type': event_type,
            'block_index': block_index
        }
        event_data.update(kwargs)
        return event_data
    
    def get_content(self) -> str:
        """Get accumulated content"""
        return self.content
    
    def get_tool_calls(self) -> List[Dict]:
        """Get completed tool calls"""
        return [self.tool_calls[i] for i in sorted(self.tool_calls.keys())]
    
    def has_tool_calls(self) -> bool:
        """Check if response has tool calls"""
        return len(self.tool_calls) > 0
    
    def update_response(self, standard_response: Dict) -> None:
        """
        Update standard_response with accumulated data.
        Called at end of stream.
        """
        # Update metadata
        if self.message_id:
            standard_response['id'] = self.message_id
        if self.model:
            standard_response['model'] = self.model
        if self.created:
            standard_response['created'] = self.created
        if self.system_fingerprint:  # FIXED: aggiunto system_fingerprint
            standard_response['system_fingerprint'] = self.system_fingerprint
        
        # Update content
        if standard_response.get('choices'):
            standard_response['choices'][0]['message']['content'] = self.content
            standard_response['choices'][0]['finish_reason'] = self.finish_reason or 'stop'
            
            # Add tool calls if present
            if self.tool_calls:
                standard_response['choices'][0]['message']['tool_calls'] = self.get_tool_calls()
    
    def cleanup(self):
        """Cleanup processor state"""
        self.content = ""
        self.tool_calls.clear()
        self.message_started = False
        self.is_complete = False
