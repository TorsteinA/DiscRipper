import os
import asyncio
import logging
from app.models import AppSettings, DiscType, JobManifest, MediaType

logger = logging.getLogger("ripper.mkv")


def write_job_manifest(
    staging_dir: str,
    job_id: str,
    title: str,
    year: str,
    media_type: MediaType,
    disc_type: DiscType,
    preset_key: str,
    season: int = 1,
    episode: int = 1
) -> JobManifest:
    """Creates and writes a strongly-typed JobManifest to job.json."""
    os.makedirs(staging_dir, exist_ok=True)

    manifest = JobManifest(
        job_id=job_id,
        title=title,
        year=year,
        media_type=media_type,
        disc_type=disc_type,
        preset_key=preset_key,
        season=season,
        episode=episode,
        status="RIPPED"
    )

    manifest_path = os.path.join(staging_dir, "job.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    logger.info(f"Job manifest saved: {manifest_path}")
    return manifest


def read_job_manifest(staging_dir: str) -> JobManifest:
    """Reads and parses job.json back into a JobManifest model."""
    manifest_path = os.path.join(staging_dir, "job.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return JobManifest.model_validate_json(f.read())


async def extract_disc_titles(
    config: AppSettings,
    staging_dir: str
) -> list[str]:
    """
    Executes makemkvcon to extract all titles matching minimum length criteria.
    Streams all log output to stdout in real time.
    """
    os.makedirs(staging_dir, exist_ok=True)

    cmd = [
        "makemkvcon",
        "-r",
        "mkv",
        "disc:0",
        "all",
        staging_dir,
        f"--minlength={config.makemkv_preset.min_length_seconds}",
    ]

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