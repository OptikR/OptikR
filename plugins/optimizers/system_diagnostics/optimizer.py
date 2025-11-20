"""
Real-Time Audio Translation Plugin

Hidden Feature: Live bidirectional audio translation for calls (Zoom, Skype, etc.)
Unlock: Alt+V in Pipeline Management tab

Pipeline Flow:
1. Capture audio from microphone
2. Transcribe with Whisper (Speech-to-Text)
3. Translate using OptikR translation engine
4. Generate speech with TTS (Text-to-Speech)
5. Output to virtual/physical audio device

Use Case: Single PC setup where user speaks in one language,
system translates and outputs in another language for calls.
Also listens to incoming audio, translates it back.
"""

from typing import Dict, Any, Optional
import threading
import time
import queue
import numpy as np

class SystemDiagnosticsOptimizer:
    """
    Real-time bidirectional audio translation for video calls.
    
    Features:
    - Microphone → Translation → Speaker output
    - Speaker input → Translation → Headphones output
    - Works with Zoom, Skype, Teams, etc.
    - Single device setup (one PC)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
        
        if not self.enabled:
            return
        
        # Device settings (single PC setup)
        self.input_device = config.get('input_device', None)  # Microphone
        self.output_device = config.get('output_device', None)  # Speaker/Headphones
        
        # Translation settings
        self.source_language = config.get('source_language', 'en')
        self.target_language = config.get('target_language', 'ja')
        self.bidirectional = config.get('bidirectional', True)  # Translate both ways
        
        # Model settings
        self.whisper_model_size = config.get('whisper_model', 'base')
        self.use_gpu = config.get('use_gpu', True)
        self.vad_enabled = config.get('vad_enabled', True)
        self.vad_sensitivity = config.get('vad_sensitivity', 2)
        
        # Audio settings
        self.sample_rate = 16000
        self.chunk_duration = 1.0  # seconds
        self.silence_threshold = 0.5  # seconds
        
        # Components (lazy loaded)
        self.whisper_model = None
        self.tts_engine = None
        self.pyaudio = None
        self.vad = None
        
        # State
        self.is_running = False
        self.input_stream = None
        self.output_stream = None
        self.audio_queue = queue.Queue()
        self.translation_queue = queue.Queue()
        self.worker_thread = None
        
        # Statistics
        self.stats = {
            'transcriptions': 0,
            'translations': 0,
            'speeches': 0,
            'errors': 0,
            'dict_hits': 0,
            'dict_misses': 0
        }
        
        # Translation engine integration (lazy loaded)
        self.translation_engine = None
        self.smart_dict = None
        
        print("[AUDIO_TRANSLATION] Plugin initialized")
        print(f"[AUDIO_TRANSLATION] Mode: {'Bidirectional' if self.bidirectional else 'Unidirectional'}")
        print(f"[AUDIO_TRANSLATION] {self.source_language} ↔ {self.target_language}")

    
    def initialize_components(self):
        """Initialize audio translation components (lazy loading)"""
        if not self.enabled:
            return False
            
        try:
            print("[AUDIO_TRANSLATION] Initializing components...")
            
            # Import audio libraries
            import whisper
            import torch
            import pyaudio
            
            # Initialize PyAudio
            self.pyaudio = pyaudio.PyAudio()
            
            # Initialize VAD if enabled
            if self.vad_enabled:
                try:
                    import webrtcvad
                    self.vad = webrtcvad.Vad(self.vad_sensitivity)
                    print("[AUDIO_TRANSLATION] VAD initialized")
                except ImportError:
                    print("[AUDIO_TRANSLATION] VAD not available, continuing without it")
                    self.vad_enabled = False
            
            # Determine device for Whisper
            device = 'cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu'
            print(f"[AUDIO_TRANSLATION] Loading Whisper '{self.whisper_model_size}' on {device}...")
            
            # Load Whisper model
            self.whisper_model = whisper.load_model(self.whisper_model_size, device=device)
            print("[AUDIO_TRANSLATION] Whisper model loaded")
            
            # Initialize TTS (using pyttsx3 for simplicity, or Coqui TTS)
            try:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                print("[AUDIO_TRANSLATION] TTS engine initialized (pyttsx3)")
            except Exception as e:
                print(f"[AUDIO_TRANSLATION] pyttsx3 not available: {e}")
                try:
                    from TTS.api import TTS
                    self.tts_engine = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts")
                    print("[AUDIO_TRANSLATION] TTS engine initialized (Coqui)")
                except Exception as e2:
                    print(f"[AUDIO_TRANSLATION] TTS not available: {e2}")
                    return False
            
            # Initialize Smart Dictionary (optional but recommended)
            try:
                from app.translation.smart_dictionary import SmartDictionary
                self.smart_dict = SmartDictionary()
                print("[AUDIO_TRANSLATION] Smart Dictionary initialized")
            except Exception as e:
                print(f"[AUDIO_TRANSLATION] Smart Dictionary not available: {e}")
                self.smart_dict = None
            
            # Initialize translation engine (optional - will use placeholder if not available)
            try:
                # Try to get translation engine from config
                engine_name = self.config.get('translation_engine', 'marianmt')
                
                # Import translation engine registry
                from app.translation.translation_engine_interface import TranslationEngineRegistry
                
                # This would need to be passed from the main application
                # For now, we'll leave it as None and use placeholder
                print(f"[AUDIO_TRANSLATION] Translation engine '{engine_name}' will be used when available")
                self.translation_engine = None  # Will be set by main app
                
            except Exception as e:
                print(f"[AUDIO_TRANSLATION] Translation engine not available: {e}")
                self.translation_engine = None
            
            print("[AUDIO_TRANSLATION] All components initialized successfully")
            return True
            
        except ImportError as e:
            print(f"[AUDIO_TRANSLATION] Missing dependencies: {e}")
            print("[AUDIO_TRANSLATION] Install: pip install openai-whisper pyaudio pyttsx3")
            print("[AUDIO_TRANSLATION] Optional: pip install webrtcvad TTS")
            return False
        except Exception as e:
            print(f"[AUDIO_TRANSLATION] Initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self):
        """Start the audio translation pipeline"""
        if self.is_running:
            print("[AUDIO_TRANSLATION] Already running")
            return False
        
        if not self.enabled:
            print("[AUDIO_TRANSLATION] Plugin not enabled")
            return False
        
        # Initialize components if not already done
        if not self.whisper_model:
            if not self.initialize_components():
                print("[AUDIO_TRANSLATION] Failed to initialize components")
                return False
        
        try:
            # Start input stream (microphone)
            self.input_stream = self.pyaudio.open(
                format=self.pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device,
                frames_per_buffer=int(self.sample_rate * 0.1),  # 100ms chunks
                stream_callback=self._audio_input_callback
            )
            
            # Start worker thread for processing
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.worker_thread.start()
            
            print("[AUDIO_TRANSLATION] Started successfully")
            print(f"[AUDIO_TRANSLATION] Input device: {self.input_device or 'default'}")
            print(f"[AUDIO_TRANSLATION] Output device: {self.output_device or 'default'}")
            return True
            
        except Exception as e:
            print(f"[AUDIO_TRANSLATION] Failed to start: {e}")
            import traceback
            traceback.print_exc()
            self.is_running = False
            return False
    
    def stop(self):
        """Stop the audio translation pipeline"""
        if not self.is_running:
            return
        
        print("[AUDIO_TRANSLATION] Stopping...")
        self.is_running = False
        
        # Stop streams
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None
        
        # Wait for worker thread
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
            self.worker_thread = None
        
        print("[AUDIO_TRANSLATION] Stopped")
    
    def _audio_input_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio input stream"""
        if status:
            print(f"[AUDIO_TRANSLATION] Input status: {status}")
        
        # Convert to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        
        # Check for speech using VAD
        if self.vad_enabled and self.vad:
            try:
                is_speech = self.vad.is_speech(in_data, self.sample_rate)
                if not is_speech:
                    return (in_data, self.pyaudio.paContinue)
            except:
                pass  # Continue without VAD if it fails
        
        # Add to processing queue
        self.audio_queue.put(audio_data)
        
        return (in_data, self.pyaudio.paContinue)
    
    def _processing_loop(self):
        """Main processing loop for audio translation"""
        audio_buffer = []
        last_speech_time = time.time()
        
        print("[AUDIO_TRANSLATION] Processing loop started")
        
        while self.is_running:
            try:
                # Get audio chunk from queue (with timeout)
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                    audio_buffer.append(audio_chunk)
                    last_speech_time = time.time()
                except queue.Empty:
                    pass
                
                # Check if we have enough audio and there's been silence
                current_time = time.time()
                silence_duration = current_time - last_speech_time
                
                if len(audio_buffer) > 0 and silence_duration > self.silence_threshold:
                    # Process accumulated audio
                    self._process_audio_buffer(audio_buffer)
                    audio_buffer = []
                
            except Exception as e:
                print(f"[AUDIO_TRANSLATION] Processing error: {e}")
                self.stats['errors'] += 1
                audio_buffer = []
        
        print("[AUDIO_TRANSLATION] Processing loop stopped")
    
    def _process_audio_buffer(self, audio_buffer):
        """Process accumulated audio buffer"""
        try:
            # Concatenate audio chunks
            audio_data = np.concatenate(audio_buffer)
            
            # Convert to float32 and normalize
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Transcribe with Whisper
            print("[AUDIO_TRANSLATION] Transcribing...")
            result = self.whisper_model.transcribe(
                audio_float,
                language=self.source_language if not self.bidirectional else None,
                fp16=False
            )
            
            text = result['text'].strip()
            detected_lang = result.get('language', self.source_language)
            
            if not text:
                return
            
            self.stats['transcriptions'] += 1
            print(f"[AUDIO_TRANSLATION] Transcribed ({detected_lang}): {text[:50]}...")
            
            # Determine translation direction
            if self.bidirectional:
                # Auto-detect and translate to the other language
                if detected_lang == self.source_language:
                    target_lang = self.target_language
                else:
                    target_lang = self.source_language
            else:
                target_lang = self.target_language
            
            # Translate text (this would integrate with OptikR's translation engine)
            translated_text = self._translate_text(text, detected_lang, target_lang)
            
            if translated_text:
                self.stats['translations'] += 1
                print(f"[AUDIO_TRANSLATION] Translated ({target_lang}): {translated_text[:50]}...")
                
                # Generate and play speech
                self._speak(translated_text, target_lang)
                self.stats['speeches'] += 1
            
        except Exception as e:
            print(f"[AUDIO_TRANSLATION] Buffer processing error: {e}")
            self.stats['errors'] += 1
            import traceback
            traceback.print_exc()
    
    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Translate text using OptikR's translation engine with Smart Dictionary"""
        try:
            # Try Smart Dictionary first (instant lookup, ~0.01s)
            if hasattr(self, 'smart_dict') and self.smart_dict:
                dict_entry = self.smart_dict.lookup(text, source_lang, target_lang)
                if dict_entry:
                    self.stats['dict_hits'] = self.stats.get('dict_hits', 0) + 1
                    print(f"[AUDIO_TRANSLATION] Dictionary hit: {text[:30]}... → {dict_entry.translation[:30]}...")
                    return dict_entry.translation
            
            # Dictionary miss - use AI translation engine
            self.stats['dict_misses'] = self.stats.get('dict_misses', 0) + 1
            
            # Get translation engine from config
            if hasattr(self, 'translation_engine') and self.translation_engine:
                result = self.translation_engine.translate_text(
                    text=text,
                    src_lang=source_lang,
                    tgt_lang=target_lang
                )
                
                translated_text = result.translated_text
                
                # Learn from AI translation if confidence is high
                if hasattr(self, 'smart_dict') and self.smart_dict and result.confidence > 0.85:
                    self.smart_dict.learn_from_translation(
                        source_text=text,
                        translation=translated_text,
                        source_language=source_lang,
                        target_language=target_lang,
                        confidence=result.confidence
                    )
                
                return translated_text
            
            # Fallback: placeholder if no engine available
            print("[AUDIO_TRANSLATION] Warning: No translation engine available")
            return f"[{target_lang.upper()}] {text}"
            
        except Exception as e:
            print(f"[AUDIO_TRANSLATION] Translation error: {e}")
            return None
    
    def _speak(self, text: str, language: str):
        """Convert text to speech and play"""
        try:
            if hasattr(self.tts_engine, 'say'):
                # pyttsx3
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            else:
                # Coqui TTS
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                self.tts_engine.tts_to_file(
                    text=text,
                    file_path=tmp_path,
                    language=language
                )
                
                # Play audio file
                self._play_audio_file(tmp_path)
                
                # Cleanup
                os.unlink(tmp_path)
            
            print("[AUDIO_TRANSLATION] Speech played")
            
        except Exception as e:
            print(f"[AUDIO_TRANSLATION] TTS error: {e}")
            self.stats['errors'] += 1
    
    def _play_audio_file(self, audio_file: str):
        """Play audio file to output device"""
        try:
            from scipy.io import wavfile
            
            # Read audio file
            sample_rate, audio_data = wavfile.read(audio_file)
            
            # Open output stream if not already open
            if not self.output_stream:
                self.output_stream = self.pyaudio.open(
                    format=self.pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    output=True,
                    output_device_index=self.output_device
                )
            
            # Play audio
            self.output_stream.write(audio_data.tobytes())
            
        except Exception as e:
            print(f"[AUDIO_TRANSLATION] Audio playback error: {e}")
    
    def list_audio_devices(self):
        """List available audio devices"""
        if not self.pyaudio:
            import pyaudio
            self.pyaudio = pyaudio.PyAudio()
        
        devices = []
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            devices.append({
                'index': i,
                'name': info['name'],
                'max_input_channels': info['maxInputChannels'],
                'max_output_channels': info['maxOutputChannels'],
                'default_sample_rate': info['defaultSampleRate']
            })
        
        return devices
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        dict_hit_rate = 0.0
        if self.stats.get('dict_hits', 0) + self.stats.get('dict_misses', 0) > 0:
            dict_hit_rate = self.stats.get('dict_hits', 0) / (self.stats.get('dict_hits', 0) + self.stats.get('dict_misses', 0))
        
        return {
            'enabled': self.enabled,
            'running': self.is_running,
            'transcriptions': self.stats['transcriptions'],
            'translations': self.stats['translations'],
            'speeches': self.stats['speeches'],
            'errors': self.stats['errors'],
            'dict_hits': self.stats.get('dict_hits', 0),
            'dict_misses': self.stats.get('dict_misses', 0),
            'dict_hit_rate': dict_hit_rate,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'bidirectional': self.bidirectional,
            'whisper_model': self.whisper_model_size,
            'input_device': self.input_device,
            'output_device': self.output_device,
            'smart_dict_enabled': self.smart_dict is not None,
            'translation_engine_enabled': self.translation_engine is not None
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'transcriptions': 0,
            'translations': 0,
            'speeches': 0,
            'errors': 0,
            'dict_hits': 0,
            'dict_misses': 0
        }
    
    def set_translation_engine(self, engine):
        """Set translation engine from main application"""
        self.translation_engine = engine
        print(f"[AUDIO_TRANSLATION] Translation engine set: {engine.engine_name if engine else 'None'}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop()
        if self.pyaudio:
            self.pyaudio.terminate()


# Plugin interface
def initialize(config: Dict[str, Any]):
    """Initialize the system diagnostics optimizer plugin"""
    return SystemDiagnosticsOptimizer(config)
