import os
import json
import logging
from typing import List
from dataclasses import asdict
from app.models import RipHistoryItem

logger = logging.getLogger("ripper.history")

def get_history_file_path(data_dir: str) -> str:
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "ripping_history.jsonl")

def append_history_item(data_dir: str, item: RipHistoryItem):
    """Appends a new history record as a single JSON line."""
    path = get_history_file_path(data_dir)
    try:
        # asdict converts dataclasses and Enums cleanly to standard dicts/strings
        data = asdict(item)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
        logger.info(f"Recorded history entry for: {item.title}")
    except Exception as e:
        logger.error(f"Failed to append ripping history: {e}")

def load_history(data_dir: str) -> List[dict]:
    """Reads all history records from the JSONL file (newest first)."""
    path = get_history_file_path(data_dir)
    if not os.path.exists(path):
        return []
    
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return list(reversed(records))
    except Exception as e:
        logger.error(f"Failed to read ripping history: {e}")
        return []

def get_history_entry_count(data_dir: str) -> int:
    path = get_history_file_path(data_dir)
    if not os.path.exists(path):
        return 0
    try:
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
    except Exception as e:
        logger.error(f"Failed to count history entries: {e}")
        return 0