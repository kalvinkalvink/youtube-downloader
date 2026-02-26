from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import platformdirs

logger = logging.getLogger(__name__)


SETTINGS_FILE = (
    Path(platformdirs.user_config_dir("youtube-downloader")) / "settings.json"
)

DEFAULT_DOWNLOAD_DIR = str(
    Path(platformdirs.user_downloads_dir()) / "youtube-downloader"
)


@dataclass
class AppSettings:
    download_dir: str = DEFAULT_DOWNLOAD_DIR
    max_concurrent_downloads: int = 4
    video_format: str = "mp4"
    video_quality: str = "best"


def load_settings() -> AppSettings:
    if SETTINGS_FILE.is_file():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            settings = AppSettings(
                download_dir=data.get("download_dir", DEFAULT_DOWNLOAD_DIR),
                max_concurrent_downloads=data.get("max_concurrent_downloads", 4),
                video_format=str(data.get("video_format", "mp4")),
                video_quality=str(data.get("video_quality", "best")),
            )
            logger.info("Settings loaded from %s", SETTINGS_FILE)
            return settings
        except Exception:
            logger.exception("Failed to load settings from %s", SETTINGS_FILE)
    return AppSettings()


def save_settings(settings: AppSettings) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    logger.info("Settings saved to %s", SETTINGS_FILE)
