#!/usr/bin/env python3
"""
YouTube Playlist Downloader with Multithreading and Link Validation
"""

import subprocess
import sys

from services.playlist_downloader import PlaylistDownloader


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