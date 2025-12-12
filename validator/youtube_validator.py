import re
from typing import Optional, Tuple
from urllib.parse import urlparse


class YouTubeValidator:
    """Comprehensive YouTube URL validator"""

    # YouTube URL patterns
    YOUTUBE_PATTERNS = {
        'video': [
            # Standard watch URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            # Short URLs
            r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
            # Embed URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            # Mobile URLs
            r'(?:https?://)?m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            # Live URLs
            # r'(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})',
        ],
        'playlist': [
            # Standard playlist URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
            # Watch with playlist
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*list=([a-zA-Z0-9_-]+)',
            # youtu.be with playlist
            r'(?:https?://)?youtu\.be/[a-zA-Z0-9_-]+\?list=([a-zA-Z0-9_-]+)',
        ],
        # 'channel': [
        #     # Channel URLs
        #     r'(?:https?://)?(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)',
        #     # Custom channel URLs
        #     r'(?:https?://)?(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)',
        #     # User URLs
        #     r'(?:https?://)?(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)',
        #     # @username URLs
        #     r'(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_-]+)',
        # ]
    }

    # Valid playlist prefixes based on YouTube's ID format
    VALID_PLAYLIST_PREFIXES = ['PL', 'RD', 'UL', 'UU', 'LL', 'OLAK5uy_', 'MLC', 'PPSV', 'TLG', 'RDAM', 'RDCM', 'RDEM',
                               'RDGMEM', 'RDKM', 'RDMM', 'RDQM']

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Basic URL validation"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) or not result.scheme  # Allow URLs without scheme
        except:
            return False

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from URL"""
        for pattern in YouTubeValidator.YOUTUBE_PATTERNS['video']:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def extract_playlist_id(url: str) -> Optional[str]:
        """Extract playlist ID from URL"""
        for pattern in YouTubeValidator.YOUTUBE_PATTERNS['playlist']:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                playlist_id = match.group(1)
                # Validate playlist ID format
                if YouTubeValidator.is_valid_playlist_id(playlist_id):
                    return playlist_id
        return None

    @staticmethod
    def is_valid_playlist_id(playlist_id: str) -> bool:
        """Validate playlist ID format"""
        if not playlist_id or len(playlist_id) < 2:
            return False

        # Check valid prefixes
        valid_prefix = any(playlist_id.startswith(prefix) for prefix in YouTubeValidator.VALID_PLAYLIST_PREFIXES)
        if valid_prefix:
            return True

        # Old format: PL + 16 hex characters
        if re.match(r'^PL[0-9A-F]{16}$', playlist_id, re.IGNORECASE):
            return True

        # New format: PL + 32 alphanumeric characters
        if re.match(r'^PL[A-Za-z0-9_-]{32}$', playlist_id):
            return True

        # RD format (mixes/radios)
        if re.match(r'^RD[A-Za-z0-9_-]+$', playlist_id):
            return True

        # UL format (user uploads)
        if re.match(r'^UL[A-Za-z0-9_-]+$', playlist_id):
            return True

        # UU format (channel uploads)
        if re.match(r'^UU[A-Za-z0-9_-]+$', playlist_id):
            return True

        return False

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Check if URL is any type of YouTube URL"""
        if not YouTubeValidator.is_valid_url(url):
            return False

        # Check if it's a YouTube domain
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain and domain not in ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', '']:
                return False
        except:
            return False

        # Check if it matches any YouTube pattern
        return (YouTubeValidator.extract_video_id(url) is not None or
                YouTubeValidator.extract_playlist_id(url) is not None or
                any(re.search(pattern, url, re.IGNORECASE) for pattern in YouTubeValidator.YOUTUBE_PATTERNS['channel']))

    @staticmethod
    def is_playlist_url(url: str) -> bool:
        """Check if URL is specifically a YouTube playlist URL"""
        return YouTubeValidator.is_youtube_url(url) and YouTubeValidator.extract_playlist_id(url) is not None

    @staticmethod
    def validate_and_classify(url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate URL and classify its type

        Returns:
            Tuple of (is_valid, url_type, extracted_id)
            url_type can be: 'video', 'playlist', 'channel', 'invalid'
        """
        if not YouTubeValidator.is_youtube_url(url):
            return (False, 'invalid', None)

        # Try to extract playlist ID first
        playlist_id = YouTubeValidator.extract_playlist_id(url)
        if playlist_id:
            return (True, 'playlist', playlist_id)

        # Try to extract video ID
        video_id = YouTubeValidator.extract_video_id(url)
        if video_id:
            return (True, 'video', video_id)

        # Check if it's a channel URL
        for pattern in YouTubeValidator.YOUTUBE_PATTERNS['channel']:
            if re.search(pattern, url, re.IGNORECASE):
                match = re.search(pattern, url, re.IGNORECASE)
                return (True, 'channel', match.group(1))

        return (False, 'invalid', None)
