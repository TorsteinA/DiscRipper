import asyncio
import re
import shutil
import logging

logger = logging.getLogger("ripper.disc")

async def scan_optical_drive(drive_path: str = "/dev/sr0") -> dict:
    """
    Checks the drive using blkid and makemkvcon without mounting the filesystem.
    Prevents kernel locks on raw/unfinalized optical media.
    """
    result = {
        "has_disc": False,
        "label": "",
        "disc_type": "unknown",
        "title_count": 0,
        "drive": drive_path
    }

    # Step 1: Query volume label via blkid
    logger.debug(f"Executing blkid for drive: {drive_path}")
    try:
        proc = await asyncio.create_subprocess_exec(
            "blkid", "-o", "value", "-s", "LABEL", drive_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0 and stdout:
            result["label"] = stdout.decode().strip()
            result["has_disc"] = True
    except Exception as e:
        logger.warning(f"blkid execution failed: {e}")

    # Verify binary exists before execution
    makemkv_path = shutil.which("makemkvcon")
    if not makemkv_path:
        logger.error("makemkvcon executable not found in PATH!")
        return result

    # Step 2: Query makemkvcon for disc structure & metadata
    try:
        proc = await asyncio.create_subprocess_exec(
            makemkv_path, "-r", "info", f"dev:{drive_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode(errors="ignore")

        if proc.returncode == 0:
            tcount_match = re.search(r"TCOUNT:(\d+)", output)
            if tcount_match:
                result["title_count"] = int(tcount_match.group(1))
                result["has_disc"] = True

            cinfo_match = re.search(r'CINFO:2,0,"([^"]+)"', output)
            if cinfo_match and not result["label"]:
                result["label"] = cinfo_match.group(1)

            if "BD-ROM" in output or "Blu-ray" in output:
                result["disc_type"] = "Blu-ray"
            elif "DVD-ROM" in output or "DVD-Video" in output:
                result["disc_type"] = "DVD"
            elif result["has_disc"]:
                result["disc_type"] = "Optical Media"

            logger.info(f"Disc inspection finished. Type: {result['disc_type']}, Titles: {result['title_count']}")
        else:
            logger.warning(f"makemkvcon exited with code {proc.returncode}: {stderr.decode().strip()}")

    except Exception as e:
        logger.error(f"makemkvcon execution error: {e}")

    return result