from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import logging
import os
import pandas as pd
import time

# Import local modules using absolute imports
from CPipeline import PreprocTranscribeAudio, TextFeatures
from CPipeline.configs import ProcessingAudioConfig, PreprocessConfig
from controller import ExperimentController
from config import RecordingAudioConfig, EEGConfig, BlockDurations, DirectoryConfig
from configs_manager import ExperimentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('experiment.log'),
        logging.StreamHandler()
    ]
)

# Initialize controller
controller = ExperimentController()

app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:3000"]}},
    supports_credentials=True
)

@app.route('/api/save-config', methods=['POST'])
def save_config():
    """Save experiment configuration"""
    try:
        logging.info("Received POST request to /api/save-config")
        response = controller.save_config(request.json)
        logging.info(f"Configuration saved: {response}")
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in /api/save-config: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/get-config', methods=['GET'])
def get_experiment_config():
    """Get current configuration"""
    logging.info("Received GET request for /api/get-config")
    response = controller.get_config()
    logging.info(f"Configuration returned: {response}")
    return jsonify(response)

@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize the experiment system with current configuration"""
    try:
        logging.info("Received POST request to /api/initialize")
        # Create session directory
        controller.create_session_directory()

        # Initialize EEG recorder
        result = controller.eeg_recorder.initialize()

        # Create tone file
        controller.create_tone_file()

        logging.info("Experiment system initialized successfully")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error in /api/initialize: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/start', methods=['POST', 'OPTIONS'])
def start_experiment():
    """Start the experiment with current configuration"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        logging.info("Received POST request to /api/start")
        data = request.json
        logging.info(f"Received data: {data}")

        # If configuration data is provided in the request, update the controller's config
        if 'config' in data:
            response = controller.save_config(data['config'])
            if not response.get('success'):
                logging.error(f"Failed to save config: {response.get('error')}")
                return jsonify(response), 400

        if not controller.config:
            logging.error("No configuration loaded when trying to start experiment")
            return jsonify({
                "success": False,
                "error": "No configuration loaded"
            })

        controller.is_running = True
        controller.current_loop = 0

        # Start recording if EEG is required
        if controller.config.eeg_config.require_brainvision:
            result = controller.start_recording(
                f"Experiment_{time.strftime('%Y%m%d_%H%M%S')}.eeg"
            )
            if not result["success"]:
                return jsonify(result)

        # Start experiment thread
        controller.block_thread = threading.Thread(target=run_experiment_blocks)
        controller.block_thread.start()

        logging.info("Experiment started successfully")
        return jsonify({"success": True})
        
    except Exception as e:
        logging.error(f"Error in /api/start: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/stop', methods=['POST'])
def stop_experiment():
    """Stop the experiment"""
    try:
        logging.info("Received POST request to /api/stop")
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
    logging.info("Received GET request for /api/status")
    audio_status = controller.get_audio_processing_status()
    text_status = controller.get_text_analysis_status()
    
    return jsonify({
        "isRunning": controller.is_running,
        "currentBlock": controller.current_block,
        "currentLoop": controller.current_loop,
        "error": None,  # Add any error handling as needed
        "audioProcessing": audio_status,
        "textAnalysis": text_status
    })

def run_experiment_blocks():
    """Execute experiment blocks in sequence"""
    try:
        logging.info("Starting experiment blocks execution")
        num_loops = controller.config.num_loops
        for loop_index in range(num_loops):
            if not controller.is_running:
                logging.info("Experiment stopped, breaking out of loop")
                break
            controller.current_loop = loop_index + 1
            logging.info(f"Starting loop {controller.current_loop}/{num_loops}")
            blocks = controller.get_blocks_for_loop(controller.current_loop)
            for block in blocks:
                if not controller.is_running:
                    logging.info("Experiment stopped, breaking out of block loop")
                    break
                result = controller.run_block(block)
                if not result["success"]:
                    logging.error(f"Block execution failed: {result.get('error')}")
                    controller.is_running = False
                    break
            logging.info(f"Completed loop {controller.current_loop}/{num_loops}")
        logging.info("Experiment blocks execution completed")
        controller.is_running = False
    except Exception as e:
        logging.error(f"Error in experiment execution: {str(e)}")
        controller.is_running = False

@app.route('/api/browse-directory', methods=['GET'])
def browse_directory():
    """Open a directory browser dialog and return the selected path"""
    try:
        # Create and hide the tkinter root window
        root = Tk()
        root.withdraw()
        
        # Open the directory browser dialog
        directory = filedialog.askdirectory(
            title='Select Data Directory',
            initialdir=os.path.expanduser('~')  # Start from user's home directory
        )
        
        if directory:
            return jsonify({
                'success': True,
                'path': directory
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No directory selected'
            })
            
    except Exception as e:
        logging.error(f"Error in directory browser: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        # Ensure the root window is destroyed
        try:
            root.destroy()
        except:
            pass

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    """Process audio files from the experiment"""
    try:
        logging.info("Received POST request to /api/process-audio")
        # Check if already processing
        if controller.is_processing_audio:
            return jsonify({
                'success': False,
                'error': 'Audio processing is already in progress'
            }), 400

        # Start processing in a new thread to avoid blocking
        processing_thread = threading.Thread(target=controller.process_audio_files)
        processing_thread.start()

        logging.info("Audio processing started")
        return jsonify({
            'success': True,
            'message': 'Audio processing started'
        })

    except Exception as e:
        logging.error(f"Error processing audio: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analyze-text', methods=['POST'])
def analyze_text():
    """Analyze transcribed text."""
    try:
        logging.info("Received POST request to /api/analyze-text")
        # Check if already analyzing
        if controller.is_analyzing_text:
            return jsonify({
                'success': False,
                'error': 'Text analysis is already in progress'
            }), 400

        # Start analysis in a new thread to avoid blocking
        analysis_thread = threading.Thread(target=controller.analyze_text)
        analysis_thread.start()

        logging.info("Text analysis started")
        return jsonify({
            'success': True,
            'message': 'Text analysis started'
        })

    except Exception as e:
        logging.error(f"Error analyzing text: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/status/audio-processing', methods=['GET'])
def audio_processing_status():
    """Get the current status of audio processing."""
    logging.info("Received GET request for /api/status/audio-processing")
    status = controller.get_audio_processing_status()
    return jsonify(status)

@app.route('/api/status/text-analysis', methods=['GET'])
def text_analysis_status():
    """Get the current status of text analysis."""
    logging.info("Received GET request for /api/status/text-analysis")
    status = controller.get_text_analysis_status()
    return jsonify(status)

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs("experiment_data", exist_ok=True)
    os.makedirs("configs", exist_ok=True)

    # Start the Flask server
    app.run(host='0.0.0.0', port=5001, threaded=True)