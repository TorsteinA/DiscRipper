import os
import logging

logger = logging.getLogger("ripper.config")

def load_config() -> dict:
    config = {
        "drive_path": os.getenv("DRIVE_PATH", "/dev/sr0"),
        "temp_dir": os.getenv("TEMP_DIR", "/tmp/ripper"),
        "output_dir": os.getenv("OUTPUT_DIR", "/media/output"),
        "min_length": int(os.getenv("MIN_LENGTH_SECONDS", "120")),
    }
    logger.info(f"Loaded config: drive={config['drive_path']}, output={config['output_dir']}")
    return config