import threading
import asyncio
import aiohttp
import json
import time
import uuid
import queue
import gc
import tiktoken
import traceback
import logging
import copy
import re
import html
import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Optional, Callable, Iterator, Any, Union
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum

from datetime import datetime, timedelta
import cProfile
import pstats
from io import StringIO
from bs4 import BeautifulSoup


from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QApplication,
                           QLabel, QPushButton, QFrame, QSplitter, QProgressBar, QCheckBox, QSlider)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QPalette

from advanced_tool_executors import ToolRegistry
from fake_streaming_response import FakeStreamingResponse
import models_config

# ============================================================================
# DATACLASSES E ENUMS - Base robusta per typing
# ============================================================================

class ContentBlockType(Enum):
    """Content block types from Anthropic API"""
    TEXT = "text"
    THINKING = "thinking"
    REDACTED_THINKING = "redacted_thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"

class StreamEventType(Enum):
    """Streaming event types"""
    MESSAGE_START = "message_start"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    CONTENT_BLOCK_STOP = "content_block_stop"
    PING = "ping"
    ERROR = "error"

@dataclass
class StreamEvent:
    """Represents a streaming event"""
    type: StreamEventType
    data: Dict[str, Any] = field(default_factory=dict)
    index: Optional[int] = None
    delta: Optional[Dict[str, Any]] = None
    content_block: Optional[Dict[str, Any]] = None
    message: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

@dataclass
class ContentBlock:
    """Represents a content block in the conversation"""
    type: ContentBlockType
    content: str = ""  # For TEXT, THINKING (plaintext)
    encrypted_data: Optional[str] = None  # For REDACTED_THINKING (base64)
    tool_name: Optional[str] = None
    tool_id: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None
    index: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-compatible dictionary"""
        result = {"type": self.type.value}
        
        if self.type == ContentBlockType.TEXT:
            result["text"] = self.content
            
        elif self.type == ContentBlockType.THINKING:
            result["thinking"] = self.content  # ← Plaintext
            if self.signature:
                result["signature"] = self.signature
                
        elif self.type == ContentBlockType.REDACTED_THINKING:
            # ↓ FIXED: Use encrypted_data field
            result["data"] = self.encrypted_data if self.encrypted_data else ""
            if self.signature:
                result["signature"] = self.signature
                
        elif self.type == ContentBlockType.TOOL_USE:
            result["name"] = self.tool_name
            result["id"] = self.tool_id
            result["input"] = self.tool_input or {}
            
        elif self.type == ContentBlockType.TOOL_RESULT:
            result["tool_use_id"] = self.tool_id
            result["content"] = self.content
        
        return result


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
    

class StreamingState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class StreamingRequest:
    request_id: str
    payload: Dict
    progress_callback: Optional[Callable]
    state: StreamingState = StreamingState.PENDING
    result: Optional[Dict] = None
    error: Optional[Exception] = None
    progress: float = 0.0
    chunks_processed: int = 0
    thinking_mode: bool = False

@dataclass
class StructuredError:
    """Struttura errore con context completo"""
    timestamp: float
    component: str
    error_type: str
    error_message: str
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'component': self.component,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'context': self.context,
            'stack_trace': self.stack_trace
        }
    
    def __str__(self) -> str:
        return (f"[{self.component}] {self.error_type}: {self.error_message}\n"
                f"Context: {json.dumps(self.context, indent=2)}")

@dataclass
class StreamingConfig:
    """Centralized configuration per streaming"""
    # Thinking tool
    max_think_calls: int = 8
    think_token_budget_per_call: int = 20000
    total_think_budget: int = 100000
    
    # Performance
    chunk_batch_size: int = 1
    memory_cleanup_interval: int = 50
    gui_update_interval: int = 10
    abort_check_interval: int = 10
    metrics_update_interval: int = 50
    
    # Retry logic
    max_retries: int = 3
    base_retry_delay: float = 1.0
    retry_backoff_multiplier: float = 2.0
    
    # Timeouts
    connection_timeout: int = 30
    read_timeout: int = 300
    stale_connection_timeout: int = 60
    
    # Error analysis thresholds
    substantial_data_threshold: int = 1000  # bytes
    reasonable_duration_threshold: float = 5.0  # seconds
    min_chunks_normal_end: int = 10
    
    # Compression
    compression_safety_buffer: int = 2000  # tokens
    compression_preserve_recent: int = 3  # messages
    
    # Cache
    search_cache_ttl: int = 3600  # seconds
    
    # Analysis thresholds
    thinking_depth_shallow_max: int = 800  # chars
    thinking_depth_deep_min: int = 2000    # chars
    
    # Compression thresholds
    compression_sentence_threshold: int = 3
    compression_complexity_high: int = 3
    compression_complexity_medium: int = 2
    compression_text_length_threshold: int = 2000
        
    def to_dict(self) -> Dict:
        """Export config as dict"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

@dataclass
class StreamingMetrics:
    """Metrics per monitoring performance/health"""
    # Counters
    requests_total: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    requests_cancelled: int = 0
    
    # Timing
    total_time: float = 0.0
    avg_time_per_request: float = 0.0
    
    # Tokens
    total_tokens_processed: int = 0
    total_thinking_tokens: int = 0
    total_output_tokens: int = 0
    
    # Think tool specific
    think_calls_total: int = 0
    think_sessions_total: int = 0
    avg_think_calls_per_session: float = 0.0
    
    # Errors
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    retry_count_total: int = 0
    
    # Performance
    avg_tokens_per_second: float = 0.0
    peak_tokens_per_second: float = 0.0
    
    def update_request_complete(self, duration: float, tokens: int, 
                               think_calls: int, success: bool):
        """Update metrics dopo request"""
        self.requests_total += 1
        
        if success:
            self.requests_successful += 1
        else:
            self.requests_failed += 1
        
        self.total_time += duration
        self.avg_time_per_request = self.total_time / self.requests_total
        
        self.total_tokens_processed += tokens
        
        if think_calls > 0:
            self.think_calls_total += think_calls
            self.think_sessions_total += 1
            self.avg_think_calls_per_session = self.think_calls_total / self.think_sessions_total
        
        # Token/sec
        tps = tokens / duration if duration > 0 else 0
        self.avg_tokens_per_second = self.total_tokens_processed / self.total_time
        self.peak_tokens_per_second = max(self.peak_tokens_per_second, tps)
    
    def record_error(self, error_type: str):
        """Record error type"""
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
    
    def get_summary(self) -> str:
        """Human-readable summary"""
        success_rate = (self.requests_successful / self.requests_total * 100) if self.requests_total > 0 else 0
        
        return f"""
═══════════════════════════════════════════════════
STREAMING METRICS SUMMARY
═══════════════════════════════════════════════════
Requests: {self.requests_total} total ({self.requests_successful} ✓, {self.requests_failed} ✗, {self.requests_cancelled} ⊗)
Success Rate: {success_rate:.1f}%
Avg Time/Request: {self.avg_time_per_request:.2f}s
Tokens Processed: {self.total_tokens_processed:,}
Avg Speed: {self.avg_tokens_per_second:.1f} tok/s (Peak: {self.peak_tokens_per_second:.1f})
Think Tool: {self.think_calls_total} calls in {self.think_sessions_total} sessions (avg {self.avg_think_calls_per_session:.1f}/session)
Retries: {self.retry_count_total}
Errors by Type: {dict(sorted(self.errors_by_type.items(), key=lambda x: x[1], reverse=True))}
═══════════════════════════════════════════════════
        """

@dataclass
class DetailedProgress:
    """Progress information ricca per UI"""
    request_id: str
    overall_progress: float  # 0-100
    phase: str  # 'connecting', 'streaming', 'processing', 'complete'
    
    # Streaming specifics
    blocks_completed: int = 0
    blocks_total_estimated: int = 0
    current_block_type: Optional[str] = None
    current_block_index: Optional[int] = None
    
    # Performance
    tokens_processed: int = 0
    tokens_per_second: float = 0.0
    time_elapsed: float = 0.0
    time_estimated_remaining: float = 0.0
    
    # Think tool specifics
    think_calls_completed: int = 0
    current_think_depth: str = 'unknown'  # 'shallow', 'moderate', 'deep'
    
    def to_dict(self) -> Dict:
        return self.__dict__.copy()


