import os
import logging
from dataclasses import asdict
from pydantic import BaseModel
from typing import Optional
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import load_config
from app.makemkv_key_fetcher import ensure_makemkv_key, MakeMKVKeyError
from app.disc import scan_optical_drive
from app.history import load_history
from app.paths import get_target_output_path

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


class TestJobRequest(BaseModel):
    title: str
    year: Optional[str] = None
    media_type: str = "movie"
    preset_key: str = "dvd"

@app.post("/api/test-job")
def test_job_configuration(req: TestJobRequest):
    # 1. Resolve HandBrake Preset
    preset = config.handbrake_presets.get(req.preset_key)
    if not preset:
        raise HTTPException(status_code=400, detail=f"Invalid preset key: '{req.preset_key}'")

    # 2. Compute Output Path
    target_mkv_path = get_target_output_path(config, req.title, req.year, req.media_type)
    placeholder_path = target_mkv_path.replace(".mkv", "_TEST_PLACEHOLDER.txt")

    # 3. Create dummy file at target host mount path to verify volume permissions
    with open(placeholder_path, "w", encoding="utf-8") as f:
        f.write(f"Dry-run placeholder for: {req.title}\nTarget MKV: {target_mkv_path}\n")

    # 4. Generate MakeMKV CLI command
    makemkv_cmd = [
        "makemkvcon",
        "-r",
        "mkv",
        f"dev:{config.drive_path}",
        "all",
        config.temp_dir,
        f"--minlength={config.makemkv_preset.min_length_seconds}",
    ]

    # 5. Generate HandBrake CLI command
    handbrake_cmd = [
        "HandBrakeCLI",
        "-i", f"{config.temp_dir}/extracted_title.mkv",
        "-o", target_mkv_path,
        *preset.to_cli_args()
    ]

    # 6. Log output directly to Dockge container terminal
    logger.info("=== DRY-RUN JOB VERIFICATION ===")
    logger.info(f"Target Output File: {target_mkv_path}")
    logger.info(f"Test Placeholder Created: {placeholder_path}")
    logger.info(f"MakeMKV Command: {' '.join(makemkv_cmd)}")
    logger.info(f"HandBrake Command: {' '.join(handbrake_cmd)}")
    logger.info("=================================")

    return {
        "status": "ok",
        "target_mkv_path": target_mkv_path,
        "placeholder_path": placeholder_path,
        "makemkv_cmd": makemkv_cmd,
        "handbrake_cmd": handbrake_cmd
    }