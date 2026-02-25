import re
from typing import Optional, Tuple
from urllib.parse import urlparse


class YouTubeValidator:
    """Comprehensive YouTube URL validator for the GUI app."""

    YOUTUBE_PATTERNS = {
        "video": [
            r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
            r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
            r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
            r"(?:https?://)?m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        ],
        "playlist": [
            r"(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)",
            r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*list=([a-zA-Z0-9_-]+)",
            r"(?:https?://)?youtu\.be/[a-zA-Z0-9_-]+\?list=([a-zA-Z0-9_-]+)",
        ],
        "channel": [
            r"(?:https?://)?(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)",
            r"(?:https?://)?(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)",
            r"(?:https?://)?(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)",
            r"(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_-]+)",
        ],
    }

    VALID_PLAYLIST_PREFIXES = [
        "PL",
        "RD",
        "UL",
        "UU",
        "LL",
        "OLAK5uy_",
        "MLC",
        "PPSV",
        "TLG",
        "RDAM",
        "RDCM",
        "RDEM",
        "RDGMEM",
        "RDKM",
        "RDMM",
        "RDQM",
    ]

    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) or not result.scheme
        except Exception:
            return False

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        for pattern in YouTubeValidator.YOUTUBE_PATTERNS["video"]:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def extract_playlist_id(url: str) -> Optional[str]:
        for pattern in YouTubeValidator.YOUTUBE_PATTERNS["playlist"]:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                playlist_id = match.group(1)
                if YouTubeValidator.is_valid_playlist_id(playlist_id):
                    return playlist_id
        return None

    @staticmethod
    def is_valid_playlist_id(playlist_id: str) -> bool:
        if not playlist_id or len(playlist_id) < 2:
            return False

        if any(playlist_id.startswith(prefix) for prefix in YouTubeValidator.VALID_PLAYLIST_PREFIXES):
            return True

        if re.match(r"^PL[0-9A-F]{16}$", playlist_id, re.IGNORECASE):
            return True

        if re.match(r"^PL[A-Za-z0-9_-]{32}$", playlist_id):
            return True

        if re.match(r"^RD[A-Za-z0-9_-]+$", playlist_id):
            return True

        if re.match(r"^UL[A-Za-z0-9_-]+$", playlist_id):
            return True

        if re.match(r"^UU[A-Za-z0-9_-]+$", playlist_id):
            return True

        return False

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        if not YouTubeValidator.is_valid_url(url):
            return False

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain and domain not in ["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", ""]:
                return False
        except Exception:
            return False

        return (
            YouTubeValidator.extract_video_id(url) is not None
            or YouTubeValidator.extract_playlist_id(url) is not None
            or any(re.search(pattern, url, re.IGNORECASE) for pattern in YouTubeValidator.YOUTUBE_PATTERNS["channel"])
        )

    @staticmethod
    def is_playlist_url(url: str) -> bool:
        return YouTubeValidator.is_youtube_url(url) and YouTubeValidator.extract_playlist_id(url) is not None

    @staticmethod
    def validate_and_classify(url: str) -> Tuple[bool, str, Optional[str]]:
        if not YouTubeValidator.is_youtube_url(url):
            return False, "invalid", None

        playlist_id = YouTubeValidator.extract_playlist_id(url)
        if playlist_id:
            return True, "playlist", playlist_id

        video_id = YouTubeValidator.extract_video_id(url)
        if video_id:
            return True, "video", video_id

        for pattern in YouTubeValidator.YOUTUBE_PATTERNS["channel"]:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return True, "channel", match.group(1)

        return False, "invalid", None

