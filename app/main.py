import os
import logging
from dataclasses import asdict
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import load_config
from app.makemkv_key_fetcher import ensure_makemkv_key, MakeMKVKeyError
from app.disc import scan_optical_drive

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