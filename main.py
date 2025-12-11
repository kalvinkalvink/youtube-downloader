#!/usr/bin/env python3
"""
YouTube Playlist Downloader with Multithreading and Link Validation
"""

import os
import sys
import threading
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
from urllib.parse import urlparse, parse_qs


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
            r'(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})',
        ],
        'playlist': [
            # Standard playlist URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
            # Watch with playlist
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*list=([a-zA-Z0-9_-]+)',
            # youtu.be with playlist
            r'(?:https?://)?youtu\.be/[a-zA-Z0-9_-]+\?list=([a-zA-Z0-9_-]+)',
        ],
        'channel': [
            # Channel URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)',
            # Custom channel URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)',
            # User URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)',
            # @username URLs
            r'(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_-]+)',
        ]
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


class PlaylistDownloader:
    def __init__(self, max_workers: int = 4, output_base_dir: str = "downloads"):
        """
        Initialize the downloader

        Args:
            max_workers: Maximum number of concurrent downloads
            output_base_dir: Base directory for all downloads
        """
        self.max_workers = max_workers
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(exist_ok=True)
        self.validator = YouTubeValidator()

    def validate_playlist_links(self, playlist_links: List[str]) -> List[str]:
        """
        Validate and filter playlist links

        Args:
            playlist_links: List of playlist URLs to validate

        Returns:
            List of valid playlist URLs
        """
        print("\n🔍 Validating playlist links...")
        valid_links = []

        for i, url in enumerate(playlist_links, 1):
            url = url.strip()
            if not url:
                continue

            is_valid, url_type, extracted_id = self.validator.validate_and_classify(url)

            if is_valid and url_type == 'playlist':
                valid_links.append(url)
                print(f"✅ [{i}] Valid playlist: {url[:60]}...")
                print(f"   Playlist ID: {extracted_id}")
            elif is_valid and url_type == 'video':
                print(f"⚠️  [{i}] Video URL detected (not playlist): {url[:60]}...")
                print("   This appears to be a single video, not a playlist.")
            elif is_valid and url_type == 'channel':
                print(f"⚠️  [{i}] Channel URL detected (not playlist): {url[:60]}...")
                print("   This appears to be a channel, not a playlist.")
            else:
                print(f"❌ [{i}] Invalid YouTube URL: {url[:60]}...")
                if url and not url.startswith('http'):
                    print("   💡 Tip: Make sure the URL starts with http:// or https://")

        print(f"\n📊 Validation complete: {len(valid_links)}/{len(playlist_links)} valid playlist links")
        return valid_links

    def get_playlist_info(self, playlist_url: str) -> Optional[Dict]:
        """Get playlist information using yt-dlp"""
        try:
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--print', '%(title)s',
                '--print', '%(id)s',
                '--print', '%(playlist_title)s',
                playlist_url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')

            if len(lines) < 3:
                return None

            playlist_title = lines[-1]
            videos = []

            for i in range(0, len(lines) - 1, 3):
                if i + 1 < len(lines) - 1:
                    videos.append({
                        'title': lines[i],
                        'id': lines[i + 1],
                        'url': f'https://www.youtube.com/watch?v={lines[i + 1]}'
                    })

            return {
                'title': playlist_title,
                'videos': videos,
                'url': playlist_url
            }

        except subprocess.CalledProcessError as e:
            print(f"Error getting playlist info: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def download_video(self, video_info: Dict, playlist_folder: Path, video_number: int) -> bool:
        """Download a single video"""
        try:
            safe_title = "".join(c for c in video_info['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]

            output_template = str(playlist_folder / f"{video_number:03d} - {safe_title}.%(ext)s")

            cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]/best',
                '--merge-output-format', 'mp4',
                '--no-playlist',
                '-o', output_template,
                video_info['url']
            ]

            print(f"[Thread {threading.current_thread().name}] Downloading: {video_info['title']}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Completed: {video_info['title']}")
                return True
            else:
                print(f"❌ Failed: {video_info['title']} - {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error downloading {video_info['title']}: {str(e)}")
            return False

    def download_playlist(self, playlist_url: str) -> bool:
        """Download all videos in a playlist to a separate folder"""
        print(f"\n🔍 Processing playlist: {playlist_url}")

        playlist_info = self.get_playlist_info(playlist_url)
        if not playlist_info:
            print("❌ Failed to get playlist information")
            return False

        playlist_title = playlist_info['title']
        videos = playlist_info['videos']

        print(f"📋 Found {len(videos)} videos in playlist: '{playlist_title}'")

        safe_playlist_title = "".join(c for c in playlist_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        playlist_folder = self.output_base_dir / safe_playlist_title
        playlist_folder.mkdir(exist_ok=True)

        print(f"📁 Download folder: {playlist_folder}")

        successful_downloads = 0
        failed_downloads = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_video = {
                executor.submit(self.download_video, video, playlist_folder, i + 1): video
                for i, video in enumerate(videos)
            }

            for future in as_completed(future_to_video):
                video = future_to_video[future]
                try:
                    success = future.result()
                    if success:
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                except Exception as e:
                    print(f"❌ Exception downloading {video['title']}: {str(e)}")
                    failed_downloads += 1

        print(f"\n📊 Playlist '{playlist_title}' download complete!")
        print(f"✅ Successful: {successful_downloads}")
        print(f"❌ Failed: {failed_downloads}")

        return failed_downloads == 0

    def process_playlist_links(self, playlist_links: List[str]) -> None:
        """Process multiple playlist links with validation"""
        print(f"🚀 Starting download of {len(playlist_links)} playlists with {self.max_workers} threads")
        print("=" * 60)

        # Validate links first
        valid_links = self.validate_playlist_links(playlist_links)

        if not valid_links:
            print("❌ No valid playlist links found!")
            return

        for i, playlist_url in enumerate(valid_links, 1):
            print(f"\n[{i}/{len(valid_links)}] Processing playlist...")

            try:
                self.download_playlist(playlist_url)
            except Exception as e:
                print(f"❌ Error processing playlist {playlist_url}: {str(e)}")

            if i < len(valid_links):
                time.sleep(2)

        print("\n🎉 All playlists processed!")
        print(f"📁 Downloads saved to: {self.output_base_dir.absolute()}")


def main():
    """Main function"""
    print("🎬 YouTube Playlist Downloader with Link Validation")
    print("=" * 60)

    MAX_WORKERS = 4
    OUTPUT_DIR = "downloads"

    print("Enter YouTube playlist links (one per line, empty line to finish):")
    playlist_links = []

    while True:
        link = input("> ").strip()
        if not link:
            break
        playlist_links.append(link)

    if not playlist_links:
        print("❌ No playlist links provided!")
        return

    downloader = PlaylistDownloader(max_workers=MAX_WORKERS, output_base_dir=OUTPUT_DIR)

    try:
        downloader.process_playlist_links(playlist_links)
    except KeyboardInterrupt:
        print("\n\n⚠️ Download interrupted by user!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ yt-dlp is not installed!")
        print("Please install it first: pip install yt-dlp")
        sys.exit(1)

    main()