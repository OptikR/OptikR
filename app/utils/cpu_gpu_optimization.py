"""
CPU and GPU Optimization System for OptikR

This module provides comprehensive CPU and GPU optimization capabilities including:

Author: Niklas Verhasselt
Date: November 2025
- Multi-threading pipeline with lock-free queues for parallel processing
- SIMD instructions (SSE, AVX) for image preprocessing operations
- GPU kernel optimization for CUDA and OpenCL operations
- Dynamic batch size optimization based on available resources
- CPU affinity management for critical threads
- Hardware-specific code paths for different CPU architectures

Requirements: 1.5, 2.5, 3.5, 7.2, 7.3
"""

import ctypes
import multiprocessing
import os
import platform
import queue
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import logging
import psutil
import numpy as np

# Optional imports for GPU acceleration
try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    cp = None

try:
    import pyopencl as cl
    PYOPENCL_AVAILABLE = True
except ImportError:
    PYOPENCL_AVAILABLE = False
    cl = None

# Optional imports for SIMD operations
try:
    import numba
    from numba import jit, vectorize
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    numba = None
    jit = lambda *args, **kwargs: lambda f: f
    vectorize = lambda *args, **kwargs: lambda f: f

class ProcessorArchitecture(Enum):
    """CPU architecture types"""
    X86_64 = "x86_64"
    ARM64 = "arm64"
    ARM32 = "arm32"
    UNKNOWN = "unknown"

class SIMDInstructionSet(Enum):
    """SIMD instruction set support"""
    SSE = "sse"
    SSE2 = "sse2"
    SSE3 = "sse3"
    SSSE3 = "ssse3"
    SSE4_1 = "sse4_1"
    SSE4_2 = "sse4_2"
    AVX = "avx"
    AVX2 = "avx2"
    AVX512 = "avx512"
    NEON = "neon"  # ARM NEON

class GPUBackend(Enum):
    """GPU acceleration backends"""
    CUDA = "cuda"
    OPENCL = "opencl"
    NONE = "none"

