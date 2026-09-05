import os
import logging
from dataclasses import asdict
import uuid
from pydantic import BaseModel
from typing import Optional
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import load_config
from app.makemkv_key_fetcher import ensure_makemkv_key, MakeMKVKeyError
from app.disc import scan_optical_drive
from app.history import get_history_entry_count, load_history
from app.mkv import extract_disc_titles, write_job_manifest
from app.models import DryRunRequest, ExtractionTestRequest, MediaType
from app.paths import get_disc_output_path, get_target_output_path

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


@app.post("/api/test-extract")
async def test_extraction(req: ExtractionTestRequest):
    job_id = f"job_{str(uuid.uuid4())[:8]}"
    staging_dir = os.path.join(config.temp_dir, job_id)

    try:
        # 1. Write job manifest
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

        # 2. Perform live disc extraction
        extracted_files = await extract_disc_titles(config, staging_dir)

        return {
            "status": "ok",
            "job_id": job_id,
            "staging_dir": staging_dir,
            "manifest_path": os.path.join(staging_dir, "job.json"),
            "extracted_files": extracted_files
        }

    except Exception as e:
        logger.exception(f"Extraction failed for {req.title}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
