from __future__ import annotations

from pathlib import Path

import flet as ft

from app.core.models import DownloadTask, DownloadType
from app.services.download_manager import DownloadManager
from app.services.yt_services import VideoInfo, fetch_single_video_info
from app.validator.youtube_validator import YouTubeValidator


def build_single_video_tab(page: ft.Page, download_manager: DownloadManager) -> ft.Tab:
    url_field = ft.TextField(label="YouTube video URL", expand=True)
    status_text = ft.Text("")
    video_info: VideoInfo | None = None

    thumbnail_image = ft.Image(width=320, height=180, src="")
    title_text = ft.Text("", size=18, weight=ft.FontWeight.BOLD)
    duration_text = ft.Text("")
    download_button = ft.ElevatedButton("Download", disabled=True)

    def refresh_video_view() -> None:
        if video_info:
            thumbnail_image.src = video_info.thumbnail_url or ""
            title_text.value = video_info.title
            duration_text.value = f"Duration: {video_info.duration or 'Unknown'}"
            download_button.disabled = False
        else:
            thumbnail_image.src = ""
            title_text.value = ""
            duration_text.value = ""
            download_button.disabled = True
        page.update()

    def on_fetch_click(e: ft.ControlEvent) -> None:
        nonlocal video_info
        url = url_field.value.strip()
        if not url:
            status_text.value = "Please paste a video URL."
            page.update()
            return

        is_valid, url_type, _ = YouTubeValidator.validate_and_classify(url)
        if not is_valid or url_type != "video":
            status_text.value = "URL is not a valid YouTube video."
            page.update()
            return

        status_text.value = "Fetching video info..."
        page.update()

        def worker() -> None:
            nonlocal video_info
            try:
                info = fetch_single_video_info(url)
                video_info = info
                status_text.value = f"Found video: {info.title}"
            except Exception as exc:
                status_text.value = f"Error: {exc}"
                video_info = None
            refresh_video_view()

        page.run_thread(worker)

    def on_download_click(e: ft.ControlEvent) -> None:
        if not video_info:
            return

        download_dir = Path(download_manager._settings.download_dir)
        task = DownloadTask.create(
            source_url=video_info.url,
            download_type=DownloadType.SINGLE_VIDEO,
            title=video_info.title,
            target_path=download_dir,
            thumbnail_url=video_info.thumbnail_url,
            video_format=download_manager._settings.video_format,
            video_quality=download_manager._settings.video_quality,
        )
        download_manager.add_task(task)
        status_text.value = "Added to download queue."
        page.update()

    fetch_button = ft.ElevatedButton("Fetch video", on_click=on_fetch_click)
    download_button.on_click = on_download_click

    content = ft.Column(
        controls=[
            ft.Row(controls=[url_field, fetch_button]),
            status_text,
            ft.Container(
                content=ft.Column(
                    controls=[
                        thumbnail_image,
                        title_text,
                        duration_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                alignment="center",
                padding=20,
            ),
            ft.Container(
                content=download_button,
                alignment="center",
                padding=20,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
    )

    tab = ft.Tab(label="Single Video")
    tab.content = content
    return tab
