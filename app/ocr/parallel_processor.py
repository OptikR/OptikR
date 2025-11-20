#!/usr/bin/env python3
"""
Parallel OCR Processor
Processes multiple text blocks simultaneously for maximum speed.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import multiprocessing

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result from OCR processing of a single text block."""
    block_id: int
    bbox: tuple  # (x, y, width, height)
    text: str
    confidence: float
    success: bool
    processing_time: float
    error: Optional[str] = None


class ParallelOCRProcessor:
    """
    Process multiple text blocks in parallel for maximum speed.
    
    This processor uses ThreadPoolExecutor to process multiple text regions
    simultaneously, providing 4-8x speedup over sequential processing.
    
    Example:
        processor = ParallelOCRProcessor(ocr_engine, max_workers=4)
        results = processor.process_all_blocks(text_blocks)
    """
    
    def __init__(self, ocr_engine, max_workers: Optional[int] = None, use_gpu: bool = True):
        """
        Initialize parallel OCR processor.
        
        Args:
            ocr_engine: Pre-initialized OCR engine (EasyOCR or Tesseract)
            max_workers: Number of parallel threads
                        - None: Auto-detect based on hardware
                        - GPU: Recommended 2-4 workers
                        - CPU: Recommended 4-8 workers
            use_gpu: Whether GPU is being used (affects worker count)
        """
        self.ocr_engine = ocr_engine
        self.use_gpu = use_gpu
        
        if max_workers is None:
            max_workers = self._auto_detect_workers()
        
        self.max_workers = max_workers
        logger.info(f"Parallel OCR processor initialized with {max_workers} workers (GPU: {use_gpu})")
    
    def _auto_detect_workers(self) -> int:
        """Auto-detect optimal number of workers based on hardware."""
        if self.use_gpu:
            # GPU can handle multiple requests efficiently, but don't overload
            return 4
        else:
            # CPU: Use all cores but leave one for system
            cpu_count = multiprocessing.cpu_count()
            return max(1, cpu_count - 1)
    
    def process_single_block(self, text_block: Dict[str, Any]) -> OCRResult:
        """
        Process a single text block.
        
        Args:
            text_block: Dict with 'id', 'bbox', 'image'
        
        Returns:
            OCRResult with processing results
        """
        try:
            # Extract region from image
            x, y, w, h = text_block['bbox']
            region = text_block['image'][y:y+h, x:x+w]
            
            # Perform OCR
            start_time = time.time()
            result = self.ocr_engine.readtext(region)
            elapsed = time.time() - start_time
            
            # Extract text and confidence from result
            if result:
                # EasyOCR returns list of (bbox, text, confidence)
                text = ' '.join([item[1] for item in result])
                confidence = sum([item[2] for item in result]) / len(result)
            else:
                text = ""
                confidence = 0.0
            
            return OCRResult(
                block_id=text_block['id'],
                bbox=text_block['bbox'],
                text=text,
                confidence=confidence,
                success=True,
                processing_time=elapsed
            )
            
        except Exception as e:
            logger.error(f"Error processing block {text_block['id']}: {e}")
            return OCRResult(
                block_id=text_block['id'],
                bbox=text_block.get('bbox', (0, 0, 0, 0)),
                text="",
                confidence=0.0,
                success=False,
                processing_time=0.0,
                error=str(e)
            )
    
    def process_all_blocks(
        self, 
        text_blocks: List[Dict[str, Any]], 
        show_progress: bool = False
    ) -> List[OCRResult]:
        """
        Process all text blocks in parallel.
        
        Args:
            text_blocks: List of text block dicts with 'id', 'bbox', 'image'
            show_progress: Whether to log progress messages
        
        Returns:
            List of OCRResult objects in original order
        """
        if not text_blocks:
            return []
        
        start_time = time.time()
        results = [None] * len(text_blocks)
        completed = 0
        
        if show_progress:
            logger.info(f"Processing {len(text_blocks)} text blocks in parallel...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self.process_single_block, block): i 
                for i, block in enumerate(text_blocks)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                    completed += 1
                    
                    if show_progress and completed % 10 == 0:
                        logger.info(f"Progress: {completed}/{len(text_blocks)} blocks completed")
                        
                except Exception as e:
                    logger.error(f"Error collecting result for block {index}: {e}")
                    results[index] = OCRResult(
                        block_id=text_blocks[index]['id'],
                        bbox=text_blocks[index].get('bbox', (0, 0, 0, 0)),
                        text="",
                        confidence=0.0,
                        success=False,
                        processing_time=0.0,
                        error=str(e)
                    )
        
        elapsed = time.time() - start_time
        
        if show_progress:
            successful = sum(1 for r in results if r.success)
            avg_time = elapsed / len(text_blocks)
            logger.info(f"Completed: {successful}/{len(text_blocks)} successful")
            logger.info(f"Total time: {elapsed:.2f}s, Average: {avg_time:.3f}s per block")
            logger.info(f"Estimated speedup: ~{self.max_workers}x vs sequential")
        
        return results
    
    def process_in_batches(
        self,
        text_blocks: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> List[OCRResult]:
        """
        Process text blocks in batches to manage memory.
        
        Useful when processing very large numbers of text blocks.
        
        Args:
            text_blocks: List of text block dicts
            batch_size: Size of each batch (default: max_workers * 2)
            show_progress: Whether to log progress
        
        Returns:
            List of OCRResult objects
        """
        if batch_size is None:
            batch_size = self.max_workers * 2
        
        all_results = []
        total_batches = (len(text_blocks) + batch_size - 1) // batch_size
        
        if show_progress:
            logger.info(f"Processing {len(text_blocks)} blocks in {total_batches} batches")
        
        for batch_num, i in enumerate(range(0, len(text_blocks), batch_size), 1):
            batch = text_blocks[i:i+batch_size]
            
            if show_progress:
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} blocks)")
            
            batch_results = self.process_all_blocks(batch, show_progress=False)
            all_results.extend(batch_results)
            
            # Optional: Clear cache between batches
            import gc
            gc.collect()
        
        return all_results


