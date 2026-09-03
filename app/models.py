from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List
from app.models import MakeMKVPreset


class DiscType(str, Enum):
    UNKNOWN = "unknown"
    DVD = "DVD"
    BLU_RAY = "Blu-ray"
    OPTICAL_MEDIA = "Optical Media"


@dataclass
class ScanResult:
    has_disc: bool = False
    drive_connected: bool = False
    label: str = ""
    disc_type: DiscType = DiscType.UNKNOWN
    title_count: int = 0
    drive: str = "/dev/sr0"
    error: Optional[str] = None


@dataclass
class AppConfig:
    drive_path: str = "/dev/sr0"
    temp_dir: str = "/tmp/ripper"
    output_dir: str = "/media/library"
    min_length: int = 1200
    makemkv_key: str = ""
    makemkv_preset: MakeMKVPreset = field(default_factory=MakeMKVPreset)


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
    languages: List[str] = field(default_factory=lambda: ["eng", "jpn", "nor", "nob", "nno"])

    @property
    def track_selection(self) -> str:
        return build_makemkv_selection_string(self.languages)