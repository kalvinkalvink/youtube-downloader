import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import time
from pathlib import Path
from typing import List, Optional, Dict

from validator.youtube_validator import YouTubeValidator


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
