from __future__ import annotations

from pathlib import Path
from typing import List

import flet as ft

from app.core.models import DownloadTask, DownloadType
from app.services.download_manager import DownloadManager
from app.services.yt_services import (
    PlaylistInfo,
    PlaylistVideoInfo,
    fetch_playlist_info,
    format_duration,
)
from app.validator.youtube_validator import YouTubeValidator


def build_playlist_tab(page: ft.Page, download_manager: DownloadManager) -> ft.Tab:
    url_field = ft.TextField(label="YouTube playlist URL", expand=True)
    status_text = ft.Text("")
    videos: List[PlaylistVideoInfo] = []
    video_checkboxes: List[ft.Checkbox] = []
    playlist_info: PlaylistInfo | None = None

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
        nonlocal videos, video_checkboxes, playlist_info
        url = url_field.value.strip()
        if not url:
            status_text.value = "Please paste a playlist URL."
            page.update()
            return

        is_valid, url_type, _ = YouTubeValidator.validate_and_classify(url)
        if not is_valid or url_type != "playlist":
            status_text.value = "URL is not a valid YouTube playlist."
            page.update()
            return

        status_text.value = "Fetching playlist info..."
        page.update()

        def worker() -> None:
            nonlocal videos, video_checkboxes, playlist_info
            try:
                info = fetch_playlist_info(url)
                playlist_info = info
                videos = info.videos
                video_checkboxes = [ft.Checkbox(value=True) for _ in videos]
                status_text.value = (
                    f"Found {len(videos)} videos in playlist '{info.title}'."
                )
            except Exception as exc:
                status_text.value = f"Error: {exc}"
                videos = []
                video_checkboxes = []
            refresh_videos_view()

        page.run_thread(worker)

    def enqueue_tasks(selected_only: bool) -> None:
        if not playlist_info or not videos:
            status_text.value = "No playlist loaded yet."
            page.update()
            return

        download_dir = Path(download_manager._settings.download_dir)
        playlist_folder = download_dir / "playlist" / playlist_info.title
        for v, cb in zip(videos, video_checkboxes):
            if selected_only and not cb.value:
                continue
            task = DownloadTask.create(
                source_url=v.url,
                download_type=DownloadType.PLAYLIST_VIDEO,
                title=v.title,
                target_path=playlist_folder,
                thumbnail_url=v.thumbnail_url,
                extra={"playlist_title": playlist_info.title},
            )
            download_manager.add_task(task)
        status_text.value = "Added selected videos to download queue."
        page.update()

    def on_download_all(e: ft.ControlEvent) -> None:
        enqueue_tasks(selected_only=False)

    def on_download_selected(e: ft.ControlEvent) -> None:
        enqueue_tasks(selected_only=True)

    fetch_button = ft.ElevatedButton("Fetch playlist", on_click=on_fetch_click)
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

    tab = ft.Tab(label="Playlist")
    tab.content = content
    return tab
