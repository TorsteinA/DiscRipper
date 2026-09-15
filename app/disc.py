import asyncio
from dataclasses import asdict
import re
import os
import shutil
import logging

from fastapi import HTTPException

from app.makemkv_key_fetcher import validate_mkv_output, MakeMKVKeyError
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

async def scan_optical_drive(drive_path: str = "/dev/sg1") -> ScanResult:
    logger.info(f"Scanning optical drive...")
    result = ScanResult(drive=drive_path)

    # Fail fast and clean if the physical drive is powered off / disconnected
    if not os.path.exists(drive_path):
        logger.warning(f"Drive path {drive_path} not found. Drive is powered off or disconnected.")
        return result

    result.drive_connected = True

    makemkv_path = shutil.which("makemkvcon")
    if not makemkv_path:
        e_msg = "makemkvcon executable not found in PATH!"
        logger.error(e_msg)
        result.error = e_msg
        return result

    # Step 2: Query makemkvcon for disc structure & metadata (with 15s timeout safeguard)
    logger.info(f"Executing makemkvcon info on /dev/sg1")
    try:
        proc_mkv = await asyncio.create_subprocess_exec(
            makemkv_path, "-r", "info", "/dev/sg1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc_mkv.communicate(), timeout=300.0)
            output = stdout.decode(errors="ignore")
        except asyncio.TimeoutError:
            logger.warning("makemkvcon scan timed out after 15s (USB bridge or CSS stall). Killing process.")
            proc_mkv.kill()
            await proc_mkv.wait()
            return result

        # Raise exception immediately if output indicates an expired/invalid key
        validate_mkv_output(output)

        if proc_mkv.returncode == 0:
            tcount_match = re.search(r"TCOUNT:(\d+)", output)
            if tcount_match:
                result.title_count = int(tcount_match.group(1))
                result.has_disc = True
                logger.info(f"makemkvcon detected {result.title_count} total titles on disc.")

            cinfo_match = re.search(r'CINFO:2,0,"([^"]+)"', output)
            if cinfo_match and not result.label:
                result.label = cinfo_match.group(1)

            if "BD-ROM" in output or "Blu-ray" in output:
                result.disc_type = DiscType.BLU_RAY
            elif "DVD-ROM" in output or "DVD-Video" in output:
                result.disc_type = DiscType.DVD
            elif result.has_disc:
                result.disc_type = DiscType.OPTICAL_MEDIA

            logger.info(f"Disc inspection finished. Type: {result.disc_type}, Titles: {result.title_count}")
        else:
            logger.warning(f"makemkvcon exited with code {proc_mkv.returncode}: {stderr.decode().strip()}")

    except MakeMKVKeyError:
        raise
    except Exception as e:
        logger.error(f"makemkvcon execution error: {e}")

    return result