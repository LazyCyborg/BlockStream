# controller.py

import os
import threading
import logging
import pandas as pd
import time
from typing import Optional, Dict, Any

# Absolute imports
from recorder import (
    EEGRecorderBase,
    BrainVisionRecorder,
    SimulatedEEGRecorder,
    IS_WINDOWS,
    BRAINVISION_AVAILABLE,
    PLATFORM
)

from config import (
    RecordingAudioConfig,
    EEGConfig,
    BlockDurations,
    DirectoryConfig
)

from configs_manager import ExperimentConfig

from CPipeline.configs import ProcessingAudioConfig, PreprocessConfig
from CPipeline import PreprocTranscribeAudio, TextFeatures

class ExperimentController:
    def __init__(self):
        self.is_running = False
        self.current_block = None
        self.audio_files = []
        self.config = None
        self.current_loop = 0
        self.block_thread = None
        self.block_event = threading.Event()
        self.session_dir = None
        self.tone_file = None

        # Initialize audio processing and text analysis attributes
        self.audio_processing_results = None
        self.audio_processing_error = None
        self.is_processing_audio = False

        self.analysis_results = None
        self.analysis_error = None
        self.is_analyzing_text = False

        # Initialize EEG recorder
        self.eeg_recorder = self._initialize_eeg_recorder()

        # Load default configuration
        self.load_default_config()

    def load_default_config(self):
        """Load a default configuration"""
        config_dir = 'configs'
        os.makedirs(config_dir, exist_ok=True)
        default_config_path = os.path.join(config_dir, 'experiment_config.json')
        
        if os.path.exists(default_config_path):
            self.config = ExperimentConfig.load(default_config_path)
            logging.info("Loaded default configuration from file.")
        else:
            # Create a default configuration with preset values
            self.config = ExperimentConfig(
                experiment_type='full',
                num_loops=5,
                block_durations=BlockDurations(),
                audio_config=RecordingAudioConfig(),
                eeg_config=EEGConfig(),
                directories=DirectoryConfig(
                    base='experiment_data',
                    input='experiment_data/input',
                    output='experiment_data/output',
                    temp='experiment_data/temp'
                )
            )
            logging.info("Initialized with default configuration.")

    def save_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save experiment configuration"""
        try:
            logging.info(f"Attempting to save config: {config_data}")
            # Create ExperimentConfig from the incoming data
            config = ExperimentConfig.from_dict(config_data)
            
            # Create config directory if it doesn't exist
            config_dir = 'configs'
            os.makedirs(config_dir, exist_ok=True)
            
            # Save the config
            config_path = os.path.join(config_dir, 'experiment_config.json')
            config.save(config_path)
            self.config = config
            
            return {"success": True}
        except Exception as e:
            logging.error(f"Failed to save config: {str(e)}")
            return {"success": False, "error": str(e)}

    def _initialize_eeg_recorder(self) -> EEGRecorderBase:
        """Initialize appropriate EEG recorder based on platform and availability"""
        if IS_WINDOWS and BRAINVISION_AVAILABLE:
            logging.info("Using BrainVision Recorder")
            return BrainVisionRecorder()
        else:
            logging.info("Using Simulated EEG Recorder")
            return SimulatedEEGRecorder()

    def create_session_directory(self):
        """Create a directory for the current session."""
        self.session_dir = os.path.join(self.config.directories.output, f"session_{time.strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.session_dir, exist_ok=True)
        logging.info(f"Session directory created at {self.session_dir}")

    def create_tone_file(self):
        """Create a tone file required for the experiment."""
        # This is a placeholder implementation.
        self.tone_file = os.path.join(self.session_dir, 'tone.wav')
        # Generate or copy the tone file to self.tone_file
        # For now, let's assume the tone file is generated here
        logging.info(f"Tone file created at {self.tone_file}")

    def start_recording(self, filename: str) -> Dict[str, Any]:
        """Start EEG recording."""
        try:
            recording_path = os.path.join(self.session_dir, filename)
            result = self.eeg_recorder.start_recording(recording_path)
            logging.info(f"Started EEG recording at {recording_path}")
            return {"success": True}
        except Exception as e:
            logging.error(f"Failed to start recording: {str(e)}")
            return {"success": False, "error": str(e)}

    def stop_recording(self) -> Dict[str, Any]:
        """Stop EEG recording."""
        try:
            self.eeg_recorder.stop_recording()
            logging.info("EEG recording stopped.")
            return {"success": True}
        except Exception as e:
            logging.error(f"Failed to stop recording: {str(e)}")
            return {"success": False, "error": str(e)}

    def run_block(self, block):
        """Run an experiment block."""
        try:
            if not self.is_running:
                logging.info("Experiment stopped before block could start.")
                return {"success": False, "error": "Experiment stopped"}
            self.current_block = block['type']
            logging.info(f"Running block: {self.current_block}")
            duration = block['duration']
            # Simulate block execution
            time.sleep(duration)
            # Simulate recording audio
            audio_file = f"block_{self.current_block}_{time.strftime('%Y%m%d_%H%M%S')}.wav"
            audio_file_path = os.path.join(self.session_dir, audio_file)
            with open(audio_file_path, 'w') as f:
                f.write('Simulated audio data')
            self.audio_files.append(audio_file_path)
            logging.info(f"Completed block: {self.current_block}")
            self.current_block = None
            return {"success": True}
        except Exception as e:
            logging.error(f"Error running block: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_blocks_for_loop(self, loop_number):
        """Generate blocks for a specific loop."""
        blocks = []
        # Generate blocks based on experiment_type
        # Placeholder logic
        blocks.append({'type': 'A1', 'duration': self.config.block_durations.A1})
        blocks.append({'type': 'A2', 'duration': self.config.block_durations.A2})
        blocks.append({'type': 'B1', 'duration': self.config.block_durations.B1})
        blocks.append({'type': 'B2', 'duration': self.config.block_durations.B2})
        blocks.append({'type': 'Lag', 'duration': self.config.block_durations.Lag})
        blocks.append({'type': 'Intermission', 'duration': self.config.block_durations.Intermission})
        return blocks

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load experiment configuration"""
        try:
            self.config = ExperimentConfig.load(config_path)
            return {"success": True}
        except Exception as e:
            logging.error(f"Failed to load config: {str(e)}")
            return {"success": False, "error": str(e)}

    def save_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save experiment configuration"""
        try:
            # Map keys from camelCase to snake_case if necessary
            config = ExperimentConfig(
                experiment_type=config_data['experimentType'],
                num_loops=config_data['numLoops'],
                block_durations=BlockDurations(**config_data['blockDurations']),
                audio_config=RecordingAudioConfig(**config_data['audioConfig']),
                eeg_config=EEGConfig(
                    require_brainvision=config_data['eegConfig']['requireBrainvision'],
                    markers=config_data['eegConfig']['markers']
                ),
                directories=DirectoryConfig(**config_data['directories'])
            )

            config_path = os.path.join('configs', 'experiment_config.json')
            config.save(config_path)
            self.config = config
            return {"success": True}
        except Exception as e:
            logging.error(f"Failed to save config: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        if not hasattr(self, 'config') or not self.config:
            return {"success": False, "error": "No configuration loaded"}

        return {
            "success": True,
            "config": {
                "experimentType": self.config.experiment_type,
                "numLoops": self.config.num_loops,
                "blockDurations": vars(self.config.block_durations),
                "audioConfig": vars(self.config.audio_config),
                "eegConfig": {
                    "requireBrainvision": self.config.eeg_config.require_brainvision,
                    "markers": self.config.eeg_config.markers
                },
                "directories": vars(self.config.directories)
            }
        }

    def process_audio_files(self):
        """Process recorded audio files and generate transcriptions"""
        try:
            self.is_processing_audio = True
            audio_config = ProcessingAudioConfig(
                lowpass_freq=300,
                highpass_freq=2000,
                target_rate=16000,
                chunk_duration=6
            )
            preprocess_config = PreprocessConfig(
                remove_punctuation=False,
                normalize_chars=True,
                min_sentence_length=5,
                join_sentences=True
            )
            processor = PreprocTranscribeAudio(
                audio_dir=self.session_dir,
                audio_config=audio_config,
                preprocess_config=preprocess_config,
                whisper=True
            )
            processed_data = processor.process_all_files()
            output_path = os.path.join(self.session_dir, 'transcribed_audio.csv')
            processor.save_results(output_path)
            self.audio_processing_results = {
                'transcriptions': processed_data.to_dict(orient='records'),
                'summary': {
                    'total_files': len(self.audio_files),
                    'processed_files': len(processed_data['Filename'].unique()),
                    'total_sentences': len(processed_data) if not processed_data.empty else 0
                }
            }
            return True
        except Exception as e:
            self.audio_processing_error = str(e)
            logging.error(f"Error processing audio: {e}")
            return False
        finally:
            self.is_processing_audio = False

    def get_audio_processing_status(self):
        """Get current audio processing status and results"""
        return {
            'isProcessing': self.is_processing_audio,
            'results': self.audio_processing_results,
            'error': self.audio_processing_error
        }

    def analyze_text(self):
        """Analyze transcribed text for emotions and similarities."""
        try:
            self.is_analyzing_text = True
            transcription_path = os.path.join(self.session_dir, 'transcribed_audio.csv')
            if not os.path.exists(transcription_path):
                self.analysis_error = "Transcribed audio file not found."
                return False

            transcription_df = pd.read_csv(transcription_path)
            text_features = TextFeatures()
            analysis_result = text_features.process_transcriptions(transcription_df)

            output_path = os.path.join(self.session_dir, 'analyzed_text.csv')
            text_features.save_results(output_path)

            self.analysis_results = {
                'analysis': analysis_result.reset_index().to_dict(orient='records')
            }
            return True
        except Exception as e:
            self.analysis_error = str(e)
            logging.error(f"Error analyzing text: {e}")
            return False
        finally:
            self.is_analyzing_text = False

    def get_text_analysis_status(self):
        """Get current text analysis status and results"""
        return {
            'isAnalyzing': self.is_analyzing_text,
            'results': self.analysis_results,
            'error': self.analysis_error
        }
