import logging
import os
import shutil

from fastapi import BackgroundTasks, HTTPException

from app.job_manifest import read_job_manifest
from app.models import AppSettings, RipRequest
from app.pipeline import run_full_pipeline_task, run_stages_3_forward

logger = logging.getLogger("ripper.jobs")

async def start_new_job(config: AppSettings, req: RipRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_full_pipeline_task, config, req)
    return {
        "status": "started",
        "request_title": req.title,
        "request_year": req.year,
        "request_media_type": req.media_type,
        "request_disc_type": req.disc_type,
        "reqest_preset_key": req.preset_key,
        "reqest_season": req.season,
        "reqest_episode": req.episode,
    }

async def resume_job_that_failed_stage_3(config: AppSettings, job_id: str, background_tasks: BackgroundTasks):
    logger.info(f"resuming stage 3 job {job_id}")
    staging_dir = os.path.join(config.temp_dir, job_id)
    manifest_path = os.path.join(staging_dir, "job.json")

    if not os.path.exists(manifest_path):
        e_msg = f"Cannot resume: No job manifest found at {staging_dir}"
        logger.error(e_msg)
        raise HTTPException(status_code=404, detail=e_msg)

    # Verify extracted .mkv files exist in the staging directory
    mkv_files = [f for f in os.listdir(staging_dir) if f.endswith(".mkv")]
    if not mkv_files:
        e_msg = f"Cannot resume: No .mkv source files found in {staging_dir}"
        logger.error(e_msg)
        raise HTTPException(status_code=400, detail=e_msg)

    logger.info(f"Starting stage3 transcode task in background")
    background_tasks.add_task(run_stages_3_forward, config, job_id, staging_dir)

    return {
        "status": "resumed",
        "job_id": job_id,
        "staging_dir": staging_dir
    }

def get_jobs_that_failed_stage_3(config: AppSettings):
    logger.info("Getting jobs that failed stage 3, " \
    "by searching for manifests in staging directories")

    resumable = []
    
    if not os.path.exists(config.temp_dir):
        return resumable

    for folder_name in os.listdir(config.temp_dir):
        staging_dir = os.path.join(config.temp_dir, folder_name)
        manifest_path = os.path.join(staging_dir, "job.json")
        
        if os.path.isdir(staging_dir) and os.path.exists(manifest_path):
            # Check if extracted .mkv files exist
            mkv_files = [f for f in os.listdir(staging_dir) if f.endswith(".mkv")]
            if mkv_files:
                try:
                    manifest = read_job_manifest(staging_dir)
                    resumable.append(manifest.model_dump())
                except Exception as e:
                    logger.warning(f"Could not read manifest at {manifest_path}: {e}")
                    
    return resumable

async def delete_staging_files_for_job(config: AppSettings, job_id: str):
    logger.info(f"Deleting staging files for job {job_id}")
    # Ensure job_id parameter stays safely within config.temp_dir
    staging_dir = os.path.abspath(os.path.join(config.temp_dir, job_id))
    temp_base = os.path.abspath(config.temp_dir)

    if not staging_dir.startswith(temp_base) or not os.path.exists(staging_dir):
        e_msg = f"Staging directory for job '{job_id}' not found."
        logger.error(e_msg)
        raise HTTPException(status_code=404, detail=e_msg)

    try:
        shutil.rmtree(staging_dir)
        logger.info(f"Deleted staging folder for job: {job_id}")
        return {"status": "deleted", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to delete staging folder {staging_dir}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete staging files: {str(e)}"
        )
