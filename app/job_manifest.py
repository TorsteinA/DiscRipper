import os
import logging
from app.models import JobManifest, RipRequest, RippingStatus

logger = logging.getLogger("ripper.job_manifest")

def write_job_manifest(
    staging_dir: str,
    job_id: str,
    rip_request: RipRequest,
) -> JobManifest:
    logger.info(f"Writing new job manifest for staging dir: {staging_dir}")
    os.makedirs(staging_dir, exist_ok=True)
    manifest = JobManifest(
        job_id=job_id,
        title=rip_request.title,
        year=rip_request.year,
        media_type=rip_request.media_type,
        disc_type=rip_request.disc_type,
        preset_key=rip_request.preset_key,
        season=rip_request.season,
        episode=rip_request.episode,
        status=RippingStatus.INITIATING
    )
    manifest_path = os.path.join(staging_dir, "job.json")
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))
    except Exception as e:
        logger.exception(f"Failed to write manifest for {staging_dir}")
        raise
    logger.info(f"Job manifest saved: {manifest_path}")
    return manifest


def read_job_manifest(staging_dir: str) -> JobManifest:
    """Reads and parses job.json back into a JobManifest model."""
    manifest_path = os.path.join(staging_dir, "job.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return JobManifest.model_validate_json(f.read())

