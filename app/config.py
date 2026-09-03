import os
import logging
from typing import Dict
from app.models import AppConfig, MakeMKVPreset, HandBrakePreset

logger = logging.getLogger("ripper.config")

DEFAULT_HANDBRAKE_PRESETS: Dict[str, HandBrakePreset] = {
    "dvd": HandBrakePreset(
        name="DVD 576p/480p (x264 Slower RF18 Decomb)",
        encoder="x264",
        quality=18,
        encoder_preset="slower",
        decomb=True,
        audio_languages=["eng", "nor", "nob", "nno", "jpn"]
    ),
    "bluray": HandBrakePreset(
        name="Blu-ray 1080p (x264 Slow RF20 Passthrough)",
        encoder="x264",
        quality=20,
        encoder_preset="slow",
        decomb=False,
        audio_languages=["eng", "nor", "nob", "nno", "jpn"]
    ),
    "uhd": HandBrakePreset(
        name="UHD 4K HDR (x265 10-bit Medium RF22 Passthrough)",
        encoder="x265_10bit",
        quality=22,
        encoder_preset="medium",
        decomb=False,
        audio_languages=["eng", "nor", "nob", "nno", "jpn"]
    )
}

def load_config() -> AppConfig:
    raw_langs = os.getenv("MAKEMKV_LANGUAGES", "eng,jpn,nor,nob,nno")
    languages = [lang.strip() for lang in raw_langs.split(",") if lang.strip()]
    min_len = int(os.getenv("MIN_LENGTH_SECONDS", "120"))

    config = AppConfig(
        drive_path = os.getenv("DRIVE_PATH", "/dev/sr0"),
        temp_dir = os.getenv("TEMP_DIR", "/tmp/ripper"),
        output_dir = os.getenv("OUTPUT_DIR", "/media/output"),
        min_length = int(os.getenv("MIN_LENGTH_SECONDS", "120")),
        makemkv_key = os.getenv("MAKEMKV_KEY", "").strip(),
        makemkv_preset=MakeMKVPreset(
            name="Default (Movies + Extras)",
            min_length_seconds=min_len,
            languages=languages
        ),
        handbrake_presets=DEFAULT_HANDBRAKE_PRESETS
    )
    logger.info(f"Loaded config: drive={config.drive_path}, output={config.output_dir}")
    logger.info(f"MakeMKV selection rule: {config.makemkv_preset.track_selection}")
    return config