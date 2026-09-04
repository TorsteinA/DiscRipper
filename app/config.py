import os
import logging
from typing import Dict
from app.models import MakeMKVPreset, HandBrakePreset, AppSettings, DEFAULT_TARGET_LANGUAGES

logger = logging.getLogger("ripper.config")

def get_default_handbrake_presets(languages: list[str]) -> Dict[str, HandBrakePreset]:
    """Generates default HandBrake presets using the configured language list."""
    return {
        "dvd": HandBrakePreset(
            name="DVD 576p/480p (x264 Slower RF18 Decomb)",
            encoder="x264",
            quality=18,
            encoder_preset="slower",
            decomb=True,
            audio_languages=languages
        ),
        "bluray": HandBrakePreset(
            name="Blu-ray 1080p (x264 Slow RF20 Passthrough)",
            encoder="x264",
            quality=20,
            encoder_preset="slow",
            decomb=False,
            audio_languages=languages
        ),
        "uhd": HandBrakePreset(
            name="UHD 4K HDR (x265 10-bit Medium RF22 Passthrough)",
            encoder="x265_10bit",
            quality=22,
            encoder_preset="medium",
            decomb=False,
            audio_languages=languages
        )
    }


def load_config() -> AppSettings:
    config = AppSettings()

    config.makemkv_preset = MakeMKVPreset(
        name="Default (Movies + Extras)",
        min_length_seconds=config.min_length_seconds,
        languages=config.makemkv_languages
    )
    config.handbrake_presets = get_default_handbrake_presets(config.makemkv_languages)

    logger.info(
        f"Loaded config: drive={config.drive_path}, "
        f"movies={config.output_dir_movies}, "
        f"shows={config.output_dir_shows}, "
        f"data={config.data_dir}"
    )
    return config