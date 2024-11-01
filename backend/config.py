# config.py

from dataclasses import dataclass


@dataclass
class RecordingAudioConfig:
    """Configuration for audio recording parameters."""
    sample_rate: int = 44100
    channels: int = 1
    format: str = '16bit'


@dataclass
class EEGConfig:
    """Configuration for EEG recording parameters."""
    require_brainvision: bool = True
    markers: bool = True


@dataclass
class BlockDurations:
    """Configuration for experiment block durations."""
    A1: int = 45
    A2: int = 45
    B1: int = 45
    B2: int = 45
    Lag: int = 5
    Intermission: int = 60


@dataclass
class DirectoryConfig:
    """Configuration for experiment directories."""
    base: str
    input: str
    output: str
    temp: str
