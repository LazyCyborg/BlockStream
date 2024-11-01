import os
import json
import logging
from typing import Dict, Any, Optional, Tuple

# Absolute imports
from config import RecordingAudioConfig, EEGConfig, BlockDurations, DirectoryConfig

class ExperimentConfig:
    """Manages experiment configuration loading, validation, and saving."""
    def __init__(
        self,
        experiment_type: str,
        num_loops: int,
        block_durations: BlockDurations,
        audio_config: RecordingAudioConfig,
        eeg_config: EEGConfig,
        directories: DirectoryConfig
    ):
        self.experiment_type = experiment_type
        self.num_loops = num_loops
        self.block_durations = block_durations
        self.audio_config = audio_config
        self.eeg_config = eeg_config
        self.directories = directories
        
    @classmethod
    def load(cls, config_path: str) -> 'ExperimentConfig':
        """Load configuration from a JSON file, or return default if not found."""
        if not os.path.exists(config_path):
            logging.warning(f"Config file not found: {config_path}. Loading default configuration.")
            return cls(
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

        with open(config_path, 'r') as f:
            data = json.load(f)

        return cls(
            experiment_type=data.get('experiment_type', 'full'),
            num_loops=data.get('num_loops', 5),
            block_durations=BlockDurations(**data.get('block_durations', {})),
            audio_config=RecordingAudioConfig(**data.get('audio_config', {})),
            eeg_config=EEGConfig(**data.get('eeg_config', {})),
            directories=DirectoryConfig(**data.get('directories', {}))
        )

    def save(self, config_path: str):
        """Save configuration to a JSON file."""
        config_data = {
            'experiment_type': self.experiment_type,
            'num_loops': self.num_loops,
            'block_durations': {
                k: getattr(self.block_durations, k)
                for k in ['A1', 'A2', 'B1', 'B2', 'Lag', 'Intermission']
            },
            'audio_config': {
                'sample_rate': self.audio_config.sample_rate,
                'channels': self.audio_config.channels,
                'format': self.audio_config.format
            },
            'eeg_config': {
                'require_brainvision': self.eeg_config.require_brainvision,
                'markers': self.eeg_config.markers
            },
            'directories': {
                'base': self.directories.base,
                'input': self.directories.input,
                'output': self.directories.output,
                'temp': self.directories.temp
            }
        }

        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate the current configuration."""
        try:
            # Validate experiment type
            if self.experiment_type not in ['full', 'partial', 'simple']:
                return False, "Invalid experiment type"

            # Validate number of loops
            if not 1 <= self.num_loops <= 20:
                return False, "Number of loops must be between 1 and 20"

            # Validate block durations
            for name, duration in vars(self.block_durations).items():
                if not 0 <= duration <= 120:
                    return False, f"Invalid duration for block {name}"

            # Validate audio config
            if self.audio_config.sample_rate not in [44100, 48000, 96000]:
                return False, "Invalid sample rate"
            if self.audio_config.format not in ['16bit', '24bit', '32bit']:
                return False, "Invalid audio format"

            # Validate directories
            for dir_name, path in vars(self.directories).items():
                if not path:
                    return False, f"Missing {dir_name} directory path"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "experimentType": self.experiment_type,
            "numLoops": self.num_loops,
            "blockDurations": vars(self.block_durations),
            "audioConfig": {
                "sampleRate": self.audio_config.sample_rate,
                "channels": self.audio_config.channels,
                "format": self.audio_config.format
            },
            "eegConfig": {
                "requireBrainvision": self.eeg_config.require_brainvision,
                "markers": self.eeg_config.markers
            },
            "settings": {
                "dataDir": self.directories.base,
                "requireEEG": self.eeg_config.require_brainvision,
                "sampleRate": self.audio_config.sample_rate
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentConfig':
        """Create ExperimentConfig from dictionary data."""
        try:
            # Extract block durations
            block_durations = BlockDurations(**data.get('blockDurations', {}))
            
            # Create audio config
            audio_config = RecordingAudioConfig(
                sample_rate=data.get('settings', {}).get('sampleRate', 44100),
                channels=1,  # Default value
                format='16bit'  # Default value
            )
            
            # Create EEG config
            eeg_config = EEGConfig(
                require_brainvision=data.get('settings', {}).get('requireEEG', True),
                markers=True  # Default value
            )
            
            # Create directory config
            data_dir = data.get('settings', {}).get('dataDir', 'experiment_data')
            directories = DirectoryConfig(
                base=data_dir,
                input=os.path.join(data_dir, 'input'),
                output=os.path.join(data_dir, 'output'),
                temp=os.path.join(data_dir, 'temp')
            )
            
            return cls(
                experiment_type=data.get('experimentType', 'full'),
                num_loops=data.get('numLoops', 5),
                block_durations=block_durations,
                audio_config=audio_config,
                eeg_config=eeg_config,
                directories=directories
            )
            
        except Exception as e:
            logging.error(f"Error creating ExperimentConfig from dict: {str(e)}")
            raise