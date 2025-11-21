"""
GPU Memory Optimization - Experimental Feature
Advanced GPU memory management for better performance.
"""

import gc
from typing import Optional, Dict, List
import numpy as np


class GPUMemoryOptimizer:
    """
    GPU memory optimizer for efficient memory management.
    
    Features:
    - Automatic memory cleanup
    - Batch size optimization
    - Memory usage monitoring
    - Dynamic memory allocation
    """
    
    def __init__(self):
        """Initialize GPU memory optimizer."""
        self.torch_available = False
        self.cuda_available = False
        self.torch = None
        
        try:
            import torch
            self.torch = torch
            self.torch_available = True
            self.cuda_available = torch.cuda.is_available()
            
            if self.cuda_available:
                print("[INFO] GPU Memory Optimizer initialized with CUDA support")
            else:
                print("[INFO] GPU Memory Optimizer initialized (CPU mode)")
        except ImportError:
            print("[WARNING] PyTorch not available, GPU optimization disabled")
    
    def get_memory_info(self) -> Dict[str, float]:
        """
        Get current GPU memory information.
        
        Returns:
            Dictionary with memory statistics (in MB)
        """
        if not self.cuda_available:
            return {
                'total': 0,
                'allocated': 0,
                'cached': 0,
                'free': 0,
                'utilization': 0.0
            }
        
        try:
            allocated = self.torch.cuda.memory_allocated() / 1024**2
            cached = self.torch.cuda.memory_reserved() / 1024**2
            total = self.torch.cuda.get_device_properties(0).total_memory / 1024**2
            free = total - allocated
            utilization = (allocated / total) * 100 if total > 0 else 0
            
            return {
                'total': total,
                'allocated': allocated,
                'cached': cached,
                'free': free,
                'utilization': utilization
            }
        except Exception as e:
            print(f"[WARNING] Failed to get GPU memory info: {e}")
            return {
                'total': 0,
                'allocated': 0,
                'cached': 0,
                'free': 0,
                'utilization': 0.0
            }
    
    def clear_cache(self):
        """Clear GPU cache to free memory."""
        if not self.cuda_available:
            return
        
        try:
            # Clear PyTorch cache
            self.torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            
            print("[INFO] GPU cache cleared")
        except Exception as e:
            print(f"[WARNING] Failed to clear GPU cache: {e}")
    
    def optimize_batch_size(self, base_batch_size: int = 8, 
                           memory_threshold: float = 0.8) -> int:
        """
        Optimize batch size based on available GPU memory.
        
        Args:
            base_batch_size: Starting batch size
            memory_threshold: Maximum memory utilization (0-1)
            
        Returns:
            Optimized batch size
        """
        if not self.cuda_available:
            return base_batch_size
        
        try:
            mem_info = self.get_memory_info()
            utilization = mem_info['utilization'] / 100.0
            
            if utilization > memory_threshold:
                # Reduce batch size
                new_batch_size = max(1, int(base_batch_size * 0.7))
                print(f"[INFO] Reducing batch size: {base_batch_size} -> {new_batch_size} (GPU: {utilization*100:.1f}%)")
                return new_batch_size
            elif utilization < memory_threshold * 0.5:
                # Increase batch size
                new_batch_size = int(base_batch_size * 1.3)
                print(f"[INFO] Increasing batch size: {base_batch_size} -> {new_batch_size} (GPU: {utilization*100:.1f}%)")
                return new_batch_size
            else:
                return base_batch_size
        except Exception as e:
            print(f"[WARNING] Failed to optimize batch size: {e}")
            return base_batch_size
    
    def should_clear_cache(self, threshold: float = 0.85) -> bool:
        """
        Check if cache should be cleared based on memory usage.
        
        Args:
            threshold: Memory utilization threshold (0-1)
            
        Returns:
            True if cache should be cleared
        """
        if not self.cuda_available:
            return False
        
        mem_info = self.get_memory_info()
        utilization = mem_info['utilization'] / 100.0
        
        return utilization > threshold
    
    def allocate_tensor_safely(self, shape: tuple, dtype=None) -> Optional[any]:
        """
        Safely allocate tensor with memory management.
        
        Args:
            shape: Tensor shape
            dtype: Data type
            
        Returns:
            Allocated tensor or None if failed
        """
        if not self.torch_available:
            return None
        
        try:
            # Check if we need to clear cache first
            if self.should_clear_cache(threshold=0.8):
                self.clear_cache()
            
            # Allocate tensor
            if self.cuda_available:
                tensor = self.torch.zeros(shape, dtype=dtype, device='cuda')
            else:
                tensor = self.torch.zeros(shape, dtype=dtype)
            
            return tensor
        except RuntimeError as e:
            if "out of memory" in str(e):
                print("[WARNING] GPU out of memory, clearing cache and retrying...")
                self.clear_cache()
                
                try:
                    # Retry with CPU
                    tensor = self.torch.zeros(shape, dtype=dtype)
                    return tensor
                except Exception as e2:
                    print(f"[ERROR] Failed to allocate tensor: {e2}")
                    return None
            else:
                print(f"[ERROR] Failed to allocate tensor: {e}")
                return None
    
    def optimize_model_memory(self, model: any) -> any:
        """
        Optimize model memory usage.
        
        Args:
            model: PyTorch model
            
        Returns:
            Optimized model
        """
        if not self.torch_available or model is None:
            return model
        
        try:
            # Move model to GPU if available
            if self.cuda_available:
                model = model.cuda()
            
            # Enable gradient checkpointing if available
            if hasattr(model, 'gradient_checkpointing_enable'):
                model.gradient_checkpointing_enable()
                print("[INFO] Gradient checkpointing enabled")
            
            # Set to eval mode to save memory
            model.eval()
            
            return model
        except Exception as e:
            print(f"[WARNING] Failed to optimize model memory: {e}")
            return model
    
    def monitor_memory_usage(self, operation_name: str = "operation"):
        """
        Context manager for monitoring memory usage during operations.
        
        Usage:
            with optimizer.monitor_memory_usage("translation"):
                # Your code here
                pass
        """
        return MemoryMonitorContext(self, operation_name)
    
    def get_optimal_worker_count(self) -> int:
        """
        Get optimal number of GPU workers based on available memory.
        
        Returns:
            Recommended worker count
        """
        if not self.cuda_available:
            return 1
        
        mem_info = self.get_memory_info()
        total_memory_gb = mem_info['total'] / 1024
        
        # Heuristic: 1 worker per 2GB of GPU memory
        optimal_workers = max(1, int(total_memory_gb / 2))
        optimal_workers = min(optimal_workers, 8)  # Cap at 8 workers
        
        return optimal_workers
    
    def get_stats(self) -> Dict:
        """Get optimizer statistics."""
        mem_info = self.get_memory_info()
        
        return {
            'cuda_available': self.cuda_available,
            'memory_info': mem_info,
            'optimal_workers': self.get_optimal_worker_count(),
            'should_clear_cache': self.should_clear_cache()
        }


class MemoryMonitorContext:
    """Context manager for monitoring memory usage."""
    
    def __init__(self, optimizer: GPUMemoryOptimizer, operation_name: str):
        """Initialize memory monitor context."""
        self.optimizer = optimizer
        self.operation_name = operation_name
        self.start_memory = None
    
    def __enter__(self):
        """Enter context - record starting memory."""
        self.start_memory = self.optimizer.get_memory_info()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - report memory usage."""
        end_memory = self.optimizer.get_memory_info()
        
        memory_used = end_memory['allocated'] - self.start_memory['allocated']
        
        print(f"[MEMORY] {self.operation_name}: {memory_used:.1f} MB used, "
              f"{end_memory['utilization']:.1f}% GPU utilization")
        
        # Auto-clear cache if needed
        if self.optimizer.should_clear_cache():
            print(f"[MEMORY] High memory usage detected, clearing cache...")
            self.optimizer.clear_cache()
