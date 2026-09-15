from datetime import datetime
import logging
import os
import shutil
import uuid

from fastapi import HTTPException

from app.history import append_history_item, update_history_item
from app.job_manifest import write_job_manifest
from app.mkv import extract_disc_titles
from app.models import AppSettings, DryRunRequest, RipHistoryItem, RipRequest, RippingStatus
from app.paths import get_disc_output_path, get_target_output_path
from app.transcode import transcode_staging_directory

logger = logging.getLogger("ripper.pipeline")

async def run_dry_run(config: AppSettings, req: DryRunRequest):
    preset = config.handbrake_presets.get(req.preset_key)
    if not preset:
        raise HTTPException(status_code=400, detail=f"Invalid preset key: '{req.preset_key}'")

    # Compute Target Directory & Sample Output File Path using form fields
    target_dir = get_disc_output_path(config, req.title, req.year, req.media_type, season=req.season)
    sample_target_file = get_target_output_path(
        config, 
        req.title, 
        req.year, 
        req.media_type, 
        season=req.season, 
        episode=req.episode,
        extra_num=1
    )

    simulated_job_id = "job_sample123"
    job_staging_dir = os.path.join(config.temp_dir, simulated_job_id)

    makemkv_cmd = [
        "makemkvcon",
        "-r",
        "mkv",
        f"dev:{config.drive_path}",
        "all",
        job_staging_dir,
        f"--minlength={config.makemkv_preset.min_length_seconds}",
    ]

    handbrake_cmd_template = [
        "HandBrakeCLI",
        "-i", f"{job_staging_dir}/<extracted_title>.mkv",
        "-o", sample_target_file,
        *preset.to_cli_args()
    ]

    logger.info("=== DRY-RUN JOB INSPECTION ===")
    logger.info(f"Media Type: {req.media_type.value}")
    logger.info(f"Target Directory: {target_dir}")
    logger.info(f"Sample Output File: {sample_target_file}")
    logger.info(f"MakeMKV Command: {' '.join(makemkv_cmd)}")
    logger.info(f"HandBrake Template: {' '.join(handbrake_cmd_template)}")
    logger.info("===============================")

    return {
        "status": "ok",
        "job_staging_dir": job_staging_dir,
        "target_directory": target_dir,
        "sample_output_file": sample_target_file,
        "makemkv_cmd": makemkv_cmd,
        "handbrake_cmd_template": handbrake_cmd_template
    }


async def run_stage1_initiation_task(config: AppSettings, rip_request: RipRequest):
    job_id = f"job_{str(uuid.uuid4())[:8]}"
    logger.info(f"Starting Stage 1 (Initation) for {job_id}...")
    staging_dir = os.path.join(config.temp_dir, job_id)
    preset = config.handbrake_presets.get(rip_request.preset_key)
    try:
        write_job_manifest(
            staging_dir=staging_dir,
            job_id=job_id,
            rip_request=rip_request
        )
        append_history_item(config.data_dir, RipHistoryItem(
            id=job_id,
            title=rip_request.title,
            year=rip_request.year,
            media_type=rip_request.media_type,
            disc_type=rip_request.disc_type,
            preset_used=preset.name if preset else rip_request.preset_key,
            start_time=datetime.now().isoformat(),
            status=RippingStatus.EXTRACTING
        ))
    except Exception as e:
        logger.exception(f"Pipeline failed at Stage 1 for job {job_id}: {e}")
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.FAILED1,
            end_time=datetime.now().isoformat(),
            error=str(e)
        )
        raise
    return [job_id, staging_dir]


async def run_stage2_extraction_task(config: AppSettings, job_id: str, staging_dir: str):
    logger.info(f"Starting Stage 2 (Extraction) for job {job_id}...")
    try: 
        await extract_disc_titles(config, staging_dir)
        
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.EXTRACTED
        )
    except Exception as e:
        logger.exception(f"Pipeline failed at Stage 2 for job {job_id}: {e}")
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.FAILED2,
            end_time=datetime.now().isoformat(),
            error=str(e)
        )
        raise


async def run_stage3_transcode_task(config: AppSettings, job_id: str, staging_dir: str):
    logger.info(f"Starting Stage 3 (Transcode) for job {job_id}...")
    try:
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.COMPRESSING
        )
        output_files = await transcode_staging_directory(config, staging_dir)

        logger.info(f"Job {job_id} Stage 3 completed! Target files placed: {output_files}")

    except Exception as e:
        logger.exception(f"Stage 3 transcode failed for job {job_id}: {e}")
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.FAILED3,
            end_time=datetime.now().isoformat(),
            error=str(e)
        )
        raise


async def run_stage4_cleanup_task(config: AppSettings, job_id: str):
    logger.info(f"Starting Stage 4 (Cleanup) for job {job_id}...")
    staging_dir = os.path.abspath(os.path.join(config.temp_dir, job_id))
    temp_base = os.path.abspath(config.temp_dir)

    if not staging_dir.startswith(temp_base) or not os.path.exists(staging_dir):
        e_msg = f"Staging directory for job '{job_id}' not found."
        logger.error(e_msg)
        raise HTTPException(status_code=404, detail=e_msg)

    try:
        shutil.rmtree(staging_dir)
        logger.info(f"Deleted staging folder for job: {job_id}")
    except Exception as e:
        logger.error(f"Failed to delete staging folder {staging_dir}: {e}")
        e_msg = f"Failed to delete staging files: {str(e)}"
        raise HTTPException(status_code=500, detail=e_msg)

    update_history_item(
        config.data_dir,
        job_id=job_id,
        status=RippingStatus.COMPLETED,
        end_time=datetime.now().isoformat()
    )


async def run_full_pipeline_task(config: AppSettings, rip_request: RipRequest):
    try:
        job_id, staging_dir = await run_stage1_initiation_task(config, rip_request)
        # Stage 2: Rip Disc
        await run_stage2_extraction_task(config, job_id, staging_dir)
        # Stage 3: Transcode
        await run_stage3_transcode_task(config, job_id, staging_dir)
        # Stage 4: Cleanup
        await run_stage4_cleanup_task(config, job_id)
    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}: {e}")
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.FAILED,
            end_time=datetime.now().isoformat(),
            error=str(e)
        )

async def run_stages_3_forward(config: AppSettings, job_id: str, staging_dir: str):
    try:
        # Stage 3: Transcode
        await run_stage3_transcode_task(config, job_id, staging_dir)
        # Stage 4: Cleanup
        await run_stage4_cleanup_task(config, job_id)
    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}: {e}")
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.FAILED,
            end_time=datetime.now().isoformat(),
            error=str(e)
        )
