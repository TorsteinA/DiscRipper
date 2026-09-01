import logging
from fastapi import FastAPI, Response
from app.config import load_config
from app.makemkv_key_fetcher import ensure_makemkv_key
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

# SVG Favicon endpoint (Optical Disc Icon)
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="45" fill="#4f46e5" />
  <circle cx="50" cy="50" r="18" fill="#0f172a" />
  <circle cx="50" cy="50" r="8" fill="#4f46e5" />
</svg>"""

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@app.on_event("startup")
async def startup_event():
    ensure_makemkv_key()

@app.get("/api/health")
def healthcheck():
    logger.info("Healthcheck endpoint pinged.")
    return {"status": "ok", "message": "Disc Ripper container is running."}

@app.get("/api/scan")
async def scan_disc():
    try:
        logger.info("Initiating optical drive scan on /dev/sr0...")
        result = await scan_optical_drive(config["drive_path"])
        logger.info(f"Scan complete. Disc present: {result.get('has_disc')} | Label: '{result.get('label')}' | Type: {result.get('disc_type')}")
        return result
    except MakeMKVKeyError as e:
        status_code=400,
        detail=f"MakeMKV Key Error: {str(e)}"