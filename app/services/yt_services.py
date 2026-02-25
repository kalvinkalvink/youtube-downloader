from __future__ import annotations

import ssl
import subprocess
from dataclasses import dataclass
from typing import List, Optional

ssl._create_default_https_context = ssl._create_unverified_context


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


def format_duration(seconds_str: str | None) -> str:
    if not seconds_str:
        return "Unknown"
    try:
        total_seconds = int(seconds_str)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "Unknown"


def _run_yt_dlp(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "yt-dlp failed")
    return result.stdout


def fetch_playlist_info(playlist_url: str) -> PlaylistInfo:
    """
    Use yt-dlp to fetch playlist info, including thumbnail URLs.
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print",
        "%(title)s",
        "--print",
        "%(id)s",
        "--print",
        "%(thumbnail)s",
        "--print",
        "%(duration)s",
        "--print",
        "%(playlist_title)s",
        playlist_url,
    ]
    stdout = _run_yt_dlp(cmd)
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) < 4:
        raise RuntimeError("Failed to parse playlist information")

    playlist_title = lines[-1]
    videos: List[PlaylistVideoInfo] = []

    # Groups of 4 lines (title, id, thumbnail, duration) per video, last line is playlist title
    for i in range(0, len(lines) - 1, 5):
        title = lines[i]
        vid = lines[i + 1]
        thumbnail = lines[i + 2] or None
        duration = lines[i + 3] if lines[i + 3] != "None" else None
        playlist_title = lines[i + 4] or None
        url = f"https://www.youtube.com/watch?v={vid}"
        videos.append(
            PlaylistVideoInfo(
                title=title,
                video_id=vid,
                url=url,
                thumbnail_url=thumbnail,
                duration=duration,
            )
        )

    return PlaylistInfo(title=playlist_title, url=playlist_url, videos=videos)


def fetch_single_video_info(video_url: str) -> VideoInfo:
    cmd = [
        "yt-dlp",
        "--print",
        "%(title)s",
        "--print",
        "%(id)s",
        "--print",
        "%(thumbnail)s",
        "--print",
        "%(duration)s",
        video_url,
    ]
    stdout = _run_yt_dlp(cmd)
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) < 4:
        raise RuntimeError("Failed to parse video information")

    title = lines[0]
    vid = lines[1]
    thumbnail = lines[2] or None
    duration = lines[3] if lines[3] != "None" else None
    url = f"https://www.youtube.com/watch?v={vid}"

    return VideoInfo(
        title=title,
        video_id=vid,
        url=url,
        thumbnail_url=thumbnail,
        duration=duration,
    )


def fetch_channel_info(channel_url: str) -> ChannelInfo:
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print",
        "%(title)s",
        "--print",
        "%(id)s",
        "--print",
        "%(thumbnail)s",
        "--print",
        "%(duration)s",
        channel_url,
    ]
    stdout = _run_yt_dlp(cmd)
    lines = [line for line in stdout.splitlines() if line.strip()]
    if len(lines) < 5:
        raise RuntimeError("Failed to parse channel information")

    channel_title = lines[-1]
    videos: List[ChannelVideoInfo] = []

    for i in range(0, len(lines) - 1, 4):
        if i + 3 >= len(lines) - 1:
            break
        title = lines[i]
        vid = lines[i + 1]
        thumbnail = lines[i + 2] or None
        duration = lines[i + 3] if lines[i + 3] != "None" else None
        url = f"https://www.youtube.com/watch?v={vid}"
        videos.append(
            ChannelVideoInfo(
                title=title,
                video_id=vid,
                url=url,
                thumbnail_url=thumbnail,
                duration=duration,
            )
        )

    return ChannelInfo(title=channel_title, url=channel_url, videos=videos)