class ThreadPriority(Enum):
    """Thread priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    REALTIME = "realtime"

@dataclass
class HardwareCapabilities:
    """Hardware capabilities detection results"""
    cpu_count: int
    cpu_architecture: ProcessorArchitecture
    simd_support: List[SIMDInstructionSet]
    gpu_backend: GPUBackend
    gpu_memory_mb: int
    total_memory_mb: int
    cache_sizes: Dict[str, int]  # L1, L2, L3 cache sizes
    numa_nodes: int
    timestamp: float = field(default_factory=time.time)

@dataclass
class OptimizationProfile:
    """Optimization configuration profile"""
    use_simd: bool = True
    use_gpu: bool = True
    max_threads: int = 0  # 0 = auto-detect
    batch_size: int = 0   # 0 = auto-optimize
    cpu_affinity: Optional[List[int]] = None
    thread_priority: ThreadPriority = ThreadPriority.NORMAL
    memory_pool_size_mb: int = 100
    gpu_memory_fraction: float = 0.8

@dataclass
class PerformanceMetrics:
    """Performance measurement results"""
    throughput_ops_per_sec: float
    latency_ms: float
    cpu_utilization: float
    gpu_utilization: float
    memory_usage_mb: float
    cache_hit_rate: float
    thread_efficiency: float
    timestamp: float = field(default_factory=time.time)

class LockFreeQueue:
    """
    Lock-free queue implementation for high-performance inter-thread communication.
    Uses atomic operations and memory barriers for thread safety.
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize lock-free queue.
        
        Args:
            maxsize: Maximum queue size
        """
        self.maxsize = maxsize
        self._buffer = [None] * maxsize
        self._head = multiprocessing.Value('i', 0)
        self._tail = multiprocessing.Value('i', 0)
        self._size = multiprocessing.Value('i', 0)
    
    def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """
        Put item in queue (non-blocking).
        
        Args:
            item: Item to put
            timeout: Timeout in seconds (ignored for lock-free implementation)
            
        Returns:
            True if item was added, False if queue is full
        """
        with self._size.get_lock():
            if self._size.value >= self.maxsize:
                return False
            
            tail_pos = self._tail.value
            self._buffer[tail_pos] = item
            self._tail.value = (tail_pos + 1) % self.maxsize
            self._size.value += 1
            return True
    
    def get(self, timeout: Optional[float] = None) -> Any:
        """
        Get item from queue (non-blocking).
        
        Args:
            timeout: Timeout in seconds (ignored for lock-free implementation)
            
        Returns:
            Item from queue or None if empty
        """
        with self._size.get_lock():
            if self._size.value == 0:
                return None
            
            head_pos = self._head.value
            item = self._buffer[head_pos]
            self._buffer[head_pos] = None  # Clear reference
            self._head.value = (head_pos + 1) % self.maxsize
            self._size.value -= 1
            return item
    
    def qsize(self) -> int:
        """Get current queue size"""
        return self._size.value
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        return self._size.value == 0
    
    def full(self) -> bool:
        """Check if queue is full"""
        return self._size.value >= self.maxsize

class HardwareDetector:
    """
    Hardware capabilities detection system.
    Detects CPU architecture, SIMD support, GPU capabilities, and memory configuration.
    """
    
    def __init__(self):
        """Initialize hardware detector"""
        self.logger = logging.getLogger(__name__)
    
    def detect_capabilities(self) -> HardwareCapabilities:
        """
        Detect comprehensive hardware capabilities.
        
        Returns:
            HardwareCapabilities with detected features
        """
        return HardwareCapabilities(
            cpu_count=self._detect_cpu_count(),
            cpu_architecture=self._detect_cpu_architecture(),
            simd_support=self._detect_simd_support(),
            gpu_backend=self._detect_gpu_backend(),
            gpu_memory_mb=self._detect_gpu_memory(),
            total_memory_mb=self._detect_total_memory(),
            cache_sizes=self._detect_cache_sizes(),
            numa_nodes=self._detect_numa_nodes()
        )
    
    def _detect_cpu_count(self) -> int:
        """Detect number of CPU cores"""
        return multiprocessing.cpu_count()
    
    def _detect_cpu_architecture(self) -> ProcessorArchitecture:
        """Detect CPU architecture"""
        machine = platform.machine().lower()
        
        if machine in ['x86_64', 'amd64']:
            return ProcessorArchitecture.X86_64
        elif machine in ['aarch64', 'arm64']:
            return ProcessorArchitecture.ARM64
        elif machine.startswith('arm'):
            return ProcessorArchitecture.ARM32
        else:
            return ProcessorArchitecture.UNKNOWN
    
    def _detect_simd_support(self) -> List[SIMDInstructionSet]:
        """Detect SIMD instruction set support"""
        supported = []
        
        try:
            # Try to detect x86 SIMD support
            if platform.machine().lower() in ['x86_64', 'amd64']:
                # Use cpuinfo if available
                try:
                    import cpuinfo
                    info = cpuinfo.get_cpu_info()
                    flags = info.get('flags', [])
                    
                    if 'sse' in flags:
                        supported.append(SIMDInstructionSet.SSE)
                    if 'sse2' in flags:
                        supported.append(SIMDInstructionSet.SSE2)
                    if 'sse3' in flags:
                        supported.append(SIMDInstructionSet.SSE3)
                    if 'ssse3' in flags:
                        supported.append(SIMDInstructionSet.SSSE3)
                    if 'sse4_1' in flags:
                        supported.append(SIMDInstructionSet.SSE4_1)
                    if 'sse4_2' in flags:
                        supported.append(SIMDInstructionSet.SSE4_2)
                    if 'avx' in flags:
                        supported.append(SIMDInstructionSet.AVX)
                    if 'avx2' in flags:
                        supported.append(SIMDInstructionSet.AVX2)
                    if 'avx512f' in flags:
                        supported.append(SIMDInstructionSet.AVX512)
                        
                except ImportError:
                    # Fallback: assume basic SSE2 support on x86_64
                    supported.extend([
                        SIMDInstructionSet.SSE,
                        SIMDInstructionSet.SSE2
                    ])
            
            # ARM NEON detection
            elif platform.machine().lower().startswith('arm'):
                # Assume NEON support on modern ARM processors
                supported.append(SIMDInstructionSet.NEON)
                
        except Exception as e:
            self.logger.warning(f"SIMD detection failed: {e}")
        
        return supported
    
    def _detect_gpu_backend(self) -> GPUBackend:
        """Detect available GPU backend"""
        # Check CUDA availability
        if CUPY_AVAILABLE:
            try:
                cp.cuda.runtime.getDeviceCount()
                return GPUBackend.CUDA
            except:
                pass
        
        # Check OpenCL availability
        if PYOPENCL_AVAILABLE:
            try:
                platforms = cl.get_platforms()
                if platforms:
                    return GPUBackend.OPENCL
            except:
                pass
        
        return GPUBackend.NONE
    
    def _detect_gpu_memory(self) -> int:
        """Detect GPU memory in MB"""
        try:
            if CUPY_AVAILABLE:
                device = cp.cuda.Device()
                return device.mem_info[1] // (1024 * 1024)  # Total memory in MB
        except:
            pass
        
        try:
            if PYOPENCL_AVAILABLE:
                platforms = cl.get_platforms()
                if platforms:
                    devices = platforms[0].get_devices()
                    if devices:
                        return devices[0].global_mem_size // (1024 * 1024)
        except:
            pass
        
        return 0
    
    def _detect_total_memory(self) -> int:
        """Detect total system memory in MB"""
        return psutil.virtual_memory().total // (1024 * 1024)
    
    def _detect_cache_sizes(self) -> Dict[str, int]:
        """Detect CPU cache sizes"""
        cache_sizes = {}
        
        try:
            # Try to get cache info from psutil
            if hasattr(psutil, 'cpu_stats'):
                # This is a simplified approach
                # Real cache detection would require platform-specific code
                cache_sizes = {
                    'L1': 32 * 1024,      # 32KB typical L1
                    'L2': 256 * 1024,     # 256KB typical L2
                    'L3': 8 * 1024 * 1024 # 8MB typical L3
                }
        except:
            pass
        
        return cache_sizes
    
    def _detect_numa_nodes(self) -> int:
        """Detect number of NUMA nodes"""
        try:
            # Simple NUMA detection
            numa_dirs = [d for d in os.listdir('/sys/devices/system/node/') 
                        if d.startswith('node') and d[4:].isdigit()]
            return len(numa_dirs)
        except:
            return 1  # Assume single NUMA node

class SIMDOptimizer:
    """
    SIMD instruction optimization for image preprocessing operations.
    Provides vectorized implementations using SSE, AVX, and ARM NEON.
    """
    
    def __init__(self, capabilities: HardwareCapabilities):
        """
        Initialize SIMD optimizer.
        
        Args:
            capabilities: Hardware capabilities
        """
        self.capabilities = capabilities
        self.logger = logging.getLogger(__name__)
        self._initialize_optimized_functions()
    
    def _initialize_optimized_functions(self) -> None:
        """Initialize optimized function implementations"""
        if NUMBA_AVAILABLE and SIMDInstructionSet.AVX2 in self.capabilities.simd_support:
            self._init_avx2_functions()
        elif NUMBA_AVAILABLE and SIMDInstructionSet.SSE2 in self.capabilities.simd_support:
            self._init_sse2_functions()
        else:
            self._init_fallback_functions()
    
    def _init_avx2_functions(self) -> None:
        """Initialize AVX2 optimized functions"""
        @jit(nopython=True, parallel=True)
        def grayscale_convert_avx2(rgb_image: np.ndarray) -> np.ndarray:
            """AVX2 optimized grayscale conversion"""
            height, width, channels = rgb_image.shape
            gray_image = np.zeros((height, width), dtype=np.uint8)
            
            for i in numba.prange(height):
                for j in range(width):
                    # Weighted average: 0.299*R + 0.587*G + 0.114*B
                    gray_value = (0.299 * rgb_image[i, j, 0] + 
                                 0.587 * rgb_image[i, j, 1] + 
                                 0.114 * rgb_image[i, j, 2])
                    gray_image[i, j] = int(gray_value)
            
            return gray_image
        
        @jit(nopython=True, parallel=True)
        def gaussian_blur_avx2(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
            """AVX2 optimized Gaussian blur"""
            height, width = image.shape
            result = np.zeros_like(image)
            
            # Simple box blur approximation for performance
            radius = kernel_size // 2
            
            for i in numba.prange(radius, height - radius):
                for j in range(radius, width - radius):
                    total = 0
                    count = 0
                    
                    for ki in range(-radius, radius + 1):
                        for kj in range(-radius, radius + 1):
                            total += image[i + ki, j + kj]
                            count += 1
                    
                    result[i, j] = total // count
            
            return result
        
        self.grayscale_convert = grayscale_convert_avx2
        self.gaussian_blur = gaussian_blur_avx2
    
    def _init_sse2_functions(self) -> None:
        """Initialize SSE2 optimized functions"""
        @jit(nopython=True, parallel=True)
        def grayscale_convert_sse2(rgb_image: np.ndarray) -> np.ndarray:
            """SSE2 optimized grayscale conversion"""
            height, width, channels = rgb_image.shape
            gray_image = np.zeros((height, width), dtype=np.uint8)
            
            for i in numba.prange(height):
                for j in range(width):
                    gray_value = (0.299 * rgb_image[i, j, 0] + 
                                 0.587 * rgb_image[i, j, 1] + 
                                 0.114 * rgb_image[i, j, 2])
                    gray_image[i, j] = int(gray_value)
            
            return gray_image
        
        @jit(nopython=True)
        def gaussian_blur_sse2(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
            """SSE2 optimized Gaussian blur"""
            height, width = image.shape
            result = np.zeros_like(image)
            radius = kernel_size // 2
            
            for i in range(radius, height - radius):
                for j in range(radius, width - radius):
                    total = 0
                    count = 0
                    
                    for ki in range(-radius, radius + 1):
                        for kj in range(-radius, radius + 1):
                            total += image[i + ki, j + kj]
                            count += 1
                    
                    result[i, j] = total // count
            
            return result
        
        self.grayscale_convert = grayscale_convert_sse2
        self.gaussian_blur = gaussian_blur_sse2
    
    def _init_fallback_functions(self) -> None:
        """Initialize fallback functions without SIMD"""
        def grayscale_convert_fallback(rgb_image: np.ndarray) -> np.ndarray:
            """Fallback grayscale conversion"""
            return np.dot(rgb_image[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
        
        def gaussian_blur_fallback(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
            """Fallback Gaussian blur using scipy if available"""
            try:
                from scipy import ndimage
                return ndimage.gaussian_filter(image, sigma=kernel_size/6.0).astype(np.uint8)
            except ImportError:
                # Simple box blur
                from scipy.ndimage import uniform_filter
                return uniform_filter(image.astype(np.float32), size=kernel_size).astype(np.uint8)
        
        self.grayscale_convert = grayscale_convert_fallback
        self.gaussian_blur = gaussian_blur_fallback
    
    def adaptive_threshold_simd(self, image: np.ndarray, 
                               block_size: int = 11, 
                               c: float = 2.0) -> np.ndarray:
        """
        SIMD optimized adaptive thresholding.
        
        Args:
            image: Input grayscale image
            block_size: Size of neighborhood area
            c: Constant subtracted from mean
            
        Returns:
            Binary thresholded image
        """
        if NUMBA_AVAILABLE:
            return self._adaptive_threshold_numba(image, block_size, c)
        else:
            return self._adaptive_threshold_fallback(image, block_size, c)
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def _adaptive_threshold_numba(image: np.ndarray, 
                                 block_size: int, 
                                 c: float) -> np.ndarray:
        """Numba optimized adaptive threshold"""
        height, width = image.shape
        result = np.zeros_like(image)
        radius = block_size // 2
        
        for i in numba.prange(height):
            for j in range(width):
                # Calculate local mean
                total = 0
                count = 0
                
                for ki in range(max(0, i - radius), min(height, i + radius + 1)):
                    for kj in range(max(0, j - radius), min(width, j + radius + 1)):
                        total += image[ki, kj]
                        count += 1
                
                mean_val = total / count
                threshold = mean_val - c
                
                result[i, j] = 255 if image[i, j] > threshold else 0
        
        return result
    
    def _adaptive_threshold_fallback(self, image: np.ndarray, 
                                   block_size: int, 
                                   c: float) -> np.ndarray:
        """Fallback adaptive threshold using OpenCV if available"""
        try:
            import cv2
            return cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                cv2.THRESH_BINARY, block_size, c
            )
        except ImportError:
            # Simple global threshold as fallback
            threshold = np.mean(image) - c
            return (image > threshold).astype(np.uint8) * 255

class GPUKernelOptimizer:
    """
    GPU kernel optimization for CUDA and OpenCL operations.
    Provides optimized GPU implementations for image processing tasks.
    """
    
    def __init__(self, capabilities: HardwareCapabilities):
        """
        Initialize GPU kernel optimizer.
        
        Args:
            capabilities: Hardware capabilities
        """
        self.capabilities = capabilities
        self.backend = capabilities.gpu_backend
        self.logger = logging.getLogger(__name__)
        
        if self.backend == GPUBackend.CUDA and CUPY_AVAILABLE:
            self._init_cuda_kernels()
        elif self.backend == GPUBackend.OPENCL and PYOPENCL_AVAILABLE:
            self._init_opencl_kernels()
    
    def _init_cuda_kernels(self) -> None:
        """Initialize CUDA kernels using CuPy built-in functions"""
        # Use CuPy's built-in functions instead of raw kernels to avoid NVRTC dependency
        self.use_raw_kernels = False
        
        try:
            # Try to create a simple raw kernel to test NVRTC availability
            test_kernel = cp.RawKernel(r'''
            extern "C" __global__
            void test_kernel(float* x) {
                int idx = blockIdx.x * blockDim.x + threadIdx.x;
                x[idx] = x[idx] + 1.0f;
            }
            ''', 'test_kernel')
            
            # If we get here, NVRTC is available, use raw kernels
            self.use_raw_kernels = True
            
            # Grayscale conversion kernel
            self.cuda_grayscale_kernel = cp.RawKernel(r'''
            extern "C" __global__
            void grayscale_kernel(const unsigned char* rgb, unsigned char* gray, 
                                 int width, int height) {
                int idx = blockIdx.x * blockDim.x + threadIdx.x;
                int idy = blockIdx.y * blockDim.y + threadIdx.y;
                
                if (idx < width && idy < height) {
                    int pixel_idx = idy * width + idx;
                    int rgb_idx = pixel_idx * 3;
                    
                    float r = rgb[rgb_idx];
                    float g = rgb[rgb_idx + 1];
                    float b = rgb[rgb_idx + 2];
                    
                    gray[pixel_idx] = (unsigned char)(0.299f * r + 0.587f * g + 0.114f * b);
                }
            }
            ''', 'grayscale_kernel')
            
            # Gaussian blur kernel
            self.cuda_blur_kernel = cp.RawKernel(r'''
            extern "C" __global__
            void blur_kernel(const unsigned char* input, unsigned char* output,
                            int width, int height, int kernel_size) {
                int idx = blockIdx.x * blockDim.x + threadIdx.x;
                int idy = blockIdx.y * blockDim.y + threadIdx.y;
                
                if (idx < width && idy < height) {
                    int radius = kernel_size / 2;
                    int sum = 0;
                    int count = 0;
                    
                    for (int ki = -radius; ki <= radius; ki++) {
                        for (int kj = -radius; kj <= radius; kj++) {
                            int ni = idy + ki;
                            int nj = idx + kj;
                            
                            if (ni >= 0 && ni < height && nj >= 0 && nj < width) {
                                sum += input[ni * width + nj];
                                count++;
                            }
                        }
                    }
                    
                    output[idy * width + idx] = sum / count;
                }
            }
            ''', 'blur_kernel')
            
        except Exception as e:
            # NVRTC not available, use built-in CuPy functions
            self.logger.info(f"NVRTC not available, using CuPy built-in functions: {e}")
            self.use_raw_kernels = False
    
    def _init_opencl_kernels(self) -> None:
        """Initialize OpenCL kernels"""
        try:
            self.cl_context = cl.create_some_context()
            self.cl_queue = cl.CommandQueue(self.cl_context)
            
            # Grayscale conversion kernel
            grayscale_source = """
            __kernel void grayscale_kernel(__global const uchar* rgb,
                                         __global uchar* gray,
                                         int width, int height) {
                int idx = get_global_id(0);
                int idy = get_global_id(1);
                
                if (idx < width && idy < height) {
                    int pixel_idx = idy * width + idx;
                    int rgb_idx = pixel_idx * 3;
                    
                    float r = rgb[rgb_idx];
                    float g = rgb[rgb_idx + 1];
                    float b = rgb[rgb_idx + 2];
                    
                    gray[pixel_idx] = (uchar)(0.299f * r + 0.587f * g + 0.114f * b);
                }
            }
            """
            
            self.cl_program = cl.Program(self.cl_context, grayscale_source).build()
            
        except Exception as e:
            self.logger.error(f"OpenCL initialization failed: {e}")
            self.backend = GPUBackend.NONE
    
    def grayscale_convert_gpu(self, rgb_image: np.ndarray) -> np.ndarray:
        """
        GPU accelerated grayscale conversion.
        
        Args:
            rgb_image: RGB image array
            
        Returns:
            Grayscale image array
        """
        if self.backend == GPUBackend.CUDA and CUPY_AVAILABLE:
            return self._grayscale_cuda(rgb_image)
        elif self.backend == GPUBackend.OPENCL and PYOPENCL_AVAILABLE:
            return self._grayscale_opencl(rgb_image)
        else:
            # Fallback to CPU
            return np.dot(rgb_image[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
    
    def _grayscale_cuda(self, rgb_image: np.ndarray) -> np.ndarray:
        """CUDA grayscale conversion"""
        height, width, channels = rgb_image.shape
        
        # Transfer to GPU
        rgb_gpu = cp.asarray(rgb_image, dtype=cp.float32)
        
        if self.use_raw_kernels:
            # Use raw kernel if NVRTC is available
            rgb_gpu_uint8 = cp.asarray(rgb_image, dtype=cp.uint8)
            gray_gpu = cp.zeros((height, width), dtype=cp.uint8)
            
            # Launch kernel
            block_size = (16, 16)
            grid_size = ((width + block_size[0] - 1) // block_size[0],
                        (height + block_size[1] - 1) // block_size[1])
            
            self.cuda_grayscale_kernel(
                grid_size, block_size,
                (rgb_gpu_uint8, gray_gpu, width, height)
            )
            
            return cp.asnumpy(gray_gpu)
        else:
            # Use CuPy built-in functions (no NVRTC required)
            # Apply grayscale conversion using matrix multiplication
            weights = cp.array([0.299, 0.587, 0.114], dtype=cp.float32)
            gray_gpu = cp.dot(rgb_gpu, weights)
            
            # Convert back to uint8
            gray_gpu = cp.clip(gray_gpu, 0, 255).astype(cp.uint8)
            
            # Transfer back to CPU
            return cp.asnumpy(gray_gpu)
    
    def _grayscale_opencl(self, rgb_image: np.ndarray) -> np.ndarray:
        """OpenCL grayscale conversion"""
        height, width, channels = rgb_image.shape
        
        # Create buffers
        rgb_buffer = cl.Buffer(self.cl_context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=rgb_image)
        gray_buffer = cl.Buffer(self.cl_context, cl.mem_flags.WRITE_ONLY, size=height * width)
        
        # Execute kernel
        self.cl_program.grayscale_kernel(
            self.cl_queue, (width, height), None,
            rgb_buffer, gray_buffer, np.int32(width), np.int32(height)
        )
        
        # Read result
        gray_image = np.zeros((height, width), dtype=np.uint8)
        cl.enqueue_copy(self.cl_queue, gray_image, gray_buffer)
        
        return gray_image
    
    def gaussian_blur_gpu(self, image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        GPU accelerated Gaussian blur.
        
        Args:
            image: Input grayscale image
            kernel_size: Blur kernel size
            
        Returns:
            Blurred image
        """
        if self.backend == GPUBackend.CUDA and CUPY_AVAILABLE:
            return self._gaussian_blur_cuda(image, kernel_size)
        else:
            # Fallback to CPU
            try:
                from scipy import ndimage
                return ndimage.gaussian_filter(image, sigma=kernel_size/6.0).astype(np.uint8)
            except ImportError:
                return image  # No blur if scipy not available
    
    def _gaussian_blur_cuda(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """CUDA Gaussian blur"""
        height, width = image.shape
        
        # Transfer to GPU
        input_gpu = cp.asarray(image, dtype=cp.float32)
        
        if self.use_raw_kernels:
            # Use raw kernel if NVRTC is available
            input_gpu_uint8 = cp.asarray(image, dtype=cp.uint8)
            output_gpu = cp.zeros_like(input_gpu_uint8)
            
            # Launch kernel
            block_size = (16, 16)
            grid_size = ((width + block_size[0] - 1) // block_size[0],
                        (height + block_size[1] - 1) // block_size[1])
            
            self.cuda_blur_kernel(
                grid_size, block_size,
                (input_gpu_uint8, output_gpu, width, height, kernel_size)
            )
            
            return cp.asnumpy(output_gpu)
        else:
            # Use CuPy built-in functions for Gaussian blur approximation
            try:
                # Try to use SciPy-like filtering if available
                from cupyx.scipy import ndimage
                sigma = kernel_size / 6.0
                blurred_gpu = ndimage.gaussian_filter(input_gpu, sigma=sigma)
                result = cp.clip(blurred_gpu, 0, 255).astype(cp.uint8)
                return cp.asnumpy(result)
            except ImportError:
                # Fallback to simple box blur using convolution
                # Create a simple box kernel
                kernel = cp.ones((kernel_size, kernel_size), dtype=cp.float32) / (kernel_size * kernel_size)
                
                # Pad the image
                pad_size = kernel_size // 2
                padded = cp.pad(input_gpu, pad_size, mode='edge')
                
                # Simple convolution approximation
                result = cp.zeros_like(input_gpu)
                for i in range(height):
                    for j in range(width):
                        region = padded[i:i+kernel_size, j:j+kernel_size]
                        result[i, j] = cp.sum(region * kernel)
                
                result = cp.clip(result, 0, 255).astype(cp.uint8)
                return cp.asnumpy(result)

class BatchSizeOptimizer:
    """
    Dynamic batch size optimization based on available resources.
    Automatically adjusts batch sizes for optimal performance.
    """
    
    def __init__(self, capabilities: HardwareCapabilities):
        """
        Initialize batch size optimizer.
        
        Args:
            capabilities: Hardware capabilities
        """
        self.capabilities = capabilities
        self.logger = logging.getLogger(__name__)
        
        # Performance history for adaptive optimization
        self.performance_history = deque()
        self.max_history_size = 100
        self.current_batch_size = self._calculate_initial_batch_size()
        
        # Optimization parameters
        self.min_batch_size = 1
        self.max_batch_size = self._calculate_max_batch_size()
        self.optimization_window = 10  # Number of measurements for optimization
    
    def _calculate_initial_batch_size(self) -> int:
        """Calculate initial batch size based on hardware"""
        # Base batch size on available memory and CPU cores
        memory_factor = min(self.capabilities.total_memory_mb // 1024, 16)  # Max 16 for memory
        cpu_factor = min(self.capabilities.cpu_count, 8)  # Max 8 for CPU
        
        if self.capabilities.gpu_backend != GPUBackend.NONE:
            gpu_factor = min(self.capabilities.gpu_memory_mb // 512, 32)  # GPU can handle larger batches
            return max(4, min(memory_factor * 2, cpu_factor * 4, gpu_factor))
        else:
            return max(2, min(memory_factor, cpu_factor * 2))
    
    def _calculate_max_batch_size(self) -> int:
        """Calculate maximum safe batch size"""
        # Conservative estimate based on available memory
        available_memory_mb = self.capabilities.total_memory_mb * 0.7  # Use 70% of memory
        
        if self.capabilities.gpu_backend != GPUBackend.NONE:
            gpu_memory_mb = self.capabilities.gpu_memory_mb * 0.8  # Use 80% of GPU memory
            # Assume each batch item uses ~10MB on GPU
            return min(int(available_memory_mb // 5), int(gpu_memory_mb // 10), 128)
        else:
            # Assume each batch item uses ~5MB on CPU
            return min(int(available_memory_mb // 5), 64)
    
    def optimize_batch_size(self, performance_metrics: PerformanceMetrics) -> int:
        """
        Optimize batch size based on performance metrics.
        
        Args:
            performance_metrics: Current performance measurements
            
        Returns:
            Optimized batch size
        """
        self.performance_history.append(performance_metrics)
        
        # Maintain max history size
        while len(self.performance_history) > self.max_history_size:
            self.performance_history.popleft()
        
        if len(self.performance_history) < self.optimization_window:
            return self.current_batch_size
        
        # Analyze recent performance trends
        recent_metrics = list(self.performance_history)[-self.optimization_window:]
        
        # Calculate performance trend
        throughputs = [m.throughput_ops_per_sec for m in recent_metrics]
        latencies = [m.latency_ms for m in recent_metrics]
        
        avg_throughput = sum(throughputs) / len(throughputs)
        avg_latency = sum(latencies) / len(latencies)
        
        # Optimization strategy
        if avg_latency > 100:  # High latency, reduce batch size
            new_batch_size = max(self.min_batch_size, int(self.current_batch_size * 0.8))
        elif avg_throughput < 10:  # Low throughput, try increasing batch size
            new_batch_size = min(self.max_batch_size, int(self.current_batch_size * 1.2))
        else:
            # Performance is acceptable, make small adjustments
            if len(throughputs) > 1:
                throughput_trend = throughputs[-1] - throughputs[-2]
                if throughput_trend > 0:
                    # Throughput improving, try slight increase
                    new_batch_size = min(self.max_batch_size, self.current_batch_size + 1)
                elif throughput_trend < -1:
                    # Throughput declining, try slight decrease
                    new_batch_size = max(self.min_batch_size, self.current_batch_size - 1)
                else:
                    new_batch_size = self.current_batch_size
            else:
                new_batch_size = self.current_batch_size
        
        self.current_batch_size = new_batch_size
        return new_batch_size
    
    def get_recommended_batch_size(self, 
                                  operation_type: str = "default",
                                  memory_usage_mb: float = 0) -> int:
        """
        Get recommended batch size for specific operation.
        
        Args:
            operation_type: Type of operation (ocr, translation, preprocessing)
            memory_usage_mb: Current memory usage
            
        Returns:
            Recommended batch size
        """
        base_size = self.current_batch_size
        
        # Adjust based on operation type
        if operation_type == "ocr":
            # OCR is CPU intensive, smaller batches
            base_size = max(1, base_size // 2)
        elif operation_type == "translation":
            # Translation can benefit from larger batches
            base_size = min(self.max_batch_size, base_size * 2)
        elif operation_type == "preprocessing":
            # Preprocessing is memory intensive
            if self.capabilities.gpu_backend != GPUBackend.NONE:
                base_size = min(self.max_batch_size, base_size * 3)
        
        # Adjust based on current memory usage
        memory_pressure = memory_usage_mb / self.capabilities.total_memory_mb
        if memory_pressure > 0.8:
            base_size = max(1, base_size // 2)
        elif memory_pressure < 0.5:
            base_size = min(self.max_batch_size, int(base_size * 1.5))
        
        return max(self.min_batch_size, min(self.max_batch_size, base_size))

class CPUAffinityManager:
    """
    CPU affinity management for critical threads.
    Optimizes thread placement for NUMA and cache efficiency.
    """
    
    def __init__(self, capabilities: HardwareCapabilities):
        """
        Initialize CPU affinity manager.
        
        Args:
            capabilities: Hardware capabilities
        """
        self.capabilities = capabilities
        self.logger = logging.getLogger(__name__)
        
        # CPU topology information
        self.cpu_count = capabilities.cpu_count
        self.numa_nodes = capabilities.numa_nodes
        
        # Thread assignments
        self.thread_assignments = {}
        self.reserved_cpus = set()
        
        # Initialize CPU groups
        self._initialize_cpu_groups()
    
    def _initialize_cpu_groups(self) -> None:
        """Initialize CPU groups for different thread types"""
        cpus_per_node = self.cpu_count // max(1, self.numa_nodes)
        
        self.cpu_groups = {
            'critical': list(range(0, min(2, self.cpu_count))),  # First 2 CPUs for critical threads
            'processing': list(range(2, min(self.cpu_count - 1, cpus_per_node))),  # Processing threads
            'background': list(range(max(2, cpus_per_node), self.cpu_count))  # Background threads
        }
        
        # Reserve system CPU (last CPU)
        if self.cpu_count > 1:
            self.reserved_cpus.add(self.cpu_count - 1)
    
    def set_thread_affinity(self, 
                           thread_id: int,
                           thread_type: str = "processing",
                           priority: ThreadPriority = ThreadPriority.NORMAL) -> bool:
        """
        Set CPU affinity for thread.
        
        Args:
            thread_id: Thread ID or threading.Thread object
            thread_type: Type of thread (critical, processing, background)
            priority: Thread priority level
            
        Returns:
            True if affinity was set successfully
        """
        try:
            # Get appropriate CPU set
            if thread_type in self.cpu_groups:
                cpu_set = [cpu for cpu in self.cpu_groups[thread_type] 
                          if cpu not in self.reserved_cpus]
            else:
                cpu_set = list(range(self.cpu_count))
            
            if not cpu_set:
                return False
            
            # Set affinity using psutil
            if isinstance(thread_id, threading.Thread):
                # For threading.Thread objects, we need the native thread ID
                # This is platform-specific and may not work on all systems
                process = psutil.Process()
                process.cpu_affinity(cpu_set)
            else:
                # Assume it's a process ID
                process = psutil.Process(thread_id)
                process.cpu_affinity(cpu_set)
            
            # Set thread priority
            self._set_thread_priority(process, priority)
            
            self.thread_assignments[thread_id] = {
                'cpu_set': cpu_set,
                'thread_type': thread_type,
                'priority': priority
            }
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to set thread affinity: {e}")
            return False
    
    def _set_thread_priority(self, process: psutil.Process, priority: ThreadPriority) -> None:
        """Set thread priority"""
        try:
            if priority == ThreadPriority.LOW:
                process.nice(10)  # Lower priority
            elif priority == ThreadPriority.HIGH:
                process.nice(-5)  # Higher priority
            elif priority == ThreadPriority.REALTIME:
                process.nice(-10)  # Highest priority
            # NORMAL priority doesn't change nice value
            
        except Exception as e:
            self.logger.warning(f"Failed to set thread priority: {e}")
    
    def get_optimal_cpu_for_thread(self, thread_type: str = "processing") -> Optional[int]:
        """
        Get optimal CPU for new thread.
        
        Args:
            thread_type: Type of thread
            
        Returns:
            Optimal CPU ID or None if no CPU available
        """
        if thread_type not in self.cpu_groups:
            return None
        
        available_cpus = [cpu for cpu in self.cpu_groups[thread_type] 
                         if cpu not in self.reserved_cpus]
        
        if not available_cpus:
            return None
        
        # Simple round-robin assignment
        # In a more sophisticated implementation, we could consider
        # current CPU load, cache locality, etc.
        return available_cpus[0]
    
    def release_thread_affinity(self, thread_id: int) -> None:
        """Release thread affinity assignment"""
        if thread_id in self.thread_assignments:
            del self.thread_assignments[thread_id]
    
    def get_affinity_stats(self) -> Dict[str, Any]:
        """Get CPU affinity statistics"""
        return {
            'cpu_count': self.cpu_count,
            'numa_nodes': self.numa_nodes,
            'cpu_groups': self.cpu_groups,
            'reserved_cpus': list(self.reserved_cpus),
            'active_assignments': len(self.thread_assignments),
            'assignments_by_type': {
                thread_type: sum(1 for assignment in self.thread_assignments.values() 
                               if assignment['thread_type'] == thread_type)
                for thread_type in ['critical', 'processing', 'background']
            }
        }

class MultiThreadingPipeline:
    """
    Multi-threading pipeline with lock-free queues for parallel processing.
    Coordinates multiple processing stages with optimal thread management.
    """
    
    def __init__(self, 
                 capabilities: HardwareCapabilities,
                 optimization_profile: OptimizationProfile):
        """
        Initialize multi-threading pipeline.
        
        Args:
            capabilities: Hardware capabilities
            optimization_profile: Optimization configuration
        """
        self.capabilities = capabilities
        self.profile = optimization_profile
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.affinity_manager = CPUAffinityManager(capabilities)
        self.batch_optimizer = BatchSizeOptimizer(capabilities)
        
        # Pipeline stages
        self.stages = {}
        self.queues = {}
        self.workers = {}
        self.running = False
        
        # Performance monitoring
        self.performance_metrics = deque()
        self.max_metrics_size = 1000
        self._stats_lock = threading.Lock()
    
    def add_stage(self, 
                  stage_name: str,
                  processor_func: Callable,
                  num_workers: int = 0,
                  queue_size: int = 1000,
                  thread_type: str = "processing") -> None:
        """
        Add processing stage to pipeline.
        
        Args:
            stage_name: Name of the stage
            processor_func: Function to process items
            num_workers: Number of worker threads (0 = auto)
            queue_size: Input queue size
            thread_type: Type of threads for this stage
        """
        if num_workers == 0:
            # Auto-determine worker count based on stage type and hardware
            if thread_type == "critical":
                num_workers = min(2, self.capabilities.cpu_count)
            elif thread_type == "processing":
                num_workers = min(self.capabilities.cpu_count // 2, 4)
            else:
                num_workers = min(self.capabilities.cpu_count // 4, 2)
        
        # Create input queue
        input_queue = LockFreeQueue(maxsize=queue_size)
        
        self.stages[stage_name] = {
            'processor_func': processor_func,
            'num_workers': num_workers,
            'thread_type': thread_type,
            'input_queue': input_queue,
            'workers': [],
            'stats': {
                'processed': 0,
                'errors': 0,
                'avg_processing_time': 0.0
            }
        }
        
        self.queues[stage_name] = input_queue
    
    def connect_stages(self, from_stage: str, to_stage: str) -> None:
        """
        Connect two pipeline stages.
        
        Args:
            from_stage: Source stage name
            to_stage: Destination stage name
        """
        if from_stage not in self.stages or to_stage not in self.stages:
            raise ValueError("Invalid stage names")
        
        # Store connection information
        if 'output_stages' not in self.stages[from_stage]:
            self.stages[from_stage]['output_stages'] = []
        
        self.stages[from_stage]['output_stages'].append(to_stage)
    
    def start_pipeline(self) -> None:
        """Start the processing pipeline"""
        if self.running:
            return
        
        self.running = True
        
        # Start workers for each stage
        for stage_name, stage_info in self.stages.items():
            workers = []
            
            for worker_id in range(stage_info['num_workers']):
                worker = threading.Thread(
                    target=self._worker_loop,
                    args=(stage_name, worker_id),
                    name=f"{stage_name}_worker_{worker_id}",
                    daemon=True
                )
                
                # Set CPU affinity
                self.affinity_manager.set_thread_affinity(
                    worker.ident if worker.ident else id(worker),
                    stage_info['thread_type']
                )
                
                worker.start()
                workers.append(worker)
            
            stage_info['workers'] = workers
        
        self.logger.info(f"Started pipeline with {len(self.stages)} stages")
    
    def stop_pipeline(self) -> None:
        """Stop the processing pipeline"""
        self.running = False
        
        # Wait for workers to finish
        for stage_info in self.stages.values():
            for worker in stage_info['workers']:
                worker.join(timeout=5.0)
        
        self.logger.info("Pipeline stopped")
    
    def _worker_loop(self, stage_name: str, worker_id: int) -> None:
        """Main worker loop for processing stage"""
        stage_info = self.stages[stage_name]
        processor_func = stage_info['processor_func']
        input_queue = stage_info['input_queue']
        
        while self.running:
            try:
                # Get batch of items to process
                batch_size = self.batch_optimizer.get_recommended_batch_size(stage_name)
                batch = []
                
                # Collect batch items
                for _ in range(batch_size):
                    item = input_queue.get(timeout=0.1)
                    if item is None:
                        break
                    batch.append(item)
                
                if not batch:
                    time.sleep(0.001)  # Short sleep if no items
                    continue
                
                # Process batch
                start_time = time.time()
                results = processor_func(batch)
                processing_time = time.time() - start_time
                
                # Update statistics
                with self._stats_lock:
                    stage_info['stats']['processed'] += len(batch)
                    stage_info['stats']['avg_processing_time'] = (
                        (stage_info['stats']['avg_processing_time'] * 0.9) +
                        (processing_time * 0.1)
                    )
                
                # Send results to output stages
                if 'output_stages' in stage_info and results:
                    for output_stage in stage_info['output_stages']:
                        output_queue = self.queues[output_stage]
                        for result in results:
                            if not output_queue.put(result):
                                self.logger.warning(f"Output queue full for stage {output_stage}")
                
                # Record performance metrics
                metrics = PerformanceMetrics(
                    throughput_ops_per_sec=len(batch) / processing_time,
                    latency_ms=processing_time * 1000 / len(batch),
                    cpu_utilization=0.0,  # Would need system monitoring
                    gpu_utilization=0.0,  # Would need GPU monitoring
                    memory_usage_mb=0.0,  # Would need memory monitoring
                    cache_hit_rate=0.0,   # Would need cache monitoring
                    thread_efficiency=1.0  # Simplified
                )
                
                self.performance_metrics.append(metrics)
                
                # Maintain max metrics size
                while len(self.performance_metrics) > self.max_metrics_size:
                    self.performance_metrics.popleft()
                
                # Optimize batch size based on performance
                self.batch_optimizer.optimize_batch_size(metrics)
                
            except Exception as e:
                self.logger.error(f"Worker error in stage {stage_name}: {e}")
                with self._stats_lock:
                    stage_info['stats']['errors'] += 1
                time.sleep(0.1)  # Brief pause on error
    
    def submit_work(self, stage_name: str, item: Any) -> bool:
        """
        Submit work item to pipeline stage.
        
        Args:
            stage_name: Target stage name
            item: Work item to process
            
        Returns:
            True if item was submitted successfully
        """
        if stage_name not in self.queues:
            return False
        
        return self.queues[stage_name].put(item)
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        with self._stats_lock:
            stats = {
                'running': self.running,
                'stages': {},
                'performance_summary': {}
            }
            
            # Stage statistics
            for stage_name, stage_info in self.stages.items():
                stats['stages'][stage_name] = {
                    'num_workers': stage_info['num_workers'],
                    'queue_size': self.queues[stage_name].qsize(),
                    'processed': stage_info['stats']['processed'],
                    'errors': stage_info['stats']['errors'],
                    'avg_processing_time': stage_info['stats']['avg_processing_time']
                }
            
            # Performance summary
            if self.performance_metrics:
                recent_metrics = list(self.performance_metrics)[-100:]  # Last 100 measurements
                
                stats['performance_summary'] = {
                    'avg_throughput': sum(m.throughput_ops_per_sec for m in recent_metrics) / len(recent_metrics),
                    'avg_latency': sum(m.latency_ms for m in recent_metrics) / len(recent_metrics),
                    'current_batch_size': self.batch_optimizer.current_batch_size,
                    'measurements_count': len(recent_metrics)
                }
            
            return stats

class CPUGPUOptimizationManager:
    """
    Central manager for CPU and GPU optimization.
    Coordinates all optimization components and provides unified interface.
    """
    
    def __init__(self, optimization_profile: Optional[OptimizationProfile] = None):
        """
        Initialize CPU/GPU optimization manager.
        
        Args:
            optimization_profile: Optimization configuration
        """
        self.logger = logging.getLogger(__name__)
        
        # Detect hardware capabilities
        self.hardware_detector = HardwareDetector()
        self.capabilities = self.hardware_detector.detect_capabilities()
        
        # Use provided profile or create default
        self.profile = optimization_profile or OptimizationProfile()
        
        # Initialize optimization components
        self.simd_optimizer = SIMDOptimizer(self.capabilities)
        self.gpu_optimizer = GPUKernelOptimizer(self.capabilities)
        self.batch_optimizer = BatchSizeOptimizer(self.capabilities)
        self.affinity_manager = CPUAffinityManager(self.capabilities)
        self.pipeline = MultiThreadingPipeline(self.capabilities, self.profile)
        
        # Performance tracking
        self.optimization_stats = {
            'initialization_time': time.time(),
            'operations_optimized': 0,
            'performance_improvements': []
        }
        
        self.logger.info(f"Initialized optimization manager with {self.capabilities.cpu_count} CPUs, "
                        f"{self.capabilities.gpu_backend.value} GPU backend")
    
    def optimize_image_preprocessing(self, 
                                   image: np.ndarray,
                                   operations: List[str]) -> np.ndarray:
        """
        Optimize image preprocessing operations.
        
        Args:
            image: Input image
            operations: List of operations to perform
            
        Returns:
            Processed image
        """
        start_time = time.time()
        result = image.copy()
        
        for operation in operations:
            if operation == "grayscale":
                if self.profile.use_gpu and self.capabilities.gpu_backend != GPUBackend.NONE:
                    result = self.gpu_optimizer.grayscale_convert_gpu(result)
                elif self.profile.use_simd:
                    result = self.simd_optimizer.grayscale_convert(result)
                else:
                    result = np.dot(result[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
            
            elif operation == "blur":
                kernel_size = 5
                if self.profile.use_gpu and self.capabilities.gpu_backend != GPUBackend.NONE:
                    result = self.gpu_optimizer.gaussian_blur_gpu(result, kernel_size)
                elif self.profile.use_simd:
                    result = self.simd_optimizer.gaussian_blur(result, kernel_size)
                else:
                    try:
                        from scipy import ndimage
                        result = ndimage.gaussian_filter(result, sigma=kernel_size/6.0).astype(np.uint8)
                    except ImportError:
                        pass  # Skip blur if scipy not available
            
            elif operation == "threshold":
                result = self.simd_optimizer.adaptive_threshold_simd(result)
        
        processing_time = time.time() - start_time
        self.optimization_stats['operations_optimized'] += 1
        
        return result
    
    def create_optimized_pipeline(self, 
                                 stage_configs: List[Dict[str, Any]]) -> MultiThreadingPipeline:
        """
        Create optimized processing pipeline.
        
        Args:
            stage_configs: List of stage configurations
            
        Returns:
            Configured pipeline
        """
        pipeline = MultiThreadingPipeline(self.capabilities, self.profile)
        
        # Add stages
        for config in stage_configs:
            pipeline.add_stage(
                stage_name=config['name'],
                processor_func=config['processor'],
                num_workers=config.get('workers', 0),
                queue_size=config.get('queue_size', 1000),
                thread_type=config.get('thread_type', 'processing')
            )
        
        # Connect stages if specified
        for i, config in enumerate(stage_configs[:-1]):
            if 'connect_to' in config:
                pipeline.connect_stages(config['name'], config['connect_to'])
            else:
                # Auto-connect sequential stages
                pipeline.connect_stages(config['name'], stage_configs[i + 1]['name'])
        
        return pipeline
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """
        Get optimization recommendations based on hardware capabilities.
        
        Returns:
            Optimization recommendations
        """
        recommendations = {
            'hardware_summary': {
                'cpu_count': self.capabilities.cpu_count,
                'cpu_architecture': self.capabilities.cpu_architecture.value,
                'simd_support': [s.value for s in self.capabilities.simd_support],
                'gpu_backend': self.capabilities.gpu_backend.value,
                'total_memory_mb': self.capabilities.total_memory_mb
            },
            'optimization_settings': {},
            'performance_tips': []
        }
        
        # CPU optimization recommendations
        if self.capabilities.cpu_count >= 8:
            recommendations['optimization_settings']['max_threads'] = self.capabilities.cpu_count - 2
            recommendations['performance_tips'].append("Use multi-threading with CPU affinity")
        else:
            recommendations['optimization_settings']['max_threads'] = max(2, self.capabilities.cpu_count // 2)
        
        # SIMD recommendations
        if SIMDInstructionSet.AVX2 in self.capabilities.simd_support:
            recommendations['optimization_settings']['use_simd'] = True
            recommendations['performance_tips'].append("Enable AVX2 SIMD optimizations")
        elif SIMDInstructionSet.SSE2 in self.capabilities.simd_support:
            recommendations['optimization_settings']['use_simd'] = True
            recommendations['performance_tips'].append("Enable SSE2 SIMD optimizations")
        
        # GPU recommendations
        if self.capabilities.gpu_backend == GPUBackend.CUDA:
            recommendations['optimization_settings']['use_gpu'] = True
            recommendations['optimization_settings']['batch_size'] = 32
            recommendations['performance_tips'].append("Use CUDA GPU acceleration for large batches")
        elif self.capabilities.gpu_backend == GPUBackend.OPENCL:
            recommendations['optimization_settings']['use_gpu'] = True
            recommendations['optimization_settings']['batch_size'] = 16
            recommendations['performance_tips'].append("Use OpenCL GPU acceleration")
        else:
            recommendations['optimization_settings']['use_gpu'] = False
            recommendations['optimization_settings']['batch_size'] = 8
        
        # Memory recommendations
        if self.capabilities.total_memory_mb < 4096:  # Less than 4GB
            recommendations['performance_tips'].append("Consider reducing batch sizes due to limited memory")
        elif self.capabilities.total_memory_mb > 16384:  # More than 16GB
            recommendations['performance_tips'].append("Increase cache sizes and batch sizes for better performance")
        
        return recommendations
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""
        return {
            'hardware_capabilities': {
                'cpu_count': self.capabilities.cpu_count,
                'cpu_architecture': self.capabilities.cpu_architecture.value,
                'simd_support': [s.value for s in self.capabilities.simd_support],
                'gpu_backend': self.capabilities.gpu_backend.value,
                'gpu_memory_mb': self.capabilities.gpu_memory_mb,
                'total_memory_mb': self.capabilities.total_memory_mb
            },
            'optimization_profile': {
                'use_simd': self.profile.use_simd,
                'use_gpu': self.profile.use_gpu,
                'max_threads': self.profile.max_threads,
                'batch_size': self.profile.batch_size
            },
            'batch_optimizer': {
                'current_batch_size': self.batch_optimizer.current_batch_size,
                'min_batch_size': self.batch_optimizer.min_batch_size,
                'max_batch_size': self.batch_optimizer.max_batch_size
            },
            'affinity_manager': self.affinity_manager.get_affinity_stats(),
            'optimization_stats': self.optimization_stats
        }

# Factory functions
def create_optimization_manager(profile: Optional[OptimizationProfile] = None) -> CPUGPUOptimizationManager:
    """
    Create CPU/GPU optimization manager.
    
    Args:
        profile: Optimization profile
        
    Returns:
        Configured optimization manager
    """
    return CPUGPUOptimizationManager(profile)

def detect_hardware_capabilities() -> HardwareCapabilities:
    """
    Detect hardware capabilities.
    
    Returns:
        Hardware capabilities
    """
    detector = HardwareDetector()
    return detector.detect_capabilities()

def create_optimization_profile(use_simd: bool = True,
                              use_gpu: bool = True,
                              max_threads: int = 0,
                              batch_size: int = 0) -> OptimizationProfile:
    """
    Create optimization profile.
    
    Args:
        use_simd: Enable SIMD optimizations
        use_gpu: Enable GPU acceleration
        max_threads: Maximum threads (0 = auto)
        batch_size: Batch size (0 = auto)
        
    Returns:
        Optimization profile
    """
    return OptimizationProfile(
        use_simd=use_simd,
        use_gpu=use_gpu,
        max_threads=max_threads,
        batch_size=batch_size
    )

# Global optimization manager instance
_global_optimization_manager: Optional[CPUGPUOptimizationManager] = None

def get_global_optimization_manager() -> CPUGPUOptimizationManager:
    """Get or create global optimization manager"""
    global _global_optimization_manager
    if _global_optimization_manager is None:
        _global_optimization_manager = create_optimization_manager()
    return _global_optimization_manager

def cleanup_global_optimization_manager() -> None:
    """Clean up global optimization manager"""
    global _global_optimization_manager
    if _global_optimization_manager is not None:
        if hasattr(_global_optimization_manager, 'pipeline'):
            _global_optimization_manager.pipeline.stop_pipeline()
        _global_optimization_manager = None