"""
streaming_types.py - Definizioni base per streaming.

ESTRATTO DA: streaming_daemon.py
SCOPO: Evitare dipendenze circolari tra moduli

Contiene:
    - ContentBlockType (Enum)
    - StreamEventType (Enum)
    - StreamEvent (dataclass)
    - ContentBlock (dataclass)
    - StreamingState (Enum)
    - StreamingRequest (dataclass)
    - StreamContext (dataclass) - ITERAZIONE #3
    - StreamResult (dataclass) - ITERAZIONE #3
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List, TYPE_CHECKING
import threading

if TYPE_CHECKING:
    from advanced_tool_executors import ToolRegistry


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
            result["thinking"] = self.content  # Plaintext
            if self.signature:
                result["signature"] = self.signature
                
        elif self.type == ContentBlockType.REDACTED_THINKING:
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


class StreamingState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StreamingRequest:
    """
    Request per streaming - GENERICO (no agent-specific fields).
    
    REFACTORING: extended_mode RIMOSSO - il daemon non deve sapere
    se l'handler sta usando "extended mode" o qualsiasi altra
    feature agent-specific.
    """
    request_id: str
    payload: Dict
    progress_callback: Optional[Callable]
    state: StreamingState = StreamingState.PENDING
    result: Optional[Dict] = None
    error: Optional[Exception] = None
    progress: float = 0.0
    chunks_processed: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# STREAM CONTEXT - Dipendenze per process_stream()
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StreamContext:
    """
    Context per process_stream() - UNICO canale di comunicazione daemon→handler.
    
    REFACTORING: Budget limits e tool_registry RIMOSSI.
    - Budget: gestiti INTERNAMENTE dall'handler
    - tool_registry: l'handler vi accede direttamente (non passa per daemon)
    
    Il daemon non deve sapere nulla di "extended mode", "thinking budgets" o "tools".
    
    Contiene:
    - Callbacks per output (emit)
    - Callbacks per controllo (pause, abort)
    - Dipendenze (make_request per continuation)
    - Configurazione GENERICA
    - Stato runtime GENERICO
    """
    
    # ═══ OUTPUT CALLBACKS ═══
    emit_stream_output: Callable[[List[Dict]], None]  # Batch di output per GUI
    emit_gui_update: Callable[[], None]               # Request GUI refresh
    emit_metrics_update: Callable[[], None]           # Metrics per dashboard
    emit_interleaved_info: Callable[..., None]        # Debug info (kwargs)
    
    # ═══ CONTROL CALLBACKS ═══
    is_paused: Callable[[], bool]                     # Check se in pausa
    pause_event: threading.Event                      # Event per blocking wait
    is_aborted: Callable[[str], bool]                 # Check se request abortita
    
    # ═══ EXECUTION DEPENDENCIES ═══
    make_request: Callable[['StreamingRequest'], Dict]  # Per continuation
    
    # ═══ CONFIGURATION (GENERICA - no agent-specific) ═══
    chunk_batch_size: int = 5                         # Batch size per emit
    gui_update_interval: int = 10                     # Chunks tra GUI updates  
    memory_cleanup_interval: int = 100                # Chunks tra gc.collect()
    metrics_update_interval: int = 50                 # Chunks tra metrics emit
    abort_check_interval: int = 5                     # Chunks tra abort checks
    
    # ═══ RUNTIME STATE (GENERICO) ═══
    original_payload: Optional[Dict] = None           # Payload originale (per continuation)
    is_multi_call_session: bool = False               # Se in sessione multi-call
    step_by_step_mode: bool = False                   # Debug step mode
    
    # ═══ TRACKING (aggiornati dall'handler) ═══
    accumulated_content_blocks: List[Dict] = field(default_factory=list)
    accumulated_tokens: int = 0
    call_count: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# STREAM RESULT - Risultato di process_stream()
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StreamResult:
    """
    Risultato di process_stream() - il daemon riceve SOLO questo.
    
    Tutti i dettagli del processing sono nascosti nell'handler.
    """
    success: bool
    response: Optional[Dict] = None
    partial: bool = False
    should_retry: bool = False
    aborted: bool = False
    error: Optional[str] = None
    chunks_received: int = 0
    bytes_read: int = 0
