import os
import re
from app.models import AppSettings

def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters and extra whitespace."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    return " ".join(cleaned.split()).strip()

def get_target_output_path(
    config: AppSettings, 
    title: str, 
    year: str | None, 
    media_type: str
) -> str:
    """
    Generates Jellyfin-compliant folder and file paths.
    
    Movies: /media/movies/Title (Year)/Title (Year).mkv
    Shows:  /media/shows/Title (Year)/Title (Year).mkv
    """
    clean_title = sanitize_filename(title)
    
    if year and year.strip():
        folder_name = f"{clean_title} ({year.strip()})"
    else:
        folder_name = clean_title

    base_dir = config.output_dir_shows if media_type == "tv" else config.output_dir_movies
    destination_dir = os.path.join(base_dir, folder_name)
    os.makedirs(destination_dir, exist_ok=True)

    file_name = f"{folder_name}.mkv"
    return os.path.join(destination_dir, file_name)