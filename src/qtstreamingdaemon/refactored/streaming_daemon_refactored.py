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

# REFACTORING: ToolRegistry NON più importato - ricevuto come parametro
# FakeStreamingResponse → SPOSTATO in agent_streaming_handler.py (ITERAZIONE #5)
import models_config

# ═══ EXTRACTED MODULES ═══
from streaming_types import (
    # ContentBlockType, ContentBlock → RIMOSSI (ITERAZIONE #5) - agent-specific
    # StreamEventType, StreamEvent → RIMOSSI (ITERAZIONE #5) - usati solo dall'handler
    StreamingState,
    StreamingRequest,
    StreamContext,
    StreamResult
)
# ContentBlockPool, StreamingProcessor → RIMOSSI (ITERAZIONE #5) - usati solo dall'handler
from agent_streaming_handler import AgentStreamingHandler, ResponseValidator

# ============================================================================
# DATACLASSES E ENUMS - Base robusta per typing
# ============================================================================


# ContentBlockPool → SPOSTATO in streaming_processors.py


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
    """
    Centralized configuration per streaming.
    
    REFACTORING: Parametri agent-specific RIMOSSI:
    - max_extended_calls → gestito da ClaudeHandler
    - extended_token_budget_per_call → gestito da ClaudeHandler
    - total_extended_budget → gestito da ClaudeHandler
    - extended_depth_shallow_max → gestito da ClaudeHandler
    - extended_depth_deep_min → gestito da ClaudeHandler
    
    Il daemon NON sa cosa sia "extended mode" o "thinking".
    """
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
    
    # Compression (GENERICO - non agent-specific)
    compression_safety_buffer: int = 2000  # tokens
    compression_preserve_recent: int = 3  # messages
    compression_sentence_threshold: int = 3
    compression_complexity_high: int = 3
    compression_complexity_medium: int = 2
    compression_text_length_threshold: int = 2000
    
    # Cache
    search_cache_ttl: int = 3600  # seconds
        
    def to_dict(self) -> Dict:
        """Export config as dict"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

@dataclass
class StreamingMetrics:
    """
    Metrics per monitoring performance/health.
    
    REFACTORING: Campi agent-specific RIMOSSI:
    - total_extended_tokens → gestito internamente dall'handler
    - extended_calls_total → gestito internamente dall'handler
    - extended_sessions_total → gestito internamente dall'handler
    - avg_extended_calls_per_session → gestito internamente dall'handler
    
    Il daemon traccia solo metriche GENERICHE.
    """
    # Counters
    requests_total: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    requests_cancelled: int = 0
    
    # Timing
    total_time: float = 0.0
    avg_time_per_request: float = 0.0
    
    # Tokens (GENERICI - non differenziati per tipo)
    total_tokens_processed: int = 0
    total_output_tokens: int = 0
    
    # Errors
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    retry_count_total: int = 0
    
    # Performance
    avg_tokens_per_second: float = 0.0
    peak_tokens_per_second: float = 0.0
    
    def update_request_complete(self, duration: float, tokens: int, success: bool):
        """
        Update metrics dopo request.
        
        REFACTORING: extended_calls parametro RIMOSSO.
        """
        self.requests_total += 1
        
        if success:
            self.requests_successful += 1
        else:
            self.requests_failed += 1
        
        self.total_time += duration
        self.avg_time_per_request = self.total_time / self.requests_total
        
        self.total_tokens_processed += tokens
        
        # Token/sec
        tps = tokens / duration if duration > 0 else 0
        self.avg_tokens_per_second = self.total_tokens_processed / self.total_time if self.total_time > 0 else 0
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
Retries: {self.retry_count_total}
Errors by Type: {dict(sorted(self.errors_by_type.items(), key=lambda x: x[1], reverse=True))}
═══════════════════════════════════════════════════
        """

@dataclass
class DetailedProgress:
    """
    Progress information ricca per UI.
    
    REFACTORING: Campi agent-specific RIMOSSI:
    - extended_calls_completed → gestito internamente dall'handler
    - current_extended_depth → gestito internamente dall'handler
    
    Il daemon traccia solo progress GENERICO.
    """
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
    
    def to_dict(self) -> Dict:
        return self.__dict__.copy()



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

# StreamingProcessor → SPOSTATO in streaming_processors.py

