import json
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"

load_dotenv(PROJECT_ROOT / ".env")


def load_json_file(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as json_file:
        loaded_content = json.load(json_file)
    return loaded_content


def get_settings() -> dict:
    settings = load_json_file(SETTINGS_PATH)
    return settings


def get_project_path(relative_path: str) -> Path:
    absolute_path = PROJECT_ROOT / relative_path
    return absolute_path
