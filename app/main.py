from fastapi import FastAPI
from app.disc import scan_optical_drive

app = FastAPI(title="Disc Ripper")

@app.get("/api/health")
def healthcheck():
    return {"status": "ok", "message": "Disc Ripper container is running."}

@app.get("/api/scan")
async def scan_disc():
    return await scan_optical_drive("/dev/sr0")