class ResponseValidator:
    """Valida response per consistency/completeness"""
    
    @staticmethod
    def validate_claude_response(response: Dict) -> tuple[bool, List[str]]:
        """
        Valida risposta Claude per issues.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        if 'id' not in response or not response['id']:
            issues.append("Missing response ID")
        
        if 'content' not in response:
            issues.append("Missing content field")
        elif not isinstance(response['content'], list):
            issues.append("Content is not list")
        elif len(response['content']) == 0:
            issues.append("Content is empty")
        
        # Check content blocks
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
        
        # Check usage
        if 'usage' in response:
            usage = response['usage']
            if usage.get('output_tokens', 0) == 0 and len(response.get('content', [])) > 0:
                issues.append("Has content but 0 output tokens (suspicious)")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    @staticmethod
    def sanitize_response(response: Dict) -> Dict:
        """Sanitize response rimuovendo/fixing problemi"""
        sanitized = response.copy()
        
        # Remove None blocks
        if 'content' in sanitized and isinstance(sanitized['content'], list):
            sanitized['content'] = [b for b in sanitized['content'] if b is not None]
        
        # Ensure usage exists
        if 'usage' not in sanitized:
            sanitized['usage'] = {
                'input_tokens': 0,
                'output_tokens': 0
            }
        
        # Ensure required fields
        if 'type' not in sanitized:
            sanitized['type'] = 'message'
        if 'role' not in sanitized:
            sanitized['role'] = 'assistant'
        
        return sanitized


class PerformanceProfiler:
    """Profiler per identificare bottlenecks"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.profiler = None
        self.profiles = []
    
    def start_profiling(self, label: str = ""):
        """Start profiling session"""
        if not self.enabled:
            return
        
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.current_label = label
    
    def stop_profiling(self) -> Optional[str]:
        """Stop e return risultati"""
        if not self.enabled or not self.profiler:
            return None
        
        self.profiler.disable()
        
        # Generate stats
        s = StringIO()
        stats = pstats.Stats(self.profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20
        
        result = s.getvalue()
        
        # Store
        self.profiles.append({
            'label': self.current_label,
            'timestamp': time.time(),
            'stats': result
        })
        
        return result
    
    def get_bottlenecks(self) -> List[str]:
        """Analizza profiles per bottlenecks comuni"""
        # Simple analysis - potrebbe essere più sofisticata
        bottlenecks = []
        
        for profile in self.profiles[-5:]:  # Last 5
            stats_text = profile['stats']
            
            # Parse per function names con high cumtime
            # (Questo è simplified - proper parsing requirerebbe più lavoro)
            if '_format_content' in stats_text:
                bottlenecks.append("Formatting content")
            if 'insertHtml' in stats_text:
                bottlenecks.append("HTML insertion")
            if 'json.loads' in stats_text:
                bottlenecks.append("JSON parsing")
        
        # Return unique
        return list(set(bottlenecks))
    

class CircuitBreaker:
    """Circuit breaker pattern per prevenire retry loops"""
    
    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout)
        self.failures = defaultdict(list)  # endpoint → [timestamps]
        self.state = {}  # endpoint → 'closed'|'open'|'half_open'
    
    def record_failure(self, endpoint: str):
        """Record failure per endpoint"""
        now = datetime.now()
        # Clean old failures
        self.failures[endpoint] = [
            ts for ts in self.failures[endpoint]
            if now - ts < self.timeout
        ]
        # Add new failure
        self.failures[endpoint].append(now)
        
        # Check threshold
        if len(self.failures[endpoint]) >= self.failure_threshold:
            self.state[endpoint] = 'open'
            logging.warning(f"Circuit breaker OPENED for {endpoint}")
    
    def record_success(self, endpoint: str):
        """Record success - reset failures"""
        self.failures[endpoint] = []
        if self.state.get(endpoint) == 'half_open':
            self.state[endpoint] = 'closed'
            logging.info(f"Circuit breaker CLOSED for {endpoint}")
    
    def can_attempt(self, endpoint: str) -> tuple[bool, str]:
        """Check se può tentare request"""
        state = self.state.get(endpoint, 'closed')
        
        if state == 'closed':
            return True, "Circuit closed - OK to proceed"
        
        elif state == 'open':
            # Check se timeout passato
            if self.failures[endpoint]:
                oldest_failure = min(self.failures[endpoint])
                if datetime.now() - oldest_failure > self.timeout:
                    # Transition to half-open
                    self.state[endpoint] = 'half_open'
                    logging.info(f"Circuit breaker HALF-OPEN for {endpoint} (testing)")
                    return True, "Circuit half-open - testing connection"
                else:
                    time_remaining = (self.timeout - (datetime.now() - oldest_failure)).seconds
                    return False, f"Circuit open - {time_remaining}s until retry allowed"
            return False, "Circuit open - no retry allowed"
        
        else:  # half_open
            return True, "Circuit half-open - testing"
        





# ============================================================================
# STREAMING PROCESSOR - Riscritta per EventSystem
# ============================================================================

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


# ============================================================================
# QT STREAMING DAEMON - Enhanced COMPLETO
# ============================================================================

