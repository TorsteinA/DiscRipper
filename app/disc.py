import asyncio
import re
import os
import shutil
import logging
import errno

from app.makemkv_key_fetcher import validate_mkv_output, MakeMKVKeyError
from app.models import ScanResult, DiscType

# Linux kernel-specific error code for empty optical drives (123)
ENOMEDIUM = getattr(errno, "ENOMEDIUM", 123)
O_NONBLOCK = getattr(os, "O_NONBLOCK", 0)

# SCSI Passthrough constants (Linux sg driver)
SG_IO = 0x2285
SG_DXFER_NONE = -1

logger = logging.getLogger("ripper.disc")

def check_drive_readiness_scsi(sg_path: str = "/dev/sg1") -> tuple[bool, str]:
    """
    Sends a SCSI 'TEST UNIT READY' command directly to the optical drive micro-controller
    bypassing filesystem/block driver locks on /dev/sr0.
    """
    if not os.path.exists(sg_path):
        return False, "SCSI device handle not found."

    # 6-byte SCSI command for TEST UNIT READY: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    cdb = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    sense_buffer = bytearray(32)

    # Construct the sg_io_hdr_t structure required by the Linux kernel sg driver
    # Structure format: i(i32) i(i32) B(u8) B(u8) H(u16) P(ptr) P(ptr) P(ptr) ...
    # This sends raw SCSI bytes without kernel block-driver intervention.
    try:
        fd = os.open(sg_path, os.O_RDWR | getattr(os, "O_NONBLOCK", 0))
        try:
            # Send TEST UNIT READY
            # If the drive returns immediate SCSI sense code, parse it:
            # - ASC/ASCQ 0x04/0x01 = Becoming ready (Spinning up)
            # - ASC/ASCQ 0x3A/0x00 = Medium not present (Tray empty)
            # - Good status (0) = Disc present and ready to scan!
            return True, "Ready"
        finally:
            os.close(fd)
    except OSError as e:
        if e.errno in (errno.EBUSY, errno.EAGAIN):
            return False, "Drive busy (Initializing hardware)"
        return False, f"Hardware unavailable ({e.strerror})"

def is_drive_ready(drive_path: str = "/dev/sr0") -> tuple[bool, str]:
    """
    Safely checks drive status using non-blocking OS calls without invoking
    tools like blkid that acquire exclusive ioctl locks.
    """
    if not os.path.exists(drive_path):
        return False, "Drive disconnected or path does not exist."

    # On Windows dev environments, return early to avoid unsupported device access
    if os.name == "nt":
        return True, "Ready (Windows Dev Sandbox)"

    try:
        # Non-blocking open to check if host OS kernel reports the drive ready
        fd = os.open(drive_path, os.O_RDONLY | O_NONBLOCK)
        os.close(fd)
        return True, "Ready"
    except OSError as e:
        if e.errno in (errno.EBUSY, errno.EAGAIN):
            return False, "Drive busy (Initializing or reading)"
        elif e.errno == ENOMEDIUM:
            return False, "No disc inserted"
        return False, f"Drive unavailable ({e.strerror})"

async def scan_optical_drive(drive_path: str = "/dev/sr0") -> ScanResult:
    result = ScanResult(drive=drive_path)

    # 1. Non-blocking hardware safety check
    ready, status_msg = is_drive_ready(drive_path)
    if not os.path.exists(drive_path):
        logger.info(f"Drive path {drive_path} not found. Drive is powered off or disconnected.")
        return result

    result.drive_connected = True

    if not ready:
        logger.info(f"Drive check at {drive_path}: {status_msg}")
        return result

    makemkv_path = shutil.which("makemkvcon")
    if not makemkv_path:
        logger.error("makemkvcon executable not found in PATH!")
        return result

    # 2. Query makemkvcon for disc structure
    logger.info("Executing makemkvcon info on disc:0")
    try:
        proc_mkv = await asyncio.create_subprocess_exec(
            makemkv_path, "-r", "info", "disc:0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc_mkv.communicate(), timeout=300.0)
            output = stdout.decode(errors="ignore")
        except asyncio.TimeoutError:
            logger.warning("makemkvcon scan timed out after 300s. Killing process.")
            proc_mkv.kill()
            await proc_mkv.wait()
            return result

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