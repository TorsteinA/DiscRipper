import asyncio
import re
import os
import shutil
import logging

from app.makemkv_key_fetcher import validate_mkv_output, MakeMKVKeyError
from app.models import ScanResult, DiscType

logger = logging.getLogger("ripper.disc")

async def release_drive_lock(drive_path: str = "/dev/sr0") -> None:
    """Forces the kernel to release SCSI/block handles on the optical drive."""
    try:
        # Step 1: Request media change / lock drop via eject
        proc = await asyncio.create_subprocess_exec(
            "eject", "-X", drive_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        
        # Step 2: Flush kernel block buffers for sr0
        proc_block = await asyncio.create_subprocess_exec(
            "blockdev", "--flushbufs", drive_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc_block.wait()
        logger.debug(f"Released SCSI handles and flushed block buffers for {drive_path}")
    except Exception as e:
        logger.warning(f"Failed to release drive lock on {drive_path}: {e}")


async def scan_optical_drive(drive_path: str = "/dev/sr0") -> ScanResult:
    await release_drive_lock(drive_path)
    result = ScanResult(drive=drive_path)

    # Fail fast and clean if the physical drive is powered off / disconnected
    if not os.path.exists(drive_path):
        logger.info(f"Drive path {drive_path} not found. Drive is powered off or disconnected.")
        return result

    result.drive_connected = True

    # Step 1: Fast volume label check via blkid (with 5s timeout to prevent I/O stalls)
    logger.debug(f"Executing blkid for drive: {drive_path}")
    try:
        proc_blkid = await asyncio.create_subprocess_exec(
            "blkid", "-o", "value", "-s", "LABEL", drive_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc_blkid.communicate(), timeout=5.0)
            if proc_blkid.returncode == 0 and stdout:
                result.label = stdout.decode().strip()
                result.has_disc = True
                logger.info(f"blkid successfully read disc label: '{result.label}'")
            else:
                logger.debug(f"blkid returned code {proc_blkid.returncode}: {stderr.decode().strip()}")
        except asyncio.TimeoutError:
            logger.warning("blkid timed out after 5s (hardware bus or sector read stall).")
            proc_blkid.kill()
            await proc_blkid.wait()

    except Exception as e:
        logger.warning(f"blkid execution failed: {e}")

    # Verify binary exists before execution
    makemkv_path = shutil.which("makemkvcon")
    if not makemkv_path:
        logger.error("makemkvcon executable not found in PATH!")
        return result

    # Step 2: Query makemkvcon for disc structure & metadata (with 15s timeout safeguard)
    logger.debug(f"Executing makemkvcon info on disc:0")
    try:
        proc_mkv = await asyncio.create_subprocess_exec(
            makemkv_path, "-r", "info", "disc:0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc_mkv.communicate(), timeout=15.0)
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