class QtStreamingDaemon:
    """
    Enhanced streaming daemon COMPLETO con:
    - Parsing SSE corretto (iter_lines)
    - Intelligent error handling per InvalidChunkLength
    - StreamingProcessor integrato con EventSystem
    - WebSearchTool integrato
    - Gestione multi-call think tool
    - Supporto API multiple (Claude/GPT)
    - Payload compression intelligente
    - Sistema abort funzionante
    """
    
    def __init__(self, event_system, logger=None, config: StreamingConfig = None):
        """CORRECTED: Daemon is BLIND on tools - Registry manages ALL"""
        self.event_system = event_system
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or StreamingConfig()
        
        self.daemon_thread = None
        self.request_queue = queue.Queue()
        self.active_requests = {}
        self.running = False
        
        self.original_payload = None
        self.original_task_summary = ""
        
        # Multi-call tracking
        self.is_multi_call_session = False
        self.current_request = None
        self.current_content_blocks = None
        self.accumulated_content_blocks = []
        self.accumulated_tokens = 0
        self.call_count = 0
  
        # ═══ TOOL REGISTRY - CENTRAL MANAGER ═══
        self.tool_registry = ToolRegistry(self.event_system, self.logger)
        
        # NEW: Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=60
        )
        
        # NEW: Performance profiler
        self.profiler = PerformanceProfiler(enabled=False)  # Disabled di default

        # Metrics & tracking
        self.metrics = StreamingMetrics()
        self.error_history = deque(maxlen=50)
        self.abort_flags = {}
        
        # Stats
        self.stats = {
            'requests_processed': 0,
            'total_chunks': 0,
            'memory_cleanups': 0,
            'gui_updates': 0,
            'multiblock_sequences': 0
        }
        
        # Config shortcuts
        self.chunk_batch_size = self.config.chunk_batch_size
        self.memory_cleanup_interval = self.config.memory_cleanup_interval
        self.gui_update_interval = self.config.gui_update_interval
        self.max_think_calls = self.config.max_think_calls
        self.total_think_budget = self.config.total_think_budget
        
        # ═══ STEP-BY-STEP MODE ═══
        self.step_by_step_mode = False
        # Pause/resume state
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # Non paused by default
        
        # Subscribe eventi
        self.event_system.subscribe('step_forward', self._on_step_forward)
        self.event_system.subscribe('toggle_step_mode', self._on_toggle_step_mode)
        self.event_system.subscribe('modify_payload', self._on_modify_payload) 
        self.event_system.subscribe('modify_tool_result', self._on_modify_tool_result) 
        self.event_system.subscribe('reexecute_tool', self._on_reexecute_tool)
        self.event_system.subscribe('stream_pause', self._on_stream_pause)
        self.event_system.subscribe('stream_resume', self._on_stream_resume)
        self.event_system.subscribe('session_replay', self._on_session_replay)

        self.event_system.subscribe('stream_request', self._handle_stream_request)
        self.event_system.subscribe('stream_cancel', self._handle_stream_cancel)
        
        # ═══ SIMULATION MODE (per testing) ═══
        self.simulation_mode = False  # Set True per usare fake streaming
        self.simulation_config = None
        self.fake_response = None
        self.event_system.subscribe('toggle_simulation_mode', self._on_toggle_simulation_mode)
    
    # ═══════════════════════════════════════════════════════════
    # TOOL CONFIGURATION METHODS (Delegate to Registry)
    # ═══════════════════════════════════════════════════════════
    
    def enable_tool(self, tool_name: str):
        """Enable tool via registry"""
        self.tool_registry.enable_tool(tool_name)
    
    def disable_tool(self, tool_name: str):
        """Disable tool via registry"""
        self.tool_registry.disable_tool(tool_name)
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if tool enabled"""
        return self.tool_registry.is_tool_enabled(tool_name)
    
    def get_enabled_tools(self) -> List[str]:
        """Get enabled tools"""
        return self.tool_registry.get_tool_names(enabled_only=True)
    
    def get_all_tools(self) -> List[str]:
        """Get all tools"""
        return self.tool_registry.get_tool_names(enabled_only=False)
        
    def start_daemon(self):
        if self.daemon_thread and self.daemon_thread.is_alive():
            return
        
        self.running = True
        self.daemon_thread = threading.Thread(target=self._daemon_worker, daemon=True)
        self.daemon_thread.start()
        self.logger.info("QtStreamingDaemon started (enhanced)")
        
    def stop_daemon(self):
        self.running = False
        if self.daemon_thread:
            self.request_queue.put(None)
            self.daemon_thread.join(timeout=5)
        self.logger.info("QtStreamingDaemon stopped")
    
    def _handle_stream_request(self, data):
        request = StreamingRequest(
            request_id=data['request_id'],
            payload=data['payload'],
            progress_callback=data.get('progress_callback')
        )
        self.active_requests[request.request_id] = request
        self.request_queue.put(request)
        
    def _handle_stream_cancel(self, data):
        request_id = data['request_id']
        if request_id in self.active_requests:
            self.active_requests[request_id].state = StreamingState.CANCELLED
            self.logger.info(f"Request {request_id} cancelled")
            
    def _daemon_worker(self):
        self.logger.info("QtStreamingDaemon worker started (enhanced)")
        
        while self.running:
            try:
                request = self.request_queue.get(timeout=1.0)
                if request is None:
                    break
                
                if request.state == StreamingState.CANCELLED:
                    continue
                
                self._process_streaming_request(request)
                self.stats['requests_processed'] += 1
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Daemon worker error: {e}")

    def _on_step_forward(self, data):
        """Handle step forward from UI"""
        
        self.logger.info(f"Stepping forward (call {self.call_count})...")
        
        try:
            
            # Simply execute current request
            result = self._execute_streaming_with_retry(self.current_request)
            
            if not self.is_multi_call_session:
                
                # Success metrics
                duration = time.time() - self.start_time
                tokens = result.get('usage', {}).get('output_tokens', 0)
                self.metrics.update_request_complete(
                    duration=duration,
                    tokens=tokens,
                    think_calls=self.call_count,
                    success=True
                )
                
                self.request.result = result
                self.request.state = StreamingState.COMPLETED
                self.request.progress = 100.0
                
                self._emit_progress(self.request, phase='complete')

            return result 
            
        except Exception as e:
            # Error metrics & logging
            duration = time.time() - self.start_time
            self.metrics.update_request_complete(
                duration=duration,
                tokens=0,
                think_calls=self.call_count,
                success=False
            )
            
            self._log_structured_error(
                component='streaming_request',
                error=e,
                context={
                    'request_id': self.request.request_id,
                    'duration': duration,
                    'call_count': self.call_count
                }
            )
            
            self.request.error = e
            self.request.state = StreamingState.FAILED
              
            self._emit_progress(self.request, phase='failed')

    def _on_modify_payload(self, data):
        """
        Modifica payload - SOLO sostituzione.
        
        Acknowledge: Solo messaggio conferma.
        """
        if not self.current_request:
            self.logger.warning("modify_payload received but no current_request")
            return
        
        modified_payload = data.get('payload')
        if not modified_payload:
            self.logger.warning("modify_payload received but no payload")
            return
        
        self.logger.info("Applying modified payload")
        
        # ═══ REPLACE PAYLOAD ═══
        self.current_request.payload = modified_payload
        
        # ═══ EMIT ACKNOWLEDGE (solo messaggio) ═══
        self._emit_interleaved_info(
            message="Payload updated",
            call_number=self.call_count,
            request_type="acknowledge",
            action="modify_payload"
        )
        
        self.logger.info("Payload modified")

    def _on_modify_tool_result(self, data):
        """
        Modifica tool result - REBUILD continuation (no execution).
        
        Acknowledge: Messaggio + nuovo continuation_payload.
        """
        if not self.current_content_blocks:
            self.logger.warning("modify_tool_result received but no current_content_blocks")
            return
        
        modified_result = data.get('result')
        if modified_result is None:
            self.logger.warning("modify_tool_result received but no result")
            return
        
        self.logger.info("Rebuilding continuation with modified tool result")
        
        # ═══ FIND TOOL CALL ═══
        tool_call = None
        for block in self.current_content_blocks:
            if block.type == ContentBlockType.TOOL_USE:
                tool_call = block
                break
        
        if not tool_call:
            self.logger.error("No tool call found in content blocks")
            return
        
        # ═══ EMIT UPDATED TOOL RESULT EVENT ═══
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': 'tool_result',
                'block_index': tool_call.index,
                'tool_name': tool_call.tool_name,
                'tool_result': modified_result
            }]
        })
        
        # ═══ REBUILD CONTINUATION (SOLO BUILD, NO EXECUTE) ═══
        continue_payload = self._build_continue_payload_with_results(
            self.original_payload,
            self.current_content_blocks,
            tool_call,
            modified_result
        )
        
        # ═══ UPDATE REQUEST ═══
        self.current_request.payload = continue_payload
        
        # ═══ EMIT ACKNOWLEDGE (messaggio + payload) ═══
        self._emit_interleaved_info(
            message="Tool result modified and payload rebuilt",
            call_number=self.call_count,
            request_type="acknowledge",
            action="modify_tool_result",
            continuation_payload=continue_payload,
            messages_count=len(continue_payload.get('messages', [])),
            payload_size_estimate=len(json.dumps(continue_payload))
        )
        
        self.logger.info("✓ Continuation rebuilt with modified result")

    def _on_reexecute_tool(self, data):
        """
        Re-execute tool - EXECUTE + REBUILD.
        
        Acknowledge: Messaggio + tool_result + continuation_payload.
        """
        if not self.current_content_blocks:
            self.logger.warning("reexecute_tool received but no current_content_blocks")
            return
        
        tool_name = data.get('tool_name')
        modified_input = data.get('tool_input')
        
        if not tool_name or not modified_input:
            self.logger.warning("reexecute_tool received but missing data")
            return
        
        self.logger.info(f"Re-executing tool: {tool_name}")
        
        # ═══ FIND TOOL CALL ═══
        tool_call = None
        for block in self.current_content_blocks:
            if block.type == ContentBlockType.TOOL_USE and block.tool_name == tool_name:
                tool_call = block
                break
        
        if not tool_call:
            self.logger.error(f"Tool call {tool_name} not found")
            return
        
        # ═══ UPDATE TOOL INPUT ═══
        tool_call.tool_input = modified_input
        
        # ═══ EMIT UPDATED TOOL INPUT EVENT ═══
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': 'tool_input',
                'block_index': tool_call.index,
                'tool_name': tool_name,
                'tool_input': modified_input
            }]
        })
        
        # ═══ RE-EXECUTE AND REBUILD ═══
        tool_result, execution_success, continue_payload = self._execute_tool_and_build_continuation(
            tool_call,
            self.current_content_blocks,
            replace_last=True
        )
        
        # ═══ UPDATE REQUEST ═══
        # updated in _execute_tool_and_build_continuation
        
        # ═══ EMIT ACKNOWLEDGE (messaggio + result + payload) ═══
        self._emit_interleaved_info(
            message="Tool re-executed with modified input",
            call_number=self.call_count,
            request_type="acknowledge",
            action="reexecute_tool",
            tool_name=tool_name,
            tool_result=tool_result,
            continuation_payload=continue_payload,
            tool_execution_success=execution_success,
            messages_count=len(continue_payload.get('messages', [])),
            payload_size_estimate=len(json.dumps(continue_payload))
        )
        
        self.logger.info("Tool re-executed and payload updated")
    
    def _on_toggle_step_mode(self, data):
        """Handle step mode toggle from UI"""
        enabled = data.get('enabled', False)
        self.step_by_step_mode = enabled
        self.logger.info(f"Step-by-step mode: {'ENABLED' if enabled else 'DISABLED'}")

    def _on_toggle_simulation_mode(self, data):
        """
        Handle simulation mode toggle from UI.
        
        Se enabled, genera fake request e la processa.
        """
        enabled = data.get('enabled', False)
        self.simulation_mode = enabled
        
        self.logger.info(f"Simulation mode: {'ENABLED' if enabled else 'DISABLED'}")
        
        if enabled:
            # Config default: thinking + text (no tool yet, viene settato in _check_thinking_mode)
            self.simulation_config = {
                'include_text': True,
                'include_tool': False,
                'tool_name': None,
                'tool_input': None,
                'timing': 'fast'
            }
            
            # Genera fake request minimale
            fake_payload = {
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
            
            # Invia fake request
            self._handle_stream_request({
                'request_id': None, # fake 
                'payload': fake_payload,
                'progress_callback': None
            })
        else:
            # Reset config
            self.simulation_config = None    

    def _on_stream_pause(self, data):
        """Handle stream pause request"""
        request_id = data.get('request_id')
        
        if request_id in self.active_requests:
            
            # Set pause flag 
            self.is_paused = True
            self.pause_event.clear()
            
            # Log 
            self.logger.info(f"Pause requested for {request_id}")
            
            # Emit acknowledge
            self.event_system.emit_event('stream_output_batch', {
                'outputs': [{
                    'type': 'stream_paused_ack',
                    'paused': True,
                    'at_block': self.current_content_blocks[0].index if self.current_content_blocks else 0
                }]
            })
    
    def _on_stream_resume(self, data):
        """Handle stream resume request"""
        request_id = data.get('request_id')
        
        if request_id in self.active_requests:
            
            # Clear pause flag 
            self.is_paused = False
            self.pause_event.set()
            
            # Log 
            self.logger.info(f"Resume requested for {request_id}")
            
            # Emit acknowledge
            self.event_system.emit_event('stream_output_batch', {
                'outputs': [{
                    'type': 'stream_resumed_ack',
                    'resumed': True
                }]
            })
    
    def _on_session_replay(self, data):
        """Handle session replay request"""
        session_data = data.get('session_data')
        
        if not session_data:
            self.logger.warning("Session replay requested but no data")
            return
        
        self.logger.info(f"Session replay requested with {len(session_data.get('call_history', []))} calls")
        
        # TODO: Implement replay logic
        # For now, just acknowledge
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': 'interleaved_info',
                'message': 'Session replay not yet implemented',
                'call_number': 0,
                'request_type': 'acknowledge'
            }]
        })
                
    def _handle_stream_cancel(self, data):
        """Enhanced cancel con immediate flag"""
        request_id = data['request_id']
        
        # Set abort flag IMMEDIATELY
        self.abort_flags[request_id] = True
        
        if request_id in self.active_requests:
            self.active_requests[request_id].state = StreamingState.CANCELLED
            self.logger.info(f"Request {request_id} marked for cancellation")
    
    def _is_aborted(self, request_id: str) -> bool:
        """Check se request aborted"""
        return self.abort_flags.get(request_id, False)
    
    def _process_streaming_request(self, request: StreamingRequest):
        """MODIFIED: Add metrics tracking & error logging"""
        self.profiler.start_profiling(f"request_{request.request_id}")
        self.start_time = time.time()
        
        request.start_time = self.start_time  # Track start
        request.state = StreamingState.ACTIVE
        request.first_call = True
        
        # Check thinking mode
        thinking_enabled = self._check_thinking_mode(request.payload)
        request.thinking_mode = thinking_enabled
        
        self.headers = request.payload.pop("headers")
        self.request = request
        self.original_payload = copy.deepcopy(request.payload)
        
        payload = request.payload.copy()
        
        # Determina provider
        self.is_claude = 'CLAUDE' in str(models_config.SELECTED_CONF)
        
        self.api_url = models_config.MODELS_CONF[models_config.SELECTED_CONF]['api_url']
        
        # ═══ STEP CHECK ═══
        if self.step_by_step_mode:
            
            # ═══ EMIT DEBUG INFO - COMPLETO ═══
            self._emit_interleaved_info(
                message="Ready to perform initial streaming request",
                call_number=0,
                request_type="initial",
                thinking_enabled=thinking_enabled,
                tools_attached=[tool['name'] for tool in payload.get('tools', [])],
                headers=self.headers,
                initial_payload=payload,  # PAYLOAD COMPLETO
                messages_count=len(payload.get('messages', [])),
                payload_size_estimate=len(json.dumps(payload))
            )
            
            self.logger.info("Step-by-step mode: Pausing before initial request")
            
            self.current_request = self.request 
            return None

        # Streaming con retry
        return self._on_step_forward(None)
            
    def _execute_streaming_with_retry(self, request: StreamingRequest):
        """Execute streaming con retry logic robusto"""
        payload = request.payload.copy()
        max_tokens = payload.get('max_tokens', 4096)
        headers = self.headers 
        is_claude = self.is_claude
        api_url = self.api_url
        
        # Check circuit breaker PRIMA di tentare
        can_attempt, reason = self.circuit_breaker.can_attempt(api_url)
        if not can_attempt:
            self.logger.error(f"Circuit breaker prevents attempt: {reason}")
            return self._create_error_response(
                self._init_claude_response() if 'CLAUDE' in str(models_config.SELECTED_CONF) else self._init_gpt_response(),
                f"Service temporarily unavailable: {reason}"
            )
        
        # Inizializza risposta
        standard_response = self._init_claude_response() if self.is_claude else self._init_gpt_response()
        
        # Retry logic
        max_retries = 3

        # ═══ SIMULATION MODE ═══
        if self.simulation_mode:
            self.logger.info("Using SIMULATION mode (no real API call)")
            response = self.fake_response
            response._init_turn()
            result = self._process_claude_stream_with_error_handling(
                response, request, standard_response, max_tokens, 0
            )
            return result['response']
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                session.headers.update(headers)
                
                self.logger.info(f"Attempt {attempt + 1}/{max_retries} - Starting streaming")
                
                with session.post(api_url, json=payload, stream=True, timeout=(30, 300)) as response:
                    if response.status_code != 200:
                        raise Exception(f"API Error {response.status_code}: {response.text}")
                    
                    # Process stream con intelligent error handling
                    if is_claude:
                        result = self._process_claude_stream_with_error_handling(
                            response, request, standard_response, max_tokens, attempt
                        )
                    else:
                        result = self._process_gpt_stream_with_error_handling(
                            response, request, standard_response, max_tokens, attempt
                        )
                    
                    if result['success']:
                        self.circuit_breaker.record_success(api_url)
                        return result['response']
                    
                    if result.get('partial') and result.get('should_retry'):
                        raise Exception("Partial data - retry")
                    
                    return result['response']
                    
            except Exception as e:
                # ↓ USE CLASSIFICATION
                should_retry, wait_time = self._classify_error_for_retry(e, attempt)
                
                if not should_retry:
                    self.logger.error(f"Non-retryable error: {e}")
                    self.circuit_breaker.record_failure(api_url)
                    raise
                
                if attempt < max_retries - 1:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e} - Waiting {wait_time}s before retry")
                    self.circuit_breaker.record_failure(api_url)
                    self.metrics.retry_count_total += 1
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries} attempts failed")
                    self.circuit_breaker.record_failure(api_url)
                    raise
        
        return self._create_error_response(standard_response, "All retries exhausted")

    def _classify_error_for_retry(self, error: Exception, attempt: int) -> tuple[bool, float]:
        """
        Classify error and determine retry strategy.
        
        ENHANCED: Più granularità per network vs payload errors.
        
        Returns:
            (should_retry, wait_time)
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        base_delay = self.config.base_retry_delay
        
        # ═══ AUTH ERRORS - No retry ═══
        if any(x in error_str for x in ['unauthorized', '401', 'invalid api key', 'authentication']):
            self.logger.error(f"Authentication error - no retry")
            return False, 0
        
        # ═══ PAYLOAD/VALIDATION ERRORS - No retry ═══
        # These are user errors, not transient issues
        if any(x in error_str for x in [
            '400', 'bad request', 'invalid request', 'validation error',
            'missing required', 'expected thinking', 'invalid message format'
        ]):
            self.logger.error(f"Payload validation error - no retry (fix payload)")
            return False, 0
        
        # ═══ RATE LIMIT - Longer backoff ═══
        if any(x in error_str for x in ['429', 'rate limit', 'too many requests']):
            wait = base_delay * (4 ** attempt)  # Aggressive backoff
            self.logger.warning(f"Rate limit hit - retry in {wait}s")
            return True, wait
        
        # ═══ SERVER ERROR - Standard retry ═══
        if any(x in error_str for x in ['500', '502', '503', '504', 'internal server error', 'bad gateway', 'gateway timeout']):
            wait = base_delay * (2 ** attempt)
            self.logger.warning(f"Server error - retry in {wait}s")
            return True, wait
        
        # ═══ TIMEOUT - Retry with increased timeout ═══
        if any(x in error_str for x in ['timeout', 'timed out', 'read timeout']):
            wait = base_delay * (1.5 ** attempt)
            self.logger.warning(f"Timeout - retry in {wait}s")
            return True, wait
        
        # ═══ DNS/NETWORK ERRORS - Quick retry ═══
        if any(x in error_str for x in ['dns', 'name resolution', 'connection refused', 'network unreachable']):
            wait = base_delay * (1.5 ** attempt)
            self.logger.warning(f"Network error - retry in {wait}s")
            return True, wait
        
        # ═══ CONNECTION ERROR - Standard retry ═══
        if isinstance(error, (ConnectionError, ChunkedEncodingError)):
            wait = base_delay * (2 ** attempt)
            self.logger.warning(f"Connection error ({error_type}) - retry in {wait}s")
            return True, wait
        
        # ═══ INVALID CHUNK LENGTH - Quick retry (transient) ═══
        if 'invalidchunklength' in error_str:
            wait = 0.5  # Quick retry
            self.logger.warning(f"Invalid chunk length - quick retry")
            return True, wait
        
        # ═══ JSON DECODE ERROR - Likely transient SSE issue ═══
        if 'json' in error_str and 'decode' in error_str:
            wait = base_delay
            self.logger.warning(f"JSON decode error - retry in {wait}s")
            return True, wait
        
        # ═══ UNKNOWN - Conservative retry ═══
        wait = base_delay * (2 ** attempt)
        self.logger.warning(f"Unknown error type ({error_type}) - conservative retry in {wait}s")
        return True, wait
    
    def _process_claude_stream_with_error_handling(self, response, request: StreamingRequest,
                                                    standard_response: Dict, max_tokens: int,
                                                    attempt: int) -> Dict:
        """MODIFIED: Use return value da finalize se presente"""
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
                if self.is_paused:
                    self.pause_event.wait()  # Block until resumed
                
                # Immediate abort check
                if chunks_processed % self.config.abort_check_interval == 0:
                    if self._is_aborted(request.request_id):
                        self.logger.info(f"Stream {request.request_id} aborted mid-processing")
                        
                        # Add abortion notice
                        if standard_response.get('content'):
                            for block in standard_response['content']:
                                if block and block.get('type') == 'text':
                                    block['text'] = (block.get('text', '') + 
                                                   "\n\n[⛔ Stream aborted by user]")
                                    break
                        
                        # Finalize e return
                        final_response = self._finalize_claude_response(standard_response, processor)
                        request.state = StreamingState.CANCELLED
                        return {
                            'success': True,
                            'partial': True,
                            'aborted': True,
                            'response': final_response 
                        }
                
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
                        event = self._parse_claude_event(data)
                        stream_output = processor.process_event(event)
                        if stream_output:
                            stream_outputs_batch.append(stream_output)
                            self.logger.info(f"Stream_output generated: {stream_output}. New outputs batch size: {len(stream_outputs_batch)}. Target flush size: {self.chunk_batch_size} ")

                            if len(stream_outputs_batch) >= self.chunk_batch_size:
                                # Aggiorna GUI batch
                                self._emit_stream_output_batch(stream_outputs_batch)
                                stream_outputs_batch.clear()
                                
                        self._update_standard_response_from_event(standard_response, data, processor)
                        
                        chunks_processed += 1
                        
                        gui_update_counter += 1
                        if gui_update_counter >= self.gui_update_interval:
                            self._emit_gui_update_request()
                            gui_update_counter = 0
                        
                        if chunks_processed % self.memory_cleanup_interval == 0:
                            gc.collect()
                        
                        if chunks_processed % self.config.metrics_update_interval == 0:
                            self._emit_metrics_update()
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"JSON decode error: {e}")
                        continue
            
            # Ultimo batch GUI
            if stream_outputs_batch:
                self._emit_stream_output_batch(stream_outputs_batch)
                
            # ═══ FINALIZE - USE RETURN VALUE ═══
            final_response = self._finalize_claude_response(standard_response, processor)
            
            return {
                'success': True,
                'partial': False,
                'response': final_response,  
                'chunks_received': chunks_received,
                'bytes_read': bytes_read
            }
            
        except (ChunkedEncodingError, ConnectionError, Exception) as stream_error:
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
                self.metrics.retry_count_total += 1
                return {
                    'success': False,
                    'partial': True,
                    'should_retry': True,
                    'error': str(stream_error)
                }
            else:
                self.logger.info("Error analysis: normal end-of-stream - processing available data")
                
                if chunks_processed > 0:
                    final_response = self._finalize_claude_response(standard_response, processor)
                    
                    if standard_response.get('content'):
                        for block in standard_response['content']:
                            if block and block.get('type') == 'text':
                                block['text'] = (block.get('text', '') +
                                               "\n\n[Stream ended unexpectedly but response is complete]")
                                break
                    
                    return {
                        'success': True,
                        'partial': True,
                        'should_retry': False,
                        'response': standard_response,
                        'chunks_received': chunks_received
                    }
                else:
                    return {
                        'success': False,
                        'partial': True,
                        'should_retry': True,
                        'error': f"No useful data: {str(stream_error)}"
                    }
    
    def _analyze_chunk_error_severity(self, context: Dict, error: Exception) -> bool:
        """Analizza se errore è reale o end-of-stream normale"""
        # === INDICATORI END-OF-STREAM NORMALE ===
        normal_indicators = 0
        
        # 1. Dati sostanziali ricevuti
        if context['bytes_read'] > 1000 and context['chunks_processed'] > 0:
            self.logger.debug("Substantial data - likely normal end")
            normal_indicators += 1
        
        # 2. Stream durato tempo ragionevole
        if context['stream_duration'] > 5.0:
            self.logger.debug("Reasonable duration - likely normal completion")
            normal_indicators += 1
        
        # 3. Multiple chunks
        if context['chunks_received'] > 10:
            self.logger.debug("Multiple chunks - likely normal end")
            normal_indicators += 1
        
        # 4. Ha dati sostanziali
        if context['has_substantial_data']:
            self.logger.debug("Has substantial data - likely complete")
            normal_indicators += 1
        
        # === INDICATORI ERRORE REALE ===
        error_indicators = 0
        
        # 1. Pochissimi dati
        if context['bytes_read'] < 100:
            self.logger.debug("Very little data - likely error")
            error_indicators += 2
        
        # 2. Stream molto breve
        if context['stream_duration'] < 1.0:
            self.logger.debug("Very short stream - likely error")
            error_indicators += 1
        
        # 3. Pochi chunks
        if context['chunks_received'] < 3:
            self.logger.debug("Few chunks - likely early error")
            error_indicators += 1
        
        # 4. Error message con keywords
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
        
        # Caso ambiguo
        if context['chunks_processed'] > 0:
            self.logger.info("Ambiguous but have data - treating as normal")
            return False
        else:
            self.logger.info("Ambiguous with no data - treating as error")
            return True
    
    def _process_gpt_stream_with_error_handling(self, response, request: StreamingRequest,
                                                standard_response: Dict, max_tokens: int,
                                                attempt: int) -> Dict:
        """Process GPT stream con intelligent error handling"""
        chunks_processed = 0
        gui_update_counter = 0
        first_chunk = True
        
        # Variabili per analisi intelligente
        bytes_read = 0
        chunks_received = 0
        stream_started_time = time.time()
        has_received_substantial_data = False
        
        try:
            # CORRETTO: iter_lines per SSE
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
                        
                        if data.get('object') != 'chat.completion.chunk':
                            continue
                        
                        # First chunk
                        if first_chunk:
                            standard_response['id'] = data.get('id')
                            standard_response['created'] = data.get('created')
                            standard_response['model'] = data.get('model')
                            
                            if not standard_response['choices']:
                                standard_response['choices'] = [{
                                    'index': 0,
                                    'message': {'role': 'assistant', 'content': ''},
                                    'finish_reason': None
                                }]
                            
                            self._emit_event_simple('new_stream')
                            first_chunk = False
                        
                        # Process choices
                        choices = data.get('choices', [])
                        if choices:
                            choice = choices[0]
                            delta = choice.get('delta', {})
                            
                            # Content delta
                            delta_content = delta.get('content', '')
                            if delta_content:
                                standard_response['choices'][0]['message']['content'] += delta_content
                                self._emit_event_simple('text_content', delta_content, 0)
                            
                            # Finish reason
                            finish_reason = choice.get('finish_reason')
                            if finish_reason:
                                standard_response['choices'][0]['finish_reason'] = finish_reason
                                if finish_reason in ['stop', 'length']:
                                    self._emit_event_simple('stream_finished')
                            
                            # Usage
                            usage = data.get('usage', {})
                            if usage:
                                std_usage = standard_response['usage']
                                std_usage['prompt_tokens'] = usage.get('prompt_tokens', std_usage['prompt_tokens'])
                                std_usage['completion_tokens'] = usage.get('completion_tokens', std_usage['completion_tokens'])
                                std_usage['total_tokens'] = usage.get('total_tokens', std_usage['total_tokens'])
                        
                        chunks_processed += 1
                        
                        # GUI update
                        gui_update_counter += 1
                        if gui_update_counter >= self.gui_update_interval:
                            self._emit_gui_update_request()
                            gui_update_counter = 0
                        
                        # Memory cleanup
                        if chunks_processed % self.memory_cleanup_interval == 0:
                            gc.collect()
                            
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"JSON decode error: {e}")
                        continue
            
            # Finalize
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
            
            return {
                'success': True,
                'partial': False,
                'response': standard_response,
                'chunks_received': chunks_received,
                'bytes_read': bytes_read
            }
            
        except (ChunkedEncodingError, ConnectionError, Exception) as stream_error:
            # Intelligent error analysis (stesso di Claude)
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
                return {
                    'success': False,
                    'partial': True,
                    'should_retry': True,
                    'error': str(stream_error)
                }
            else:
                # Use partial data
                if chunks_processed > 0:
                    if standard_response.get('choices'):
                        standard_response['choices'][0]['message']['content'] += "\n\n[Stream ended unexpectedly but response is complete]"
                    
                    return {
                        'success': True,
                        'partial': True,
                        'should_retry': False,
                        'response': standard_response
                    }
                else:
                    return {
                        'success': False,
                        'partial': True,
                        'should_retry': True,
                        'error': str(stream_error)
                    }
    
    def _parse_claude_event(self, data: Dict) -> StreamEvent:
        """Parse raw data into StreamEvent"""
        data_type = data.get('type', '')
        
        try:
            event_type = StreamEventType(data_type)
        except ValueError:
            event_type = StreamEventType.ERROR
        
        if event_type == StreamEventType.MESSAGE_START and not self.is_multi_call_session:
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
    
    def _update_standard_response_from_event(self, standard_response: Dict, 
                                            data: Dict, processor: StreamingProcessor):
        """
        Update standard_response metadata ONLY.
        
        FIXED: NON popola content[] - viene ricostruito da _finalize_response_metadata.
        Preserva id/model dalla PRIMA call, aggiorna usage e stop_reason.
        """
        data_type = data.get('type')
        
        if data_type == 'message_start':
            message = data.get('message', {})
            
            # Preserva id/model SOLO se non già impostati (prima call)
            if not standard_response.get('id'):
                standard_response['id'] = message.get('id')
            if not standard_response.get('model'):
                standard_response['model'] = message.get('model')
            
            # Input tokens: preserva primo valore
            usage = message.get('usage', {})
            if usage and not standard_response['usage'].get('input_tokens'):
                standard_response['usage']['input_tokens'] = usage.get('input_tokens', 0)
                        
        elif data_type == 'message_delta':
            delta = data.get('delta', {})
            
            # Stop reason: usa ultimo (sempre 'end_turn' alla fine)
            if delta.get('stop_reason'):
                standard_response['stop_reason'] = delta.get('stop_reason')
            
            # Output tokens: ACCUMULA (ogni call aggiunge tokens)
            usage = data.get('usage', {})
            if usage and usage.get('output_tokens'):
                current_output = standard_response['usage'].get('output_tokens', 0)
                standard_response['usage']['output_tokens'] = current_output + usage.get('output_tokens', 0)
    
    def _finalize_claude_response(self, standard_response: Dict, processor: StreamingProcessor):
        """
        Finalize response con tool execution e multi-call logic.
        COMPLETE REWRITE per gestione corretta ANY tool (non solo think).
        """
        content_blocks = processor.get_content_blocks()
        self._accumulate_content_blocks(content_blocks)
        
        # ═══ CLEANUP: Return blocks to pool ═══
        processor.cleanup()
            
        tool_calls = [b for b in content_blocks if b.type == ContentBlockType.TOOL_USE]
        
        # No tools - finalize normally
        if not tool_calls:
            self._finalize_response_metadata(standard_response)
            self._reset_multi_call_session()
            return standard_response
        
        # ═══ ALWAYS ONE TOOL PER TURN ═══
        if len(tool_calls) != 1:
            self.logger.error(f"Expected 1 tool call, got {len(tool_calls)} - API contract violation!")
            # Fallback: use first
        
        tool_call = tool_calls[0]
        
        # ═══ CHECK STOP CONDITIONS (solo per think tool) ═══
        if tool_call.tool_name == 'think':
            stop_reason = self._should_stop_thinking()
            
            if stop_reason:
                self.logger.warning(f"Stopping think loop: {stop_reason}")
                termination_note = self._create_termination_note(stop_reason)
                self._finalize_response_metadata(standard_response)
                # self._add_note_to_response(standard_response, termination_note)
                self._reset_multi_call_session()
                return standard_response
        
        # ═══ INITIALIZE MULTI-CALL SESSION ═══
        if not self.is_multi_call_session:
            self.is_multi_call_session = True
            self.current_request.payload['messages'] = []

        # ═══ EMIT TOOL INPUT EVENT ═══
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': 'tool_input',
                'block_index': tool_call.index,
                'tool_name': tool_call.tool_name,
                'tool_input': tool_call.tool_input
            }]
        })
        
        self.logger.info(f"Generato evento stream_output_batch 'tool_input' per tool {tool_call.tool_name} con input: [{tool_call.tool_input}]")
       
        # ═══ EXECUTE TOOL AND BUILD CONTINUE PAYLOAD ═══
        tool_result, execution_success, continue_payload = self._execute_tool_and_build_continuation(
            tool_call,
            content_blocks
        )
        
        # ═══ UPDATE TRACKING ═══
        self.call_count += 1
        usage = standard_response.get('usage', {})
        self.accumulated_tokens += usage.get('output_tokens', 0)
        
        # ═══ RECURSIVE CALL ═══
        continue_request = StreamingRequest(
            request_id=str(uuid.uuid4()),
            payload=continue_payload,
            progress_callback=None,
            thinking_mode=self.request.thinking_mode
        )
        
        self.current_content_blocks = content_blocks
        self.current_request = continue_request
        
        # ═══ STEP CHECK ═══
        if self.step_by_step_mode:
            
            # ═══ EMIT DEBUG INFO - COMPLETO ═══
            self._emit_interleaved_info(
                message="Ready to perform next streaming request",
                call_number=self.call_count,
                request_type="continuation",
                
                # Tool call block completo
                tool_call_block={
                    'type': tool_call.type.value,
                    'index': tool_call.index,
                    'tool_name': tool_call.tool_name,
                    'tool_id': tool_call.tool_id,
                    'tool_input': tool_call.tool_input
                },
                
                # Tool result completo
                tool_result=tool_result,
                tool_execution_success=execution_success,
                
                # Continuation payload completo
                continuation_payload=continue_payload,
                messages_count=len(continue_payload.get('messages', [])),
                payload_size_estimate=len(json.dumps(continue_payload))
            )
        
            self.logger.info(f"Step-by-step mode: Pausing before continuation #{self.call_count}")
            return standard_response

        return self._on_step_forward(None)

    def _execute_tool_and_build_continuation(self, tool_call: ContentBlock, 
                                                      content_blocks: List[ContentBlock],
                                                      replace_last: bool = False) -> tuple[str, bool, Dict]:
        """
        Execute tool AND build continuation.
        
        Args:
            tool_call: Tool call block da eseguire
            content_blocks: Content blocks correnti
        
        Returns:
            tuple: (tool_result, continuation_payload)
        """
        tool_name = tool_call.tool_name
        tool_id = tool_call.tool_id
        
        self.logger.info(f"Executing tool: {tool_name} (id: {tool_id})")
        
        # ═══ EXECUTE TOOL ═══
        try:
            
            tool_result = self.tool_registry.execute_tool(tool_call.tool_name, tool_call.tool_input)
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
            execution_success
        )
        
        # ═══ EMIT TOOL RESULT EVENT ═══
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': 'tool_result',
                'block_index': tool_call.index,
                'tool_name': tool_call.tool_name,
                'tool_result': tool_result
            }]
        })
        
        # ═══ BUILD CONTINUATION PAYLOAD ═══
        continue_payload = self._build_continue_payload_with_results(
            self.original_payload,
            content_blocks,
            tool_call,
            tool_result,
            replace_last=replace_last 
        )
        
        if self.current_request:
            self.current_request.payload = continue_payload
        
        return tool_result, execution_success, continue_payload    

    def _finalize_response_metadata(self, standard_response: Dict):
        """
        COMPLETE REWRITE: Assembly intelligente con semantic markup.
        
        Costruisce final response con:
        - Sequenza chronological (per call_number)
        - Semantic markup tags ([THINKING], [TOOL_RESULT], etc.)
        - Call separators per leggibilità
        - Distinction thinking puro vs tool results
        """
        
        # ═══ STEP 1: GROUP BY CALL NUMBER ═══
        calls = {}
        for block in self.accumulated_content_blocks:
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
            
            # ═══ STEP 3: SORT BLOCKS WITHIN CALL ═══
            # Order: thinking → text → tool_use → tool_result
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
            
            # ═══ STEP 4: BUILD FINAL CONTENT CON MARKUP ═══
            for block in call_blocks_sorted:
                block_type = block['type']
                
                if block_type == 'thinking':
                    # Thinking con markup per PHP stripping
                    thinking_text = block['content'] or ''
                    final_content += f"[THINKING]\n{thinking_text}\n[/THINKING]\n\n"

                
                elif block_type == 'redacted_thinking':
                    # Redacted indicator
                    final_content += "[REDACTED_THINKING]\n(Encrypted reasoning for safety)\n[/REDACTED_THINKING]\n\n"
                
                elif block_type == 'text':
                    # Plain text - no markup needed
                    final_content += block['content'] or '' 
                    final_content += "\n\n"
                    
                elif block_type == 'tool_use':
                    # Tool use metadata (optional - omit think tool)
                    tool_name = block.get('tool_name', 'unknown')
                    if tool_name != 'think':  # Skip internal think metadata
                        tool_input_str = json.dumps(block.get('tool_input', {}), indent=2)
                        final_content += f"[TOOL_CALL: {tool_name}]\n{tool_input_str}\n[/TOOL_CALL]\n\n"
                
                elif block_type == 'tool_result':
                    # Tool result (operational tools only - think già filtrato in accumulation)
                    tool_name = block.get('tool_name', 'unknown')
                    result_content = block['content'] or ''
                    result_content = "Tool eseguito con successo"
                    final_content += f"[TOOL_RESULT: {tool_name}]\n{result_content}\n[/TOOL_RESULT]\n\n"
            
            # ═══ CALL SEPARATOR (se multi-call e non ultimo) ═══
            if call_num < max(calls.keys()):
                separator = f"\n{'═' * 60}\n[Reasoning cycle {call_num + 1} → {call_num + 2}]\n{'═' * 60}\n\n"
                final_content += separator
        
        # ═══ STEP 5: SET RESPONSE ═══
        # Crea text block integrato se ci sono parti di testo
        if final_content:
            integrated_text = ''.join(final_content).strip()
            text_block = {
                "type": "text",
                "text": integrated_text
            }
            final_response.insert(0, text_block)  # Text sempre primo
        
        standard_response['content'] = final_response
        
        # ═══ STEP 6: METADATA ═══
        if 'type' not in standard_response:
            standard_response['type'] = 'message'
        if 'role' not in standard_response:
            standard_response['role'] = 'assistant'
        
        # ═══ STEP 7: USAGE TOKENS ═══
        if 'usage' not in standard_response:
            standard_response['usage'] = {}
            
        standard_response['usage']['output_tokens'] = self.accumulated_tokens
        
        self.logger.info(
            f"Final response assembled: {len(final_content)} blocks, "
            f"{len(calls)} reasoning cycles, {self.accumulated_tokens} tokens"
        )    

    def _check_thinking_mode(self, payload: Dict) -> bool:
        """Check thinking + add enabled tools to payload"""
        thinking_enabled = False
        
        if 'thinking' in payload:
            thinking_config = payload['thinking']
            if isinstance(thinking_config, dict):
                thinking_enabled = thinking_config.get('budget_tokens', 0) > 0
            elif isinstance(thinking_config, bool):
                thinking_enabled = thinking_config
        
        if thinking_enabled:
            interleaved_header = payload['headers'].get("anthropic-beta", "")
            if "interleaved-thinking" in interleaved_header:
                if "tools" not in payload:
                    payload["tools"] = []
                
                # ═══ GET ENABLED TOOLS FROM REGISTRY ═══
                enabled_definitions = self.tool_registry.get_enabled_definitions()
                
                # Get tools section for system prompt
                tools_section = self.tool_registry.get_complete_system_prompt_addition()
                
                # Add each enabled tool se non già presente
                for tool_def in enabled_definitions:
                    tool_name = tool_def['name']
                    if not any(t.get("name") == tool_name for t in payload["tools"]):
                        payload["tools"].append(tool_def)
                        
                # Append to existing system message
                current_content = payload.get('system', '')
                payload['system'] = tools_section # + "\n\n" + current_content  

        # ═══ SIMULATION MODE: Config tool ═══
        if self.simulation_mode and thinking_enabled:
            # Recupera primo tool disponibile da payload
            tools = payload.get('tools', [])
            if tools:
                first_tool_name = tools[0].get('name')
                if first_tool_name:
                    # Configura simulation per usare primo tool
                    self.simulation_config['include_tool'] = True
                    self.simulation_config['tool_name'] = first_tool_name
                    self.fake_response = FakeStreamingResponse(self.simulation_config)
                    self.logger.info(f"Simulation configured with tool: {first_tool_name}")
                
                return thinking_enabled
           
    def _reset_multi_call_session(self):
        """Reset multi-call session"""
        self.is_multi_call_session = False
        self.current_request = None
        self.current_content_blocks = None
        self.accumulated_content_blocks = []
        self.accumulated_tokens = 0
        self.call_count = 0
    
    def _accumulate_content_blocks(self, content_blocks: List[ContentBlock]):
        """
        Accumulate content from this call - PRESERVA SIGNATURE.
        
        ENHANCED: Più logging per tracking signature preservation.
        """
        for block in content_blocks:
            accumulated_block = {
                "type": block.type.value,
                "content": block.content,
                "call_number": self.call_count,
                "index": block.index
            }
            
            # ↓ CRITICAL: Preserva signature per thinking blocks
            if block.type in [ContentBlockType.THINKING, ContentBlockType.REDACTED_THINKING]:
                if block.signature:
                    accumulated_block["signature"] = block.signature
                    self.logger.debug(f"Accumulated thinking block {block.index} with signature (call {self.call_count})")
                else:
                    self.logger.error(f"CRITICAL: Thinking block {block.index} missing signature in call {self.call_count}")
                    # Don't raise - log error but continue (might be API issue)
                
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
            
            self.accumulated_content_blocks.append(accumulated_block)


    def _accumulate_tool_result(self, tool_name: str, tool_id: str, 
                                result: str, success: bool = True):
        """
        Accumulate tool result con strategia differenziata.
        
        LOGIC:
        - Think tool: Result è feedback interno, salvato separately per debug
        - Operational tools: Result è user-facing, accumulato in main blocks
        
        Args:
            tool_name: Nome tool
            tool_id: ID univoco tool call
            result: String result da execution
            success: Se execution successful
        """
        
        # ═══ THINK TOOL: Internal Feedback Only ═══
        if tool_name == "think":
            # Save separately per potential debugging
            if not hasattr(self, '_think_results_internal'):
                self._think_results_internal = []
            
            self._think_results_internal.append({
                "call_number": self.call_count,
                "tool_id": tool_id,
                "result": result,
                "success": success,
                "timestamp": time.time()
            })
            
            self.logger.debug(f"Think result saved internally (call {self.call_count})")
            return  # Don't add to main accumulated_content_blocks
        
        # ═══ OPERATIONAL TOOLS: User-Facing Content ═══
        result_block = {
            "type": "tool_result",
            "content": result,
            "tool_use_id": tool_id,
            "tool_name": tool_name,  # Metadata per formatting
            "call_number": self.call_count,
            "success": success
        }
        
        self.accumulated_content_blocks.append(result_block)
        self.logger.debug(f"Tool result accumulated: {tool_name} (call {self.call_count})")

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
                                             replace_last: bool = False) -> Dict:
        """
        Build continuation payload con TUTTA la storia multi-turn.
        
        FIXED: Ricostruisce TUTTI i turni precedenti da accumulated_content_blocks.
        
        Args:
            original_payload: Payload originale della richiesta
            content_blocks: Content blocks del turn CORRENTE
            tool_call: Tool call del turn corrente
            tool_result: Tool result del turn corrente
            replace_last: Se True, sostituisce ultimo turno invece di appendere (per debug)
        
        Returns:
            Dict payload ready per continuazione con storia completa
        """
        # ═══ VALIDATE SIGNATURES ═══
        # self._validate_thinking_signatures_before_send(content_blocks)
        
        continue_payload = copy.deepcopy(original_payload)
        
        # ═══ RICOSTRUISCI STORIA DA ACCUMULATED_BLOCKS ═══
        # Gruppo accumulated_blocks per call_number
        turns_history = {}  # {call_number: {'blocks': [...], 'tool_result': {...}}}
        
        for accumulated_block in self.accumulated_content_blocks:
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
        if replace_last:
            last_call = sorted_calls.pop()
            
            # Rimuovi da turns_history
            del turns_history[last_call]
            
            # Rimuovi da accumulated_content_blocks
            self.accumulated_content_blocks = [
                b for b in self.accumulated_content_blocks 
                if b.get('call_number', 0) != last_call
            ]

            self.logger.info(f"Replacing last turn (call #{last_call})")

        last_call_num = sorted_calls[-1] if sorted_calls else None
        
        # ═══ AGGIUNGI TURNI PRECEDENTI ═══
        for call_num in sorted_calls:
            turn = turns_history[call_num]
            assistant_content = []
            
            # Single pass - ordine: thinking → text → tool_use
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
            if turn['tool_result']:  # <-- DENTRO IL LOOP = CORRETTO
                tool_name = turn['tool_result'].get('tool_name', '')
                is_verbose_tool = tool_name in ['view', 'bash_tool', 'web_search', 'web_fetch']
                is_last_turn = (call_num == last_call_num)
                
                '''
                # TRUNCATE precedenti verbose tools
                if is_verbose_tool and not is_last_turn:
                    result_content = self._compact_tool_result(
                        turn['tool_result']['content'],
                        tool_name,
                        max_chars=50  # Configurable
                    )
                else:
                '''
                
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

    
    def _compress_payload_advanced(self, payload, max_context, max_tokens, encoding):
        """
        Compression gerarchica intelligente preservando essenziale.
        
        STRATEGIA:
        1. SEMPRE preserva: System prompt + ultimi N messages
        2. COMPATTA selettivamente: Middle messages con priority
        3. RIASSUMI: Solo se necessario, preservando struttura
        """
        target_tokens = max_context - max_tokens - self.config.compression_safety_buffer  
        
        messages = payload.get("messages", [])
        if len(messages) <= 3:
            return payload  # Too few to compress
        
        # TIER 1: ALWAYS PRESERVE (Essenziale)
        preserved = []
        
        # System message (se presente)
        if messages[0].get("role") == "system":
            preserved.append(messages[0])
            remaining = messages[1:]
        else:
            remaining = messages
        
        # TIER 2: ANALYZE MIDDLE (Compression Candidates)
        # Ultimi N messages preserve count basato su complessità
        preserve_recent = self._calculate_preserve_count(remaining, target_tokens)
        
        recent_messages = remaining[-preserve_recent:]
        middle_messages = remaining[:-preserve_recent] if len(remaining) > preserve_recent else []
        
        # TIER 3: COMPRESS MIDDLE INTELLIGENTLY
        if middle_messages:
            compressed_middle = self._compress_middle_messages_hierarchical(
                middle_messages, 
                target_tokens,
                encoding
            )
            preserved.extend(compressed_middle)
        
        # TIER 4: ADD RECENT (Always full)
        preserved.extend(recent_messages)
        
        compressed_payload = copy.deepcopy(payload)
        compressed_payload["messages"] = preserved
        
        # Verify final size
        final_tokens = len(encoding.encode(json.dumps(compressed_payload)))
        
        if final_tokens > target_tokens:
            # TIER 5: EXTREME COMPRESSION (Last resort)
            return self._extreme_compression(payload, target_tokens, preserve_recent, encoding)
        
        return compressed_payload
        
    def _calculate_preserve_count(self, messages, target_tokens):
        """
        Calcola quanti messaggi recenti preservare basato su:
        - Complessità messaggi (tool calls = più importanti)
        - Budget tokens disponibile
        - Minimum safety (almeno 2)
        """
        # Analizza complessità messaggi recenti
        complexity_scores = []
        for msg in reversed(messages[-10:]):  # Analizza ultimi 10
            score = 1  # Base
            content = msg.get("content", "")
            
            # Tool calls sono più importanti
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") in ["tool_use", "tool_result"]:
                            score += 2
            
            # Messaggi lunghi potrebbero essere importanti
            if isinstance(content, str) and len(content) > 1000:
                score += 1
            
            complexity_scores.append(score)
        
        # Decide preserve count
        if max(complexity_scores) > self.config.compression_complexity_high:
            return min(5, len(messages))
        elif max(complexity_scores) > self.config.compression_complexity_medium:
            return min(3, len(messages))
        else:
            return min(2, len(messages))  # Minimum
    
    def _compress_middle_messages_hierarchical(self, middle_messages, target_tokens, encoding):
        """
        Compression gerarchica che preserva struttura essenziale.
        
        FIXED: Preserva SEMPRE thinking blocks integralmente perché contengono
        signature immutabile.
        
        STRATEGY:
        1. Identifica messaggi CRITICAL (tool calls, thinking, long reasoning)
        2. Preserva CRITICAL integralmente
        3. Summarize NON-CRITICAL
        4. Se ancora troppo, compatta CRITICAL selettivamente (MA MAI thinking)
        """
        critical_messages = []
        non_critical_messages = []
        
        for msg in middle_messages:
            # Classifica critical vs non-critical
            is_critical = self._is_message_critical(msg)
            
            if is_critical:
                critical_messages.append(msg)
            else:
                non_critical_messages.append(msg)
        
        # Start with critical preserved
        result = critical_messages.copy()
        
        # Summarize non-critical
        if non_critical_messages:
            summary_msg = {
                "role": "user",
                "content": self._create_structured_summary(non_critical_messages)
            }
            result.insert(0, summary_msg)
        
        # Check size
        current_tokens = len(encoding.encode(json.dumps(result)))
        
        if current_tokens > target_tokens * 0.6:  # Still too big
            # Compatta anche critical selettivamente
            # BUT: NEVER compress thinking blocks (they have immutable signatures)
            result = self._compress_critical_messages_preserve_thinking(result, target_tokens, encoding)
        
        return result

    def _compress_critical_messages_preserve_thinking(self, messages, target_tokens, encoding):
        """
        Compress critical messages MA preservando SEMPRE thinking blocks.
        
        NUOVO METODO per gestire compression avanzata senza toccare thinking blocks.
        """
        preserved = []
        thinking_messages = []
        other_critical = []
        
        # Separate thinking from other critical messages
        for msg in messages:
            content = msg.get("content", "")
            has_thinking = False
            
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") in ["thinking", "redacted_thinking"]:
                            has_thinking = True
                            break
            
            if has_thinking:
                thinking_messages.append(msg)
            else:
                other_critical.append(msg)
        
        # ALWAYS preserve thinking messages (immutable signatures)
        preserved.extend(thinking_messages)
        
        # Compress other critical messages if needed
        current_tokens = len(encoding.encode(json.dumps(preserved)))
        remaining_budget = target_tokens - current_tokens
        
        if remaining_budget > 0 and other_critical:
            # Add as many other critical messages as budget allows
            for msg in other_critical:
                msg_tokens = len(encoding.encode(json.dumps(msg)))
                if msg_tokens <= remaining_budget:
                    preserved.append(msg)
                    remaining_budget -= msg_tokens
                else:
                    # Summarize this message
                    summary = self._create_structured_summary([msg])
                    summary_msg = {"role": msg.get("role", "user"), "content": summary}
                    summary_tokens = len(encoding.encode(json.dumps(summary_msg)))
                    
                    if summary_tokens <= remaining_budget:
                        preserved.append(summary_msg)
                        remaining_budget -= summary_tokens
        
        return preserved
    
    def _is_message_critical(self, msg):
        """
        Determina se messaggio è critical (da preservare integralmente).
        
        FIXED: Thinking blocks sono SEMPRE critical perché contengono
        signature immutabile che deve essere preservata.
        """
        content = msg.get("content", "")
        
        # ═══ THINKING BLOCKS: ALWAYS CRITICAL ═══
        # Thinking blocks have immutable signatures that MUST be preserved
        # Removing or modifying them breaks reasoning continuity
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    
                    # Thinking blocks are ALWAYS critical
                    if item_type in ["thinking", "redacted_thinking"]:
                        return True
                    
                    # Tool calls SEMPRE critical
                    if item_type in ["tool_use", "tool_result"]:
                        return True
        
        # Messaggi molto lunghi potrebbero essere critical
        if isinstance(content, str) and len(content) > self.config.compression_text_length_threshold:
            # Check se contiene reasoning markers
            reasoning_markers = [
                "let me think", "step by step", "analyzing", 
                "reasoning:", "therefore", "because", "conclusion"
            ]
            if any(marker in content.lower() for marker in reasoning_markers):
                return True
        
        return False
    
    def _create_structured_summary(self, messages):
        """Crea summary STRUTTURATO invece generico"""
        summary_parts = []
        
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # Estrai essenziale
            if isinstance(content, str):
                # Per messaggi testuali, estrai sentence chiave
                sentences = content.split('.')
                if len(sentences) > 3:
                    # Prima + ultima sentence (di solito contengono essenziale)
                    key_content = sentences[0] + "..." + sentences[-1]
                else:
                    key_content = content[:200]
                
                summary_parts.append(f"[{role}]: {key_content}")
            
            elif isinstance(content, list):
                # Questo non dovrebbe accadere qui (critical preservati)
                # Ma safety fallback
                summary_parts.append(f"[{role}]: [Complex content]")
        
        header = f"[COMPRESSED: {len(messages)} messages summarized]\n"
        return header + " | ".join(summary_parts)
    
    def _compress_critical_messages(self, messages, target_tokens, encoding):
        """Compression selettiva - NEVER compress thinking blocks"""
        compressed = []
        
        for msg in messages:
            content = msg.get("content", "")
            
            if isinstance(content, list):
                compressed_content = []
                for item in content:
                    if item.get("type") == "tool_use":
                        tool_input = item.get("input", {})
                        
                        # ↓ CHECK: Se è think tool, NON comprimere
                        if isinstance(tool_input, dict) and "thought" in tool_input:
                            # PRESERVE thinking content integralmente
                            # Signature dipende da content esatto
                            compressed_content.append({
                                "type": "tool_use",
                                "name": item.get("name"),
                                "id": item.get("id"),
                                "input": tool_input  # ← NO COMPRESSION
                            })
                        else:
                            # Altri tool: compatta se input molto grande
                            if isinstance(tool_input, dict):
                                # Compatta solo se NON è thinking
                                compressed_input = self._compress_non_thinking_input(tool_input)
                                compressed_content.append({
                                    "type": "tool_use",
                                    "name": item.get("name"),
                                    "id": item.get("id"),
                                    "input": compressed_input
                                })
                            else:
                                compressed_content.append(item)
                        
                    elif item.get("type") == "tool_result":
                        # Compatta result se molto lungo
                        result_content = item.get("content", "")
                        if len(result_content) > 1000:
                            result_content = result_content[:1000] + "...[truncated]"
                        compressed_content.append({
                            "type": "tool_result",
                            "tool_use_id": item.get("tool_use_id"),
                            "content": result_content
                        })
                        
                    elif item.get("type") in ["thinking", "redacted_thinking"]:
                        # ↓ CRITICAL: NEVER modify thinking blocks
                        compressed_content.append(item)
                        
                    else:
                        compressed_content.append(item)
                
                compressed.append({
                    "role": msg.get("role"),
                    "content": compressed_content
                })
            else:
                # Text message - compatta se troppo lungo
                if len(content) > 2000:
                    content = content[:2000] + "...[compressed]"
                compressed.append({
                    "role": msg.get("role"),
                    "content": content
                })
        
        return compressed
    
    def _compress_non_thinking_input(self, tool_input: Dict) -> Dict:
        """Helper per comprimere input di tool NON-thinking"""
        compressed = {}
        for key, value in tool_input.items():
            if isinstance(value, str) and len(value) > 500:
                compressed[key] = value[:500] + "...[truncated]"
            else:
                compressed[key] = value
        return compressed
    
    def _compact_step(self, lines):
        """Compatta corpo di uno step preservando essenziale"""
        # Se step è breve (<3 lines), preserva integrale
        if len(lines) <= 3:
            return '\n'.join(lines)
        
        # Altrimenti preserva prima + ultima line (di solito contengono key info)
        return lines[0] + "..." + lines[-1]

    def _extreme_compression(self, payload: Dict, target_tokens: int, 
                            preserve_recent: int, encoding) -> Dict:
        """
        Extreme compression last resort quando hierarchical non basta.
        Preserva SOLO: system + ultimissimi messages essenziali + current.
        """
        self.logger.warning("Applying EXTREME compression - substantial context loss expected")
        
        messages = payload.get("messages", [])
        compressed = []
        
        # System message (se presente)
        if messages and messages[0].get("role") == "system":
            # Compatta anche system se necessario
            system_content = messages[0].get("content", "")
            if len(system_content) > 2000:
                system_content = system_content[:2000] + "...[COMPRESSED]"
            compressed.append({
                "role": "system",
                "content": system_content
            })
            remaining = messages[1:]
        else:
            remaining = messages
        
        # Prendi SOLO ultimissimi messages (preserve_recent già calculated)
        recent = remaining[-preserve_recent:] if len(remaining) > preserve_recent else remaining
        
        # Compatta anche questi se necessario
        for msg in recent:
            content = msg.get("content", "")
            
            if isinstance(content, list):
                # Preserva structure ma trunca aggressively
                compressed_content = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        
                        if item_type == "text":
                            text = item.get("text", "")
                            # Extreme truncation
                            if len(text) > 500:
                                text = text[:250] + "...[TRUNCATED]..." + text[-250:]
                            compressed_content.append({"type": "text", "text": text})
                        
                        elif item_type == "tool_use":
                            # Preserve minimal tool info
                            compressed_content.append({
                                "type": "tool_use",
                                "name": item.get("name"),
                                "id": item.get("id"),
                                "input": {"thought": "[COMPRESSED]"}  # Minimal
                            })
                        
                        elif item_type == "tool_result":
                            # Extreme truncation
                            result_text = item.get("content", "")
                            if len(result_text) > 300:
                                result_text = result_text[:300] + "...[TRUNCATED]"
                            compressed_content.append({
                                "type": "tool_result",
                                "tool_use_id": item.get("tool_use_id"),
                                "content": result_text
                            })
                        
                        elif item_type in ["thinking", "redacted_thinking"]:
                            # Skip thinking in extreme mode (API filtrerebbe anyway)
                            continue
                        else:
                            compressed_content.append(item)
                
                compressed.append({
                    "role": msg.get("role"),
                    "content": compressed_content
                })
            
            elif isinstance(content, str):
                # Text message - extreme truncation
                if len(content) > 800:
                    content = content[:400] + "...[COMPRESSED]..." + content[-400:]
                compressed.append({
                    "role": msg.get("role"),
                    "content": content
                })
            else:
                compressed.append(msg)
        
        # Build result
        extreme_payload = copy.deepcopy(payload)
        extreme_payload["messages"] = compressed
        
        # Final verification
        final_text = json.dumps(extreme_payload, ensure_ascii=False)
        final_tokens = len(encoding.encode(final_text))
        
        self.logger.warning(f"Extreme compression result: {final_tokens} tokens")
        
        if final_tokens > target_tokens:
            # Last resort - just keep system + last user message
            self.logger.error("Even extreme compression insufficient - keeping minimal context")
            minimal = []
            if messages and messages[0].get("role") == "system":
                minimal.append({"role": "system", "content": "You are SAGE."})
            # Last user message only
            last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
            if last_user:
                minimal.append(last_user)
            extreme_payload["messages"] = minimal
        
        return extreme_payload        

    def _init_claude_response(self) -> Dict:
        """Initialize Claude response structure"""
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
    
    def _init_gpt_response(self) -> Dict:
        """Initialize GPT response structure"""
        return {
            "id": None,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": None,
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
    
    def _create_error_response(self, standard_response: Dict, error_message: str) -> Dict:
        """Create error response"""
        if 'content' in standard_response:
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
        else:
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
    
    def _emit_gui_update_request(self):
        """Request GUI update"""
        self.event_system.emit_event('gui_update_request', {})
    
    def _emit_progress(self, request: StreamingRequest, 
                      phase: str = 'streaming',
                      current_block_type: str = None,
                      current_block_index: int = None,
                      tokens_per_second: float = 0.0):
        """
        UNIFIED progress emission - single source of truth.
        Emette sia simple progress che detailed info.
        """
        # Build comprehensive progress data
        progress_data = {
            'request_id': request.request_id,
            'progress': request.progress,
            'state': request.state.value,
            'chunks_processed': request.chunks_processed,
            'error': str(request.error) if request.error else None,
            # Detailed info
            'phase': phase,
            'current_block_type': current_block_type,
            'current_block_index': current_block_index,
            'tokens_processed': self.accumulated_tokens,
            'tokens_per_second': tokens_per_second,
            'think_calls_completed': self.call_count,
            'time_elapsed': time.time() - request.start_time if hasattr(request, 'start_time') else 0
        }
        
        if phase == 'complete' or phase == 'failed':
            # Cleanup abort flag
            if self.request.request_id in self.abort_flags:
                del self.abort_flags[self.request.request_id]

            profile_result = self.profiler.stop_profiling()
            if profile_result:
                self.logger.debug(f"Profile:\n{profile_result}")
        
        # Emit single event con tutti dati
        self.event_system.emit_event('stream_progress', progress_data)
    
    def _emit_retry_event(self, event_type: str, message: str, attempt: int):
        """Emit retry event"""
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': event_type,
                'message': message,
                'block_index': None,
                'attempt': attempt
            }]
        })
    
    def _emit_event_simple(self, event_type: str, text: str = '', block_index: Optional[int] = None):
        """Emit simple event"""
        event_data = {
            'type': event_type,
            'block_index': block_index
        }
        if text:
            event_data['text'] = text
        
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [event_data]
        })

    def _emit_stream_output_batch(self, stream_outputs):
        """Emette batch di output per show_stream via eventi, con multiblock support."""
        
        self.event_system.emit_event('stream_output_batch', {
            'outputs': copy.deepcopy(stream_outputs)
        })

    def _emit_interleaved_info(self, message: str, **kwargs):
        """
        Emit interleaved_info debug event with complete context.
        
        Args:
            message: Human-readable message
            **kwargs: All debug data (tool_call_block, tool_result, continuation_payload, etc)
        """
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': 'interleaved_info',
                'message': message,
                'timestamp': time.time(),
                **kwargs  # Tutti i dati completi passati dal caller
            }]
        })

    def _emit_metrics_update(self):
        """Emit periodic metrics update for UI dashboard"""
        if not hasattr(self, 'metrics'):
            return
        
        metrics_data = {
            'total_tokens': self.accumulated_tokens,
            'thinking_tokens': getattr(self, '_thinking_tokens_tracked', 0),
            'text_tokens': getattr(self, '_text_tokens_tracked', 0),
            'tool_io_tokens': getattr(self, '_tool_io_tokens_tracked', 0),
            'current_velocity': getattr(self, '_current_velocity', 0),
            'avg_velocity': self.metrics.avg_tokens_per_second,
            'peak_velocity': self.metrics.peak_tokens_per_second,
            'input_tokens': 0,  # TODO: track separately
            'output_tokens': self.accumulated_tokens,
            'latency_ms': 0,  # TODO: calculate
            'efficiency_pct': 0,  # TODO: calculate
        }
        
        self.event_system.emit_event('stream_output_batch', {
            'outputs': [{
                'type': 'metrics_update',
                **metrics_data
            }]
        })
    
    def _should_stop_thinking(self) -> Optional[str]:
        """
        Determina se fermare multi-call think loop.
        
        Returns:
            None se continuare
            String reason se fermare
        """
        # Check 1: Max calls reached
        if self.call_count >= self.max_think_calls:
            return f"Maximum thinking cycles reached ({self.max_think_calls})"
        
        # Check 2: Total token budget exceeded
        if self.accumulated_tokens >= self.total_think_budget:
            return f"Total thinking token budget exceeded ({self.accumulated_tokens}/{self.total_think_budget})"
        
        # Check 3: Diminishing returns (se thinking diventa ripetitivo)
        if self.call_count >= 3:
            # Compare last 2 thinking contents per similarity
            if len(self.accumulated_content) >= 2:
                last_thought = self.accumulated_content[-1].get('content', '')
                prev_thought = self.accumulated_content[-2].get('content', '')
                
                # Simple similarity check
                similarity = self._calculate_similarity(last_thought, prev_thought)
                if similarity > 0.7:  # 70% similar
                    return f"Thinking appears repetitive (similarity: {similarity:.0%})"
        
        # Check 4: Model explicitly indicates completion
        # (Questo è tricky - requirebbe NLP del thinking content)
        # Per ora skippiamo - modello dovrebbe semplicemente non chiamare think se finito
        
        return None  # Continue thinking
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple word-overlap similarity"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_termination_note(self, reason: str) -> str:
        """Crea nota informativa per terminazione"""
        return f"""

╔═══════════════════════════════════════════════════════════╗
║ ⚠️  THINKING PROCESS TERMINATED                          ║
╚═══════════════════════════════════════════════════════════╝

Reason: {reason}

Your reasoning across {self.call_count} thinking cycle(s) has been 
recorded and integrated. Proceeding with response formulation based 
on accumulated analysis.

Total thinking tokens used: {self.accumulated_tokens}
"""
    
    def _add_note_to_response(self, response: Dict, note: str):
        """Aggiunge nota a response text block"""
        content = response.get('content', [])
        
        # Find last text block
        for block in reversed(content):
            if block and block.get('type') == 'text':
                block['text'] = (block.get('text', '') + note)
                return
        
        # No text block found - add new one
        content.append({
            'type': 'text',
            'text': note
        })
    
    def _extract_task_summary(self, payload: Dict) -> str:
        """Estrai summary task da payload per context preservation"""
        messages = payload.get('messages', [])
        if not messages:
            return "Unknown task"
        
        # Last user message è tipicamente il task
        last_user = next(
            (m for m in reversed(messages) if m.get('role') == 'user'),
            None
        )
        
        if not last_user:
            return "Unknown task"
        
        content = last_user.get('content', '')
        
        if isinstance(content, str):
            return content[:200] + "..." if len(content) > 200 else content
        elif isinstance(content, list):
            texts = [
                item.get('text', '')
                for item in content
                if isinstance(item, dict) and item.get('type') == 'text'
            ]
            combined = ' '.join(texts)
            return combined[:200] + "..." if len(combined) > 200 else combined
        
        return "Complex task"

    def _log_structured_error(self, component: str, error: Exception, context: Dict = None):
        """Log error con full context"""
        structured = StructuredError(
            timestamp=time.time(),
            component=component,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {},
            stack_trace=traceback.format_exc()
        )
        
        # Log
        self.logger.error(str(structured))
        
        # Store history
        self.error_history.append(structured)
        
        # Emit event (opzionale - per debugging UI)
        self.event_system.emit_event('error_occurred', structured.to_dict())
        
        return structured

    def get_metrics_summary(self) -> str:
        """Get comprehensive metrics summary"""
        return self.metrics.get_summary()

    def enable_tool(self, tool_name: str):
        """Enable tool via registry"""
        self.tool_registry.enable_tool(tool_name)
    
    def disable_tool(self, tool_name: str):
        """Disable tool via registry"""
        self.tool_registry.disable_tool(tool_name)
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check tool enabled"""
        return self.tool_registry.is_tool_enabled(tool_name)
    
    def get_enabled_tools(self) -> List[str]:
        """Get enabled tool names"""
        return self.tool_registry.get_tool_names(enabled_only=True)
    
    def get_all_tools(self) -> List[str]:
        """Get all tool names"""
        return self.tool_registry.get_tool_names(enabled_only=False)
