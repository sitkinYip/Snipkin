"""
snipkin.handlers.concat_handler - 视频拼接的事件处理层（Flet 版）

本模块提供视频拼接功能的所有事件处理函数，包括：
- handle_concat_add_files_picked: 多文件选择完成后的回调处理
- handle_concat_remove_file:     移除指定索引的文件
- handle_concat_move_up:         上移选中文件
- handle_concat_move_down:       下移选中文件
- handle_concat_clear:           清空文件列表
- handle_concat_output_picked:   输出路径选择完成后的回调处理
- handle_concat_run:             "开始拼接"按钮点击处理

设计说明：
  从 Mixin 模式迁移为独立的函数模块。
  所有函数接收 AppState 实例和 UI 控件引用作为参数。
  核心的参数校验、ffmpeg 命令构建、命令执行逻辑仍由 snipkin.core.concat_core 提供。
"""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

import flet as ft

from snipkin.core.concat_core import (
    build_concat_ffmpeg_command,
    execute_concat_ffmpeg,
    generate_concat_output_path,
    validate_concat_params,
)

if TYPE_CHECKING:
    from snipkin.app import AppState


def _log(state: AppState, message: str) -> None:
    """
    向日志 ListView 追加一行消息。

    每条日志以 Monospace 字体的 Text 控件形式追加到 ListView 中，
    ListView 设置了 auto_scroll=True 会自动滚动到最新行。

    参数:
        state:   应用状态实例
        message: 要写入的日志消息文本
    """
    if state.log_text is not None:
        state.log_text.controls.append(
            ft.Text(
                message,
                size=12,
                color="#8e8e93",
                font_family="SF Mono, Menlo, Consolas, monospace",
                selectable=True,
            ),
        )
        state.page.update()


def _refresh_file_list(
    state: AppState,
    file_list_view: ft.ListView,
) -> None:
    """
    刷新拼接文件列表的显示内容。

    清空 ListView 后重新构建所有文件条目的 ListTile。

    参数:
        state:          应用状态实例
        file_list_view: ListView 控件引用
    """
    from snipkin.ui.concat_tab import build_file_list_tile

    file_list_view.controls.clear()
    for index, file_path in enumerate(state.concat_file_list):
        tile = build_file_list_tile(index, file_path, state, file_list_view)
        file_list_view.controls.append(tile)
    state.page.update()


def handle_concat_add_files_picked(
    result: list,
    state: AppState,
    file_list_view: ft.ListView,
    output_path_field: ft.TextField,
) -> None:
    """
    处理多文件选择完成后的回调。

    Flet 0.82+ 中 pick_files() 直接返回 list[FilePickerFile]。
    将选中的文件添加到拼接列表中（自动去重），
    如果是首次添加文件且输出路径为空，自动生成默认输出路径。

    参数:
        result:            pick_files() 返回的文件列表
        state:             应用状态实例
        file_list_view:    ListView 控件引用
        output_path_field: 输出路径 TextField 控件
    """
    if not result:
        return

    added_count = 0
    for picked_file in result:
        if picked_file.path and picked_file.path not in state.concat_file_list:
            state.concat_file_list.append(picked_file.path)
            added_count += 1

    _refresh_file_list(state, file_list_view)
    _log(
        state,
        f"已添加 {added_count} 个文件，当前共 {len(state.concat_file_list)} 个",
    )

    # 自动生成默认输出路径
    if state.concat_file_list and not state.concat_output_path:
        default_output = generate_concat_output_path(
            state.concat_file_list[0], state.concat_output_format,
        )
        state.concat_output_path = default_output
        output_path_field.value = default_output
        state.page.update()


def handle_concat_remove_file(
    state: AppState,
    file_list_view: ft.ListView,
    index: int,
) -> None:
    """
    移除拼接列表中指定索引的文件。

    参数:
        state:          应用状态实例
        file_list_view: ListView 控件引用
        index:          要移除的文件索引
    """
    if 0 <= index < len(state.concat_file_list):
        removed_file = state.concat_file_list.pop(index)
        _refresh_file_list(state, file_list_view)
        _log(state, f"已移除: {os.path.basename(removed_file)}")


def handle_concat_move_up(
    state: AppState,
    file_list_view: ft.ListView,
) -> None:
    """
    将当前选中的文件在列表中上移一位。

    通过 state.concat_selected_index 获取当前选中项索引，
    与上一项交换位置后刷新列表并更新选中状态。
    当没有选中项或选中项已在顶部时无操作。

    参数:
        state:          应用状态实例
        file_list_view: ListView 控件引用
    """
    index = state.concat_selected_index
    if index <= 0 or index >= len(state.concat_file_list):
        if index == -1:
            _log(state, "请先点击选中要移动的文件。")
        return
    state.concat_file_list[index], state.concat_file_list[index - 1] = (
        state.concat_file_list[index - 1], state.concat_file_list[index],
    )
    state.concat_selected_index = index - 1
    _refresh_file_list(state, file_list_view)
    _log(
        state,
        f"已上移: {os.path.basename(state.concat_file_list[index - 1])}",
    )


