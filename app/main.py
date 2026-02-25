from __future__ import annotations

import subprocess

import flet as ft

from app.services.download_manager import DownloadManager
from app.core.settings import AppSettings, load_settings
from app.ui.tabs.download_manager_tab import build_download_manager_tab
from app.ui.tabs.playlist_tab import build_playlist_tab
from app.ui.tabs.settings_tab import build_settings_tab
from app.ui.tabs.single_video_tab import build_single_video_tab
from app.ui.tabs.channel_tab import build_channel_tab


def ensure_yt_dlp_available() -> str:
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return "yt-dlp is not available. Please install it (pip install yt-dlp)."
        return ""
    except FileNotFoundError:
        return "yt-dlp command not found. Please install it and ensure it is on PATH."


def main(page: ft.Page) -> None:
    page.title = "YouTube Downloader"
    page.window_width = 1200
    page.window_height = 800

    err = ensure_yt_dlp_available()
    if err:
        dlg = ft.AlertDialog(title=ft.Text("yt-dlp missing"), content=ft.Text(err))
        page.dialog = dlg
        dlg.open = True
        page.update()

    settings: AppSettings = load_settings()
    download_manager = DownloadManager(settings=settings)

    playlist_tab = build_playlist_tab(page, download_manager)
    single_tab = build_single_video_tab(page, download_manager)
    channel_tab = build_channel_tab(page, download_manager)
    downloads_tab = build_download_manager_tab(page, download_manager)
    settings_tab = build_settings_tab(page, settings, download_manager)

    content_container = ft.Container(expand=True, content=playlist_tab.content)
    current_index = 0

    def switch_view(index: int) -> None:
        nonlocal current_index
        if index == 0:
            content_container.content = playlist_tab.content
        elif index == 1:
            content_container.content = single_tab.content
        elif index == 2:
            content_container.content = channel_tab.content
        elif index == 3:
            content_container.content = downloads_tab.content
        elif index == 4:
            content_container.content = settings_tab.content

        for i, btn in enumerate(buttons):
            btn.style = ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.WHITE) if i == index else None

        current_index = index
        page.update()

    playlist_btn = ft.TextButton(
        "Playlist",
        on_click=lambda e: switch_view(0),
        style=ft.ButtonStyle(color=ft.Colors.PRIMARY),
    )
    single_btn = ft.TextButton("Single Video", on_click=lambda e: switch_view(1))
    channel_btn = ft.TextButton("Channel", on_click=lambda e: switch_view(2))
    downloads_btn = ft.TextButton("Downloads", on_click=lambda e: switch_view(3))
    settings_btn = ft.TextButton("Settings", on_click=lambda e: switch_view(4))

    buttons = [playlist_btn, single_btn, channel_btn, downloads_btn, settings_btn]

    buttons_row = ft.Row(
        controls=buttons,
        alignment=ft.MainAxisAlignment.START,
    )

    page.add(ft.Column(controls=[buttons_row, content_container], expand=True))
    switch_view(0)

if __name__ == "__main__":
    ft.run(main)
