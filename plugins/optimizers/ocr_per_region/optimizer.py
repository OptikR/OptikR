"""
OCR per Region Optimizer Plugin

Allows assigning different OCR engines to different capture regions.
Perfect for multi-region setups where different areas have different text styles.

Example use cases:
- Region 1 (manga): Use EasyOCR or Hybrid OCR
- Region 2 (subtitles): Use Tesseract (faster)
- Region 3 (UI text): Use PaddleOCR
"""

import time
from typing import Dict, Any, List, Optional
import threading
import concurrent.futures


class OCRPerRegionOptimizer:
    """Routes OCR processing to different engines based on region."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.region_ocr_mapping = config.get('region_ocr_mapping', {})
        self.default_ocr = config.get('default_ocr', 'easyocr')
        self.parallel_regions = config.get('parallel_regions', True)
        self.cache_engines = config.get('cache_engines', True)
        
        # Cache for loaded OCR engines
        self.engine_cache = {}
        self.lock = threading.Lock()
        
        # Statistics
        self.total_frames = 0
        self.regions_processed = {}
        self.engine_usage = {}
        
        # Load mappings from config manager if available
        self._load_mappings_from_config()
        
        print(f"[OCR_PER_REGION] Initialized")
        print(f"  Default OCR: {self.default_ocr}")
        print(f"  Region mappings: {len(self.region_ocr_mapping)}")
        print(f"  Mappings: {self.region_ocr_mapping}")
        print(f"  Parallel processing: {self.parallel_regions}")
        print(f"  Engine caching: {self.cache_engines}")
    
    def _load_mappings_from_config(self):
        """Load region-to-OCR mappings from config manager."""
        try:
            # Try to get config_manager from global context
            config_manager = self.config.get('config_manager')
            if config_manager:
                saved_mappings = config_manager.get_setting('plugins.ocr_per_region.region_ocr_mapping', {})
                if saved_mappings:
                    self.region_ocr_mapping.update(saved_mappings)
                    print(f"[OCR_PER_REGION] Loaded mappings from config: {saved_mappings}")
        except Exception as e:
            print(f"[OCR_PER_REGION] Could not load mappings from config: {e}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-process: Route OCR to appropriate engine based on region.
        
        This runs BEFORE OCR, so we need to:
        1. Check which region this frame is from
        2. Select appropriate OCR engine
        3. Store engine selection for OCR layer to use
        """
        frame = data.get('frame')
        if not frame:
            return data
        
        # Get region information from frame
        region = getattr(frame, 'source_region', None)
        if not region:
            # No region info - use default
            data['selected_ocr_engine'] = self.default_ocr
            return data
        
        region_id = region.region_id
        region_name = region.name
        
        # Get OCR engine for this region
        selected_engine = self.region_ocr_mapping.get(region_id, self.default_ocr)
        
        # Store selection in data for OCR layer
        data['selected_ocr_engine'] = selected_engine
        data['region_id'] = region_id
        data['region_name'] = region_name
        
        # Update statistics
        with self.lock:
            self.total_frames += 1
            self.regions_processed[region_id] = self.regions_processed.get(region_id, 0) + 1
            self.engine_usage[selected_engine] = self.engine_usage.get(selected_engine, 0) + 1
        
        print(f"[OCR_PER_REGION] Region '{region_name}' → {selected_engine}")
        
        return data
    
    def set_region_ocr(self, region_id: str, ocr_engine: str):
        """Set OCR engine for a specific region."""
        with self.lock:
            self.region_ocr_mapping[region_id] = ocr_engine
            print(f"[OCR_PER_REGION] Set region '{region_id}' → {ocr_engine}")
            # Save to config if available
            self._save_mappings_to_config()
    
    def _save_mappings_to_config(self):
        """Save region-to-OCR mappings to config manager."""
        try:
            config_manager = self.config.get('config_manager')
            if config_manager:
                config_manager.set_setting('plugins.ocr_per_region.region_ocr_mapping', self.region_ocr_mapping)
                print(f"[OCR_PER_REGION] Saved mappings to config: {self.region_ocr_mapping}")
        except Exception as e:
            print(f"[OCR_PER_REGION] Could not save mappings to config: {e}")
    
    def get_region_ocr(self, region_id: str) -> str:
        """Get OCR engine for a specific region."""
        return self.region_ocr_mapping.get(region_id, self.default_ocr)
    
    def get_all_mappings(self) -> Dict[str, str]:
        """Get all region-to-OCR mappings."""
        return self.region_ocr_mapping.copy()
    
    def clear_mapping(self, region_id: str):
        """Clear OCR mapping for a region (will use default)."""
        with self.lock:
            if region_id in self.region_ocr_mapping:
                del self.region_ocr_mapping[region_id]
                print(f"[OCR_PER_REGION] Cleared mapping for region '{region_id}'")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        with self.lock:
            return {
                'total_frames': self.total_frames,
                'regions_processed': self.regions_processed.copy(),
                'engine_usage': self.engine_usage.copy(),
                'active_mappings': len(self.region_ocr_mapping),
                'default_ocr': self.default_ocr
            }
    
    def reset(self):
        """Reset optimizer state."""
        with self.lock:
            self.total_frames = 0
            self.regions_processed.clear()
            self.engine_usage.clear()


# Plugin interface
def initialize(config: Dict[str, Any]) -> OCRPerRegionOptimizer:
    """Initialize the optimizer plugin."""
    return OCRPerRegionOptimizer(config)
