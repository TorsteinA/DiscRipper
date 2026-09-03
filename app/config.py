import os
import logging
from app.models import AppConfig, MakeMKVPreset

logger = logging.getLogger("ripper.config")

def load_config() -> AppConfig:

    # Allow comma-separated env var or fallback to default target languages
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
        )
    )
    logger.info(f"Loaded config: drive={config.drive_path}, output={config.output_dir}")
    logger.info(f"MakeMKV selection rule: {config.makemkv_preset.track_selection}")
    return config