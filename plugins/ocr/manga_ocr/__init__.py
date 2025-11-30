"""
MANGA_OCR Plugin

This plugin provides OCR functionality for Japanese manga using manga_ocr library.
"""

import logging
from typing import List, Optional, Tuple
from pathlib import Path
import numpy as np

try:
    from manga_ocr import MangaOcr
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False

# Import OCR interfaces
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.ocr.ocr_engine_interface import IOCREngine, OCRProcessingOptions, OCREngineType, OCREngineStatus
from app.models import Frame, TextBlock, Rectangle


class OCREngine(IOCREngine):
    """MANGA_OCR engine implementation (Japanese only)."""
    
    def __init__(self, engine_name: str = "manga_ocr", engine_type=None):
        """Initialize MANGA_OCR engine."""
        if engine_type is None:
            engine_type = OCREngineType.MANGA_OCR
        super().__init__(engine_name, engine_type)
        
        self.mocr = None
        self.current_language = 'ja'  # Manga OCR is Japanese only
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, config: dict) -> bool:
        """Initialize the OCR engine."""
        try:
            if not ENGINE_AVAILABLE:
                self.logger.error("manga_ocr library not available")
                self.status = OCREngineStatus.ERROR
                return False
            
            self.status = OCREngineStatus.INITIALIZING
            
            self.logger.info("Initializing Manga OCR (Japanese only)")
            self.mocr = MangaOcr()
            
            self.status = OCREngineStatus.READY
            self.logger.info("Manga OCR initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Manga OCR: {e}")
            self.status = OCREngineStatus.ERROR
            return False
    
    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> List[TextBlock]:
        """Extract text from frame using Manga OCR with automatic text detection.
        
        Strategy:
        1. Use OpenCV to detect text regions (speech bubbles)
        2. Run Manga OCR on each detected region
        3. Return text blocks with proper positions
        """
        if not self.is_ready():
            return []
        
        try:
            from PIL import Image
            import numpy as np
            import cv2
            
            # Convert frame to PIL Image and numpy array
            if isinstance(frame.data, np.ndarray):
                image_np = frame.data.copy()
                # Convert BGR to RGB for PIL
                if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                    image_rgb = image_np[:, :, ::-1]
                    image_pil = Image.fromarray(image_rgb)
                else:
                    image_pil = Image.fromarray(image_np)
            else:
                self.logger.error("Frame data is not a numpy array")
                return []
            
            # Detect text regions using OpenCV
            text_regions = self._detect_text_regions(image_np)
            
            if not text_regions:
                # Fallback: process entire image as one block
                self.logger.debug("No text regions detected, processing entire image")
                text = self.mocr(image_pil)
                
                if text and text.strip():
                    h, w = image_np.shape[:2]
                    position = Rectangle(x=0, y=0, width=w, height=h)
                    text_block = TextBlock(
                        text=text.strip(),
                        position=position,
                        confidence=0.95,
                        language='ja'
                    )
                    return [text_block]
                return []
            
            # Process each detected region with Manga OCR
            text_blocks = []
            for i, (x, y, w, h) in enumerate(text_regions):
                try:
                    # Crop region from image
                    region_np = image_np[y:y+h, x:x+w]
                    
                    # Convert to RGB for PIL
                    if len(region_np.shape) == 3 and region_np.shape[2] == 3:
                        region_rgb = region_np[:, :, ::-1]
                        region_pil = Image.fromarray(region_rgb)
                    else:
                        region_pil = Image.fromarray(region_np)
                    
                    # Run Manga OCR on this region
                    text = self.mocr(region_pil)
                    
                    if text and text.strip():
                        position = Rectangle(x=x, y=y, width=w, height=h)
                        text_block = TextBlock(
                            text=text.strip(),
                            position=position,
                            confidence=0.95,
                            language='ja'
                        )
                        text_blocks.append(text_block)
                        self.logger.debug(f"Region {i+1}: '{text[:30]}...' at ({x}, {y})")
                
                except Exception as e:
                    self.logger.warning(f"Failed to process region {i+1}: {e}")
                    continue
            
            self.logger.info(f"Manga OCR extracted {len(text_blocks)} text blocks")
            return text_blocks
            
        except Exception as e:
            self.logger.error(f"OCR processing failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _detect_text_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect text regions (speech bubbles) in manga image using OpenCV.
        
        Strategy: Find white speech bubbles with black text (typical manga style)
        
        Args:
            image: Input image as numpy array (BGR)
            
        Returns:
            List of (x, y, width, height) tuples for detected text regions
        """
        try:
            import cv2
            
            self.logger.info("🔍 Starting text region detection...")
            
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            h, w = gray.shape
            self.logger.debug(f"Image size: {w}x{h}")
            
            # IMPROVED: Multi-method approach for robust bubble detection
            regions = []
            
            # Method 1: Find white/bright regions (traditional manga bubbles)
            # IMPORTANT: Manga with screentones needs MUCH lower threshold!
            self.logger.info("Method 1: Detecting speech bubbles (adaptive for screentones)...")
            
            # Use adaptive thresholding instead of fixed threshold
            # This works better with screentone backgrounds
            white_mask = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 51, -10  # Large block size, negative C to get bright regions
            )
            
            # Morphological operations to connect nearby white regions
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))  # Larger kernel
            white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel_close)
            
            # Remove small noise
            kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))  # Smaller to preserve more
            white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel_open)
            
            # Find contours of white regions
            contours, _ = cv2.findContours(
                white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            self.logger.info(f"Found {len(contours)} white region contours")
            
            # Filter contours to find speech bubbles (VERY LENIENT)
            min_area = (w * h) * 0.0003  # 0.03% of image (was 0.1%)
            max_area = (w * h) * 0.95    # 95% of image (accept almost full page - manga pages are mostly white!)
            
            self.logger.info(f"Filtering contours: min_area={min_area:.0f}, max_area={max_area:.0f}")
            
            rejected_reasons = {'too_small': 0, 'too_large': 0, 'too_narrow': 0, 'no_text': 0, 'too_much_text': 0}
            
            for i, contour in enumerate(contours):
                x, y, cw, ch = cv2.boundingRect(contour)
                area = cw * ch
                
                # Filter by size (very lenient)
                if area < min_area:
                    rejected_reasons['too_small'] += 1
                    if i < 5:  # Log first few
                        self.logger.debug(f"  Contour {i}: REJECTED (too small) - area={area:.0f} < {min_area:.0f}")
                    continue
                if area > max_area:
                    rejected_reasons['too_large'] += 1
                    if i < 5:
                        self.logger.debug(f"  Contour {i}: REJECTED (too large) - area={area:.0f} > {max_area:.0f}")
                    continue
                
                # Filter by minimum dimensions (accept small text)
                if cw < 15 or ch < 15:  # Minimum 15x15 pixels
                    rejected_reasons['too_narrow'] += 1
                    if i < 5:
                        self.logger.debug(f"  Contour {i}: REJECTED (too narrow) - size={cw}x{ch}")
                    continue
                
                # Check if region contains text (has dark pixels inside)
                roi = gray[y:y+ch, x:x+cw]
                dark_pixels = np.sum(roi < 140)  # Higher threshold for "dark"
                dark_ratio = dark_pixels / (cw * ch)
                
                # Speech bubbles should have some dark text (0.5-90% dark pixels - VERY lenient)
                if dark_ratio < 0.005:
                    rejected_reasons['no_text'] += 1
                    if i < 5:
                        self.logger.debug(f"  Contour {i}: REJECTED (no text) - dark_ratio={dark_ratio:.2%}")
                    continue
                if dark_ratio > 0.9:
                    rejected_reasons['too_much_text'] += 1
                    if i < 5:
                        self.logger.debug(f"  Contour {i}: REJECTED (too dark) - dark_ratio={dark_ratio:.2%}")
                    continue
                
                # Add padding around detected region
                padding = 15
                x = max(0, x - padding)
                y = max(0, y - padding)
                cw = min(w - x, cw + 2 * padding)
                ch = min(h - y, ch + 2 * padding)
                
                self.logger.info(f"  White bubble {i}: ✓ ACCEPTED pos=({x},{y}) size={cw}x{ch} dark={dark_ratio:.2%}")
                regions.append((x, y, cw, ch))
            
            self.logger.info(f"Rejection summary: {rejected_reasons}")
            self.logger.info(f"Accepted {len(regions)} white bubble regions")
            
            # Method 2: Direct text detection (ALWAYS run this, it's more reliable for manga)
            self.logger.info(f"Method 2: Direct text detection (found {len(regions)} white bubbles so far)...")
            text_regions = self._detect_text_directly(gray)
            
            # Merge with existing regions (avoid duplicates)
            for new_region in text_regions:
                # Check if this region overlaps with existing ones
                overlaps = False
                nx, ny, nw, nh = new_region
                for ex, ey, ew, eh in regions:
                    # Simple overlap check
                    if not (nx + nw < ex or ex + ew < nx or ny + nh < ey or ey + eh < ny):
                        overlaps = True
                        break
                
                if not overlaps:
                    regions.append(new_region)
                    self.logger.info(f"  Text region: ✓ pos=({nx},{ny}) size={nw}x{nh}")
            
            self.logger.info(f"Combined detection found {len(regions)} regions")
            
            # If still no regions found, process entire image as one block (no grid!)
            if not regions:
                self.logger.info("No speech bubbles detected - processing full image")
                regions = [(0, 0, w, h)]  # Full image, not grid
            
            # Sort regions top-to-bottom, right-to-left (manga reading order)
            regions.sort(key=lambda r: (r[1], -r[0]))  # Top-to-bottom, right-to-left
            
            self.logger.info(f"✓ Detected {len(regions)} text regions with actual positions")
            for i, (x, y, w, h) in enumerate(regions[:5]):  # Log first 5
                self.logger.debug(f"  Region {i+1}: pos=({x},{y}) size={w}x{h}")
            return regions
            
        except Exception as e:
            self.logger.warning(f"Text region detection failed: {e}")
            return []
    
    def _detect_text_directly(self, gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Alternative method: Detect text directly using edge detection and morphology.
        More aggressive approach that works even without clear bubbles.
        
        Args:
            gray: Grayscale image
            
        Returns:
            List of (x, y, width, height) tuples
        """
        try:
            import cv2
            
            h, w = gray.shape
            
            # IMPROVED: Multiple detection strategies
            all_regions = []
            
            # Strategy 1: Adaptive thresholding (works well for varied lighting)
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 15, 8  # Smaller block, more sensitive
            )
            
            # Connect text characters (manga text can be vertical or horizontal)
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))  # Horizontal text
            kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 30))  # Vertical text (manga)
            
            # Try both orientations
            dilated_h = cv2.dilate(binary, kernel_h, iterations=2)
            dilated_v = cv2.dilate(binary, kernel_v, iterations=2)
            dilated = cv2.bitwise_or(dilated_h, dilated_v)
            
            # Close gaps
            kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
            dilated = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel_close)
            
            # Find contours
            contours, _ = cv2.findContours(
                dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            # EXTREMELY LENIENT filtering for manga with screentones
            min_area = (w * h) * 0.0001  # 0.01% of image (VERY small)
            max_area = (w * h) * 0.4     # 40% of image
            
            self.logger.info(f"Text detection: Found {len(contours)} contours, filtering with min_area={min_area:.0f}")
            
            for i, contour in enumerate(contours):
                x, y, cw, ch = cv2.boundingRect(contour)
                area = cw * ch
                
                if area < min_area or area > max_area:
                    if i < 10:  # Log first 10 rejections
                        self.logger.debug(f"  Contour {i}: REJECTED size - area={area:.0f}")
                    continue
                
                # Accept even smaller regions (manga text can be tiny)
                if cw < 10 or ch < 10:
                    if i < 10:
                        self.logger.debug(f"  Contour {i}: REJECTED dimensions - {cw}x{ch}")
                    continue
                
                # More lenient aspect ratio (vertical manga text can be tall)
                aspect_ratio = cw / ch if ch > 0 else 0
                if aspect_ratio < 0.05 or aspect_ratio > 20:  # VERY lenient
                    if i < 10:
                        self.logger.debug(f"  Contour {i}: REJECTED aspect ratio - {aspect_ratio:.2f}")
                    continue
                
                # Add generous padding
                padding = 20
                x = max(0, x - padding)
                y = max(0, y - padding)
                cw = min(w - x, cw + 2 * padding)
                ch = min(h - y, ch + 2 * padding)
                
                all_regions.append((x, y, cw, ch))
            
            # Strategy 2: Edge detection (catches text with clear edges)
            if len(all_regions) < 5:  # If we didn't find much, try edges
                edges = cv2.Canny(gray, 50, 150)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
                edges_dilated = cv2.dilate(edges, kernel, iterations=2)
                
                contours2, _ = cv2.findContours(
                    edges_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                
                for contour in contours2:
                    x, y, cw, ch = cv2.boundingRect(contour)
                    area = cw * ch
                    
                    if area < min_area or area > max_area:
                        continue
                    if cw < 15 or ch < 15:
                        continue
                    
                    # Check if this overlaps with existing regions
                    overlaps = False
                    for ex, ey, ew, eh in all_regions:
                        if not (x + cw < ex or ex + ew < x or y + ch < ey or ey + eh < y):
                            overlaps = True
                            break
                    
                    if not overlaps:
                        padding = 20
                        x = max(0, x - padding)
                        y = max(0, y - padding)
                        cw = min(w - x, cw + 2 * padding)
                        ch = min(h - y, ch + 2 * padding)
                        all_regions.append((x, y, cw, ch))
            
            self.logger.info(f"Direct text detection found {len(all_regions)} regions total")
            if len(all_regions) == 0:
                self.logger.warning("Direct text detection found NO regions - image may not contain detectable text")
                self.logger.warning(f"Image size: {w}x{h}, min_area threshold: {min_area:.0f}")
            return all_regions
            
        except Exception as e:
            self.logger.warning(f"Direct text detection failed: {e}")
            import traceback
            self.logger.warning(traceback.format_exc())
            return []
    
    def _create_grid_regions(self, width: int, height: int) -> List[Tuple[int, int, int, int]]:
        """
        Fallback: Divide image into grid cells for processing.
        
        Args:
            width: Image width
            height: Image height
            
        Returns:
            List of (x, y, width, height) tuples for grid cells
        """
        regions = []
        
        # Create a 3x4 grid (12 regions) - typical manga page layout
        cols = 3
        rows = 4
        
        cell_w = width // cols
        cell_h = height // rows
        
        for row in range(rows):
            for col in range(cols):
                x = col * cell_w
                y = row * cell_h
                
                # Add some overlap between cells
                overlap = 20
                x = max(0, x - overlap)
                y = max(0, y - overlap)
                w = min(width - x, cell_w + 2 * overlap)
                h = min(height - y, cell_h + 2 * overlap)
                
                regions.append((x, y, w, h))
        
        self.logger.debug(f"Created {len(regions)} grid regions ({cols}x{rows})")
        return regions
    
    def extract_text_batch(self, frames: List[Frame], options: OCRProcessingOptions) -> List[List[TextBlock]]:
        """Extract text from multiple frames."""
        results = []
        for frame in frames:
            results.append(self.extract_text(frame, options))
        return results
    
    def set_language(self, language: str) -> bool:
        """Set the OCR language (Manga OCR only supports Japanese)."""
        if language != 'ja':
            self.logger.warning(f"Manga OCR only supports Japanese, ignoring language: {language}")
        return True
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ['ja']  # Japanese only
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.mocr = None
        self.status = OCREngineStatus.UNINITIALIZED
        self.logger.info("Manga OCR engine cleaned up")
