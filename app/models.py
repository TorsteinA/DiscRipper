from enum import Enum
from dataclasses import dataclass
from typing import Optional


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