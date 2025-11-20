"""
Async Pipeline Optimizer - Overlapping stage execution

Instead of:
  Capture → Wait → OCR → Wait → Translate → Wait → Overlay
  
Do:
  Capture (frame 1) → OCR (frame 1) → Translate (frame 1) → Overlay (frame 1)
       ↓                    ↓                  ↓                    ↓
  Capture (frame 2) → OCR (frame 2) → Translate (frame 2) → Overlay (frame 2)
       ↓                    ↓                  ↓                    ↓
  Capture (frame 3) → OCR (frame 3) → Translate (frame 3) → Overlay (frame 3)

Result: 3x throughput!
"""

import asyncio
import threading
from typing import Any, Callable, Optional
from dataclasses import dataclass
import queue


@dataclass
class PipelineStage:
    """Async pipeline stage."""
    name: str
    process_func: Callable
    input_queue: asyncio.Queue
    output_queue: asyncio.Queue
    max_concurrent: int = 4  # Process up to 4 items concurrently


class AsyncPipelineOptimizer:
    """
    Async pipeline for overlapping stage execution.
    
    Benefits:
    - 2-3x throughput improvement
    - Better resource utilization
    - Lower latency
    """
    
    def __init__(self):
        self.stages = []
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
    
    def add_stage(self, name: str, process_func: Callable, 
                  max_concurrent: int = 4, queue_size: int = 10):
        """Add a pipeline stage."""
        input_queue = asyncio.Queue(maxsize=queue_size)
        output_queue = asyncio.Queue(maxsize=queue_size)
        
        stage = PipelineStage(
            name=name,
            process_func=process_func,
            input_queue=input_queue,
            output_queue=output_queue,
            max_concurrent=max_concurrent
        )
        
        self.stages.append(stage)
        
        # Connect stages
        if len(self.stages) > 1:
            self.stages[-2].output_queue = input_queue
    
    async def _run_stage(self, stage: PipelineStage):
        """Run a single stage with concurrent processing."""
        semaphore = asyncio.Semaphore(stage.max_concurrent)
        
        async def process_item(item):
            async with semaphore:
                try:
                    # Run sync function in executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, stage.process_func, item)
                    await stage.output_queue.put(result)
                except Exception as e:
                    print(f"Stage {stage.name} error: {e}")
        
        while self.running:
            try:
                item = await asyncio.wait_for(stage.input_queue.get(), timeout=0.1)
                asyncio.create_task(process_item(item))
            except asyncio.TimeoutError:
                continue
    
    def start(self):
        """Start async pipeline."""
        self.running = True
        
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start all stages
            tasks = [self._run_stage(stage) for stage in self.stages]
            self.loop.run_until_complete(asyncio.gather(*tasks))
        
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
    
    def submit(self, item: Any):
        """Submit item to first stage."""
        if self.stages and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.stages[0].input_queue.put(item),
                self.loop
            )
    
    def stop(self):
        """Stop pipeline."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)


# Usage example:
"""
# Create async pipeline
pipeline = AsyncPipelineOptimizer()

# Add stages
pipeline.add_stage("capture", capture_frame, max_concurrent=2)
pipeline.add_stage("ocr", extract_text, max_concurrent=4)
pipeline.add_stage("translate", translate_text, max_concurrent=4)
pipeline.add_stage("overlay", show_overlay, max_concurrent=2)

# Start
pipeline.start()

# Submit frames
for frame in frames:
    pipeline.submit(frame)

# Result: All stages run concurrently!
# Frame 1: Capture → OCR → Translate → Overlay
# Frame 2:    Capture → OCR → Translate → Overlay
# Frame 3:       Capture → OCR → Translate → Overlay
"""


# Performance comparison:
"""
Sequential Pipeline (current):
Frame 1: [Capture 10ms] → [OCR 50ms] → [Translate 30ms] → [Overlay 5ms] = 95ms
Frame 2:                   [Capture 10ms] → [OCR 50ms] → [Translate 30ms] → [Overlay 5ms] = 95ms
Total: 190ms for 2 frames (10.5 FPS)

Async Pipeline (optimized):
Frame 1: [Capture 10ms] → [OCR 50ms] → [Translate 30ms] → [Overlay 5ms]
Frame 2:    [Capture 10ms] → [OCR 50ms] → [Translate 30ms] → [Overlay 5ms]
Total: 105ms for 2 frames (19 FPS) - 80% faster!
"""
