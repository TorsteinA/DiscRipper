import os
import asyncio
import logging
from typing import List
from app.job_manifest import read_job_manifest
from app.models import AppSettings, MediaType, UnsupportedMediaTypeError
from app.paths import get_disc_output_path, get_target_output_path, get_next_extra_number

logger = logging.getLogger("ripper.transcode")


async def transcode_staging_directory(
    config: AppSettings,
    staging_dir: str
) -> List[str]:
    """
    Reads job.json, routes the main feature and extras properly, and
    transcodes all titles using HandBrakeCLI with real-time verbose output logging.
    """
    manifest = read_job_manifest(staging_dir)
    preset = config.handbrake_presets.get(manifest.preset_key)
    if not preset:
        raise ValueError(f"Invalid preset key in job manifest: '{manifest.preset_key}'")

    source_files = [
        os.path.join(staging_dir, f)
        for f in os.listdir(staging_dir)
        if f.endswith(".mkv")
    ]

    if not source_files:
        raise FileNotFoundError(f"No .mkv files found in staging directory: {staging_dir}")

    logger.info(f"Starting Stage 3 transcode for job {manifest.job_id}. Found {len(source_files)} source file(s).")

    # Route movie main feature vs extras
    if manifest.media_type == MediaType.Movie:
        source_files.sort(key=lambda f: os.path.getsize(f), reverse=True)
        main_feature = source_files[0]
        logger.info(f"Main Feature selected: {os.path.basename(main_feature)} ({os.path.getsize(main_feature)} bytes)")

    output_files: List[str] = []

    movie_dir = get_disc_output_path(config, manifest.title, manifest.year, manifest.media_type, manifest.season)
    extra_counter = get_next_extra_number(movie_dir)

    for idx, source_path in enumerate(source_files):
        if manifest.media_type == MediaType.Movie:
            if source_path == main_feature:
                target_path = get_target_output_path(
                    config=config,
                    title=manifest.title,
                    year=manifest.year,
                    media_type=MediaType.Movie,
                )
            else:
                target_path = get_target_output_path(
                    config=config,
                    title=manifest.title,
                    year=manifest.year,
                    media_type=MediaType.MovieExtras,
                    extra_num=extra_counter
                )
                extra_counter += 1

        elif manifest.media_type == MediaType.MovieExtras:
            target_path = get_target_output_path(
                config=config,
                title=manifest.title,
                year=manifest.year,
                media_type=MediaType.MovieExtras,
                extra_num=extra_counter
            )
            extra_counter += 1

        elif manifest.media_type == MediaType.Show:
            episode_num = manifest.episode + idx
            target_path = get_target_output_path(
                config=config,
                title=manifest.title,
                year=manifest.year,
                media_type=MediaType.Show,
                season=manifest.season,
                episode=episode_num
            )

        else:
            raise UnsupportedMediaTypeError(f"Cannot Transcode Unsupported Media Type: {manifest.media_type}")

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        cmd = [
            "HandBrakeCLI",
            "-i", source_path,
            "-o", target_path,
            *preset.to_cli_args()
        ]

        logger.info(f"[{idx + 1}/{len(source_files)}] Transcoding {os.path.basename(source_path)} -> {target_path}")

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
                
                # Split lines on either carriage return (\r) or newline (\n)
                while "\r" in buffer or "\n" in buffer:
                    pos_r = buffer.find("\r")
                    pos_n = buffer.find("\n")
                    
                    if pos_r != -1 and (pos_n == -1 or pos_r < pos_n):
                        line, buffer = buffer[:pos_r], buffer[pos_r + 1:]
                    else:
                        line, buffer = buffer[:pos_n], buffer[pos_n + 1:]
                    
                    line = line.strip()
                    if line:
                        logger.info(f"[HandBrake] {line}")

            # Flush any trailing log buffer text before process exit
            if buffer.strip():
                logger.info(f"[HandBrake] {buffer.strip()}")

        returncode = await process.wait()

        if returncode != 0:
            logger.error(
                f"HandBrakeCLI failed on file {source_path} with exit code {returncode}.\n"
                f"The target path was {target_path}, and should maybe be deleted manually"
            )
            raise RuntimeError(f"HandBrakeCLI transcode failed on {os.path.basename(source_path)}")

        output_files.append(target_path)

    logger.info(f"Stage 3 complete for job {manifest.job_id}. Transcoded {len(output_files)} file(s).")
    return output_files