def handle_concat_move_down(
    state: AppState,
    file_list_view: ft.ListView,
) -> None:
    """
    将当前选中的文件在列表中下移一位。

    通过 state.concat_selected_index 获取当前选中项索引，
    与下一项交换位置后刷新列表并更新选中状态。
    当没有选中项或选中项已在底部时无操作。

    参数:
        state:          应用状态实例
        file_list_view: ListView 控件引用
    """
    index = state.concat_selected_index
    if index < 0 or index >= len(state.concat_file_list) - 1:
        if index == -1:
            _log(state, "请先点击选中要移动的文件。")
        return
    state.concat_file_list[index], state.concat_file_list[index + 1] = (
        state.concat_file_list[index + 1], state.concat_file_list[index],
    )
    state.concat_selected_index = index + 1
    _refresh_file_list(state, file_list_view)
    _log(
        state,
        f"已下移: {os.path.basename(state.concat_file_list[index + 1])}",
    )


def handle_concat_clear(
    state: AppState,
    file_list_view: ft.ListView,
) -> None:
    """
    清空拼接文件列表。

    参数:
        state:          应用状态实例
        file_list_view: ListView 控件引用
    """
    state.concat_file_list.clear()
    _refresh_file_list(state, file_list_view)
    _log(state, "已清空文件列表。")


def handle_concat_output_picked(
    result: str | None,
    state: AppState,
    output_path_field: ft.TextField,
) -> None:
    """
    处理输出路径选择完成后的回调。

    Flet 0.82+ 中 save_file() 直接返回 str | None。

    参数:
        result:            save_file() 返回的文件路径字符串
        state:             应用状态实例
        output_path_field: 输出路径 TextField 控件
    """
    if result:
        state.concat_output_path = result
        output_path_field.value = result
        _log(state, f"拼接输出路径已设置: {result}")
        state.page.update()


def handle_concat_run(state: AppState) -> None:
    """
    处理"开始拼接"按钮点击事件。

    执行流程：
      1. 从 state 收集所有参数值
      2. 调用 core 层校验参数（含获取视频时长）
      3. 调用 core 层构建 ffmpeg 命令
      4. 在子线程中调用 core 层执行命令

    参数:
        state: 应用状态实例
    """
    output_path = state.concat_output_path.strip()
    transition_display_name = state.concat_transition
    transition_duration_str = state.concat_transition_duration

    # ---- 调用 core 层校验参数 ----
    params, error = validate_concat_params(
        file_list=state.concat_file_list,
        output_path=output_path,
        transition_display_name=transition_display_name,
        transition_duration_str=transition_duration_str,
    )
    if error:
        _log(state, error)
        return

    if params["output_dir_created"]:
        _log(state, f"已自动创建输出文件夹: {params['output_dir_created']}")

    if params["durations"]:
        _log(state, "已获取视频时长信息:")
        for file_path, duration in zip(
            state.concat_file_list, params["durations"],
        ):
            _log(state, f"  {os.path.basename(file_path)}: {duration:.2f}s")

    # ---- 调用 core 层构建 ffmpeg 命令 ----
    command, temp_file_path = build_concat_ffmpeg_command(
        file_list=state.concat_file_list,
        output_path=output_path,
        transition_name=params["transition_name"],
        transition_duration=params["transition_duration"],
        durations=params["durations"],
        resolutions=params.get("resolutions", []),
        compress_enabled=state.concat_compress_enabled,
        quality_preset=state.concat_compress_quality,
        resolution=state.concat_resolution,
        framerate=state.concat_framerate,
        audio_bitrate=state.concat_audio_bitrate,
    )

    _log(state, f"▶ 执行命令: {' '.join(command)}")

    # 禁用按钮，防止重复点击
    run_button_container = state.concat_run_button
    if run_button_container is not None:
        inner_button = run_button_container.content
        inner_button.disabled = True
        inner_button.content = ft.Text("处理中...", size=15, weight=ft.FontWeight.W_600)
        inner_button.icon = ft.CupertinoIcons.HOURGLASS
        state.page.update()

    # ---- 在子线程中调用 core 层执行命令 ----
    thread = threading.Thread(
        target=_run_concat_ffmpeg_in_thread,
        args=(state, command, output_path, temp_file_path),
        daemon=True,
    )
    thread.start()


def _run_concat_ffmpeg_in_thread(
    state: AppState,
    command: list[str],
    output_path: str,
    temp_file_path: str | None,
) -> None:
    """
    在子线程中执行拼接 ffmpeg 命令。

    通过回调函数将 core 层的执行结果反馈到 UI 层。

    参数:
        state:          应用状态实例
        command:        完整的 ffmpeg 命令参数列表
        output_path:    输出文件路径（用于成功日志）
        temp_file_path: concat demuxer 模式的临时文件路径（可选，用于清理）
    """
    execute_concat_ffmpeg(
        command=command,
        on_log=lambda message: _log(state, message),
        on_success=lambda: _log(state, f"拼接成功！输出文件: {output_path}"),
        on_error=lambda message: _log(state, message),
        on_complete=lambda: _restore_concat_run_button(state),
        temp_file_path=temp_file_path,
    )


def _restore_concat_run_button(state: AppState) -> None:
    """
    恢复拼接按钮到可点击状态。

    在 ffmpeg 命令执行完成后（无论成功或失败）调用。

    参数:
        state: 应用状态实例
    """
    run_button_container = state.concat_run_button
    if run_button_container is not None:
        inner_button = run_button_container.content
        inner_button.disabled = False
        inner_button.content = ft.Text("开始拼接", size=15, weight=ft.FontWeight.W_600)
        inner_button.icon = ft.CupertinoIcons.PLAY_ARROW_SOLID
        state.page.update()