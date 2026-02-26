from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import flet as ft

from app.core.models import DownloadTask, DownloadType
from app.services.download_manager import DownloadManager
from app.services.yt_services import (
    ChannelInfo,
    ChannelVideoInfo,
    fetch_channel_info,
    format_duration,
)
from app.validator.youtube_validator import YouTubeValidator

logger = logging.getLogger(__name__)


def build_channel_tab(page: ft.Page, download_manager: DownloadManager) -> ft.Tab:
    url_field = ft.TextField(label="YouTube channel URL", expand=True)
    status_text = ft.Text("")
    videos: List[ChannelVideoInfo] = []
    video_checkboxes: List[ft.Checkbox] = []
    channel_info: ChannelInfo | None = None
    select_all_checkbox = ft.Checkbox(label="Select All", value=True, disabled=True)

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
        nonlocal videos, video_checkboxes, channel_info
        url = url_field.value.strip()
        if not url:
            status_text.value = "Please paste a channel URL."
            page.update()
            return

        is_valid, url_type, _ = YouTubeValidator.validate_and_classify(url)
        if not is_valid or url_type != "channel":
            status_text.value = "URL is not a valid YouTube channel."
            page.update()
            return

        status_text.value = "Fetching channel info..."
        page.update()

        def worker() -> None:
            nonlocal videos, video_checkboxes, channel_info
            try:
                logger.info("Fetching channel info url=%s", url)
                info = fetch_channel_info(url)
                channel_info = info
                videos = info.videos
                video_checkboxes = [ft.Checkbox(value=True) for _ in videos]
                status_text.value = (
                    f"Found {len(videos)} videos in channel '{info.title}'."
                )
                select_all_checkbox.disabled = False
                logger.info(
                    "Channel fetched successfully title=%s videos_count=%s",
                    info.title,
                    len(videos),
                )
            except Exception as exc:
                logger.exception("Failed to fetch channel url=%s", url)
                status_text.value = f"Error: {exc}"
                videos = []
                video_checkboxes = []
                select_all_checkbox.disabled = True
            refresh_videos_view()

        page.run_thread(worker)

    def on_select_all_changed(e: ft.ControlEvent) -> None:
        for cb in video_checkboxes:
            cb.value = select_all_checkbox.value
        page.update()

    def enqueue_tasks(selected_only: bool) -> None:
        if not channel_info or not videos:
            status_text.value = "No channel loaded yet."
            page.update()
            return

        download_dir = Path(download_manager._settings.download_dir)
        channel_folder = download_dir / "channel" / channel_info.title
        task_count = 0
        for v, cb in zip(videos, video_checkboxes):
            if selected_only and not cb.value:
                continue
            task = DownloadTask.create(
                source_url=v.url,
                download_type=DownloadType.CHANNEL_VIDEO,
                title=v.title,
                target_path=channel_folder,
                thumbnail_url=v.thumbnail_url,
                extra={"channel_title": channel_info.title},
                video_format=download_manager._settings.video_format,
                video_quality=download_manager._settings.video_quality,
            )
            download_manager.add_task(task)
            task_count += 1
        logger.info(
            "Enqueued %s channel videos channel=%s", task_count, channel_info.title
        )
        status_text.value = "Added selected videos to download queue."
        page.update()

    def on_download_all(e: ft.ControlEvent) -> None:
        enqueue_tasks(selected_only=False)

    def on_download_selected(e: ft.ControlEvent) -> None:
        enqueue_tasks(selected_only=True)

    fetch_button = ft.ElevatedButton("Fetch channel", on_click=on_fetch_click)
    download_all_button = ft.ElevatedButton("Download all", on_click=on_download_all)
    download_selected_button = ft.ElevatedButton(
        "Download selected", on_click=on_download_selected
    )
    select_all_checkbox.on_change = on_select_all_changed

    content = ft.Column(
        controls=[
            ft.Row(controls=[url_field, fetch_button]),
            ft.Row(
                controls=[
                    select_all_checkbox,
                    download_all_button,
                    download_selected_button,
                ]
            ),
            status_text,
            ft.Container(content=videos_column, expand=True),
        ],
        expand=True,
    )

    tab = ft.Tab(label="Channel")
    tab.content = content
    return tab
