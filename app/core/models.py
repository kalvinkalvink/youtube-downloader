from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class DownloadStatus(str, enum.Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class DownloadType(str, enum.Enum):
    PLAYLIST_VIDEO = "playlist_video"
    SINGLE_VIDEO = "single_video"
    CHANNEL_VIDEO = "channel_video"


@dataclass
class DownloadTask:
    id: str
    source_url: str
    download_type: DownloadType
    title: str
    target_path: Path
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    thumbnail_url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    video_format: str = "mp4"
    video_quality: str = "best"

    @staticmethod
    def create(
        source_url: str,
        download_type: DownloadType,
        title: str,
        target_path: Path,
        thumbnail_url: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        video_format: str = "mp4",
        video_quality: str = "best",
    ) -> "DownloadTask":
        now = datetime.utcnow()
        return DownloadTask(
            id=str(uuid.uuid4()),
            source_url=source_url,
            download_type=download_type,
            title=title,
            target_path=target_path,
            status=DownloadStatus.QUEUED,
            progress=0.0,
            error_message=None,
            created_at=now,
            updated_at=now,
            thumbnail_url=thumbnail_url,
            extra=extra or {},
            video_format=video_format,
            video_quality=video_quality,
        )

    def mark_status(self, status: DownloadStatus, error: Optional[str] = None) -> None:
        self.status = status
        self.updated_at = datetime.utcnow()
        if error:
            self.error_message = error
