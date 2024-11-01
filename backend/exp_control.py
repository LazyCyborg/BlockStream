import platform
import os
import time
import threading
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
from playsound import playsound
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import datetime
import logging
import importlib.util
import CPipeline

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('experiment.log'),
        logging.StreamHandler()
    ]
)

# Platform detection
PLATFORM = platform.system()
IS_WINDOWS = PLATFORM == "Windows"

# Conditional import of Windows-specific modules
if IS_WINDOWS:
    try:
        import win32com.client
        BRAINVISION_AVAILABLE = True
    except ImportError:
        logging.warning("win32com not installed. Installing required package...")
        try:
            import subprocess
            subprocess.check_call(["pip", "install", "pywin32"])
            import win32com.client
            BRAINVISION_AVAILABLE = True
        except Exception as e:
            logging.error(f"Failed to install win32com: {e}")
            BRAINVISION_AVAILABLE = False
else:
    BRAINVISION_AVAILABLE = False

class EEGRecorderBase:
    """Base class for EEG recording functionality"""
    def initialize(self):
        raise NotImplementedError

    def start_recording(self, filename):
        raise NotImplementedError

    def stop_recording(self):
        raise NotImplementedError

    def insert_marker(self, description, marker_type="Comment"):
        raise NotImplementedError

class BrainVisionRecorder(EEGRecorderBase):
    """Windows-specific BrainVision Recorder implementation"""
    def __init__(self):
        self.recorder = None

    def initialize(self):
        try:
            self.recorder = win32com.client.Dispatch("VisionRecorder.Application")
            version = self.recorder.Version
            return {"success": True, "version": version}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_recording(self, filename):
        try:
            self.recorder.Acquisition.ViewData()
            time.sleep(1)
            self.recorder.Acquisition.StartRecording(filename)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_recording(self):
        try:
            if self.recorder:
                self.recorder.Acquisition.StopRecording()
                time.sleep(1)
                self.recorder.Acquisition.StopViewing()
                self.recorder.Quit()
                self.recorder = None
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def insert_marker(self, description, marker_type="Comment"):
        try:
            self.recorder.Acquisition.SetMarker(description, marker_type)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

class SimulatedEEGRecorder(EEGRecorderBase):
    """Simulated EEG recorder for non-Windows platforms"""
    def __init__(self):
        self.is_recording = False
        self.markers = []
        self.recording_file = None

    def initialize(self):
        return {"success": True, "version": "Simulated EEG Recorder 1.0"}

    def start_recording(self, filename):
        self.is_recording = True
        self.recording_file = filename
        logging.info(f"[SIMULATION] Started EEG recording: {filename}")
        return {"success": True}

    def stop_recording(self):
        self.is_recording = False
        self.recording_file = None
        logging.info("[SIMULATION] Stopped EEG recording")
        return {"success": True}

    def insert_marker(self, description, marker_type="Comment"):
        if self.is_recording:
            self.markers.append({
                "description": description,
                "type": marker_type,
                "timestamp": datetime.datetime.now().isoformat()
            })
            logging.info(f"[SIMULATION] Marker inserted: {description}")
            return {"success": True}
        return {"success": False, "error": "Not recording"}

