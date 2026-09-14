import os

from fastapi.responses import FileResponse

async def get_favicon():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    favicon_path = os.path.join(static_dir, "favicon.svg")
    return FileResponse(favicon_path, media_type="image/svg+xml")