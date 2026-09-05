from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pydantic import Field
from pydantic_settings import BaseSettings

DEFAULT_TARGET_LANGUAGES: List[str] = ["eng", "jpn", "nor", "nob", "nno"]

class DiscType(str, Enum):
    UNKNOWN = "unknown"
    DVD = "DVD"
    BLU_RAY = "Blu-ray"
    OPTICAL_MEDIA = "Optical Media"

class MediaType(str, Enum):
    Movie = 'movie'
    Show = 'show'
    MovieExtras = 'movie extras'

class RippingStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def build_makemkv_selection_string(languages: List[str]) -> str:
    """
    Constructs a MakeMKV selection rule targeting audio and subtitles 
    for the provided ISO language codes.
    """
    if not languages:
        return "-sel:all"
    
    lang_filter = "|".join(languages)
    return f"-sel:all,+sel:audio&({lang_filter}),+sel:subtitle&({lang_filter})"

@dataclass
class MakeMKVPreset:
    name: str = "Default (Movies + Extras)"
    min_length_seconds: int = 120  # 2 minutes: captures extras, drops short menus/logos
    languages: List[str] = field(default_factory=lambda: list(DEFAULT_TARGET_LANGUAGES))

    @property
    def track_selection(self) -> str:
        return build_makemkv_selection_string(self.languages)

@dataclass
class HandBrakePreset:
    name: str
    encoder: str
    quality: int
    encoder_preset: str
    decomb: bool = False
    audio_languages: List[str] = field(default_factory=lambda: list(DEFAULT_TARGET_LANGUAGES))
    audio_copy_codecs: str = "ac3,eac3,dts,dtshd,truehd,flac,aac"
    
    def to_cli_args(self) -> List[str]:
        """Generates the command-line flags for HandBrakeCLI."""
        args = [
            "-e", self.encoder,
            "-q", str(self.quality),
            "--encoder-preset", self.encoder_preset,
            "--format", "av_mkv",
            "--markers",
        ]
        
        if self.decomb:
            args.extend(["--comb-detect", "--decomb"])
            
        if self.audio_languages:
            langs = ",".join(self.audio_languages)
            args.extend([
                "--audio-lang-list", langs,
                "--all-audio",
                "--aencoder", f"copy:{self.audio_copy_codecs}",
                "--audio-fallback", "aac",
                "--subtitle-lang-list", langs,
                "--all-subtitles"
            ])
            
        return args


@dataclass
class RipHistoryItem:
    id: str
    title: str
    year: Optional[str]
    media_type: MediaType
    disc_type: DiscType
    preset_used: str
    start_time: str
    end_time: Optional[str] = None
    status: RippingStatus = RippingStatus.IN_PROGRESS
    error: Optional[str] = None


@dataclass
class ScanResult:
    has_disc: bool = False
    drive_connected: bool = False
    label: str = ""
    disc_type: DiscType = DiscType.UNKNOWN
    title_count: int = 0
    drive: str = "/dev/sr0"
    error: Optional[str] = None


class AppSettings(BaseSettings):
    drive_path: str = "/dev/sr0"
    data_dir: str = "/data"
    temp_dir: str = "/tmp/ripper"
    output_dir_movies: str = "/media/movies"
    output_dir_shows: str = "/media/shows"
    makemkv_key: str = ""
    makemkv_languages: List[str] = Field(default_factory=lambda: list(DEFAULT_TARGET_LANGUAGES))
    min_length_seconds: int = 120

    # Populated programmatically in load_config()
    makemkv_preset: MakeMKVPreset = Field(default_factory=MakeMKVPreset)
    handbrake_presets: Dict[str, HandBrakePreset] = Field(default_factory=dict)