class QtStreamingDaemon:
    """
    Enhanced streaming daemon - AGENT-AGNOSTIC.
    
    REFACTORING: Il daemon NON sa che esistono più agenti (Claude, GPT, ecc.).
    Conosce SOLO "agent_handler" e delega tutto il processing agent-specific.
    
    Features:
    - Parsing SSE corretto (iter_lines)
    - Intelligent error handling per InvalidChunkLength
    - Supporto API multiple (via AgentStreamingHandler facade)
    - Gestione multi-call sessions (handler decides when to stop)
    - Payload compression (delegata all'handler)
    - Sistema pause/resume/abort
    - Metrics generiche
    
    NON conosce: thinking mode, extended mode, budgets, signatures, etc.
    """
    
    def __init__(self, event_system, logger=None, config: StreamingConfig = None):
        """
        Daemon completamente agent-agnostic.
        
        Args:
            event_system: Event system per emissione eventi
            logger: Logger instance
            config: Configurazione streaming
        """
        self.event_system = event_system
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or StreamingConfig()
        
        self.daemon_thread = None
        self.request_queue = queue.Queue()
        self.active_requests = {}
        self.running = False
        
        self.original_payload = None
        self.original_task_summary = ""
        
        # ═══ MULTI-CALL TRACKING - ITERAZIONE #5 ═══
        # NOTA: is_multi_call_session, accumulated_tokens, call_count
        # sono ancora qui per compatibilità con debug panel.
        # current_content_blocks è RIMOSSO - ora gestito dall'handler.
        self.is_multi_call_session = False
        self.current_request = None
        # current_content_blocks → RIMOSSO (ITERAZIONE #5) - usa agent_handler.has_active_session()
        self.accumulated_content_blocks = []  # Per compatibilità StreamContext
        self.accumulated_tokens = 0
        self.call_count = 0
        
        # Agent-specific config (set quando agent_handler viene creato)
        self._uncompressible_types = []  # Default: nessun tipo speciale
        
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
        
        # Config shortcuts (SOLO generici)
        self.chunk_batch_size = self.config.chunk_batch_size
        self.memory_cleanup_interval = self.config.memory_cleanup_interval
        self.gui_update_interval = self.config.gui_update_interval
        
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
        # ═══ ITERAZIONE #5: Nomi generici - eventi possono restare tool-specific ═══
        self.event_system.subscribe('modify_tool_result', self._on_modify_payload_feature_data) 
        self.event_system.subscribe('reexecute_tool', self._on_recalculate_payload_feature_data)
        self.event_system.subscribe('stream_pause', self._on_stream_pause)
        self.event_system.subscribe('stream_resume', self._on_stream_resume)
        self.event_system.subscribe('session_replay', self._on_session_replay)

        self.event_system.subscribe('stream_request', self._handle_stream_request)
        self.event_system.subscribe('stream_cancel', self._handle_stream_cancel)
        
        # ═══ SIMULATION MODE - ITERAZIONE #5: gestito da agent_handler ═══
        # Le variabili simulation_mode, simulation_config, fake_response
        # sono ora INTERNE all'agent_handler
        self.event_system.subscribe('toggle_simulation_mode', self._on_toggle_simulation_mode)
    
    # ═══════════════════════════════════════════════════════════
    # TOOL CONFIGURATION METHODS (Delegate to Registry)
    # ═══════════════════════════════════════════════════════════
    # DAEMON LIFECYCLE
    # ═══════════════════════════════════════════════════════════
        
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

    def _on_modify_payload_feature_data(self, data):
        """
        Modify payload feature data - REBUILD continuation (no execution).
        
        ITERAZIONE #5: Nome generico, delega all'handler.
        Handler usa suo stato interno (_current_content_blocks).
        """
        if not self.agent_handler.has_active_session():
            self.logger.warning("modify_payload_feature_data received but no active session")
            return
        
        modified_result = data.get('result')
        if modified_result is None:
            self.logger.warning("modify_payload_feature_data received but no result")
            return
        
        self.logger.info("Rebuilding continuation with modified feature data")
        
        # ═══ DELEGA ALL'HANDLER (senza content_blocks) ═══
        context = self._create_stream_context()
        continue_payload = self.agent_handler.modify_payload_feature_data(
            modified_result,
            context
        )
        
        if not continue_payload:
            self.logger.error("Handler returned empty payload")
            return
        
        # ═══ UPDATE REQUEST ═══
        self.current_request.payload = continue_payload
        
        # ═══ EMIT ACKNOWLEDGE ═══
        self._emit_interleaved_info(
            message="Feature data modified and payload rebuilt",
            call_number=self.call_count,
            request_type="acknowledge",
            action="modify_payload_feature_data",
            continuation_payload=continue_payload,
            messages_count=len(continue_payload.get('messages', [])),
            payload_size_estimate=len(json.dumps(continue_payload))
        )
        
        self.logger.info("✓ Continuation rebuilt with modified data")

    def _on_recalculate_payload_feature_data(self, data):
        """
        Recalculate payload feature data - EXECUTE + REBUILD.
        
        ITERAZIONE #5: Nome generico, delega all'handler.
        Handler usa suo stato interno (_current_content_blocks).
        """
        if not self.agent_handler.has_active_session():
            self.logger.warning("recalculate_payload_feature_data received but no active session")
            return
        
        feature_name = data.get('tool_name')  # Per ora eventi UI usano tool_name
        modified_input = data.get('tool_input')
        
        if not feature_name or not modified_input:
            self.logger.warning("recalculate_payload_feature_data received but missing data")
            return
        
        self.logger.info(f"Recalculating feature: {feature_name}")
        
        # ═══ DELEGA ALL'HANDLER (senza content_blocks) ═══
        context = self._create_stream_context()
        result, success, continue_payload = self.agent_handler.recalculate_payload_feature_data(
            feature_name,
            modified_input,
            context
        )
        # Sync state back
        self._sync_context_state(context)
        
        if not continue_payload:
            self.logger.error("Handler returned empty payload")
            return
        
        # ═══ UPDATE REQUEST ═══
        self.current_request.payload = continue_payload
        
        # ═══ EMIT ACKNOWLEDGE ═══
        self._emit_interleaved_info(
            message="Feature data recalculated and payload rebuilt",
            call_number=self.call_count,
            request_type="acknowledge",
            action="recalculate_payload_feature_data",
            feature_name=feature_name,
            feature_result=result,
            continuation_payload=continue_payload,
            execution_success=success,
            messages_count=len(continue_payload.get('messages', [])),
            payload_size_estimate=len(json.dumps(continue_payload))
        )
        
        self.logger.info("Feature recalculated and payload updated")
    
    def _on_toggle_step_mode(self, data):
        """Handle step mode toggle from UI"""
        enabled = data.get('enabled', False)
        self.step_by_step_mode = enabled
        self.logger.info(f"Step-by-step mode: {'ENABLED' if enabled else 'DISABLED'}")

    def _on_toggle_simulation_mode(self, data):
        """
        Handle simulation mode toggle from UI.
        
        ITERAZIONE #5: Il daemon rimbalza all'handler che gestisce tutto.
        """
        enabled = data.get('enabled', False)
        
        # ═══ RIMBALZO ALL'HANDLER ═══
        self.agent_handler.toggle_simulation_mode(enabled)
        
        self.logger.info(f"Simulation mode: {'ENABLED' if enabled else 'DISABLED'}")
        
        if enabled:
            # Handler ha già configurato tutto internamente
            # Ora generiamo il fake payload e processiamo
            fake_payload = self.agent_handler.create_simulation_payload()
            
            # Invia fake request
            self._handle_stream_request({
                'request_id': None,  # fake
                'payload': fake_payload,
                'progress_callback': None
            })    

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
            # ITERAZIONE #5: Usa session info dall'handler
            session_info = self.agent_handler.get_session_info()
            self.event_system.emit_event('stream_output_batch', {
                'outputs': [{
                    'type': 'stream_paused_ack',
                    'paused': True,
                    'at_block': session_info.get('content_blocks_count', 0)
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
        
        self.headers = request.payload.pop("headers")
        self.request = request
        
        # Determina provider - LA FACADE DECIDE, NON IL DAEMON
        self.agent_handler = AgentStreamingHandler(
            models_config.SELECTED_CONF, 
            self.event_system, 
            self.logger
        )
        self.api_url = models_config.MODELS_CONF[models_config.SELECTED_CONF]['api_url']
        
        # Cache uncompressible types per questa request (usato da compression logic)
        self._uncompressible_types = self.agent_handler.get_uncompressible_content_types()
        
        # Prepare payload via facade (agent-specific logic)
        # Handler decide internamente se servono tools (accede a ToolRegistry in altro modo)
        self.agent_handler.prepare_payload(request.payload)
        
        # ═══ ITERAZIONE #5: Simulation config tramite handler ═══
        # L'handler decide internamente se/come configurare la simulation
        if self.agent_handler.is_simulation_enabled():
            self.agent_handler.configure_simulation_for_payload(request.payload)
        
        self.original_payload = copy.deepcopy(request.payload)
        payload = request.payload.copy()
        
        # ═══ STEP CHECK ═══
        if self.step_by_step_mode:
            
            # ═══ EMIT DEBUG INFO - COMPLETO ═══
            self._emit_interleaved_info(
                message="Ready to perform initial streaming request",
                call_number=0,
                request_type="initial",
                tools_attached=[tool['name'] for tool in request.payload.get('tools', [])],
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
            
    def _create_stream_context(self) -> StreamContext:
        """
        Crea StreamContext con tutte le dipendenze per process_stream().
        
        ITERAZIONE #3: StreamContext è l'UNICO canale di comunicazione
        tra daemon e handler.
        
        REFACTORING: Budget limits RIMOSSI (max_extended_calls, total_extended_budget).
        L'handler gestisce internamente i propri limiti.
        """
        return StreamContext(
            # Output callbacks
            emit_stream_output=self._emit_stream_output_batch,
            emit_gui_update=self._emit_gui_update_request,
            emit_metrics_update=self._emit_metrics_update,
            emit_interleaved_info=self._emit_interleaved_info,
            
            # Control callbacks
            is_paused=lambda: self.is_paused,
            pause_event=self.pause_event,
            is_aborted=self._is_aborted,
            
            # Execution dependencies
            make_request=self._execute_streaming_with_retry,
            
            # Configuration (GENERICA)
            chunk_batch_size=self.chunk_batch_size,
            gui_update_interval=self.gui_update_interval,
            memory_cleanup_interval=self.memory_cleanup_interval,
            metrics_update_interval=self.config.metrics_update_interval,
            abort_check_interval=self.config.abort_check_interval,
            
            # Runtime state
            original_payload=self.original_payload,
            is_multi_call_session=self.is_multi_call_session,
            step_by_step_mode=self.step_by_step_mode,
            
            # Tracking (questi verranno aggiornati dall'handler)
            accumulated_content_blocks=self.accumulated_content_blocks,
            accumulated_tokens=self.accumulated_tokens,
            call_count=self.call_count
        )
    
    def _execute_streaming_with_retry(self, request: StreamingRequest):
        """Execute streaming con retry logic robusto"""
        payload = request.payload.copy()
        max_tokens = payload.get('max_tokens', 4096)
        headers = self.headers 
        api_url = self.api_url
        
        # Check circuit breaker PRIMA di tentare
        can_attempt, reason = self.circuit_breaker.can_attempt(api_url)
        if not can_attempt:
            self.logger.error(f"Circuit breaker prevents attempt: {reason}")
            return self.agent_handler.create_error_response(
                f"Service temporarily unavailable: {reason}"
            )
        
        # Inizializza risposta
        standard_response = self.agent_handler.init_response()
        
        # Retry logic
        max_retries = 3

        # ═══ SIMULATION MODE - ITERAZIONE #5: tramite handler ═══
        if self.agent_handler.is_simulation_enabled():
            self.logger.info("Using SIMULATION mode (no real API call)")
            response = self.agent_handler.get_simulation_response()
            context = self._create_stream_context()
            result = self.agent_handler.process_stream(
                response, request, standard_response, context
            )
            # Sync context state back to daemon
            self._sync_context_state(context)
            return result.response if result.success else self.agent_handler.create_error_response(result.error or "Unknown error")
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                session.headers.update(headers)
                
                self.logger.info(f"Attempt {attempt + 1}/{max_retries} - Starting streaming")
                
                with session.post(api_url, json=payload, stream=True, timeout=(30, 300)) as response:
                    if response.status_code != 200:
                        raise Exception(f"API Error {response.status_code}: {response.text}")
                    
                    # ═══ ITERAZIONE #3: UNA SOLA CHIAMATA ═══
                    context = self._create_stream_context()
                    result = self.agent_handler.process_stream(
                        response, request, standard_response, context
                    )
                    
                    # Sync context state back to daemon
                    self._sync_context_state(context)
                    
                    if result.success:
                        self.circuit_breaker.record_success(api_url)
                        return result.response
                    
                    if result.partial and result.should_retry:
                        raise Exception("Partial data - retry")
                    
                    return result.response
                    
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
        
        return self.agent_handler.create_error_response("All retries exhausted")
    
    def _sync_context_state(self, context: StreamContext):
        """
        Sincronizza lo stato dal context al daemon.
        
        L'handler aggiorna il context durante il processing,
        il daemon deve riportare queste modifiche al proprio stato.
        """
        self.is_multi_call_session = context.is_multi_call_session
        self.accumulated_content_blocks = context.accumulated_content_blocks
        self.accumulated_tokens = context.accumulated_tokens
        self.call_count = context.call_count

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
            'missing required', 'expected format', 'invalid message format'
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
    
    # _configure_simulation_for_tools → RIMOSSO (ITERAZIONE #5)
    # Ora gestito da agent_handler.configure_simulation_for_payload()
           
    def _reset_multi_call_session(self):
        """Reset multi-call session"""
        self.is_multi_call_session = False
        self.current_request = None
        # ITERAZIONE #5: Reset session state nell'handler
        self.agent_handler.reset_session()
        self.accumulated_content_blocks = []  # Per compatibilità StreamContext
        self.accumulated_tokens = 0
        self.call_count = 0
    
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
        
        FIXED: Preserva SEMPRE uncompressible blocks integralmente perché possono contenere
        dati immutabili (es. signatures, encrypted data).
        
        STRATEGY:
        1. Identifica messaggi CRITICAL (tool calls, special content, long reasoning)
        2. Preserva CRITICAL integralmente
        3. Summarize NON-CRITICAL
        4. Se ancora troppo, compatta CRITICAL selettivamente (MA MAI uncompressible)
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
            # BUT: NEVER compress uncompressible blocks (they have immutable signatures)
            result = self._compress_critical_messages_preserve_uncompressible(result, target_tokens, encoding)
        
        return result

    def _compress_critical_messages_preserve_uncompressible(self, messages, target_tokens, encoding):
        """
        Compress critical messages MA preservando tipi non comprimibili.
        
        I tipi non comprimibili sono definiti dall'agent handler.
        """
        preserved = []
        uncompressible_messages = []
        other_critical = []
        
        # Separate uncompressible from other critical messages
        for msg in messages:
            content = msg.get("content", "")
            has_uncompressible = False
            
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") in self._uncompressible_types:
                            has_uncompressible = True
                            break
            
            if has_uncompressible:
                uncompressible_messages.append(msg)
            else:
                other_critical.append(msg)
        
        # ALWAYS preserve uncompressible messages (immutable signatures)
        preserved.extend(uncompressible_messages)
        
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
        
        FIXED: Extended content blocks sono SEMPRE critical perché contengono
        signature immutabile che deve essere preservata.
        """
        content = msg.get("content", "")
        
        # ═══ UNCOMPRESSIBLE BLOCKS: ALWAYS CRITICAL ═══
        # Certain blocks have immutable signatures that MUST be preserved
        # Removing or modifying them breaks reasoning continuity
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    
                    # Uncompressible types are ALWAYS critical
                    if item_type in self._uncompressible_types:
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
        """Compression selettiva - NEVER compress uncompressible blocks"""
        compressed = []
        
        for msg in messages:
            content = msg.get("content", "")
            
            if isinstance(content, list):
                compressed_content = []
                for item in content:
                    if item.get("type") == "tool_use":
                        tool_input = item.get("input", {})
                        
                        # ↓ CHECK: Se è extended mode, NON comprimere
                        if isinstance(tool_input, dict) and "thought" in tool_input:
                            # PRESERVE uncompressible content integralmente
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
                                # Compatta solo se is compressible
                                compressed_input = self._compress_compressible_input(tool_input)
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
                        
                    elif item.get("type") in self._uncompressible_types:
                        # ↓ CRITICAL: NEVER modify uncompressible blocks
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
    
    def _compress_compressible_input(self, tool_input: Dict) -> Dict:
        """Helper per comprimere input di tool compressible"""
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
                        
                        elif item_type in self._uncompressible_types:
                            # Skip uncompressible in extreme mode (API filtrerebbe anyway)
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
            'multi_call_count': self.call_count,  # REFACTORING: nome generico
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
        
        # REFACTORING: Metriche generiche - nessun riferimento agent-specific
        metrics_data = {
            'total_tokens': self.accumulated_tokens,
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

