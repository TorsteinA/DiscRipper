from dataclasses import asdict
import os
import logging
import subprocess

from fastapi import HTTPException

from app.makemkv_key_fetcher import validate_mkv_output, MakeMKVKeyError
from app.mkv import get_mkv_info_command
from app.models import AppSettings, ScanResult, DiscType

logger = logging.getLogger("ripper.disc")

async def do_drive_scan(config: AppSettings):
    try:
        logger.info("Initiating optical drive scan on /dev/sg1...")
        result = await scan_optical_drive(config.drive_path)
        logger.info(f"Scan complete. Disc present: {result.has_disc} | Label: '{result.label}' | Type: {result.disc_type}")
        return asdict(result)
    except MakeMKVKeyError as e:
        logger.error(f"Scan aborted due to MakeMKV Key failure: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"MakeMKV Key Error: {str(e)}"
        )
    except:
        raise

async def scan_optical_drive(drive_path: str) -> ScanResult:
    logger.info(f"Scanning optical drive at {drive_path}...")
    result = ScanResult(drive=drive_path)

    # Fail fast and clean if the physical drive is powered off / disconnected
    if not os.path.exists(drive_path):
        logger.warning(f"Drive path {drive_path} not found. Drive is powered off or disconnected.")
        return result

    result.drive_connected = True
    logger.info(f"Executing mkv info on {drive_path}")
    timeout = 120.0
    try:
        proc = subprocess.run(
            get_mkv_info_command(drive_path),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout
        )
        output = proc.stdout
        
        # Print the raw stdout to the logs so you can see exactly what it returned
        logger.info(f"Raw mkv output:\n{output}")
        
        if proc.stderr:
            logger.warning(f"Raw mkv stderr:\n{proc.stderr}")

        validate_mkv_output(output)

        return result

    except subprocess.TimeoutExpired:
        logger.warning(f"makemkvcon scan timed out after {timeout}s. Process killed automatically.")
        raise
    except MakeMKVKeyError:
        raise
    except Exception as e:
        logger.error(f"makemkvcon execution error: {e}")

    return result