import os
import logging

logger = logging.getLogger("ripper.key")

FORUM_KEY_URL = "https://forum.makemkv.com/forum/viewtopic.php?f=5&t=1053"
DIRECT_KEY_URL = "https://cable.ayra.ch/makemkv/api.php?raw"

class MakeMKVKeyError(Exception):
    """Raised when MakeMKV fails due to a missing, invalid, or expired key."""
    pass

def get_key_warning_message(reason: str) -> str:
    return (
        f"MakeMKV Key Failure: {reason}\n"
        f"Get the current beta key here: {FORUM_KEY_URL}\n"
        f"Here is an alternative url: {DIRECT_KEY_URL}\n" 
        "Set 'MAKEMKV_KEY=your_key_here' in your Dockge environment variables."
    )

def ensure_makemkv_key(key: str = "") -> bool:    
    if not key:
        logger.warning(
            "\n----------------------------------------------------------------------\n"
            "WARNING: MAKEMKV_KEY environment variable is not set.\n"
            f"{get_key_warning_message('Missing key')}\n"
            "----------------------------------------------------------------------"
        )
        return False

    try:
        settings_dir = os.path.expanduser("~/.makemkv")
        os.makedirs(settings_dir, exist_ok=True)
        conf_file = os.path.join(settings_dir, "settings.conf")
        with open(conf_file, "w") as f:
            f.write(f'app_Key = "{key}"\n')
        logger.info("MakeMKV registration key written to settings.conf.")
        return True
    except Exception as e:
        logger.error(f"Failed to write MakeMKV key: {e}")
        return False

def validate_mkv_output(output_text: str):
    """
    Parses makemkvcon output. Raises MakeMKVKeyError if an invalid/expired key is detected.
    """
    error_patterns = [
        "evaluation period has expired",
        "key registration failed",
        "this application version is too old"
    ]
    
    lower_output = output_text.lower()
    for pattern in error_patterns:
        if pattern in lower_output:
            msg = get_key_warning_message(f"Engine output: '{pattern}'")
            logger.error(msg)
            raise MakeMKVKeyError(msg)