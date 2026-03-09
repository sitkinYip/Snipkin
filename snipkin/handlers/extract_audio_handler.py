"""
snipkin.handlers.extract_audio_handler - 音频提取的事件处理层（Flet 版）

本模块提供音频提取功能的所有事件处理函数，包括：
- on_input_file_picked:  输入文件选择完成后的回调处理
- on_output_file_picked: 输出路径选择完成后的回调处理
- handle_extract_run:    "开始提取"按钮点击处理

设计说明：
  所有函数接收 AppState 实例和 UI 控件引用作为参数，
  通过 state 读写应用状态，通过控件引用更新 UI 显示。
  核心的参数校验、ffmpeg 命令构建、命令执行逻辑由 snipkin.core.extract_audio_core 提供。
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import flet as ft

from snipkin.core.extract_audio_core import (
    build_extract_ffmpeg_command,
    execute_ffmpeg,
    generate_audio_output_path,
    validate_extract_params,
)

if TYPE_CHECKING:
    from snipkin.app import AppState

from snipkin.app import hide_loading, show_loading, show_toast


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


def on_input_file_picked(
    result: list,
    state: AppState,
    input_path_field: ft.TextField,
    output_path_field: ft.TextField,
) -> None:
    """
    处理输入文件选择完成后的回调。

    Flet 0.82+ 中 pick_files() 直接返回 list[FilePickerFile]。
    选择输入视频文件后：
      1. 更新输入文件路径显示
      2. 更新 state 中的路径值
      3. 调用 core 层生成默认输出路径
      4. 在日志中记录操作

    参数:
        result:            pick_files() 返回的文件列表
        state:             应用状态实例
        input_path_field:  输入文件路径 TextField 控件
        output_path_field: 输出文件路径 TextField 控件
    """
    if result and len(result) > 0:
        file_path = result[0].path
        state.input_file_path = file_path
        input_path_field.value = file_path
        _log(state, f"已选择输入文件：{file_path}")

        # 调用 core 层生成默认输出路径
        output_format = state.audio_output_format
        default_output = generate_audio_output_path(file_path, output_format)
        state.output_file_path = default_output
        output_path_field.value = default_output

        state.page.update()


def on_output_file_picked(
    result: str | None,
    state: AppState,
    output_path_field: ft.TextField,
) -> None:
    """
    处理输出路径选择完成后的回调。

    Flet 0.82+ 中 save_file() 直接返回 str | None。
    选择保存路径后更新输出文件路径显示和 state 中的值。

    参数:
        result:            save_file() 返回的文件路径字符串
        state:             应用状态实例
        output_path_field: 输出文件路径 TextField 控件
    """
    if result:
        state.output_file_path = result
        output_path_field.value = result
        _log(state, f"输出路径已设置：{result}")
        state.page.update()


def handle_extract_run(state: AppState) -> None:
    """
    处理"开始提取"按钮点击事件。

    执行流程：
      1. 从 state 和 UI 控件收集所有参数值
      2. 调用 core 层校验参数
      3. 调用 core 层构建 ffmpeg 命令
      4. 在子线程中调用 core 层执行命令

    参数:
        state: 应用状态实例
    """
    # ---- 从 state 收集参数 ----
    input_path = state.input_file_path.strip()
    output_path = state.output_file_path.strip()
    start_time = state.start_time
    end_time = state.end_time
    duration_value = state.duration_value
    duration_unit = state.duration_unit
    extract_full = state.audio_extract_full

    # ---- 调用 core 层校验参数 ----
    params, error = validate_extract_params(
        input_path=input_path,
        output_path=output_path,
        start_time=start_time,
        end_time=end_time,
        duration_value=duration_value,
        duration_unit=duration_unit,
        extract_full=extract_full,
    )
    if error:
        _log(state, error)
        _show_snackbar(state, error.replace("❌ 错误：", ""), "#FF3B30")
        return

    # 如果自动创建了输出目录，记录日志
    if params["output_dir_created"]:
        _log(state, f"已自动创建输出文件夹：{params['output_dir_created']}")

    # ---- 调用 core 层构建 ffmpeg 命令 ----
    command = build_extract_ffmpeg_command(
        input_path=input_path,
        output_path=output_path,
        start_seconds=params["start_seconds"],
        duration_seconds=params["duration_seconds"],
        output_format=state.audio_output_format,
        audio_bitrate=state.audio_quality,
        extract_full=extract_full,
    )

    _log(state, f"▶ 执行命令：{' '.join(command)}")

    # 禁用按钮，防止重复点击
    run_button_wrapper = state.audio_run_button
    if run_button_wrapper is not None:
        glow_container = run_button_wrapper.content
        inner_button = glow_container.content
        inner_button.disabled = True
        inner_button.content = ft.Text("处理中...", size=15, weight=ft.FontWeight.W_600)
        inner_button.icon = ft.CupertinoIcons.HOURGLASS
        state.page.update()

    # 显示 Loading 覆盖层
    show_loading(state, "正在提取音频...")

    # ---- 在子线程中调用 core 层执行命令 ----
    thread = threading.Thread(
        target=_run_extract_ffmpeg_in_thread,
        args=(state, command, output_path),
        daemon=True,
    )
    thread.start()


def _show_snackbar(state: AppState, message: str, color: str) -> None:
    """
    通过 show_toast 显示 SnackBar 通知。

    参数:
        state:   应用状态实例
        message: 通知消息文本
        color:   SnackBar 背景色
    """
    show_toast(state, message, color)


def _run_extract_ffmpeg_in_thread(
    state: AppState,
    command: list[str],
    output_path: str,
) -> None:
    """
    在子线程中执行提取 ffmpeg 命令。

    通过回调函数将 core 层的执行结果安全地反馈到 UI 层。
    成功或失败时通过 SnackBar 通知用户。

    参数:
        state:       应用状态实例
        command:     完整的 ffmpeg 命令参数列表
        output_path: 输出文件路径（用于成功日志）
    """
    def on_success():
        _log(state, f"提取成功！输出文件：{output_path}")
        _show_snackbar(state, f"✅ 提取成功！文件已保存", "#34C759")

    def on_error(message):
        _log(state, message)
        _show_snackbar(state, f"❌ 提取失败，请展开日志查看详情", "#FF3B30")

    execute_ffmpeg(
        command=command,
        on_log=lambda message: _log(state, message),
        on_success=on_success,
        on_error=on_error,
        on_complete=lambda: _restore_extract_run_button(state),
    )


def _restore_extract_run_button(state: AppState) -> None:
    """
    恢复提取按钮到可点击状态。

    在 ffmpeg 命令执行完成后（无论成功或失败）调用，
    将按钮文本和状态恢复为初始值，并隐藏 Loading 覆盖层。

    参数:
        state: 应用状态实例
    """
    hide_loading(state)
    run_button_wrapper = state.audio_run_button
    if run_button_wrapper is not None:
        glow_container = run_button_wrapper.content
        inner_button = glow_container.content
        inner_button.disabled = False
        inner_button.content = ft.Text("开始提取", size=15, weight=ft.FontWeight.W_600)
        inner_button.icon = ft.CupertinoIcons.PLAY_ARROW_SOLID
        state.page.update()
