import os
import logging
from app.models import AppConfig

logger = logging.getLogger("ripper.config")

def load_config() -> AppConfig:
    config = AppConfig(
        drive_path = os.getenv("DRIVE_PATH", "/dev/sr0"),
        temp_dir = os.getenv("TEMP_DIR", "/tmp/ripper"),
        output_dir = os.getenv("OUTPUT_DIR", "/media/output"),
        min_length = int(os.getenv("MIN_LENGTH_SECONDS", "120")),
        makemkv_key=os.getenv("MAKEMKV_KEY", "").strip()
    )
    logger.info(f"Loaded config: drive={config.drive_path}, output={config.output_dir}")
    return config