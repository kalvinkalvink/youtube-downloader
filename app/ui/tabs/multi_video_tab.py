from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import flet as ft

from app.core.models import DownloadTask, DownloadType
from app.services.download_manager import DownloadManager
from app.services.yt_services import VideoInfo, fetch_single_video_info, format_duration
from app.validator.youtube_validator import YouTubeValidator

logger = logging.getLogger(__name__)


def build_multi_video_tab(page: ft.Page, download_manager: DownloadManager) -> ft.Tab:
    url_field = ft.TextField(
        label="YouTube video URLs (one per line)",
        expand=True,
        multiline=True,
        min_lines=3,
        max_lines=5,
    )
    status_text = ft.Text("")
    videos: List[VideoInfo] = []
    video_checkboxes: List[ft.Checkbox] = []

    videos_column = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)

    def refresh_videos_view() -> None:
        videos_column.controls.clear()
        for v, cb in zip(videos, video_checkboxes):
            row = ft.Row(
                controls=[
                    cb,
                    ft.Image(src=v.thumbnail_url or "", width=80, height=45),
                    ft.Text(v.title, expand=True),
                    ft.Text(format_duration(v.duration)),
                ],
                alignment=ft.MainAxisAlignment.START,
            )
            videos_column.controls.append(row)
        page.update()

    def on_fetch_click(e: ft.ControlEvent) -> None:
        nonlocal videos, video_checkboxes
        url_text = url_field.value.strip()
        if not url_text:
            status_text.value = "Please paste video URLs."
            page.update()
            return

        url_lines = [line.strip() for line in url_text.split("\n") if line.strip()]
        if not url_lines:
            status_text.value = "Please paste video URLs."
            page.update()
            return

        valid_urls = []
        for url in url_lines:
            is_valid, url_type, _ = YouTubeValidator.validate_and_classify(url)
            if is_valid and url_type == "video":
                valid_urls.append(url)
            else:
                logger.warning("Skipping invalid video URL: %s", url)

        if not valid_urls:
            status_text.value = "No valid YouTube video URLs found."
            page.update()
            return

        status_text.value = f"Fetching {len(valid_urls)} videos..."
        page.update()

        def worker() -> None:
            nonlocal videos, video_checkboxes
            videos = []
            video_checkboxes = []
            fetched_count = 0

            for url in valid_urls:
                try:
                    logger.info("Fetching video info url=%s", url)
                    info = fetch_single_video_info(url)
                    videos.append(info)
                    video_checkboxes.append(ft.Checkbox(value=True))
                    fetched_count += 1
                    status_text.value = (
                        f"Fetching {fetched_count}/{len(valid_urls)} videos..."
                    )
                    page.update()
                except Exception as exc:
                    logger.exception("Failed to fetch video url=%s", url)

            status_text.value = f"Found {len(videos)} videos."
            refresh_videos_view()

        page.run_thread(worker)

    def enqueue_tasks(selected_only: bool) -> None:
        if not videos:
            status_text.value = "No videos loaded yet."
            page.update()
            return

        download_dir = Path(download_manager._settings.download_dir)
        multi_folder = download_dir / "multi"
        task_count = 0
        for v, cb in zip(videos, video_checkboxes):
            if selected_only and not cb.value:
                continue
            task = DownloadTask.create(
                source_url=v.url,
                download_type=DownloadType.SINGLE_VIDEO,
                title=v.title,
                target_path=multi_folder,
                thumbnail_url=v.thumbnail_url,
                video_format=download_manager._settings.video_format,
                video_quality=download_manager._settings.video_quality,
            )
            download_manager.add_task(task)
            task_count += 1
        logger.info("Enqueued %s videos", task_count)
        status_text.value = f"Added {task_count} videos to download queue."
        page.update()

    def on_download_all(e: ft.ControlEvent) -> None:
        enqueue_tasks(selected_only=False)

    def on_download_selected(e: ft.ControlEvent) -> None:
        enqueue_tasks(selected_only=True)

    fetch_button = ft.ElevatedButton("Fetch videos", on_click=on_fetch_click)
    download_all_button = ft.ElevatedButton("Download all", on_click=on_download_all)
    download_selected_button = ft.ElevatedButton(
        "Download selected", on_click=on_download_selected
    )

    content = ft.Column(
        controls=[
            ft.Row(controls=[url_field, fetch_button]),
            ft.Row(controls=[download_all_button, download_selected_button]),
            status_text,
            ft.Container(content=videos_column, expand=True),
        ],
        expand=True,
    )

    tab = ft.Tab(label="Multi Video")
    tab.content = content
    return tab
