import asyncio
import logging
import os
import re
import shutil

from app.makemkv_key_fetcher import MakeMKVKeyError, validate_mkv_output
from app.models import DiscType, ScanResult

logger = logging.getLogger("ripper.disc")


def is_scsi_ready(drive_path: str = "/dev/sr0") -> tuple[bool, str]:
    """
    Checks physical drive availability via /dev/sg* to avoid kernel
    block-layer locks on /dev/sr0.
    """
    sg_path = drive_path.replace("sr0", "sg1")
    if not os.path.exists(sg_path):
        return False, f"SCSI device {sg_path} not found."

    try:
        fd = os.open(sg_path, os.O_RDWR | getattr(os, "O_NONBLOCK", 0))
        os.close(fd)
        return True, "SCSI Node Ready"
    except OSError as e:
        return False, f"SCSI device busy or unavailable ({e.strerror})"


async def scan_optical_drive(drive_path: str = "/dev/sr0") -> ScanResult:
    result = ScanResult(drive=drive_path)

    # 1. Non-blocking SCSI hardware safety pre-check
    ready, msg = is_scsi_ready(drive_path)
    if not ready:
        logger.warning(f"Drive pre-check failed: {msg}")
        return result

    result.drive_connected = True

    makemkv_path = shutil.which("makemkvcon")
    if not makemkv_path:
        logger.error("makemkvcon executable not found in PATH!")
        return result

    # 2. Map block device path (/dev/sr0) to direct SCSI passthrough target (dev:/dev/sg1)
    sg_target = f"dev:{drive_path.replace('sr0', 'sg1')}"
    logger.info(f"Spawning makemkvcon on target: {sg_target}")

    try:
        proc_mkv = await asyncio.create_subprocess_exec(
            makemkv_path,
            "-r",
            "--cache=1",
            "--noscan",
            "info",
            sg_target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        output_lines = []

        # Stream stdout line-by-line to avoid pipe buffer deadlocks
        while True:
            if proc_mkv.stdout is None:
                break

            try:
                line_bytes = await asyncio.wait_for(proc_mkv.stdout.readline(), timeout=30.0)
                if not line_bytes:
                    break  # EOF

                line = line_bytes.decode(errors="ignore").strip()
                if line:
                    output_lines.append(line)

                # if line.startswith(("MSG:", "TCOUNT:", "CINFO:", "DRV:")):
                logger.info(f"makemkvcon: {line}")

            except asyncio.TimeoutError:
                logger.warning("No output from makemkvcon for 30s. Terminating process.")
                try:
                    proc_mkv.terminate()
                    await asyncio.sleep(0.5)
                    if proc_mkv.returncode is None:
                        proc_mkv.kill()
                    await proc_mkv.wait()
                except ProcessLookupError:
                    pass
                return result

        await proc_mkv.wait()
        full_output = "\n".join(output_lines)

        validate_mkv_output(full_output)

        if proc_mkv.returncode == 0:
            tcount_match = re.search(r"TCOUNT:(\d+)", full_output)
            if tcount_match:
                result.title_count = int(tcount_match.group(1))
                result.has_disc = True

            cinfo_match = re.search(r'CINFO:2,0,"([^"]+)"', full_output)
            if cinfo_match and not result.label:
                result.label = cinfo_match.group(1)

            if "BD-ROM" in full_output or "Blu-ray" in full_output:
                result.disc_type = DiscType.BLU_RAY
            elif "DVD-ROM" in full_output or "DVD-Video" in full_output:
                result.disc_type = DiscType.DVD
            elif result.has_disc:
                result.disc_type = DiscType.OPTICAL_MEDIA

            logger.info(f"Disc inspection finished cleanly. Type: {result.disc_type}, Titles: {result.title_count}")
        else:
            logger.warning(f"makemkvcon exited with code {proc_mkv.returncode}")

    except MakeMKVKeyError:
        raise
    except Exception as e:
        logger.error(f"makemkvcon execution error: {e}")

    return result