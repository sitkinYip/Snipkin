"""
snipkin.handlers.clip_handler - 视频截取的 UI 事件处理层

本模块定义 ClipHandlerMixin 类，以 Mixin 模式提供视频截取功能的 UI 事件处理，包括：
- 输入文件选择事件处理（弹出对话框、更新 UI 状态）
- 输出路径选择事件处理
- "开始截取"按钮点击：从 UI 收集参数 → 调用 core 层校验与构建 → 子线程执行

设计说明：
  本模块是 UI 框架（CustomTkinter）与核心逻辑（snipkin.core.clip_core）之间的桥梁。
  核心的参数校验、ffmpeg 命令构建、命令执行逻辑已抽取到 snipkin.core.clip_core 中，
  本模块仅负责：
    1. 从 UI 组件（StringVar / BooleanVar）收集参数值
    2. 调用 core 层的纯函数
    3. 将结果反馈到 UI（日志、按钮状态等）
"""

import os
import threading
from tkinter import filedialog

from snipkin.constants import VIDEO_FILE_TYPES
from snipkin.core.clip_core import (
    build_clip_ffmpeg_command,
    execute_ffmpeg,
    generate_clip_output_path,
    validate_clip_params,
)

class ClipHandlerMixin:
    """
    视频截取的 UI 事件处理 Mixin。

    作为 UI 层与 core 层之间的桥梁，负责从 UI 收集参数、
    调用 core 层纯函数、并将结果反馈到 UI。
    混入 VideoClipperApp 后，通过 self 访问主窗口实例的属性和方法。
    """

    # ============================================================
    # 截取 Tab 事件处理
    # ============================================================

    def _on_select_input_file(self):
        """
        处理截取 Tab "选择文件"按钮点击事件。

        弹出文件选择对话框，选择输入视频文件后：
          1. 更新输入文件路径显示
          2. 调用 core 层生成默认输出路径
          3. 在日志中记录操作
        """
        file_path = filedialog.askopenfilename(
            title="选择输入视频文件",
            filetypes=VIDEO_FILE_TYPES,
        )
        if file_path:
            self.input_file_path.set(file_path)
            self._log(f"已选择输入文件: {file_path}")

            # 调用 core 层生成默认输出路径
            output_format = self.output_format_var.get()
            default_output = generate_clip_output_path(file_path, output_format)
            self.output_file_path.set(default_output)

    def _on_select_output_file(self):
        """
        处理截取 Tab "保存路径"按钮点击事件。

        弹出文件保存对话框，智能记忆当前输入框中的路径作为初始目录和文件名。
        """
        output_format = self.output_format_var.get()
        current_path = self.output_file_path.get().strip()
        initial_dir = os.path.dirname(current_path) if current_path else None
        initial_file = os.path.basename(current_path) if current_path else None

        file_path = filedialog.asksaveasfilename(
            title="选择输出文件保存位置",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=f".{output_format}",
            filetypes=[
                (f"{output_format.upper()} 文件", f"*.{output_format}"),
                ("所有文件", "*.*"),
            ],
        )
        if file_path:
            self.output_file_path.set(file_path)
            self._log(f"输出路径已设置: {file_path}")

    def _on_run(self):
        """
        处理"开始截取"按钮点击事件。

        执行流程：
          1. 从 UI 收集所有参数值
          2. 调用 core 层校验参数
          3. 调用 core 层构建 ffmpeg 命令
          4. 在子线程中调用 core 层执行命令
        """
        # ---- 从 UI 收集参数 ----
        input_path = self.input_file_path.get().strip()
        output_path = self.output_file_path.get().strip()
        start_time = self.start_time_var.get()
        end_time = self.end_time_var.get()
        duration_value = self.duration_value_var.get()
        duration_unit = self.duration_unit_var.get()

        # ---- 调用 core 层校验参数 ----
        params, error = validate_clip_params(
            input_path=input_path,
            output_path=output_path,
            start_time=start_time,
            end_time=end_time,
            duration_value=duration_value,
            duration_unit=duration_unit,
        )
        if error:
            self._log(error)
            return

        # 如果自动创建了输出目录，记录日志
        if params["output_dir_created"]:
            self._log(f"已自动创建输出文件夹: {params['output_dir_created']}")

        # ---- 调用 core 层构建 ffmpeg 命令 ----
        command = build_clip_ffmpeg_command(
            input_path=input_path,
            output_path=output_path,
            start_seconds=params["start_seconds"],
            duration_seconds=params["duration_seconds"],
            output_format=self.output_format_var.get(),
            compress_enabled=self.compress_enabled_var.get(),
            quality_preset=self.compress_quality_var.get(),
            resolution=self.resolution_var.get(),
            framerate=self.framerate_var.get(),
            audio_bitrate=self.audio_bitrate_var.get(),
        )

        self._log(f"▶ 执行命令: {' '.join(command)}")

        # 禁用按钮，防止重复点击
        self.run_button.configure(state="disabled", text="⏳ 处理中...")

        # ---- 在子线程中调用 core 层执行命令 ----
        thread = threading.Thread(
            target=self._run_clip_ffmpeg_in_thread,
            args=(command, output_path),
            daemon=True,
        )
        thread.start()

    def _run_clip_ffmpeg_in_thread(self, command: list[str], output_path: str):
        """
        在子线程中执行截取 ffmpeg 命令。

        通过回调函数将 core 层的执行结果安全地反馈到 UI 层。

        参数:
            command:     完整的 ffmpeg 命令参数列表
            output_path: 输出文件路径（用于成功日志）
        """
        execute_ffmpeg(
            command=command,
            on_log=self._log_threadsafe,
            on_success=lambda: self._log_threadsafe(
                f"✅ 截取成功！输出文件: {output_path}",
            ),
            on_error=self._log_threadsafe,
            on_complete=lambda: self.after(
                0,
                lambda: self.run_button.configure(
                    state="normal", text="🚀 开始截取",
                ),
            ),
        )