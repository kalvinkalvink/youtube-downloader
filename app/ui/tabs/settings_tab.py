from __future__ import annotations

from pathlib import Path

import flet as ft

from app.core.settings import AppSettings, save_settings
from app.services.download_manager import DownloadManager


def build_settings_tab(
    page: ft.Page, settings: AppSettings, download_manager: DownloadManager
) -> ft.Tab:
    concurrent_field = ft.TextField(
        label="Concurrent downloads",
        value=str(settings.max_concurrent_downloads),
        width=200,
    )
    download_dir_field = ft.TextField(
        label="Download folder",
        value=settings.download_dir,
        expand=True,
    )

    format_dropdown = ft.Dropdown(
        label="Video Format",
        width=200,
        options=[
            ft.dropdown.Option("mp4", "MP4 (best video)"),
            ft.dropdown.Option("webm", "WebM (best video)"),
            ft.dropdown.Option("mp3", "MP3 (audio only)"),
            ft.dropdown.Option("m4a", "M4A (audio only)"),
        ],
        value=settings.video_format,
    )

    quality_dropdown = ft.Dropdown(
        label="Video Quality",
        width=200,
        options=[
            ft.dropdown.Option("best", "Best available"),
            ft.dropdown.Option("1080p", "1080p"),
            ft.dropdown.Option("720p", "720p"),
            ft.dropdown.Option("480p", "480p"),
            ft.dropdown.Option("audio", "Audio only"),
        ],
        value=settings.video_quality,
    )

    status_text = ft.Text("")

    def on_save(e: ft.ControlEvent) -> None:
        try:
            concurrent = int(concurrent_field.value)
            if concurrent < 1:
                raise ValueError
        except ValueError:
            status_text.value = "Concurrent downloads must be a positive integer."
            page.update()
            return

        settings.max_concurrent_downloads = concurrent
        settings.download_dir = download_dir_field.value.strip() or "downloads"
        settings.video_format = format_dropdown.value or "mp4"
        settings.video_quality = quality_dropdown.value or "best"
        Path(settings.download_dir).mkdir(parents=True, exist_ok=True)

        save_settings(settings)
        download_manager.update_settings(settings)
        status_text.value = "Settings saved."
        page.update()

    save_button = ft.ElevatedButton("Save settings", on_click=on_save)

    content = ft.Column(
        controls=[
            concurrent_field,
            download_dir_field,
            format_dropdown,
            quality_dropdown,
            save_button,
            status_text,
        ],
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
    )
    tab = ft.Tab(label="Settings")
    tab.content = content
    return tab
