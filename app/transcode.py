import os
import asyncio
import logging
from typing import List
from app.models import AppSettings, MediaType
from app.mkv import read_job_manifest
from app.paths import get_target_output_path

logger = logging.getLogger("ripper.transcode")


async def transcode_staging_directory(
    config: AppSettings,
    staging_dir: str
) -> List[str]:
    """
    Reads job.json from staging_dir, batch processes all .mkv files using HandBrakeCLI,
    and outputs them to the Jellyfin destination paths.
    Returns a list of completed output file paths.
    """
    # 1. Load job manifest
    manifest = read_job_manifest(staging_dir)
    preset = config.handbrake_presets.get(manifest.preset_key)
    if not preset:
        raise ValueError(f"Invalid preset key in job manifest: '{manifest.preset_key}'")

    # 2. Discover extracted MKV files in staging
    source_files = sorted([
        os.path.join(staging_dir, f)
        for f in os.listdir(staging_dir)
        if f.endswith(".mkv")
    ])

    if not source_files:
        raise FileNotFoundError(f"No .mkv files found in staging directory: {staging_dir}")

    logger.info(f"Starting Stage 3 transcode for job {manifest.job_id}. Found {len(source_files)} source file(s).")
    output_files: List[str] = []

    # 3. Process each MKV file
    for idx, source_path in enumerate(source_files):
        # Calculate episode or extra numbers based on media type
        episode_num = manifest.episode + idx
        extra_num = idx + 1

        # Determine target output path
        target_path = get_target_output_path(
            config=config,
            title=manifest.title,
            year=manifest.year,
            media_type=manifest.media_type,
            season=manifest.season,
            episode=episode_num,
            extra_num=extra_num
        )

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        cmd = [
            "HandBrakeCLI",
            "-i", source_path,
            "-o", target_path,
            *preset.to_cli_args()
        ]

        logger.info(f"[{idx + 1}/{len(source_files)}] Transcoding {os.path.basename(source_path)} -> {target_path}")
        logger.debug(f"HandBrake Command: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        # Stream HandBrake progress output line-by-line
        if process.stdout:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode(errors="ignore").strip()
                if decoded and "Encoding: task" in decoded:
                    logger.info(f"[HandBrake] {decoded}")

        returncode = await process.wait()

        if returncode != 0:
            logger.error(f"HandBrakeCLI failed on file {source_path} with exit code {returncode}")
            raise RuntimeError(f"HandBrakeCLI transcode failed on {os.path.basename(source_path)}")

        output_files.append(target_path)

    logger.info(f"Stage 3 complete for job {manifest.job_id}. Transcoded {len(output_files)} file(s).")
    return output_files