class AdaptiveOCRProcessor(ParallelOCRProcessor):
    """
    Adaptive parallel OCR processor that adjusts worker count based on performance.
    
    Monitors processing times and automatically adjusts the number of workers
    for optimal performance.
    """
    
    def __init__(self, ocr_engine, initial_workers: int = 4, use_gpu: bool = True):
        super().__init__(ocr_engine, max_workers=initial_workers, use_gpu=use_gpu)
        self.performance_history = []
        self.adjustment_threshold = 5  # Adjust after 5 batches
    
    def process_all_blocks(
        self, 
        text_blocks: List[Dict[str, Any]], 
        show_progress: bool = False
    ) -> List[OCRResult]:
        """Process blocks and track performance for adaptation."""
        start_time = time.time()
        results = super().process_all_blocks(text_blocks, show_progress)
        elapsed = time.time() - start_time
        
        # Track performance
        avg_time = elapsed / len(text_blocks) if text_blocks else 0
        self.performance_history.append({
            'workers': self.max_workers,
            'blocks': len(text_blocks),
            'total_time': elapsed,
            'avg_time': avg_time
        })
        
        # Adapt worker count if needed
        if len(self.performance_history) >= self.adjustment_threshold:
            self._adapt_workers()
        
        return results
    
    def _adapt_workers(self):
        """Adapt worker count based on performance history."""
        if len(self.performance_history) < 2:
            return
        
        recent = self.performance_history[-5:]
        avg_time = sum(p['avg_time'] for p in recent) / len(recent)
        
        # If average time is high, try adjusting workers
        if avg_time > 0.5:  # More than 500ms per block
            if self.use_gpu and self.max_workers < 6:
                self.max_workers += 1
                logger.info(f"Increased workers to {self.max_workers} for better performance")
            elif not self.use_gpu and self.max_workers < multiprocessing.cpu_count():
                self.max_workers += 1
                logger.info(f"Increased workers to {self.max_workers} for better performance")
        
        # Keep history manageable
        if len(self.performance_history) > 20:
            self.performance_history = self.performance_history[-10:]


def create_parallel_processor(
    ocr_engine,
    max_workers: Optional[int] = None,
    use_gpu: bool = True,
    adaptive: bool = False
) -> ParallelOCRProcessor:
    """
    Factory function to create appropriate parallel processor.
    
    Args:
        ocr_engine: Pre-initialized OCR engine
        max_workers: Number of workers (None for auto-detect)
        use_gpu: Whether GPU is being used
        adaptive: Whether to use adaptive processor
    
    Returns:
        ParallelOCRProcessor or AdaptiveOCRProcessor instance
    """
    if adaptive:
        initial_workers = max_workers if max_workers else (4 if use_gpu else multiprocessing.cpu_count() - 1)
        return AdaptiveOCRProcessor(ocr_engine, initial_workers=initial_workers, use_gpu=use_gpu)
    else:
        return ParallelOCRProcessor(ocr_engine, max_workers=max_workers, use_gpu=use_gpu)
