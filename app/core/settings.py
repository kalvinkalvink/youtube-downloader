from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


SETTINGS_FILE = Path("settings.json")


@dataclass
class AppSettings:
    download_dir: str = "downloads"
    max_concurrent_downloads: int = 4
    video_format: str = "mp4"
    video_quality: str = "best"


def load_settings() -> AppSettings:
    if SETTINGS_FILE.is_file():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return AppSettings(
                download_dir=data.get("download_dir", "downloads"),
                max_concurrent_downloads=data.get("max_concurrent_downloads", 4),
                video_format=str(data.get("video_format", "mp4")),
                video_quality=str(data.get("video_quality", "best")),
            )
        except Exception:
            return AppSettings()
    return AppSettings()


def save_settings(settings: AppSettings) -> None:
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
