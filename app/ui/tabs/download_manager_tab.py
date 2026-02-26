from __future__ import annotations

import logging

import flet as ft

from app.core.models import DownloadStatus, DownloadTask
from app.services.download_manager import DownloadManager

logger = logging.getLogger(__name__)


def build_download_manager_tab(
    page: ft.Page, download_manager: DownloadManager
) -> ft.Tab:
    status_text = ft.Text("")

    def build_rows() -> list[ft.DataRow]:
        rows: list[ft.DataRow] = []
        tasks = download_manager.get_tasks()
        for task in tasks:
            cancel_btn = ft.TextButton(
                "Cancel",
                disabled=task.status
                not in (DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING),
                data=task.id,
            )

            def on_cancel(e: ft.BaseControl) -> None:
                tid = e.control.data
                download_manager.cancel_task(tid)

            cancel_btn.on_click = on_cancel

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(task.download_type.value)),
                        ft.DataCell(
                            ft.Row(
                                controls=[
                                    ft.Image(
                                        src=task.thumbnail_url or "",
                                        width=80,
                                        height=45,
                                    ),
                                    ft.Text(task.title, expand=True),
                                ]
                            )
                        ),
                        ft.DataCell(ft.Text(task.status.value)),
                        ft.DataCell(ft.Text(f"{task.progress:.0f}%")),
                        ft.DataCell(ft.Text(task.error_message or "")),
                        ft.DataCell(cancel_btn),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("Type")),
            ft.DataColumn(label=ft.Text("Title")),
            ft.DataColumn(label=ft.Text("Status")),
            ft.DataColumn(label=ft.Text("Progress")),
            ft.DataColumn(label=ft.Text("Error")),
            ft.DataColumn(label=ft.Text("Actions")),
        ],
        rows=[],
        width=float("inf"),
    )

    def refresh() -> None:
        table.rows = build_rows()
        status_text.value = f"{len(table.rows)} tasks in queue/history."
        page.update()

    download_manager.set_update_callback(refresh)
    refresh()

    def on_clear_completed(e: ft.BaseControl) -> None:
        logger.info("Clearing completed tasks from download manager")
        download_manager.clear_completed_tasks()

    def on_cancel_all(e: ft.BaseControl) -> None:
        logger.info("Cancelling all active downloads")
        download_manager.cancel_all_downloading()

    clear_completed_btn = ft.TextButton(
        "Clear Completed",
        on_click=on_clear_completed,
    )

    cancel_all_btn = ft.TextButton(
        "Cancel All",
        on_click=on_cancel_all,
    )

    header_row = ft.Row(
        controls=[
            status_text,
            ft.Container(expand=True),
            clear_completed_btn,
            cancel_all_btn,
        ]
    )

    content = ft.Column(
        controls=[
            header_row,
            ft.Container(content=table, expand=True),
        ],
        expand=True,
    )

    tab = ft.Tab(label="Downloads")
    tab.content = content
    return tab
