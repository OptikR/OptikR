"""
Base Worker - Foundation for all worker scripts that run as subprocesses.

Provides:
- Message loop (read from stdin, write to stdout)
- Initialization and shutdown handling
- Error reporting
- Logging
"""

import sys
import json
from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseWorker(ABC):
    """Base class for worker scripts that run as subprocesses."""
    
    def __init__(self, name: str):
        """
        Initialize worker.
        
        Args:
            name: Worker name for logging
        """
        self.name = name
        self.running = False
        self.initialized = False
    
    def run(self):
        """
        Main worker loop.
        
        Reads JSON messages from stdin and processes them.
        Writes JSON responses to stdout.
        """
        try:
            # Read messages from stdin
            for line in sys.stdin:
                try:
                    # Parse message
                    message = json.loads(line.strip())
                    msg_type = message.get('type')
                    
                    # Handle message
                    if msg_type == 'init':
                        self._handle_init(message.get('config', {}))
                    elif msg_type == 'process':
                        self._handle_process(message)
                    elif msg_type == 'shutdown':
                        self._handle_shutdown()
                        break
                    else:
                        self.send_error(f"Unknown message type: {msg_type}")
                        
                except json.JSONDecodeError as e:
                    self.send_error(f"Invalid JSON: {e}")
                except Exception as e:
                    self.send_error(f"Message handling error: {e}")
                    import traceback
                    traceback.print_exc(file=sys.stderr)
        
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.send_error(f"Worker loop error: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)
        finally:
            self.cleanup()
    
    def _handle_init(self, config: Dict):
        """Handle initialization message."""
        try:
            success = self.initialize(config)
            if success:
                self.initialized = True
                self.running = True
                self.send_ready()
            else:
                self.send_error("Initialization failed")
        except Exception as e:
            self.send_error(f"Initialization error: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    def _handle_process(self, message: Dict):
        """Handle process message."""
        if not self.initialized:
            self.send_error("Worker not initialized")
            return
        
        try:
            data = message.get('data', {})
            result = self.process(data)
            self.send_result(result)
        except Exception as e:
            self.send_error(f"Processing error: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    def _handle_shutdown(self):
        """Handle shutdown message."""
        self.running = False
        self.cleanup()
    
    @abstractmethod
    def initialize(self, config: Dict) -> bool:
        """
        Initialize worker with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    def process(self, data: Dict) -> Dict:
        """
        Process data.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Result dictionary
        """
        pass
    
    def cleanup(self):
        """Clean up resources (override if needed)."""
        pass
    
    def send_message(self, message: Dict):
        """
        Send JSON message to parent process.
        
        Args:
            message: Message dictionary
        """
        try:
            json_str = json.dumps(message)
            print(json_str, flush=True)
        except Exception as e:
            # Can't send error via send_message if JSON encoding fails
            print(json.dumps({'type': 'error', 'error': str(e)}), flush=True)
    
    def send_ready(self):
        """Send ready signal to parent."""
        self.send_message({'type': 'ready'})
    
    def send_result(self, result: Dict):
        """
        Send result to parent.
        
        Args:
            result: Result dictionary
        """
        self.send_message({'type': 'result', 'data': result})
    
    def send_error(self, error: str):
        """
        Send error to parent.
        
        Args:
            error: Error message
        """
        self.send_message({'type': 'error', 'error': error})
    
    def log(self, message: str):
        """
        Log message to stderr (won't interfere with stdout communication).
        
        Args:
            message: Log message
        """
        print(f"[{self.name}] {message}", file=sys.stderr, flush=True)
