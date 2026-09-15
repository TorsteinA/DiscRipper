from enum import Enum
import os
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import List
from app.models import RipHistoryItem, RippingStatus

logger = logging.getLogger("ripper.history")

def get_history_file_path(data_dir: str) -> str:
    return os.path.join(data_dir, "history.json")

def load_history(data_dir: str) -> List[RipHistoryItem]:
    path = get_history_file_path(data_dir)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = []
            for item in data:
                # Ensure status string is converted back to RippingStatus enum
                if "status" in item and isinstance(item["status"], str):
                    item["status"] = RippingStatus(item["status"])
                items.append(RipHistoryItem(**item))
            return items
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        return []

def _serialize_item(item: RipHistoryItem) -> dict:
    """Converts a RipHistoryItem dataclass/model into a JSON-serializable dict."""
    if is_dataclass(item):
        data = asdict(item)
    else:
        data = item.__dict__.copy()

    # Convert Enum values to raw strings for JSON storage
    if isinstance(data.get("status"), Enum):
        data["status"] = data["status"].value

    return data

def save_history(data_dir: str, items: List[RipHistoryItem]) -> None:
    os.makedirs(data_dir, exist_ok=True)
    path = get_history_file_path(data_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([_serialize_item(item) for item in items], f, indent=2)

def append_history_item(data_dir: str, item: RipHistoryItem) -> None:
    history = load_history(data_dir)
    history.insert(0, item)  # Newest first
    # TODO: Consider keeping history in correct order but reverse for UI instead
    save_history(data_dir, history)

def update_history_item(data_dir: str, job_id: str, **updates) -> None:
    """Finds a history record by job_id and updates specified fields in-place."""
    history = load_history(data_dir)
    updated = False
    for item in history:
        if getattr(item, "id", None) == job_id:
            for key, value in updates.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            updated = True
            break
    if updated:
        save_history(data_dir, history)