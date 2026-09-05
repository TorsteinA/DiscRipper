import os
import re
from typing import Optional
from app.models import AppSettings, MediaType


class UnsupportedMediaTypeError(Exception):
    """Raised when an unsupported MediaType is attempted used."""
    pass


def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters and extra whitespace."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    return " ".join(cleaned.split()).strip()


def get_disc_output_path(
    config: AppSettings,
    title: str,
    year: str,
    media_type: MediaType,
    season: int
) -> str:
    clean_title = sanitize_filename(title)
    folder_name = f"{clean_title} ({year.strip()})" if year and year.strip() else clean_title

    if media_type == MediaType.Show:
        if not season:
            raise ValueError("Cannot make show path without season number")
        return os.path.join(config.output_dir_shows, folder_name, f"Season {season:02d}")

    base_path = config.output_dir_movies
    if media_type == MediaType.Movie:
        return os.path.join(base_path, folder_name)
    elif media_type == MediaType.MovieExtras:
        return os.path.join(base_path, folder_name, "extras")

    raise UnsupportedMediaTypeError("Media Type not supported")


def get_target_output_path(
    config: AppSettings, 
    title: str, 
    year: str,
    media_type: MediaType,
    season: int = 0,
    episode: int = 1,
    extra_num: int | None = None
) -> str:
    """
    Generates Jellyfin-compliant folder and file paths.

    Movies:       /media/movies/Title (Year)/Title (Year).mkv
    Movie Extras: /media/movies/Title (Year)/extras/Title_XX.mkv
    Shows:        /media/shows/Title (Year)/Season XX/Title (Year) SXXEYY.mkv
    """
    clean_title = sanitize_filename(title)
    dir_path = get_disc_output_path(config, title, year, media_type, season)
    os.makedirs(dir_path, exist_ok=True)

    if media_type == MediaType.Show:
        file_name = f"{clean_title} ({year.strip()}) S{season:02d}E{episode:02d}.mkv"

    elif media_type == MediaType.Movie:
        file_name = f"{clean_title} ({year.strip()}).mkv"

    elif media_type == MediaType.MovieExtras:
        if extra_num is not None:
            num = extra_num
        else:
            pattern = re.compile(rf"^{re.escape(clean_title)}_(\d+)\.mkv$", re.IGNORECASE)
            existing_nums = set()
            for filename in os.listdir(dir_path):
                match = pattern.match(filename)
                if match:
                    existing_nums.add(int(match.group(1)))
            num = 1
            while num in existing_nums:
                num += 1

        file_name = f"{clean_title}_{num:02d}.mkv"

    else:
        raise UnsupportedMediaTypeError("Media Type not supported")

    return os.path.join(dir_path, file_name)