class ExperimentController:
    def __init__(self):
        # Initialize platform-specific EEG recorder
        if IS_WINDOWS and BRAINVISION_AVAILABLE:
            self.eeg_recorder = BrainVisionRecorder()
            logging.info("Using BrainVision Recorder")
        else:
            self.eeg_recorder = SimulatedEEGRecorder()
            logging.info("Using Simulated EEG Recorder")

        self.is_running = False
        self.current_block = None
        self.audio_files = []
        self.experiment_config = None
        self.current_loop = 0
        self.block_thread = None
        self.block_event = threading.Event()
        self.session_dir = None
        self.tone_file = None

    def create_session_directory(self):
        """Create a directory for the current session's data"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join("experiment_data", f"session_{timestamp}")
        os.makedirs(self.session_dir, exist_ok=True)
        logging.info(f"Created session directory: {self.session_dir}")

    def create_tone_file(self):
        """Create a simple tone file for audio cues"""
        self.tone_file = os.path.join(self.session_dir, "tone.wav")
        fs = 44100  # Sample rate
        duration = 0.5  # Duration in seconds
        frequency = 440.0  # Frequency in Hz (A4 note)
        t = np.linspace(0, duration, int(fs * duration), endpoint=False)
        audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)
        write(self.tone_file, fs, audio_data.astype(np.float32))
        logging.info("Created tone file")

    def initialize_recorder(self):
        """Initialize the EEG recorder"""
        return self.eeg_recorder.initialize()

    def start_recording(self, eeg_filename):
        """Start EEG recording"""
        full_path = os.path.join(self.session_dir, eeg_filename)
        return self.eeg_recorder.start_recording(full_path)

    def stop_recording(self):
        """Stop EEG recording"""
        return self.eeg_recorder.stop_recording()

    def insert_marker(self, description, marker_type="Comment"):
        """Insert a marker into the EEG recording"""
        return self.eeg_recorder.insert_marker(description, marker_type)

    def record_audio(self, duration, filename, fs=44100):
        """Record audio for the specified duration"""
        try:
            full_path = os.path.join(self.session_dir, filename)
            audio_data = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            write(full_path, fs, audio_data)
            logging.info(f"Recorded audio: {full_path}")
            return {"success": True, "filename": filename}
        except Exception as e:
            logging.error(f"Failed to record audio: {str(e)}")
            return {"success": False, "error": str(e)}

    def play_tone(self):
        """Play the audio tone"""
        try:
            playsound(self.tone_file)
            logging.info("Played tone")
            return {"success": True}
        except Exception as e:
            logging.error(f"Failed to play tone: {str(e)}")
            return {"success": False, "error": str(e)}

    def run_block(self, block_data):
        """Execute a single experiment block"""
        try:
            block_type = block_data["type"]
            duration = block_data["duration"]
            
            self.current_block = block_data
            logging.info(f"Starting block: {block_type}, Loop: {self.current_loop + 1}")
            
            if block_type.startswith('A'):
                # Audio recording blocks
                audio_filename = f"Audio_{block_type}_Loop{self.current_loop + 1}.wav"
                self.audio_files.append(audio_filename)
                self.record_audio(duration, audio_filename)
                
            elif block_type.startswith('B'):
                # EEG recording blocks
                self.insert_marker(f"{block_type}_Block_Start_Loop{self.current_loop + 1}")
                time.sleep(duration)
                self.play_tone()
                self.insert_marker(f"{block_type}_Block_End_Loop{self.current_loop + 1}")
                
            elif block_type == "Lag":
                time.sleep(duration)
                
            elif block_type == "Intermission":
                time.sleep(duration)
                self.current_loop += 1
                
            logging.info(f"Completed block: {block_type}")
            return {"success": True}
        except Exception as e:
            logging.error(f"Error in block execution: {str(e)}")
            return {"success": False, "error": str(e)}

app = Flask(__name__)
CORS(app)

controller = ExperimentController()

@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize the experiment system"""
    controller.create_session_directory()
    controller.create_tone_file()
    return jsonify(controller.initialize_recorder())

@app.route('/api/start', methods=['POST'])
def start_experiment():
    """Start the experiment"""
    try:
        data = request.json
        controller.experiment_config = data
        
        # Initialize experiment
        if data.get('eegRequired'):
            result = controller.start_recording(f"Experiment_{time.strftime('%Y%m%d_%H%M%S')}.eeg")
            if not result["success"]:
                return jsonify(result)
        
        controller.is_running = True
        controller.current_loop = 0
        
        # Start experiment thread
        controller.block_thread = threading.Thread(target=run_experiment_blocks)
        controller.block_thread.start()
        
        logging.info("Started experiment")
        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"Failed to start experiment: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_experiment():
    """Stop the experiment"""
    try:
        controller.is_running = False
        if controller.block_thread:
            controller.block_thread.join()
        result = controller.stop_recording()
        logging.info("Stopped experiment")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Failed to stop experiment: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current experiment status"""
    return jsonify({
        "isRunning": controller.is_running,
        "currentBlock": controller.current_block,
        "currentLoop": controller.current_loop,
        "audioFiles": controller.audio_files
    })

def run_experiment_blocks():
    """Execute experiment blocks in sequence"""
    try:
        blocks = controller.experiment_config.get('blocks', [])
        
        for block in blocks:
            if not controller.is_running:
                break
            
            result = controller.run_block(block)
            if not result["success"]:
                logging.error(f"Block execution failed: {result.get('error')}")
                controller.is_running = False
                break
    except Exception as e:
        logging.error(f"Error in experiment execution: {str(e)}")
        controller.is_running = False
from CPipeline import PreprocTranscribeAudio, AudioConfig, PreprocessConfig

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    """Process audio files from the experiment"""
    try:
        # Get session directory from the active experiment controller
        if not controller.session_dir:
            return jsonify({
                'success': False,
                'error': 'No active session directory'
            }), 400

        # Initialize audio processor with custom configs
        audio_config = AudioConfig(
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
            audio_dir=controller.session_dir,
            audio_config=audio_config,
            preprocess_config=preprocess_config,
            whisper=True  # Using Whisper model for Swedish
        )

        # Process all audio files
        processed_data = processor.process_all_files()
        
        # Save results
        output_path = os.path.join(controller.session_dir, 'transcribed_audio.csv')
        processor.save_results(output_path)

        return jsonify({
            'success': True,
            'transcriptions': processed_data.to_dict(orient='records'),
            'summary': {
                'total_files': len(controller.audio_files),
                'processed_files': len(processor.transcriptions),
                'total_sentences': len(processed_data) if not processed_data.empty else 0
            }
        })

    except Exception as e:
        logging.error(f"Error processing audio: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Print platform information
    logging.info(f"Running on platform: {PLATFORM}")
    logging.info(f"BrainVision Recorder available: {BRAINVISION_AVAILABLE}")
    
    # Ensure experiment data directory exists
    os.makedirs("experiment_data", exist_ok=True)
    
    # Start the Flask server
    app.run(port=5000)