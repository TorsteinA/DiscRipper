import os
import asyncio
import logging
import shutil
from app.models import AppSettings

logger = logging.getLogger("ripper.mkv")

async def extract_disc_titles(
    config: AppSettings,
    staging_dir: str
) -> list[str]:
    """
    Executes makemkvcon to extract all titles matching minimum length criteria.
    Streams all log output to stdout in real time.
    """
    os.makedirs(staging_dir, exist_ok=True)

    cmd = get_mkv_extraction_command(config.drive_path, staging_dir, config.makemkv_preset.min_length_seconds)
    logger.info(f"Executing MakeMKV extraction: {' '.join(cmd)}")

    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        if process.stdout:
            buffer = ""
            while True:
                chunk = await process.stdout.read(1024)
                if not chunk:
                    break
                
                buffer += chunk.decode(errors="ignore")
                
                # Handle both carriage returns (\r) and newlines (\n)
                while "\r" in buffer or "\n" in buffer:
                    pos_r = buffer.find("\r")
                    pos_n = buffer.find("\n")
                    
                    if pos_r != -1 and (pos_n == -1 or pos_r < pos_n):
                        line, buffer = buffer[:pos_r], buffer[pos_r + 1:]
                    else:
                        line, buffer = buffer[:pos_n], buffer[pos_n + 1:]
                    
                    line = line.strip()
                    if line:
                        logger.info(f"[MakeMKV] {line}")

            # Flush remaining buffer text upon process completion
            if buffer.strip():
                logger.info(f"[MakeMKV] {buffer.strip()}")

        returncode = await process.wait()
    except Exception:
        if process and process.returncode is None:
            process.kill()
            await process.wait()
        raise

    if returncode != 0:
        logger.error(f"MakeMKV extraction failed with exit code {returncode}")
        raise RuntimeError(f"MakeMKV extraction failed (code {returncode})")

    extracted_files = [
        os.path.join(staging_dir, f)
        for f in os.listdir(staging_dir)
        if f.endswith(".mkv")
    ]

    if not extracted_files:
        raise FileNotFoundError("MakeMKV finished but no .mkv files were produced.")

    logger.info(f"Extraction successful. Produced {len(extracted_files)} title(s).")
    return sorted(extracted_files)

def get_mkv_extraction_command(drive_path: str, staging_dir: str, min_length_seconds: int):
    try:
        makemkv_path = _get_makemkvcon_path()
    except:
        raise
    return [
            makemkv_path,
            "-r",
            "mkv",
            f"dev:{drive_path}",
            "all",
            staging_dir,
            f"--minlength={min_length_seconds}",
        ]

def get_mkv_info_command(drive_path: str):
    try:
        makemkv_path = _get_makemkvcon_path()
    except:
        raise
    return [
        makemkv_path, 
        "-r", 
        "info", 
        drive_path,
    ]

def _get_makemkvcon_path():
    makemkv_path = shutil.which("makemkvcon")
    if not makemkv_path:
        e_msg = "makemkvcon executable not found in PATH!"
        logger.error(e_msg)
        raise Exception(e_msg)
    return makemkv_path




