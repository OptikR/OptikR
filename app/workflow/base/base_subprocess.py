"""
Base Subprocess - Foundation for all pipeline stage subprocesses.

Provides:
- Subprocess lifecycle management (start/stop/restart)
- JSON message communication (stdin/stdout)
- Crash detection and automatic restart
- Error handling and logging
"""

import subprocess
import json
import threading
import queue
import time
import sys
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
from pathlib import Path

# Import EXE compatibility helpers
try:
    from ..exe_compat import get_subprocess_args
except ImportError:
    # Fallback if exe_compat not available
    def get_subprocess_args(worker_script):
        return [sys.executable, worker_script]


class BaseSubprocess(ABC):
    """Base class for all pipeline stage subprocesses."""
    
    def __init__(self, name: str, worker_script: str):
        """
        Initialize subprocess wrapper.
        
        Args:
            name: Human-readable name for this subprocess
            worker_script: Path to worker script (relative to project root)
        """
        self.name = name
        self.worker_script = worker_script
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.crashed = False
        self.restart_count = 0
        self.max_restarts = 3
        self.last_config = {}
        
        # Communication
        self.reader_thread: Optional[threading.Thread] = None
        self.output_queue = queue.Queue()
        
        # Metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.errors_count = 0
        self.start_time = None
    
    def start(self, config: Dict) -> bool:
        """
        Start the subprocess.
        
        Args:
            config: Configuration dictionary for initialization
            
        Returns:
            True if started successfully
        """
        try:
            print(f"[{self.name}] Starting subprocess...")
            
            # Store config for potential restart
            self.last_config = config
            
            # Get subprocess arguments (EXE-compatible)
            args = get_subprocess_args(self.worker_script)
            
            # Start subprocess
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Send initial configuration
            self._send_message({'type': 'init', 'config': config})
            
            # Wait for ready signal (with timeout)
            response = self._receive_message_sync(timeout=10.0)
            
            if response and response.get('type') == 'ready':
                self.running = True
                self.crashed = False
                self.start_time = time.time()
                print(f"[{self.name}] Subprocess ready (PID: {self.process.pid})")
                
                # Start background reader thread
                self.reader_thread = threading.Thread(
                    target=self._read_output_loop,
                    daemon=True,
                    name=f"{self.name}-Reader"
                )
                self.reader_thread.start()
                
                return True
            else:
                print(f"[{self.name}] Subprocess failed to initialize")
                print(f"[{self.name}] Response: {response}")
                
                # Try to read stderr for error messages
                if self.process and self.process.stderr:
                    try:
                        stderr_output = self.process.stderr.read()
                        if stderr_output:
                            print(f"[{self.name}] STDERR: {stderr_output}")
                    except:
                        pass
                
                self._cleanup_process()
                return False
                
        except Exception as e:
            print(f"[{self.name}] Failed to start: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup_process()
            return False
    
    def stop(self):
        """Stop the subprocess gracefully."""
        if not self.process:
            return
        
        print(f"[{self.name}] Stopping subprocess...")
        self.running = False
        
        try:
            # Send shutdown message
            self._send_message({'type': 'shutdown'})
            
            # Wait for process to exit
            self.process.wait(timeout=5.0)
            print(f"[{self.name}] Subprocess stopped gracefully")
            
        except subprocess.TimeoutExpired:
            print(f"[{self.name}] Subprocess didn't stop, terminating...")
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                print(f"[{self.name}] Force killing subprocess...")
                self.process.kill()
        
        except Exception as e:
            print(f"[{self.name}] Error during stop: {e}")
        
        finally:
            self._cleanup_process()
    
    def process_data(self, data: Any, timeout: float = 5.0) -> Optional[Any]:
        """
        Send data to subprocess and get result.
        
        Args:
            data: Data to process
            timeout: Maximum time to wait for result (seconds)
            
        Returns:
            Processed result or None on error
        """
        if not self.running:
            if self.crashed and self.restart_count < self.max_restarts:
                print(f"[{self.name}] Attempting restart ({self.restart_count + 1}/{self.max_restarts})...")
                if self.restart():
                    self.restart_count += 1
                else:
                    print(f"[{self.name}] Restart failed")
                    return None
            else:
                print(f"[{self.name}] Subprocess not running")
                return None
        
        try:
            # Prepare message data
            prepared_data = self._prepare_message(data)
            
            # Create process message with data field
            message = {
                'type': 'process',
                'data': prepared_data
            }
            
            # Send data
            self._send_message(message)
            
            # Wait for result
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    result = self.output_queue.get(timeout=0.1)
                    
                    if result.get('type') == 'result':
                        self.messages_received += 1
                        return self._parse_result(result)
                    elif result.get('type') == 'error':
                        self.errors_count += 1
                        print(f"[{self.name}] Error: {result.get('error')}")
                        return None
                    else:
                        # Put back if not the message we're waiting for
                        self.output_queue.put(result)
                        
                except queue.Empty:
                    continue
            
            print(f"[{self.name}] Timeout waiting for result")
            return None
                
        except Exception as e:
            print(f"[{self.name}] Processing error: {e}")
            import traceback
            traceback.print_exc()
            self.crashed = True
            return None
    
    def restart(self) -> bool:
        """Restart crashed subprocess."""
        print(f"[{self.name}] Restarting subprocess...")
        self.stop()
        time.sleep(0.5)  # Brief pause before restart
        return self.start(self.last_config)
    
    def is_alive(self) -> bool:
        """Check if subprocess is alive."""
        if not self.process:
            return False
        return self.process.poll() is None
    
    def _send_message(self, message: Dict):
        """Send JSON message to subprocess."""
        try:
            if not self.process or not self.process.stdin:
                raise RuntimeError("Process not running")
            
            json_str = json.dumps(message)
            self.process.stdin.write(json_str + '\n')
            self.process.stdin.flush()
            self.messages_sent += 1
            
        except Exception as e:
            print(f"[{self.name}] Send error: {e}")
            self.crashed = True
            raise
    
    def _receive_message_sync(self, timeout: float = 5.0) -> Optional[Dict]:
        """Receive JSON message from subprocess (synchronous)."""
        try:
            if not self.process or not self.process.stdout:
                return None
            
            # Read line with timeout (simple approach)
            start_time = time.time()
            while time.time() - start_time < timeout:
                line = self.process.stdout.readline()
                if line:
                    return json.loads(line.strip())
                time.sleep(0.01)
            
            return None
            
        except Exception as e:
            print(f"[{self.name}] Receive error: {e}")
            return None
    
    def _read_output_loop(self):
        """Background thread to read subprocess output."""
        while self.running and self.is_alive():
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                # Parse JSON message
                message = json.loads(line.strip())
                self.output_queue.put(message)
                
            except json.JSONDecodeError as e:
                print(f"[{self.name}] Invalid JSON: {line}")
            except Exception as e:
                print(f"[{self.name}] Reader error: {e}")
                break
        
        print(f"[{self.name}] Reader thread stopped")
    
    def _cleanup_process(self):
        """Clean up process resources."""
        if self.process:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                if self.process.stdout:
                    self.process.stdout.close()
                if self.process.stderr:
                    self.process.stderr.close()
            except:
                pass
            
            self.process = None
        
        self.running = False
    
    @abstractmethod
    def _prepare_message(self, data: Any) -> Dict:
        """
        Prepare data for sending to subprocess.
        
        Args:
            data: Input data
            
        Returns:
            Dictionary to send as JSON
        """
        pass
    
    @abstractmethod
    def _parse_result(self, result: Dict) -> Any:
        """
        Parse result from subprocess.
        
        Args:
            result: Result dictionary from subprocess
            
        Returns:
            Parsed result data
        """
        pass
    
    def get_metrics(self) -> Dict:
        """Get subprocess metrics."""
        uptime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'name': self.name,
            'running': self.running,
            'crashed': self.crashed,
            'restart_count': self.restart_count,
            'pid': self.process.pid if self.process else None,
            'uptime_seconds': uptime,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'errors_count': self.errors_count,
        }
