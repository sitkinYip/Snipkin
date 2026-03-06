"""
snipkin.handlers.concat_handler - 视频拼接的 UI 事件处理层

本模块定义 ConcatHandlerMixin 类，以 Mixin 模式提供视频拼接功能的 UI 事件处理，包括：
- 文件列表管理（添加、移除、排序、清空 — 操作 Tkinter Listbox）
- 输出路径选择事件处理（弹出对话框、更新 UI 状态）
- "开始拼接"按钮点击：从 UI 收集参数 → 调用 core 层校验与构建 → 子线程执行

设计说明：
  本模块是 UI 框架（CustomTkinter）与核心逻辑（snipkin.core.concat_core）之间的桥梁。
  核心的参数校验、ffmpeg 命令构建、命令执行逻辑已抽取到 snipkin.core.concat_core 中，
  本模块仅负责：
    1. 从 UI 组件（StringVar / BooleanVar / Listbox）收集参数值
    2. 调用 core 层的纯函数
    3. 将结果反馈到 UI（日志、按钮状态、列表刷新等）
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog

from snipkin.constants import VIDEO_FILE_TYPES
from snipkin.core.concat_core import (
    build_concat_ffmpeg_command,
    execute_concat_ffmpeg,
    generate_concat_output_path,
    validate_concat_params,
)

class ConcatHandlerMixin:
    """
    视频拼接的 UI 事件处理 Mixin。

    作为 UI 层与 core 层之间的桥梁，负责从 UI 收集参数、
    调用 core 层纯函数、并将结果反馈到 UI。
    混入 VideoClipperApp 后，通过 self 访问主窗口实例的属性和方法。
    """

    # ============================================================
    # 文件列表管理
    # ============================================================

    def _on_concat_add_files(self):
        """
        处理拼接 Tab "添加文件"按钮点击事件。

        弹出多选文件对话框，将选中的文件添加到拼接列表中（自动去重）。
        如果是首次添加文件且输出路径为空，调用 core 层自动生成默认输出路径。
        """
        file_paths = filedialog.askopenfilenames(
            title="选择要拼接的视频文件（可多选）",
            filetypes=VIDEO_FILE_TYPES,
        )
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.concat_file_list:
                    self.concat_file_list.append(file_path)
            self._refresh_concat_listbox()
            self._log(
                f"已添加 {len(file_paths)} 个文件，"
                f"当前共 {len(self.concat_file_list)} 个",
            )

            # 调用 core 层生成默认输出路径
            if self.concat_file_list and not self.concat_output_path.get():
                output_format = self.concat_output_format_var.get()
                default_output = generate_concat_output_path(
                    self.concat_file_list[0], output_format,
                )
                self.concat_output_path.set(default_output)

    def _on_concat_remove_file(self):
        """移除拼接列表中当前选中的文件"""
        selection = self.concat_listbox.curselection()
        if not selection:
            self._log("⚠️ 请先在列表中选中要移除的文件。")
            return
        index = selection[0]
        removed_file = self.concat_file_list.pop(index)
        self._refresh_concat_listbox()
        self._log(f"已移除: {os.path.basename(removed_file)}")

    def _on_concat_move_up(self):
        """将选中的文件在列表中上移一位，用于调整拼接顺序"""
        selection = self.concat_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index <= 0:
            return
        self.concat_file_list[index], self.concat_file_list[index - 1] = (
            self.concat_file_list[index - 1], self.concat_file_list[index],
        )
        self._refresh_concat_listbox()
        self.concat_listbox.selection_set(index - 1)

    def _on_concat_move_down(self):
        """将选中的文件在列表中下移一位，用于调整拼接顺序"""
        selection = self.concat_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(self.concat_file_list) - 1:
            return
        self.concat_file_list[index], self.concat_file_list[index + 1] = (
            self.concat_file_list[index + 1], self.concat_file_list[index],
        )
        self._refresh_concat_listbox()
        self.concat_listbox.selection_set(index + 1)

    def _on_concat_clear_files(self):
        """清空拼接文件列表"""
        self.concat_file_list.clear()
        self._refresh_concat_listbox()
        self._log("已清空文件列表。")

    def _refresh_concat_listbox(self):
        """
        刷新拼接文件列表的显示内容。

        清空 Listbox 后重新插入所有文件，显示格式为 "序号. 文件名"。
        """
        self.concat_listbox.delete(0, tk.END)
        for index, file_path in enumerate(self.concat_file_list):
            display_name = f"{index + 1}. {os.path.basename(file_path)}"
            self.concat_listbox.insert(tk.END, display_name)

    # ============================================================
    # 输出路径选择
    # ============================================================

    def _on_concat_select_output(self):
        """
        处理拼接 Tab "保存路径"按钮点击事件。

        弹出文件保存对话框，智能记忆当前输入框中的路径作为初始目录和文件名。
        """
        output_format = self.concat_output_format_var.get()
        current_path = self.concat_output_path.get().strip()
        initial_dir = os.path.dirname(current_path) if current_path else None
        initial_file = os.path.basename(current_path) if current_path else None

        file_path = filedialog.asksaveasfilename(
            title="选择拼接输出文件保存位置",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=f".{output_format}",
            filetypes=[
                (f"{output_format.upper()} 文件", f"*.{output_format}"),
                ("所有文件", "*.*"),
            ],
        )
        if file_path:
            self.concat_output_path.set(file_path)
            self._log(f"拼接输出路径已设置: {file_path}")

    # ============================================================
    # 拼接执行入口
    # ============================================================

    def _on_concat_run(self):
        """
        处理"开始拼接"按钮点击事件。

        执行流程：
          1. 从 UI 收集所有参数值
          2. 调用 core 层校验参数（含获取视频时长）
          3. 调用 core 层构建 ffmpeg 命令
          4. 在子线程中调用 core 层执行命令
        """
        # ---- 从 UI 收集参数 ----
        output_path = self.concat_output_path.get().strip()
        transition_display_name = self.concat_transition_var.get()
        transition_duration_str = self.concat_transition_duration_var.get()

        # ---- 调用 core 层校验参数 ----
        params, error = validate_concat_params(
            file_list=self.concat_file_list,
            output_path=output_path,
            transition_display_name=transition_display_name,
            transition_duration_str=transition_duration_str,
        )
        if error:
            self._log(error)
            return

        # 如果自动创建了输出目录，记录日志
        if params["output_dir_created"]:
            self._log(f"已自动创建输出文件夹: {params['output_dir_created']}")

        # 如果有过渡动画，输出各视频时长信息
        if params["durations"]:
            self._log("⏳ 已获取视频时长信息:")
            for file_path, duration in zip(self.concat_file_list, params["durations"]):
                self._log(f"  📎 {os.path.basename(file_path)}: {duration:.2f}s")

        # ---- 调用 core 层构建 ffmpeg 命令 ----
        command, temp_file_path = build_concat_ffmpeg_command(
            file_list=self.concat_file_list,
            output_path=output_path,
            transition_name=params["transition_name"],
            transition_duration=params["transition_duration"],
            durations=params["durations"],
            resolutions=params.get("resolutions", []),
            compress_enabled=self.concat_compress_enabled_var.get(),
            quality_preset=self.concat_compress_quality_var.get(),
            resolution=self.concat_resolution_var.get(),
            framerate=self.concat_framerate_var.get(),
            audio_bitrate=self.concat_audio_bitrate_var.get(),
        )

        self._log(f"▶ 执行命令: {' '.join(command)}")

        # 禁用按钮，防止重复点击
        self.concat_run_button.configure(state="disabled", text="⏳ 处理中...")

        # ---- 在子线程中调用 core 层执行命令 ----
        thread = threading.Thread(
            target=self._run_concat_ffmpeg_in_thread,
            args=(command, output_path, temp_file_path),
            daemon=True,
        )
        thread.start()

    def _run_concat_ffmpeg_in_thread(
        self,
        command: list[str],
        output_path: str,
        temp_file_path: str | None,
    ):
        """
        在子线程中执行拼接 ffmpeg 命令。

        通过回调函数将 core 层的执行结果安全地反馈到 UI 层。

        参数:
            command:        完整的 ffmpeg 命令参数列表
            output_path:    输出文件路径（用于成功日志）
            temp_file_path: concat demuxer 模式的临时文件路径（可选，用于清理）
        """
        execute_concat_ffmpeg(
            command=command,
            on_log=self._log_threadsafe,
            on_success=lambda: self._log_threadsafe(
                f"✅ 拼接成功！输出文件: {output_path}",
            ),
            on_error=self._log_threadsafe,
            on_complete=lambda: self.after(
                0,
                lambda: self.concat_run_button.configure(
                    state="normal", text="🚀 开始拼接",
                ),
            ),
            temp_file_path=temp_file_path,
        )