from datetime import datetime
import os
import logging
from dataclasses import asdict
import shutil
import uuid
from fastapi import BackgroundTasks, FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import load_config
from app.makemkv_key_fetcher import ensure_makemkv_key, MakeMKVKeyError
from app.disc import scan_optical_drive
from app.history import append_history_item, update_history_item, load_history
from app.models import RipHistoryItem, RippingStatus
from app.mkv import extract_disc_titles, read_job_manifest, write_job_manifest
from app.models import AppSettings, DryRunRequest, RipRequest
from app.paths import get_disc_output_path, get_target_output_path
from app.transcode import transcode_staging_directory

# Configure structured console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("ripper.main")

app = FastAPI(title="Disc Ripper")
config = load_config()

# MARK: Event Triggers

@app.on_event("startup")
async def startup_event():
    ensure_makemkv_key(config.makemkv_key, selection_rule=config.makemkv_preset.track_selection)

# MARK: API

@app.get("/api/health")
def healthcheck():
    logger.info("Healthcheck endpoint pinged.")
    return {"status": "ok", "message": "Disc Ripper container is running."}

@app.get("/api/scan")
async def scan_disc():
    try:
        logger.info("Initiating optical drive scan on /dev/sr0...")
        result = await scan_optical_drive(config.drive_path)
        logger.info(f"Scan complete. Disc present: {result.has_disc} | Label: '{result.label}' | Type: {result.disc_type}")
        return asdict(result)
    except MakeMKVKeyError as e:
        logger.error(f"Scan aborted due to MakeMKV Key failure: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"MakeMKV Key Error: {str(e)}"
        )

@app.get("/api/presets")
def get_presets():
    return {
        "handbrake": {k: asdict(v) for k, v in config.handbrake_presets.items()},
        "makemkv": asdict(config.makemkv_preset)
    }

@app.get("/api/history")
def get_ripping_history():
    return load_history(config.data_dir)

# MARK: Web UI

# SVG Favicon endpoint (Optical Disc Icon)
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <!-- Outer Indigo Circle -->
  <circle cx="50" cy="50" r="48" fill="#4f46e5" />
  <!-- Shiny Disc Body -->
  <circle cx="50" cy="50" r="32" fill="#cbd5e1" />
  <!-- Inner Reflective Ring -->
  <circle cx="50" cy="50" r="18" fill="#94a3b8" />
  <!-- Clear Center Hole -->
  <circle cx="50" cy="50" r="10" fill="#0f172a" />
</svg>"""

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

# Serve Static Frontend Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Disc Ripper API running."}


@app.post("/api/dry-run")
def dry_run_job_configuration(req: DryRunRequest):
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
        "disc:0",
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

@app.post("/api/rip", status_code=202)
async def start_rip_job(req: RipRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{str(uuid.uuid4())[:8]}"
    staging_dir = os.path.join(config.temp_dir, job_id)
    preset = config.handbrake_presets.get(req.preset_key)

    write_job_manifest(
        staging_dir=staging_dir,
        job_id=job_id,
        title=req.title,
        year=req.year,
        media_type=req.media_type,
        disc_type=req.disc_type,
        preset_key=req.preset_key,
        season=req.season,
        episode=req.episode
    )

    initial_history = RipHistoryItem(
        id=job_id,
        title=req.title,
        year=req.year,
        media_type=req.media_type,
        disc_type=req.disc_type,
        preset_used=preset.name if preset else req.preset_key,
        start_time=datetime.now().isoformat(),
        status=RippingStatus.EXTRACTING
    )
    append_history_item(config.data_dir, initial_history)

    background_tasks.add_task(run_full_pipeline_task, config, job_id, staging_dir)

    return {
        "status": "started",
        "job_id": job_id,
        "staging_dir": staging_dir
    }

async def run_full_pipeline_task(config: AppSettings, job_id: str, staging_dir: str):
    """Executes Stage 2 (Extraction) -> Stage 3 (Transcode) -> Staging Cleanup."""
    try:
        # Stage 2: Rip Disc
        await run_stage2_extraction_task(config, job_id, staging_dir)
        # Stage 3: Transcode & Cleanup
        await run_stage3_transcode_task(config, job_id, staging_dir)
    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}: {e}")
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.FAILED,
            end_time=datetime.now().isoformat(),
            error=str(e)
        )


@app.post("/api/jobs/resume/{job_id}", status_code=202)
async def resume_stage3_job(job_id: str, background_tasks: BackgroundTasks):
    staging_dir = os.path.join(config.temp_dir, job_id)
    manifest_path = os.path.join(staging_dir, "job.json")

    if not os.path.exists(manifest_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Cannot resume: No job manifest found at {staging_dir}"
        )

    # Verify extracted .mkv files exist in the staging directory
    mkv_files = [f for f in os.listdir(staging_dir) if f.endswith(".mkv")]
    if not mkv_files:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot resume: No .mkv source files found in {staging_dir}"
        )

    background_tasks.add_task(run_stage3_transcode_task, config, job_id, staging_dir)

    return {
        "status": "resumed",
        "job_id": job_id,
        "staging_dir": staging_dir
    }

async def run_stage2_extraction_task(config: AppSettings, job_id: str, staging_dir: str):
    try: 
        # --- Stage 2: Rip Disc ---
        logger.info(f"Starting Stage 2 (Extraction) for job {job_id}...")
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

async def run_stage3_transcode_task(config: AppSettings, job_id: str, staging_dir: str):
    """Executes Stage 3 (Transcode) directly from existing staging directory files."""
    try:
        logger.info(f"Resuming Stage 3 (Transcode) for existing job {job_id}...")
        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.COMPRESSING
        )

        output_files = await transcode_staging_directory(config, staging_dir)

        # Stage 4: Cleanup Staging Directory
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
            logger.info(f"Successfully cleaned up staging folder: {staging_dir}")

        update_history_item(
            config.data_dir,
            job_id=job_id,
            status=RippingStatus.COMPLETED,
            end_time=datetime.now().isoformat()
        )
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

@app.get("/api/jobs/resumable")
def get_resumable_jobs():
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


@app.delete("/api/jobs/{job_id}", status_code=200)
def delete_staging_job(job_id: str):
    # Ensure job_id parameter stays safely within config.temp_dir
    staging_dir = os.path.abspath(os.path.join(config.temp_dir, job_id))
    temp_base = os.path.abspath(config.temp_dir)

    if not staging_dir.startswith(temp_base) or not os.path.exists(staging_dir):
        raise HTTPException(
            status_code=404, 
            detail=f"Staging directory for job '{job_id}' not found."
        )

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