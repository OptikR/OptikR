"""
Hybrid OCR Plugin - Combines EasyOCR and Tesseract

This plugin runs both OCR engines and intelligently combines their results
for maximum accuracy. Uses the best of both worlds:
- EasyOCR: Better at handling stylized/italic fonts
- Tesseract: Faster and better at standard printed text

Strategies:
- best_confidence: Pick result with highest confidence per text block
- longest_text: Pick the longer/more complete text
- consensus: Use text that both engines agree on
- easyocr_primary: Use EasyOCR, fallback to Tesseract if low confidence
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.ocr.ocr_engine_interface import IOCREngine, OCRProcessingOptions, OCREngineType, OCREngineStatus
from app.models import Frame, TextBlock, Rectangle

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCREngine(IOCREngine):
    """Hybrid OCR engine: EasyOCR for positions + Manga OCR for text (manga optimized)."""
    
    def __init__(self, engine_name: str = "hybrid_ocr", engine_type=None):
        """Initialize Hybrid OCR engine."""
        if engine_type is None:
            engine_type = OCREngineType.EASYOCR  # Use EasyOCR type as base
        super().__init__(engine_name, engine_type)
        
        self.easyocr_reader = None
        self.manga_ocr = None  # Lazy loaded
        self.current_language = 'ja'  # Default to Japanese for manga
        self.confidence_threshold = 0.5
        self.cache_enabled = True
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, config: dict) -> bool:
        """Initialize EasyOCR (Manga OCR loads lazily on first use)."""
        try:
            if not EASYOCR_AVAILABLE:
                self.logger.error("EasyOCR not available")
                self.status = OCREngineStatus.ERROR
                return False
            
            self.status = OCREngineStatus.INITIALIZING
            
            self.current_language = config.get('language', 'ja')  # Default to Japanese for manga
            use_gpu = config.get('gpu', True)
            self.confidence_threshold = config.get('confidence_threshold', 0.5)
            self.cache_enabled = config.get('cache_enabled', True)
            
            self.logger.info(f"Initializing Hybrid OCR (EasyOCR + Manga OCR)")
            self.logger.info(f"  Language: {self.current_language}")
            self.logger.info(f"  GPU: {use_gpu}")
            
            # Initialize EasyOCR at startup (fast, lightweight)
            self.logger.info("  Loading EasyOCR...")
            self.easyocr_reader = easyocr.Reader([self.current_language], gpu=use_gpu)
            self.logger.info("  ✓ EasyOCR initialized")
            
            # Manga OCR will load lazily on first use (saves startup time)
            self.manga_ocr = None
            self.logger.info("  ⏳ Manga OCR will load on first translation (lazy loading)")
            
            self.status = OCREngineStatus.READY
            self.logger.info("Hybrid OCR initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Hybrid OCR: {e}")
            self.status = OCREngineStatus.ERROR
            return False

    
    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> List[TextBlock]:
        """FIXED Hybrid: EasyOCR for POSITIONS + Manga OCR for TEXT (no grid!)."""
        if not self.is_ready():
            return []
        
        try:
            import numpy as np
            from PIL import Image
            import time
            
            # Get frame data
            if not isinstance(frame.data, np.ndarray):
                self.logger.error("Frame data is not a numpy array")
                return []
            
            image_data = frame.data
            h, w = image_data.shape[:2]
            start_time = time.time()
            
            # Load Manga OCR if not already loaded
            if not hasattr(self, 'manga_ocr') or self.manga_ocr is None:
                try:
                    from manga_ocr import MangaOcr
                    self.manga_ocr = MangaOcr()
                    self.logger.info("[HYBRID FIXED] Manga OCR loaded")
                except Exception as e:
                    self.logger.error(f"[HYBRID FIXED] Failed to load Manga OCR: {e}")
                    return []
            
            # STEP 1: EasyOCR detects actual text positions (CORRECT APPROACH!)
            self.logger.info("[HYBRID FIXED] Step 1: EasyOCR detecting text positions...")
            easyocr_positions = self._run_easyocr(image_data)
            self.logger.info(f"[HYBRID FIXED] EasyOCR found {len(easyocr_positions)} text regions")
            
            if not easyocr_positions:
                self.logger.warning("[HYBRID FIXED] No positions found by EasyOCR")
                return []
            
            # STEP 2: Manga OCR reads text from each EasyOCR position
            self.logger.info(f"[HYBRID FIXED] Step 2: Manga OCR reading text from {len(easyocr_positions)} regions...")
            results = []
            
            for i, easy_block in enumerate(easyocr_positions, 1):
                try:
                    # Get region from EasyOCR position
                    bbox = easy_block['bbox']
                    x, y, bw, bh = bbox.x, bbox.y, bbox.width, bbox.height
                    
                    # Crop region
                    region = image_data[y:y+bh, x:x+bw]
                    
                    # Convert to RGB for PIL
                    if len(region.shape) == 3 and region.shape[2] == 3:
                        region_rgb = region[:, :, ::-1]
                        region_pil = Image.fromarray(region_rgb)
                    else:
                        region_pil = Image.fromarray(region)
                    
                    # Read text with Manga OCR
                    text = self.manga_ocr(region_pil)
                    
                    if text and text.strip():
                        # Use EasyOCR's position, MangaOCR's text
                        results.append(TextBlock(
                            text=text.strip(),
                            position=bbox,  # ✓ CORRECT position from EasyOCR
                            confidence=easy_block['confidence'],
                            language='ja'
                        ))
                        
                        if i <= 5:  # Log first 5
                            self.logger.info(f"  Region {i}: '{text[:30]}...' at ({x},{y})")
                    
                except Exception as e:
                    self.logger.warning(f"  Region {i} failed: {e}")
                    continue
            
            elapsed = time.time() - start_time
            self.logger.info(f"[HYBRID FIXED] ✓ {len(results)} text blocks in {elapsed:.2f}s")
            self.logger.info(f"[HYBRID FIXED] Using EasyOCR positions + MangaOCR text")
            self.logger.info(f"[HYBRID FIXED] Note: Use text_block_merger optimizer plugin to merge lines into bubbles")
            return results
            
        except Exception as e:
            self.logger.error(f"Hybrid OCR failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _run_manga_ocr_grid(self, image: np.ndarray, width: int, height: int) -> List[TextBlock]:
        """Run Manga OCR on 3x4 grid to get all text."""
        from PIL import Image
        
        # Create 3x4 grid (12 cells) - manga reading order: right to left, top to bottom
        cols = 3
        rows = 4
        cell_w = width // cols
        cell_h = height // rows
        
        text_blocks = []
        
        self.logger.info(f"[MANGA GRID] Processing {cols}x{rows} grid (cell size: {cell_w}x{cell_h})")
        
        for row in range(rows):
            for col in range(cols):
                x = col * cell_w
                y = row * cell_h
                
                # Crop grid cell
                cell = image[y:y+cell_h, x:x+cell_w]
                
                # Convert to RGB for PIL
                if len(cell.shape) == 3 and cell.shape[2] == 3:
                    cell_rgb = cell[:, :, ::-1]
                    cell_pil = Image.fromarray(cell_rgb)
                else:
                    cell_pil = Image.fromarray(cell)
                
                # Read text with Manga OCR
                try:
                    text = self.manga_ocr(cell_pil)
                    
                    # Log what we got (even if empty)
                    if text and text.strip():
                        self.logger.debug(f"[MANGA GRID] Cell ({row},{col}): '{text[:30]}...'")
                        text_blocks.append(TextBlock(
                            text=text.strip(),
                            position=Rectangle(x=x, y=y, width=cell_w, height=cell_h),
                            confidence=0.95,
                            language='ja'
                        ))
                    else:
                        self.logger.debug(f"[MANGA GRID] Cell ({row},{col}): empty")
                        
                except Exception as e:
                    self.logger.warning(f"[MANGA GRID] Cell ({row},{col}) failed: {e}")
        
        self.logger.info(f"[MANGA GRID] Found {len(text_blocks)} non-empty cells out of {cols*rows}")
        return text_blocks
    
    def _match_text_to_positions(self, manga_texts: List[TextBlock], easyocr_positions: List[Dict]) -> List[TextBlock]:
        """Match Manga OCR text to EasyOCR positions by proximity."""
        import numpy as np
        
        matched_results = []
        used_positions = set()
        
        for manga_block in manga_texts:
            # Find closest EasyOCR position
            manga_center_x = manga_block.position.x + manga_block.position.width / 2
            manga_center_y = manga_block.position.y + manga_block.position.height / 2
            
            best_match = None
            best_distance = float('inf')
            best_idx = -1
            
            for idx, easy_block in enumerate(easyocr_positions):
                if idx in used_positions:
                    continue
                
                easy_bbox = easy_block['bbox']
                easy_center_x = easy_bbox.x + easy_bbox.width / 2
                easy_center_y = easy_bbox.y + easy_bbox.height / 2
                
                # Calculate distance
                distance = np.sqrt((manga_center_x - easy_center_x)**2 + (manga_center_y - easy_center_y)**2)
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = easy_block
                    best_idx = idx
            
            if best_match:
                # Use Manga OCR text + EasyOCR position
                matched_results.append(TextBlock(
                    text=manga_block.text,
                    position=best_match['bbox'],
                    confidence=best_match['confidence'],
                    language='ja'
                ))
                used_positions.add(best_idx)
            else:
                # No match found, use original grid position
                matched_results.append(manga_block)
        
        return matched_results
    
    def _run_manga_ocr_full(self, image: np.ndarray) -> str:
        """Run Manga OCR on full image."""
        try:
            from PIL import Image
            
            # Convert to RGB for PIL
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = image[:, :, ::-1]
                pil_image = Image.fromarray(image_rgb)
            else:
                pil_image = Image.fromarray(image)
            
            return self.manga_ocr(pil_image)
        except Exception as e:
            self.logger.error(f"Manga OCR full page failed: {e}")
            return ""
    
    def _run_parallel(self, image: np.ndarray) -> tuple:
        """Run both engines in parallel using threads."""
        import concurrent.futures
        import numpy as np
        
        easyocr_results = []
        tesseract_results = []
        
        # Get worker count from config (default to 2 for hybrid OCR)
        max_workers = 2
        if hasattr(self, 'config_manager') and self.config_manager:
            max_workers = self.config_manager.get_setting('performance.worker_threads', 2)
            max_workers = min(max_workers, 2)  # Hybrid OCR only needs 2 workers max
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit both tasks
            easy_future = executor.submit(self._run_easyocr, image)
            tess_future = executor.submit(self._run_tesseract, image)
            
            # Wait for both to complete
            easyocr_results = easy_future.result()
            tesseract_results = tess_future.result()
        
        return easyocr_results, tesseract_results
    
    def _blocks_to_textblocks(self, blocks: List[Dict[str, Any]]) -> List[TextBlock]:
        """Convert dict blocks to TextBlock objects."""
        results = []
        for block in blocks:
            if block['confidence'] >= self.confidence_threshold:
                results.append(TextBlock(
                    text=block['text'],
                    position=block['bbox'],
                    confidence=block['confidence'],
                    language=self.current_language
                ))
        return results
    
    def _run_easyocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Run EasyOCR and return results."""
        try:
            # Use paragraph=False for more reliable bounding boxes
            results = self.easyocr_reader.readtext(image, paragraph=False)
            
            blocks = []
            for result in results:
                # Handle different result formats
                if len(result) == 3:
                    bbox, text, confidence = result
                elif len(result) == 2:
                    bbox, text = result
                    confidence = 0.9  # Default confidence
                else:
                    self.logger.warning(f"Unexpected EasyOCR result format: {len(result)} values")
                    continue
                
                # Convert bbox to Rectangle
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                x = int(min(x_coords))
                y = int(min(y_coords))
                w = int(max(x_coords) - x)
                h = int(max(y_coords) - y)
                
                blocks.append({
                    'text': text,
                    'bbox': Rectangle(x=x, y=y, width=w, height=h),
                    'confidence': float(confidence),
                    'source': 'easyocr'
                })
            
            return blocks
            
        except Exception as e:
            self.logger.error(f"EasyOCR failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _run_tesseract(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Run Tesseract and return results."""
        try:
            from PIL import Image
            
            # Convert to PIL Image
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = image[:, :, ::-1]  # BGR to RGB
                pil_image = Image.fromarray(image_rgb)
            else:
                pil_image = Image.fromarray(image)
            
            # Map language codes
            lang_map = {
                'en': 'eng', 'ja': 'jpn', 'ko': 'kor', 'zh': 'chi_sim',
                'de': 'deu', 'fr': 'fra', 'es': 'spa'
            }
            tesseract_lang = lang_map.get(self.current_language, self.current_language)
            
            # Run Tesseract with line grouping
            custom_config = r'--psm 6 --oem 3'
            ocr_data = pytesseract.image_to_data(
                pil_image,
                lang=tesseract_lang,
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Group by lines
            lines = {}
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])
                
                if not text or conf < 0:
                    continue
                
                line_num = ocr_data['line_num'][i]
                if line_num not in lines:
                    lines[line_num] = []
                
                lines[line_num].append({
                    'text': text,
                    'left': ocr_data['left'][i],
                    'top': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'conf': conf
                })
            
            # Merge words in each line
            blocks = []
            for line_num, words in lines.items():
                if not words:
                    continue
                
                combined_text = ' '.join(w['text'] for w in words)
                min_x = min(w['left'] for w in words)
                min_y = min(w['top'] for w in words)
                max_x = max(w['left'] + w['width'] for w in words)
                max_y = max(w['top'] + w['height'] for w in words)
                avg_conf = sum(w['conf'] for w in words) / len(words)
                
                blocks.append({
                    'text': combined_text,
                    'bbox': Rectangle(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y),
                    'confidence': avg_conf / 100.0,
                    'source': 'tesseract'
                })
            
            return blocks
            
        except Exception as e:
            self.logger.error(f"Tesseract failed: {e}")
            return []

    
    def _combine_results(self, easyocr_blocks: List[Dict], tesseract_blocks: List[Dict]) -> List[TextBlock]:
        """Combine results from both engines based on strategy."""
        
        if self.strategy == 'easyocr_primary':
            return self._strategy_easyocr_primary(easyocr_blocks, tesseract_blocks)
        elif self.strategy == 'best_confidence':
            return self._strategy_best_confidence(easyocr_blocks, tesseract_blocks)
        elif self.strategy == 'longest_text':
            return self._strategy_longest_text(easyocr_blocks, tesseract_blocks)
        elif self.strategy == 'consensus':
            return self._strategy_consensus(easyocr_blocks, tesseract_blocks)
        else:
            # Default to best_confidence
            return self._strategy_best_confidence(easyocr_blocks, tesseract_blocks)
    
    def _strategy_easyocr_primary(self, easy_blocks: List[Dict], tess_blocks: List[Dict]) -> List[TextBlock]:
        """Use EasyOCR results, fill gaps with Tesseract."""
        results = []
        
        # Use all EasyOCR results
        for block in easy_blocks:
            results.append(TextBlock(
                text=block['text'],
                position=block['bbox'],
                confidence=block['confidence'],
                language=self.current_language
            ))
        
        # Add Tesseract results that don't overlap with EasyOCR
        for tess_block in tess_blocks:
            overlaps = False
            for easy_block in easy_blocks:
                if self._boxes_overlap(tess_block['bbox'], easy_block['bbox']):
                    overlaps = True
                    break
            
            if not overlaps and tess_block['confidence'] >= self.confidence_threshold:
                results.append(TextBlock(
                    text=tess_block['text'],
                    position=tess_block['bbox'],
                    confidence=tess_block['confidence'],
                    language=self.current_language
                ))
        
        return results
    
    def _strategy_best_confidence(self, easy_blocks: List[Dict], tess_blocks: List[Dict]) -> List[TextBlock]:
        """For each region, pick the result with highest confidence."""
        all_blocks = easy_blocks + tess_blocks
        results = []
        used_blocks = set()
        
        # Sort by confidence (highest first)
        all_blocks.sort(key=lambda x: x['confidence'], reverse=True)
        
        for block in all_blocks:
            # Skip if this region already covered by higher confidence block
            overlaps_used = False
            for used_idx in used_blocks:
                if self._boxes_overlap(block['bbox'], all_blocks[used_idx]['bbox']):
                    overlaps_used = True
                    break
            
            if not overlaps_used and block['confidence'] >= self.confidence_threshold:
                results.append(TextBlock(
                    text=block['text'],
                    position=block['bbox'],
                    confidence=block['confidence'],
                    language=self.current_language
                ))
                used_blocks.add(all_blocks.index(block))
        
        return results
    
    def _strategy_longest_text(self, easy_blocks: List[Dict], tess_blocks: List[Dict]) -> List[TextBlock]:
        """For overlapping regions, pick the longer/more complete text."""
        results = []
        
        # Match overlapping blocks
        matched_pairs = []
        unmatched_easy = list(easy_blocks)
        unmatched_tess = list(tess_blocks)
        
        for easy_block in easy_blocks:
            for tess_block in tess_blocks:
                if self._boxes_overlap(easy_block['bbox'], tess_block['bbox']):
                    matched_pairs.append((easy_block, tess_block))
                    if easy_block in unmatched_easy:
                        unmatched_easy.remove(easy_block)
                    if tess_block in unmatched_tess:
                        unmatched_tess.remove(tess_block)
                    break
        
        # For matched pairs, pick longer text
        for easy_block, tess_block in matched_pairs:
            if len(easy_block['text']) >= len(tess_block['text']):
                chosen = easy_block
            else:
                chosen = tess_block
            
            results.append(TextBlock(
                text=chosen['text'],
                position=chosen['bbox'],
                confidence=chosen['confidence'],
                language=self.current_language
            ))
        
        # Add unmatched blocks
        for block in unmatched_easy + unmatched_tess:
            if block['confidence'] >= self.confidence_threshold:
                results.append(TextBlock(
                    text=block['text'],
                    position=block['bbox'],
                    confidence=block['confidence'],
                    language=self.current_language
                ))
        
        return results
    
    def _strategy_consensus(self, easy_blocks: List[Dict], tess_blocks: List[Dict]) -> List[TextBlock]:
        """Only use text that both engines detected (high confidence)."""
        results = []
        
        for easy_block in easy_blocks:
            for tess_block in tess_blocks:
                if self._boxes_overlap(easy_block['bbox'], tess_block['bbox']):
                    # Both engines detected text in this region
                    # Use the one with higher confidence
                    if easy_block['confidence'] >= tess_block['confidence']:
                        chosen = easy_block
                    else:
                        chosen = tess_block
                    
                    results.append(TextBlock(
                        text=chosen['text'],
                        position=chosen['bbox'],
                        confidence=chosen['confidence'],
                        language=self.current_language
                    ))
                    break
        
        return results
    
    def _boxes_overlap(self, box1: Rectangle, box2: Rectangle, threshold: float = 0.3) -> bool:
        """Check if two bounding boxes overlap significantly."""
        # Calculate intersection
        x1 = max(box1.x, box2.x)
        y1 = max(box1.y, box2.y)
        x2 = min(box1.x + box1.width, box2.x + box2.width)
        y2 = min(box1.y + box1.height, box2.y + box2.height)
        
        if x2 < x1 or y2 < y1:
            return False  # No overlap
        
        intersection_area = (x2 - x1) * (y2 - y1)
        box1_area = box1.width * box1.height
        box2_area = box2.width * box2.height
        
        # Check if intersection is significant relative to either box
        overlap_ratio1 = intersection_area / box1_area if box1_area > 0 else 0
        overlap_ratio2 = intersection_area / box2_area if box2_area > 0 else 0
        
        return max(overlap_ratio1, overlap_ratio2) >= threshold
    
    def extract_text_batch(self, frames: List[Frame], options: OCRProcessingOptions) -> List[List[TextBlock]]:
        """Extract text from multiple frames."""
        results = []
        for frame in frames:
            results.append(self.extract_text(frame, options))
        return results
    
    def set_language(self, language: str) -> bool:
        """Set the OCR language."""
        try:
            if language != self.current_language:
                self.logger.info(f"Changing language from {self.current_language} to {language}")
                # Reinitialize EasyOCR with new language
                use_gpu = self.easyocr_reader.gpu if hasattr(self.easyocr_reader, 'gpu') else True
                self.easyocr_reader = easyocr.Reader([language], gpu=use_gpu)
                self.current_language = language
            return True
        except Exception as e:
            self.logger.error(f"Failed to set language: {e}")
            return False
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ['en', 'ja', 'ko', 'zh_sim', 'zh_tra', 'de', 'fr', 'es', 'ru']
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.easyocr_reader = None
        if hasattr(self, 'manga_ocr'):
            self.manga_ocr = None
        self.status = OCREngineStatus.UNINITIALIZED
        self.logger.info("Hybrid OCR engine cleaned up")
