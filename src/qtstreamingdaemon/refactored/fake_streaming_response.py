import time
import uuid
import json
import random
import logging


class FakeStreamingResponse:
    """
    Simula requests.Response.iter_lines() per testing senza API calls.
    
    INTERLEAVED MODE (thinking enabled):
    - Thinking block: SEMPRE presente
    - Text block: opzionale
    - Tool use block: opzionale
    
    Flow: message_start → thinking → [text] → [tool] → message_delta → message_stop
    
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
    
    def __init__(self, config=None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        self.events = []
        self.generation_errors = []

        # Multi-turn presets tracking
        self.turn_counters = {}
        self._init_multi_turn_presets()
    
    def _default_config(self):
        """Default: thinking + text, no tool"""
        return {
            'include_text': True,
            'include_tool': False,
            'tool_name': None,
            'timing': 'fast'
        }

    def _init_turn(self):

        # Generate events
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
        - "data: {json}" per ogni evento
        - Linea vuota tra eventi (opzionale, daemon skippa)
        - "data: [DONE]" per terminare stream
        
        Args:
            decode_unicode: bool - Ignored (always True for compatibility)
        
        Yields:
            str: SSE formatted lines
        """
        if self.generation_errors:
            self.logger.error(f"Cannot iterate: generation had errors: {self.generation_errors}")
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
        self.logger.info(f"SIMULATION: Starting iteration over {event_count} events")
        
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
                    # Skip malformed event
                    continue
                
                # Emit SSE formatted line
                sse_line = f"data: {json_str}"
                
                # Debug log per eventi importanti
                event_type = event_dict.get('type', 'unknown')
                if event_type in ['message_start', 'message_delta', 'message_stop']:
                    self.logger.debug(f"Event {idx}/{event_count}: {event_type}")
                
                yield sse_line
                
                # Opzionale: linea vuota tra eventi (SSE standard)
                # Daemon skippa comunque, ma è più "realistic"
                if idx < event_count - 1:
                    yield ""
                    
            except Exception as e:
                self.logger.error(f"Error yielding event {idx}: {e}")
                # Continue to next event
                continue
        
        # Stream terminator
        self.logger.info("SIMULATION: Stream complete, sending [DONE]")
        yield "data: [DONE]"
    
    def _validate_events(self):
        """Valida eventi generati per correttezza strutturale"""
        if not self.events:
            raise ValueError("No events generated")
        
        event_types = [e.get('type') for e in self.events]
        
        required = ['message_start', 'content_block_start', 'message_delta', 'message_stop']
        for req_type in required:
            if req_type not in event_types:
                raise ValueError(f"Missing required event: {req_type}")
        
        if event_types[0] != 'message_start':
            raise ValueError(f"First event must be message_start, got {event_types[0]}")
        
        if event_types[-1] != 'message_stop':
            raise ValueError(f"Last event must be message_stop, got {event_types[-1]}")
        
        # Verifica signature_delta in thinking block
        has_thinking_start = False
        has_signature_delta = False
        
        for event in self.events:
            if event.get('type') == 'content_block_start':
                cb = event.get('content_block', {})
                if cb.get('type') == 'thinking':
                    has_thinking_start = True
            
            if event.get('type') == 'content_block_delta':
                delta = event.get('delta', {})
                if delta.get('type') == 'signature_delta':
                    has_signature_delta = True
        
        if has_thinking_start and not has_signature_delta:
            raise ValueError("Thinking block present but missing signature_delta")
        
        self.logger.debug(f"Event validation passed: {len(self.events)} events")
    
    def _generate_events(self):
        """
        Genera lista completa eventi per singola response.
        
        Flow SSE standard:
        1. message_start
        2. thinking block (sempre)
        3. text block (opzionale)
        4. tool block (opzionale)
        5. message_delta (con stop_reason + usage)
        6. message_stop
        
        Returns:
            List[Dict]: Eventi SSE formatted
        """
        events = []
        block_index = 0
        
        # 1. MESSAGE START (obbligatorio)
        events.append(self._build_message_start())
        
        # 2. THINKING BLOCK (sempre presente in interleaved)
        thinking_content = self._get_lorem_ipsum()
        events.extend(self._build_thinking_block(block_index, thinking_content))
        block_index += 1
        
        # 3. TEXT BLOCK (opzionale)
        if self.config.get('include_text', False):
            text_content = self._get_lorem_ipsum()
            events.extend(self._build_text_block(block_index, text_content))
            block_index += 1
        
        # 4. TOOL USE BLOCK (opzionale)
        if self.config.get('include_tool', False):
            tool_name = self.config.get('tool_name', 'bash')
            tool_input = self.config.get('tool_input')
            events.extend(self._build_tool_block(block_index, tool_name, tool_input))
            block_index += 1
        
        # 5. MESSAGE DELTA (obbligatorio - con stop_reason + usage)
        stop_reason = "tool_use" if self.config.get('include_tool') else "end_turn"
        output_tokens = self._estimate_output_tokens()
        events.append(self._build_message_delta(stop_reason, output_tokens))
        
        # 6. MESSAGE STOP (obbligatorio)
        events.append(self._build_message_stop())
        
        return events
    
    # ═══════════════════════════════════════════════════════════
    # EVENT BUILDERS - Formato esatto SSE
    # ═══════════════════════════════════════════════════════════
    
    def _build_message_start(self):
        """
        Build message_start event.
        
        Formato esatto:
        {
            "type": "message_start",
            "message": {
                "id": "msg_...",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "claude-sonnet-4-20250514",
                "stop_reason": null,
                "stop_sequence": null,
                "usage": {"input_tokens": N}
            }
        }
        """
        return {
            "type": "message_start",
            "message": {
                "id": f"msg_{uuid.uuid4().hex[:16]}",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "claude-sonnet-4-20250514",
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 100  # Fixed per simulation
                }
            }
        }
    
    def _build_message_delta(self, stop_reason, output_tokens):
        """
        Build message_delta event con stop_reason + usage.
        
        CRITICAL: Daemon usa questo per:
        - stop_reason → determina se tool_use o end_turn
        - output_tokens → accumula per usage totale
        
        Formato esatto:
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn" | "tool_use"},
            "usage": {"output_tokens": N}
        }
        """
        return {
            "type": "message_delta",
            "delta": {
                "stop_reason": stop_reason
            },
            "usage": {
                "output_tokens": output_tokens
            }
        }
    
    def _build_message_stop(self):
        """Build message_stop event"""
        return {
            "type": "message_stop"
        }
    
    def _build_thinking_block(self, index, content):
        """
        Build thinking block con signature_delta.
        
        Flow CORRETTO:
        1. content_block_start (con signature in content_block)
        2. content_block_delta (thinking_delta) × N
        3. content_block_delta (signature_delta) ← CRITICAL
        4. content_block_stop
        """
        events = []
        signature = f"sig_{uuid.uuid4().hex[:16]}"
        chunks = self._split_into_chunks(content, 50)
        
        # 1. Start con signature
        events.append({
            "type": "content_block_start",
            "index": index,
            "content_block": {
                "type": "thinking",
                "signature": signature
            }
        })
        
        # 2. Thinking deltas (contenuto)
        for chunk in chunks:
            events.append({
                "type": "content_block_delta",
                "index": index,
                "delta": {
                    "type": "thinking_delta",
                    "thinking": chunk
                }
            })
        
        # 3. SIGNATURE DELTA (CRITICAL - mancava questo!)
        events.append({
            "type": "content_block_delta",
            "index": index,
            "delta": {
                "type": "signature_delta",
                "signature": signature
            }
        })
        
        # 4. Stop
        events.append({
            "type": "content_block_stop",
            "index": index
        })
        
        return events
    
    def _build_text_block(self, index, content):
        """
        Build text block.
        
        Eventi:
        - content_block_start
        - content_block_delta (text_delta) × N
        - content_block_stop
        """
        events = []
        chunks = self._split_into_chunks(content, 40)
        
        # Start
        events.append({
            "type": "content_block_start",
            "index": index,
            "content_block": {
                "type": "text",
                "text": ""
            }
        })
        
        # Deltas
        for chunk in chunks:
            events.append({
                "type": "content_block_delta",
                "index": index,
                "delta": {
                    "type": "text_delta",
                    "text": chunk
                }
            })
        
        # Stop
        events.append({
            "type": "content_block_stop",
            "index": index
        })
        
        return events
    
    def _build_tool_block(self, index, tool_name, tool_input):
        """
        Build tool_use block.
        
        Eventi:
        - content_block_start (con id, name)
        - content_block_delta (input_json_delta) × N
        - content_block_stop
        """
        events = []
        tool_id = f"toolu_{uuid.uuid4().hex[:16]}"
        
        # Get input
        if tool_input is None:
            tool_input = self._get_preset_tool_input(tool_name)
        
        # Start
        events.append({
            "type": "content_block_start",
            "index": index,
            "content_block": {
                "type": "tool_use",
                "id": tool_id,
                "name": tool_name
            }
        })
        
        # JSON progressive streaming
        json_str = json.dumps(tool_input, ensure_ascii=False, separators=(',', ':'))
        json_chunks = self._split_into_chunks(json_str)
        
        for partial_json in json_chunks:
            events.append({
                "type": "content_block_delta",
                "index": index,
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": partial_json
                }
            })
        
        # Stop
        events.append({
            "type": "content_block_stop",
            "index": index
        })
        
        return events
    
    # ═══════════════════════════════════════════════════════════
    # TOOL PRESETS
    # ═══════════════════════════════════════════════════════════

    def _init_multi_turn_presets(self):
        """
        Initialize multi-turn presets per bash_tool e view.
        
        WORKFLOW REALISTICO:
        - bash CREA files/contenuto
        - view VERIFICA quello che bash ha creato
        - bash PROCESSA ulteriormente
        - view ISPEZIONA risultati
        """
        self.multi_turn_presets = {
            'bash_tool': [
                # Turn 1: Crea script Python di test
                {
                    'command': 'cat > /home/claude/script.py << \'EOF\'\nimport sys\nimport random\n\ndef greet(name):\n    return f"Hello, {name}!"\n\ndef calculate_sum(numbers):\n    return sum(numbers)\n\nif __name__ == "__main__":\n    print(greet("Claude"))\n    nums = [random.randint(1, 10) for _ in range(5)]\n    print(f"Numbers: {nums}")\n    print(f"Sum: {calculate_sum(nums)}")\nEOF',
                    'description': 'Create test Python script'
                },
                # Turn 2: Esegui script e salva output
                {
                    'command': 'python /home/claude/script.py > /home/claude/output.txt 2>&1',
                    'description': 'Execute script and save output'
                },
                # Turn 3: Crea file di dati
                {
                    'command': 'echo -e "line 1: test data\\nline 2: more data\\nline 3: final data" > /home/claude/data.txt',
                    'description': 'Create data file'
                },
                # Turn 4: Analizza file creato
                {
                    'command': 'wc -l /home/claude/test_script.py /home/claude/data.txt',
                    'description': 'Count lines in created files'
                },
                # Turn 5: Cerca pattern nel codice
                {
                    'command': 'grep -n "def " /home/claude/script.py',
                    'description': 'Find function definitions in script'
                }
            ],
            'view': [
                # Turn 1: Verifica directory iniziale
                {
                    'path': '/home/claude',
                    'description': 'Check working directory before operations'
                },
                # Turn 2: Ispeziona script creato da bash
                {
                    'path': '/home/claude/script.py',
                    'description': 'View the Python script created by bash'
                },
                # Turn 3: Guarda output esecuzione
                {
                    'path': '/home/claude/output.txt',
                    'description': 'View script execution output'
                },
                # Turn 4: Ispeziona file dati con range
                {
                    'path': '/home/claude/data.txt',
                    'view_range': [1, 2],
                    'description': 'View first 2 lines of data file'
                },
                # Turn 5: Verifica directory finale con tutto creato
                {
                    'path': '/home/claude',
                    'description': 'View directory after all bash operations'
                }
            ]
        }
        
        # Initialize counters to 0
        for tool_name in self.multi_turn_presets:
            self.turn_counters[tool_name] = 0
    
    def reset_turn_counters(self, tool_name: str = None):
        """
        Reset contatori multi-turno.
        
        Args:
            tool_name: Tool specifico da resettare, None = reset ALL
        """
        if tool_name:
            if tool_name in self.turn_counters:
                self.turn_counters[tool_name] = 0
                self.logger.debug(f"Reset counter for '{tool_name}'")
        else:
            # Reset all counters
            for name in self.turn_counters:
                self.turn_counters[name] = 0
            self.logger.debug("Reset all turn counters")
    
    def _get_preset_tool_input(self, tool_name):
        """
        Get preset input per tool - MULTI-TURN SUPPORT.
        
        Se tool ha preset multi-turno:
        1. Restituisce preset[contatore]
        2. Incrementa contatore (se non all'ultimo)
        3. Edge case: rimane sull'ultimo preset se overflow
        
        Altrimenti: preset singolo statico.
        """
        # Check se tool ha preset multi-turno
        if tool_name in self.multi_turn_presets:
            presets_list = self.multi_turn_presets[tool_name]
            current_counter = self.turn_counters.get(tool_name, 0)
            
            # Get preset corrente
            preset = presets_list[current_counter]
            
            # Incrementa SOLO se non all'ultimo
            if current_counter < len(presets_list) - 1:
                self.turn_counters[tool_name] += 1
            # Else: rimane sull'ultimo preset per successive chiamate
            
            return preset
        
        # Fallback: preset singolo statico (legacy)
        presets = {
            'bash': {
                'command': 'ls -la /mnt/user-data/uploads',
                'description': 'List uploaded files'
            },
            'create_file': {
                'file_text': 'FILE CREATED WITH CREATE FILE TOOL',
                'path': '/home/claude/script.py'
            },
            'str_replace': {
                'path': '/tmp/test.txt',
                'old_str': 'CREATE FILE TOOL',
                'new_str': 'create_file',
                'description': 'Enable debug mode'
            },
            'view': {
                'view_range': None,
                'path': '/home/claude/script.py'
            },
            'web_search': {
                'query': 'Python asyncio best practices',
                'num_results': 5
            },
            'web_fetch': {
                'url': 'https://docs.python.org/3/library/asyncio.html'
            },
            'conversation_search': {
                'query': 'streaming architecture',
                'max_results': 5
            },
            'memory_user_edits': {
                'command': 'view'
            },
            'sequencer': {
                'step_description': 'Analyze codebase structure',
                'findings': 'Found 3 main modules with ~2500 total lines',
                'next_action': 'Review core module for refactoring'
            }
        }
        return presets.get(tool_name, {'query': 'test'})
    
    # ═══════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════
    
    def _generate_minimal_fallback(self):
        """Generate minimal valid event sequence per fallback"""
        return [
            self._build_message_start(),
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""}
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Simulation error occurred"}
            },
            {
                "type": "content_block_stop",
                "index": 0
            },
            self._build_message_delta("end_turn", 10),
            self._build_message_stop()
        ]
    
    def _get_lorem_ipsum(self):
        """Lorem ipsum standard"""
        return (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do "
            "eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut "
            "enim ad minim veniam, quis nostrud exercitation ullamco laboris "
            "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor "
            "in reprehenderit in voluptate velit esse cillum dolore eu fugiat "
            "nulla pariatur. Excepteur sint occaecat cupidatat non proident, "
            "sunt in culpa qui officia deserunt mollit anim id est laborum."
        )
    
    def _split_into_chunks(self, text, chunk_size=40):
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
    
    def _split_json_progressive(self, json_str):
        """
        Split JSON in progressive chunks (simula streaming).
        
        Ritorna versioni progressive del JSON:
        ["{", "{"key", "{"key":", "{"key":"val"}", ...]
        """
        chunks = []
        step = 15  # Chars per step
        
        for i in range(step, len(json_str) + step, step):
            chunks.append(json_str[:min(i, len(json_str))])
        
        return chunks
    
    def _estimate_output_tokens(self):
        """Stima tokens output per usage"""
        tokens = 100  # Thinking base
        if self.config.get('include_text'):
            tokens += 100
        if self.config.get('include_tool'):
            tokens += 50
        return tokens
    
    # ═══════════════════════════════════════════════════════════
    # STATIC FACTORY METHODS
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def thinking_only():
        """Scenario: solo thinking, niente altro"""
        return {
            'include_text': False,
            'include_tool': False,
            'timing': 'fast'
        }
    
    @staticmethod
    def thinking_text():
        """Scenario: thinking + text (default)"""
        return {
            'include_text': True,
            'include_tool': False,
            'timing': 'fast'
        }
    
    @staticmethod
    def bash_tool(command=None):
        """Scenario: thinking + bash tool"""
        config = {
            'include_text': False,
            'include_tool': True,
            'tool_name': 'bash',
            'timing': 'fast'
        }
        if command:
            config['tool_input'] = {
                'command': command,
                'description': 'Custom bash command'
            }
        return config
    
    @staticmethod
    def thinking_text_bash(command=None):
        """Scenario: thinking + text + bash (tutti e tre)"""
        config = {
            'include_text': True,
            'include_tool': True,
            'tool_name': 'bash',
            'timing': 'fast'
        }
        if command:
            config['tool_input'] = {
                'command': command,
                'description': 'Custom bash command'
            }
        return config
    
    @staticmethod
    def custom_tool(tool_name, tool_input=None, with_text=False):
        """Scenario: thinking + custom tool + optional text"""
        return {
            'include_text': with_text,
            'include_tool': True,
            'tool_name': tool_name,
            'tool_input': tool_input,
            'timing': 'fast'
        }
