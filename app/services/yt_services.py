from __future__ import annotations

import logging
import ssl
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

ssl._create_default_https_context = ssl._create_unverified_context

YDL_OPTS: Dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
}


@dataclass
class PlaylistVideoInfo:
    title: str
    video_id: str
    url: str
    thumbnail_url: Optional[str]
    duration: Optional[str] = None


@dataclass
class PlaylistInfo:
    title: str
    url: str
    videos: List[PlaylistVideoInfo]


@dataclass
class VideoInfo:
    title: str
    video_id: str
    url: str
    thumbnail_url: Optional[str]
    duration: Optional[str] = None


@dataclass
class ChannelVideoInfo:
    title: str
    video_id: str
    url: str
    thumbnail_url: Optional[str]
    duration: Optional[str] = None


@dataclass
class ChannelInfo:
    title: str
    url: str
    videos: List[ChannelVideoInfo]


def format_duration(seconds_val: int | str | None) -> str:
    if seconds_val is None or (
        isinstance(seconds_val, str) and (not seconds_val or seconds_val == "None")
    ):
        return "Not Found"
    if isinstance(seconds_val, str) and ":" in seconds_val:
        return seconds_val
    try:
        total_seconds = float(seconds_val)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{int(hours)}:{int(minutes)}:{(seconds)}"
        return f"{int(minutes)}:{int(seconds)}"
    except (ValueError, TypeError):
        return "Not Found"


def fetch_playlist_info(playlist_url: str) -> PlaylistInfo:
    """
    Use yt-dlp to fetch playlist info, including thumbnail URLs.
    """
    logger.info("Fetching playlist info url=%s", playlist_url)
    try:
        ydl_opts = {**YDL_OPTS, "extract_flat": "in_playlist"}
        with YoutubeDL(ydl_opts) as ydl:
            playlist_data = ydl.extract_info(playlist_url, download=False)

        if not playlist_data:
            raise RuntimeError("Failed to fetch playlist information")

        playlist_title = playlist_data.get("title", "Unknown Playlist")
        entries = playlist_data.get("entries", [])

        videos: List[PlaylistVideoInfo] = []
        for entry in entries:
            if entry is None:
                continue
            videos.append(
                PlaylistVideoInfo(
                    title=entry.get("title", "Unknown"),
                    video_id=entry.get("id", ""),
                    url=f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    thumbnail_url=entry.get("thumbnails")[-1]['url'],
                    duration=format_duration(entry.get("duration")),
                )
            )

        logger.info(
            "Playlist fetched successfully title=%s videos_count=%s",
            playlist_title,
            len(videos),
        )
        return PlaylistInfo(title=playlist_title, url=playlist_url, videos=videos)
    except Exception:
        logger.exception("Failed to fetch playlist url=%s", playlist_url)
        raise


def fetch_single_video_info(video_url: str) -> VideoInfo:
    logger.info("Fetching single video info url=%s", video_url)
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            video_data = ydl.extract_info(video_url, download=False)

        if not video_data:
            raise RuntimeError("Failed to fetch video information")

        title = video_data.get("title", "Unknown")
        video_id = video_data.get("id", "")
        thumbnail = video_data.get("thumbnail")
        duration = video_data.get("duration")
        url = f"https://www.youtube.com/watch?v={video_id}"

        logger.info("Single video fetched successfully title=%s", title)
        return VideoInfo(
            title=title,
            video_id=video_id,
            url=url,
            thumbnail_url=thumbnail,
            duration=format_duration(duration),
        )
    except Exception:
        logger.exception("Failed to fetch single video url=%s", video_url)
        raise


def fetch_channel_info(channel_url: str) -> ChannelInfo:
    logger.info("Fetching channel info url=%s", channel_url)
    try:
        ydl_opts = {**YDL_OPTS, "extract_flat": "in_playlist"}
        with YoutubeDL(ydl_opts) as ydl:
            channel_data = ydl.extract_info(channel_url, download=False)

        if not channel_data:
            raise RuntimeError("Failed to fetch channel information")

        channel_title = channel_data.get("channel") or channel_data.get(
            "title", "Unknown Channel"
        )
        entries = channel_data.get("entries", [])

        videos: List[ChannelVideoInfo] = []
        for entry in entries:
            if entry is None:
                continue
            thumbnails = entry.get("thumbnails", [])
            thumbnail_url = thumbnails[-1].get("url") if thumbnails else None

            videos.append(
                ChannelVideoInfo(
                    title=entry.get("title", "Unknown"),
                    video_id=entry.get("id", ""),
                    url=f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    thumbnail_url=thumbnail_url,
                    duration=format_duration(entry.get("duration")),
                )
            )

        logger.info(
            "Channel fetched successfully title=%s videos_count=%s",
            channel_title,
            len(videos),
        )
        return ChannelInfo(title=channel_title, url=channel_url, videos=videos)
    except Exception:
        logger.exception("Failed to fetch channel url=%s", channel_url)
        raise
