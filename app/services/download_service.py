from __future__ import annotations

import logging
import os
import platform
import ssl
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

logger = logging.getLogger(__name__)
PYTHON_VERSION = platform.python_version()
YTDLP_VERSION = getattr(yt_dlp, "__version__", "unknown")
SSL_DEFAULT_UNVERIFIED = (
    ssl._create_default_https_context is ssl._create_unverified_context
)

from app.core.models import DownloadTask


def get_ffmpeg_location() -> str | None:
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).parent
        ffmpeg_path = app_dir / "ffmpeg.exe"
        if ffmpeg_path.exists():
            return str(app_dir)
        return None
    else:
        bin_dir = Path(__file__).parent.parent.parent / "bin"
        ffmpeg_path = bin_dir / "ffmpeg.exe"
        if ffmpeg_path.exists():
            return str(bin_dir)
        return None


ProgressCallback = Callable[[float], None]


class DownloadCancelled(Exception):
    pass


class DownloadService:
    @staticmethod
    def build_format_options(
        video_format: str,
        video_quality: str,
    ) -> dict:
        if video_quality == "audio":
            if video_format == "mp3":
                return {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            else:
                return {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "m4a",
                            "preferredquality": "192",
                        }
                    ],
                }

        quality_format_map = {
            "best": "bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        }

        format_str = quality_format_map.get(video_quality, "bestvideo+bestaudio/best")

        opts = {"format": format_str}

        if video_format == "mp4":
            opts["merge_output_format"] = "mp4"
        elif video_format == "webm":
            opts["merge_output_format"] = "webm"

        return opts

    @staticmethod
    def download(
        task: DownloadTask,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> tuple[bool, Optional[str]]:
        output_dir = str(task.target_path)
        os.makedirs(output_dir, exist_ok=True)

        logger.info(
            "Starting download task_id=%s url=%s format=%s quality=%s target=%s yt_dlp=%s python=%s",
            task.id,
            task.source_url,
            task.video_format,
            task.video_quality,
            output_dir,
            YTDLP_VERSION,
            PYTHON_VERSION,
        )

        ydl_opts = {
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [],
        }

        ffmpeg_location = get_ffmpeg_location()
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location
            logger.info("Using ffmpeg from: %s", ffmpeg_location)
        else:
            logger.warning("ffmpeg not found - video merging may fail")

        format_opts = DownloadService.build_format_options(
            task.video_format, task.video_quality
        )
        ydl_opts.update(format_opts)

        loggable_opts = {
            key: value
            for key, value in ydl_opts.items()
            if key not in {"progress_hooks"}
        }
        logger.debug(
            "yt-dlp options prepared task_id=%s opts=%s", task.id, loggable_opts
        )

        if progress_callback:

            def progress_hook(d: dict) -> None:
                if cancel_event and cancel_event.is_set():
                    raise DownloadCancelled()

                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                    downloaded = d.get("downloaded_bytes", 0)
                    if total > 0:
                        progress = (downloaded / total) * 100
                        progress_callback(progress)
                elif d["status"] == "finished":
                    progress_callback(100)

            ydl_opts["progress_hooks"].append(progress_hook)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([task.source_url])
            logger.info(
                "Download completed task_id=%s output_dir=%s", task.id, output_dir
            )
            return True, None
        except DownloadCancelled:
            logger.warning("Download cancelled task_id=%s", task.id)
            return False, "Download cancelled"
        except Exception as e:
            logger.exception(
                "Download failed task_id=%s url=%s err=%s yt_dlp=%s python=%s ssl_unverified=%s",
                task.id,
                task.source_url,
                type(e).__name__,
                YTDLP_VERSION,
                PYTHON_VERSION,
                SSL_DEFAULT_UNVERIFIED,
            )
            return False, f"Download error: {str(e)}"
