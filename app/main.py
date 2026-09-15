import os
import logging
from fastapi import BackgroundTasks, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import APP_VERSION, get_presets_from_config, load_config
from app.favicon_server import get_favicon
from app.jobs import delete_staging_files_for_job, get_jobs_that_failed_stage_3, resume_job_that_failed_stage_3, start_new_job
from app.makemkv_key_fetcher import ensure_makemkv_key
from app.disc import do_drive_scan
from app.history import load_history
from app.models import DryRunRequest, RipRequest
from app.pipeline import run_dry_run

# Configure structured console logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("ripper.main")
app = FastAPI(title="Disc Ripper")
config = load_config()

#region Lifecycle

@app.on_event("startup")
async def startup_event():
    ensure_makemkv_key(config.makemkv_key, selection_rule=config.makemkv_preset.track_selection)

@app.get("/api/health")
def healthcheck():
    logger.info("Healthcheck endpoint pinged.")
    return {"status": "ok", "message": "Disc Ripper container is running."}

@app.get("/api/version")
def get_version():
    return {"version": APP_VERSION}

#endregion Lifecycle

#region Web UI

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return get_favicon()

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

@app.get("/api/presets")
def get_presets():
    return get_presets_from_config(config)
    
@app.get("/api/history")
def get_ripping_history():
    return load_history(config.data_dir)

#endregion WebUI

#region Jobs

@app.get("/api/scan")
async def scan_disc():
    await do_drive_scan(config)

@app.post("/api/jobs/dry-run")
def dry_run_job_configuration(req: DryRunRequest):
    return run_dry_run(config, req)

@app.post("/api/jobs/new", status_code=202)
async def start_rip_job(req: RipRequest, background_tasks: BackgroundTasks):
    return start_new_job(config, req, background_tasks)

@app.post("/api/jobs/resume/{job_id}", status_code=202)
async def resume_stage3_job(job_id: str, background_tasks: BackgroundTasks):
    return resume_job_that_failed_stage_3(config, job_id, background_tasks);

@app.get("/api/jobs/resumable")
def get_resumable_jobs():
    return get_jobs_that_failed_stage_3(config)

@app.delete("/api/jobs/{job_id}", status_code=200)
def delete_staging_job(job_id: str):
    return delete_staging_files_for_job(config, job_id)

#endregion Jobs
