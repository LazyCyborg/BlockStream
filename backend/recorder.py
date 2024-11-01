# recorder.py

import platform
import logging
import datetime
import time

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
