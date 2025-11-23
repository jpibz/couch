"""
GptFakeStreamingResponse - Simulazione streaming GPT/OpenAI

Basato su ClaudeFakeStreamingResponse ma con formato OpenAI.

DIFFERENZE FORMATO:
- Claude: SSE con content_block_start/delta/stop
- GPT: SSE con choices[0].delta.content/tool_calls

FLOW GPT:
1. First chunk: id, model, role
2. Content deltas: choices[0].delta.content
3. Tool call deltas: choices[0].delta.tool_calls (progressivi)
4. Finish: choices[0].finish_reason = 'stop' | 'tool_calls'
5. Usage: ultimo chunk con usage

Config structure:
{
    'include_text': bool,
    'text_content': str,
    'include_tool': bool,
    'tool_name': str,
    'tool_input': dict,
    'timing': 'fast' | 'normal' | 'slow'
}
"""

import time
import uuid
import json
import random
import logging
from typing import List, Dict, Optional


class GptFakeStreamingResponse:
    """
    Simula requests.Response.iter_lines() per GPT testing senza API calls.
    
    SUPPORTA:
    - Text streaming
    - Tool calls (function calling)
    - Multi-turn presets per tool calls
    - Timing realistico
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        self.events = []
        self.generation_errors = []
        
        # Multi-turn presets tracking
        self.turn_counters = {}
        self._init_multi_turn_presets()
        
        # Generate unique IDs
        self.chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        self.created = int(time.time())
        self.system_fingerprint = f"fp_{uuid.uuid4().hex[:10]}"  # System fingerprint
    
    def _default_config(self) -> Dict:
        """Default: text only, no tool"""
        return {
            'include_text': True,
            'include_tool': False,
            'tool_name': None,
            'timing': 'fast'
        }
    
    def _init_multi_turn_presets(self):
        """
        Initialize multi-turn tool presets (come Claude).
        
        MULTI-TURN: Per tool che richiedono multiple chiamate.
        Esempio: bash che esegue comandi sequenziali.
        """
        self.multi_turn_presets = {
            'bash': [
                # Turn 1: ls
                {
                    'command': 'ls -la /mnt/user-data/uploads',
                    'description': 'List uploaded files'
                },
                # Turn 2: view
                {
                    'command': 'cat /mnt/user-data/uploads/file.txt',
                    'description': 'Read file content'
                },
                # Turn 3: finale
                {
                    'command': 'echo "Analysis complete"',
                    'description': 'Complete analysis'
                }
            ],
            'web_search': [
                # Turn 1: search
                {
                    'query': 'Python asyncio best practices',
                    'num_results': 5
                },
                # Turn 2: refine
                {
                    'query': 'Python asyncio error handling',
                    'num_results': 3
                }
            ]
        }
        
        # Initialize counters
        for tool_name in self.multi_turn_presets:
            self.turn_counters[tool_name] = 0
    
    def _init_turn(self):
        """Initialize new turn - genera eventi"""
        try:
            self.events = self._generate_events()
            self._validate_events()
        except Exception as e:
            self.logger.error(f"Event generation failed: {e}")
            self.generation_errors.append(str(e))
            # Generate minimal fallback
            self.events = self._generate_minimal_fallback()
    
    def iter_lines(self, decode_unicode=True):
        """
        Generator compatibile con requests.Response.iter_lines()
        
        Emette stringhe in formato SSE standard:
        - "data: {json}" per ogni chunk
        - "data: [DONE]" per terminare stream
        
        Yields:
            str: SSE formatted lines
        """
        if self.generation_errors:
            self.logger.error(f"Cannot iterate: {self.generation_errors}")
            yield "data: [DONE]"
            return
        
        # Timing configuration
        timing_config = {
            'fast': {'min': 0.020, 'max': 0.050, 'variance': 0.010},
            'normal': {'min': 0.050, 'max': 0.100, 'variance': 0.020},
            'slow': {'min': 0.100, 'max': 0.200, 'variance': 0.050}
        }
        
        timing = timing_config.get(
            self.config.get('timing', 'fast'),
            timing_config['fast']
        )
        
        event_count = len(self.events)
        self.logger.info(f"GPT SIMULATION: Starting iteration over {event_count} events")
        
        for idx, event_dict in enumerate(self.events):
            try:
                # Timing realistico con varianza
                base_delay = random.uniform(timing['min'], timing['max'])
                variance = random.uniform(-timing['variance'], timing['variance'])
                delay = max(0.001, base_delay + variance)
                time.sleep(delay)
                
                # Serialize event to JSON
                try:
                    json_str = json.dumps(event_dict, ensure_ascii=False, separators=(',', ':'))
                except TypeError as e:
                    self.logger.error(f"Event {idx} serialization failed: {e}")
                    continue
                
                # Emit SSE formatted line
                sse_line = f"data: {json_str}"
                
                # Debug log
                if 'finish_reason' in str(event_dict):
                    self.logger.debug(f"Event {idx}/{event_count}: finish_reason")
                
                yield sse_line
                
                # Linea vuota tra eventi (SSE standard)
                if idx < event_count - 1:
                    yield ""
            
            except Exception as e:
                self.logger.error(f"Error yielding event {idx}: {e}")
                continue
        
        # Stream terminator
        self.logger.info("GPT SIMULATION: Stream complete, sending [DONE]")
        yield "data: [DONE]"
    
    def _validate_events(self):
        """Valida eventi generati"""
        if not self.events:
            raise ValueError("No events generated")
        
        # Verifica primo evento ha id e model
        first = self.events[0]
        if not first.get('id'):
            raise ValueError("First event missing id")
        if not first.get('model'):
            raise ValueError("First event missing model")
        
        # Verifica ultimo evento ha finish_reason
        last_with_choices = None
        for event in reversed(self.events):
            if event.get('choices'):
                last_with_choices = event
                break
        
        if last_with_choices:
            finish_reason = last_with_choices['choices'][0].get('finish_reason')
            if not finish_reason:
                raise ValueError("Last event with choices missing finish_reason")
        
        self.logger.debug(f"Event validation passed: {len(self.events)} events")
    
    def _generate_events(self) -> List[Dict]:
        """
        Genera lista completa eventi per singola response.
        
        Flow GPT:
        1. First chunk (id, model, role)
        2. Content deltas (se include_text)
        3. Tool call deltas (se include_tool)
        4. Finish chunk (finish_reason)
        5. Usage chunk (opzionale)
        
        Returns:
            List[Dict]: Eventi GPT formatted
        """
        events = []
        
        # 1. FIRST CHUNK (role + metadata)
        events.append(self._build_first_chunk())
        
        # 2. CONTENT DELTAS (opzionale)
        if self.config.get('include_text', False):
            text_content = self._get_sample_text()
            events.extend(self._build_content_deltas(text_content))
        
        # 3. TOOL CALL DELTAS (opzionale)
        if self.config.get('include_tool', False):
            tool_name = self.config.get('tool_name', 'web_search')
            tool_input = self.config.get('tool_input')
            events.extend(self._build_tool_call_deltas(tool_name, tool_input))
        
        # 4. FINISH CHUNK
        finish_reason = "tool_calls" if self.config.get('include_tool') else "stop"
        events.append(self._build_finish_chunk(finish_reason))
        
        # 5. USAGE CHUNK (opzionale - ultimo chunk)
        events.append(self._build_usage_chunk())
        
        return events
    
    def _build_first_chunk(self) -> Dict:
        """Build first chunk con metadata + role"""
        return {
            "id": self.chat_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": "gpt-4-simulation",
            "system_fingerprint": self.system_fingerprint,
            "choices": [{
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": None
            }]
        }
    
    def _build_content_deltas(self, text: str) -> List[Dict]:
        """
        Build content delta chunks.
        
        GPT streaming: choices[0].delta.content con pezzi di testo.
        """
        events = []
        chunks = self._split_into_chunks(text, chunk_size=40)
        
        for chunk in chunks:
            events.append({
                "id": self.chat_id,
                "object": "chat.completion.chunk",
                "created": self.created,
                "model": "gpt-4-simulation",
                "system_fingerprint": self.system_fingerprint,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": chunk
                    },
                    "finish_reason": None
                }]
            })
        
        return events
    
    def _build_tool_call_deltas(self, tool_name: str, tool_input: Optional[Dict]) -> List[Dict]:
        """
        Build tool call delta chunks.
        
        GPT tool calls arrivano progressivamente:
        1. First: {index, id, type, function: {name}}
        2. Then: {index, function: {arguments: "{"}}
        3. Then: {index, function: {arguments: "param"}}
        4. ...
        """
        events = []
        
        # Get tool input (preset o custom)
        if tool_input is None:
            tool_input = self._get_preset_tool_input(tool_name)
        
        # Serialize tool input
        arguments_json = json.dumps(tool_input, ensure_ascii=False)
        
        # Generate unique tool call id
        tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
        
        # 1. FIRST DELTA: id + name
        events.append({
            "id": self.chat_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": "gpt-4-simulation",
            "system_fingerprint": self.system_fingerprint,
            "choices": [{
                "index": 0,
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": ""
                        }
                    }]
                },
                "finish_reason": None
            }]
        })
        
        # 2. ARGUMENTS DELTAS (progressivi)
        argument_chunks = self._split_json_progressive(arguments_json)
        
        for chunk in argument_chunks:
            events.append({
                "id": self.chat_id,
                "object": "chat.completion.chunk",
                "created": self.created,
                "model": "gpt-4-simulation",
                "system_fingerprint": self.system_fingerprint,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "tool_calls": [{
                            "index": 0,
                            "function": {
                                "arguments": chunk  # _split_json_progressive ritorna già i delta puri
                            }
                        }]
                    },
                    "finish_reason": None
                }]
            })
        
        return events
    
    def _build_finish_chunk(self, finish_reason: str) -> Dict:
        """Build finish chunk con finish_reason"""
        return {
            "id": self.chat_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": "gpt-4-simulation",
            "system_fingerprint": self.system_fingerprint,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": finish_reason
            }]
        }
    
    def _build_usage_chunk(self) -> Dict:
        """
        Build usage chunk (ultimo chunk).
        
        Opzionale in GPT streaming se stream_options={"include_usage": true}
        """
        tokens = self._estimate_tokens()
        
        return {
            "id": self.chat_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": "gpt-4-simulation",
            "system_fingerprint": self.system_fingerprint,
            "choices": [],  # Empty choices nell'usage chunk
            "usage": {
                "prompt_tokens": tokens['prompt'],
                "completion_tokens": tokens['completion'],
                "total_tokens": tokens['total']
            }
        }
    
    def _generate_minimal_fallback(self) -> List[Dict]:
        """Generate minimal valid event sequence per fallback"""
        return [
            self._build_first_chunk(),
            {
                "id": self.chat_id,
                "object": "chat.completion.chunk",
                "created": self.created,
                "model": "gpt-4-simulation",
                "system_fingerprint": self.system_fingerprint,
                "choices": [{
                    "index": 0,
                    "delta": {"content": "Simulation error occurred"},
                    "finish_reason": None
                }]
            },
            self._build_finish_chunk("stop"),
            self._build_usage_chunk()
        ]
    
    def _get_preset_tool_input(self, tool_name: str) -> Dict:
        """
        Get preset input per tool - MULTI-TURN SUPPORT.
        
        Se tool ha preset multi-turno:
        1. Restituisce preset[contatore]
        2. Incrementa contatore (se non all'ultimo)
        3. Rimane sull'ultimo preset se overflow
        """
        # Check multi-turn presets
        if tool_name in self.multi_turn_presets:
            presets_list = self.multi_turn_presets[tool_name]
            current_counter = self.turn_counters.get(tool_name, 0)
            
            # Get preset corrente
            preset = presets_list[current_counter]
            
            # Incrementa SOLO se non all'ultimo
            if current_counter < len(presets_list) - 1:
                self.turn_counters[tool_name] += 1
            
            return preset
        
        # Fallback: preset singolo statico
        presets = {
            'bash_tool': {
                'command': 'ls -la /mnt/user-data/uploads',
                'description': 'List uploaded files'
            },
            'create_file': {
                'file_text': 'FILE CREATED WITH CREATE FILE TOOL',
                'path': '/home/claude/script.py',
                'description': 'Create script file'
            },
            'str_replace': {
                'path': '/tmp/test.txt',
                'old_str': 'old text',
                'new_str': 'new text',
                'description': 'Replace text'
            },
            'view': {
                'path': '/home/claude/script.py',
                'description': 'View file'
            },
            'web_search': {
                'query': 'Python asyncio best practices'
            },
            'web_fetch': {
                'url': 'https://docs.python.org/3/library/asyncio.html'
            }
        }
        return presets.get(tool_name, {'query': 'test'})
    
    def reset_turn_counters(self, tool_names: List[str] = None):
        """Reset turn counters per specific tools o tutti"""
        if tool_names:
            for name in tool_names:
                if name in self.turn_counters:
                    self.turn_counters[name] = 0
        else:
            for name in self.turn_counters:
                self.turn_counters[name] = 0
    
    # ═══════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════
    
    def _get_sample_text(self) -> str:
        """Sample text per simulation"""
        return self.config.get('text_content') or (
            "This is simulated GPT output. Lorem ipsum dolor sit amet, "
            "consectetur adipiscing elit. The model is generating realistic "
            "streaming responses for testing purposes."
        )
    
    def _split_into_chunks(self, text: str, chunk_size: int = 40) -> List[str]:
        """Split text in realistic streaming chunks"""
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_with_space = word + " "
            if current_length + len(word_with_space) > chunk_size and current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = [word_with_space]
                current_length = len(word_with_space)
            else:
                current_chunk.append(word_with_space)
                current_length += len(word_with_space)
        
        if current_chunk:
            chunks.append("".join(current_chunk).rstrip())
        
        return chunks
    
    def _split_json_progressive(self, json_str: str) -> List[str]:
        """
        Split JSON in progressive deltas.
        
        Returns incremental pieces: ["", "{", "{\"", "{\"key", ...]
        """
        # Simula streaming progressivo JSON
        deltas = []
        step = 15  # Chars per step
        
        prev_chunk = ""
        for i in range(step, len(json_str) + step, step):
            current_chunk = json_str[:min(i, len(json_str))]
            deltas.append(current_chunk[len(prev_chunk):])  # Solo il delta
            prev_chunk = current_chunk
        
        return deltas
    
    def _estimate_tokens(self) -> Dict[str, int]:
        """Stima tokens per usage"""
        prompt_tokens = 100  # Base
        completion_tokens = 50  # Base
        
        if self.config.get('include_text'):
            completion_tokens += 100
        
        if self.config.get('include_tool'):
            completion_tokens += 50
        
        return {
            'prompt': prompt_tokens,
            'completion': completion_tokens,
            'total': prompt_tokens + completion_tokens
        }
    
    # ═══════════════════════════════════════════════════════════
    # STATIC FACTORY METHODS
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def text_only():
        """Scenario: solo text response"""
        return {
            'include_text': True,
            'include_tool': False,
            'timing': 'fast'
        }
    
    @staticmethod
    def tool_only(tool_name: str, tool_input: Optional[Dict] = None):
        """Scenario: solo tool call (no text)"""
        config = {
            'include_text': False,
            'include_tool': True,
            'tool_name': tool_name,
            'timing': 'fast'
        }
        if tool_input:
            config['tool_input'] = tool_input
        return config
    
    @staticmethod
    def text_and_tool(tool_name: str, tool_input: Optional[Dict] = None):
        """Scenario: text + tool call"""
        config = {
            'include_text': True,
            'include_tool': True,
            'tool_name': tool_name,
            'timing': 'fast'
        }
        if tool_input:
            config['tool_input'] = tool_input
        return config
    
    @staticmethod
    def web_search_scenario():
        """Scenario: web search tool"""
        return GptFakeStreamingResponse.tool_only('web_search', {
            'query': 'Python best practices'
        })
    
    @staticmethod
    def bash_scenario(command: Optional[str] = None):
        """Scenario: bash tool"""
        return GptFakeStreamingResponse.tool_only('bash_tool', {
            'command': command or 'ls -la',
            'description': 'Execute bash command'
        })
    
    @staticmethod
    def create_file_scenario(path: str = '/home/claude/test.py'):
        """Scenario: create_file tool"""
        return GptFakeStreamingResponse.tool_only('create_file', {
            'path': path,
            'file_text': '# Auto-generated file\nprint("Hello World")',
            'description': 'Create Python file'
        })
    
    @staticmethod
    def view_scenario(path: str = '/home/claude/test.py'):
        """Scenario: view tool"""
        return GptFakeStreamingResponse.tool_only('view', {
            'path': path,
            'description': 'View file content'
        })
    
    @staticmethod
    def multi_turn_bash():
        """Scenario: multi-turn bash execution"""
        return GptFakeStreamingResponse.tool_only('bash')  # Usa preset multi-turn


# ═══════════════════════════════════════════════════════════
# USAGE EXAMPLE (commented out)
# ═══════════════════════════════════════════════════════════

"""
# Text only
config = GptFakeStreamingResponse.text_only()
fake_response = GptFakeStreamingResponse(config)
fake_response._init_turn()
for line in fake_response.iter_lines():
    print(line)

# Tool call
config = GptFakeStreamingResponse.tool_only('web_search', {'query': 'test'})
fake_response = GptFakeStreamingResponse(config)
fake_response._init_turn()
for line in fake_response.iter_lines():
    print(line)

# Text + Tool
config = GptFakeStreamingResponse.text_and_tool('bash_tool')
fake_response = GptFakeStreamingResponse(config)
fake_response._init_turn()
for line in fake_response.iter_lines():
    print(line)
"""
