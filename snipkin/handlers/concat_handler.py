"""
snipkin.handlers.concat_handler - 视频拼接的业务逻辑处理

本模块定义 ConcatHandlerMixin 类，以 Mixin 模式提供视频拼接功能的所有业务逻辑，包括：
- 文件列表管理（添加、移除、排序、清空）
- 输出路径选择事件处理
- 拼接参数校验（文件数量、文件存在性、过渡参数等）
- ffmpeg 拼接命令构建，支持三种策略：
    1. xfade 过渡动画拼接（带视频过渡效果 + 音频交叉淡入淡出）
    2. concat 滤镜拼接（无过渡 + 有压缩）
    3. concat demuxer 拼接（无过渡 + 无压缩，速度最快）
- ffmpeg 命令的子线程执行与结果回调

设计说明：
  本模块不包含任何 UI 构建代码，仅处理业务逻辑。
  通过 self 访问主窗口的状态变量和 UI 组件（由 VideoClipperApp 初始化）。
"""

import datetime
import os
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog

from snipkin.constants import (
    AUDIO_BITRATE_OPTIONS,
    COMPRESS_QUALITY_PRESETS,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
    VIDEO_FILE_TYPES,
    XFADE_TRANSITIONS,
)
from snipkin.utils import (
    check_ffmpeg_available,
    get_executable_path,
    get_video_duration,
)


class ConcatHandlerMixin:
    """
    视频拼接的业务逻辑 Mixin。

    提供拼接功能的文件管理、事件处理、参数校验、ffmpeg 命令构建与执行方法。
    混入 VideoClipperApp 后，通过 self 访问主窗口实例的属性和方法。
    """

    # ============================================================
    # 文件列表管理
    # ============================================================

    def _on_concat_add_files(self):
        """
        处理拼接 Tab "添加文件"按钮点击事件。

        弹出多选文件对话框，将选中的文件添加到拼接列表中（自动去重）。
        如果是首次添加文件且输出路径为空，自动生成默认输出路径。
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

            # 自动生成默认输出路径（基于第一个文件的目录）
            if self.concat_file_list and not self.concat_output_path.get():
                first_file = self.concat_file_list[0]
                directory = os.path.dirname(first_file)
                output_format = self.concat_output_format_var.get()
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                default_output = os.path.join(
                    directory, f"merged_output_{timestamp}.{output_format}",
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
          1. 校验 ffmpeg 可用性
          2. 校验文件列表（至少 2 个文件，且所有文件存在）
          3. 校验并创建输出目录
          4. 解析过渡动画参数（如有）
          5. 获取各视频时长（xfade 模式需要）
          6. 构建 ffmpeg 命令
          7. 在子线程中执行命令
        """
        # ---- 参数校验 ----
        if not check_ffmpeg_available():
            self._log("❌ 错误: 未检测到 ffmpeg，请先安装。")
            return

        if len(self.concat_file_list) < 2:
            self._log("❌ 错误: 请至少添加 2 个视频文件进行拼接。")
            return

        for file_path in self.concat_file_list:
            if not os.path.isfile(file_path):
                self._log(f"❌ 错误: 文件不存在: {file_path}")
                return

        output_path = self.concat_output_path.get().strip()
        if not output_path:
            self._log("❌ 错误: 请先设置输出文件保存路径。")
            return

        # 自动创建不存在的输出目录
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
                self._log(f"已自动创建输出文件夹: {out_dir}")
            except Exception as error:
                self._log(f"❌ 错误: 无法创建输出文件夹: {error}")
                return

        # 解析过渡动画参数
        transition_name = XFADE_TRANSITIONS[self.concat_transition_var.get()]
        transition_duration = 0.0
        if transition_name:
            try:
                transition_duration = float(
                    self.concat_transition_duration_var.get().strip(),
                )
                if transition_duration <= 0:
                    raise ValueError("过渡时长必须大于 0")
            except ValueError:
                self._log("❌ 错误: 过渡时长必须是一个正数（秒）。")
                return

        # 获取每个视频的时长（xfade 需要知道每段视频的时长来计算 offset）
        if transition_name:
            self._log("⏳ 正在获取视频时长信息...")
            durations = []
            for file_path in self.concat_file_list:
                duration = get_video_duration(file_path)
                if duration is None:
                    self._log(
                        f"❌ 错误: 无法获取视频时长: {os.path.basename(file_path)}，"
                        f"请确保 ffprobe 可用。",
                    )
                    return
                durations.append(duration)
                self._log(f"  📎 {os.path.basename(file_path)}: {duration:.2f}s")
        else:
            durations = []

        # ---- 构建 ffmpeg 命令 ----
        command = self._build_concat_ffmpeg_command(
            file_list=self.concat_file_list,
            output_path=output_path,
            transition_name=transition_name,
            transition_duration=transition_duration,
            durations=durations,
        )

        self._log(f"▶ 执行命令: {' '.join(command)}")

        # 禁用按钮，防止重复点击
        self.concat_run_button.configure(state="disabled", text="⏳ 处理中...")

        # 在子线程中执行
        thread = threading.Thread(
            target=self._execute_concat_ffmpeg, args=(command,), daemon=True,
        )
        thread.start()

    # ============================================================
    # 拼接命令构建
    # ============================================================

    def _build_concat_ffmpeg_command(
        self,
        file_list: list[str],
        output_path: str,
        transition_name: str | None,
        transition_duration: float,
        durations: list[float],
    ) -> list[str]:
        """
        构建视频拼接的 ffmpeg 命令（策略分发入口）。

        根据用户的设置自动选择最优的拼接策略：
          - 有过渡动画 → 使用 xfade 滤镜链（必须转码）
          - 无过渡 + 有压缩 → 使用 concat 滤镜（转码，可调参数）
          - 无过渡 + 无压缩 → 使用 concat demuxer（流复制，速度最快）

        参数:
            file_list:            输入视频文件路径列表
            output_path:          输出文件路径
            transition_name:      过渡效果名称（None 表示无过渡）
            transition_duration:  过渡时长（秒）
            durations:            各视频的时长列表（xfade 模式需要）

        返回:
            完整的 ffmpeg 命令参数列表
        """
        if transition_name:
            return self._build_xfade_command(
                file_list, output_path, transition_name,
                transition_duration, durations,
            )
        elif self.concat_compress_enabled_var.get():
            return self._build_concat_filter_command(file_list, output_path)
        else:
            return self._build_concat_demuxer_command(file_list, output_path)

    def _build_xfade_command(
        self,
        file_list: list[str],
        output_path: str,
        transition_name: str,
        transition_duration: float,
        durations: list[float],
    ) -> list[str]:
        """
        使用 xfade 滤镜构建带过渡动画的拼接命令。

        工作原理：
          每两段视频之间插入一个 xfade 视频过渡和一个 acrossfade 音频过渡。
          通过链式连接多个 xfade 滤镜实现多段视频的连续过渡。
          offset 的计算公式：前面所有视频总时长 - 前面所有过渡占用的时长 - 当前过渡时长。

        参数:
            file_list:            输入视频文件路径列表
            output_path:          输出文件路径
            transition_name:      xfade 过渡效果名称
            transition_duration:  过渡时长（秒）
            durations:            各视频的时长列表

        返回:
            完整的 ffmpeg 命令参数列表
        """
        file_count = len(file_list)

        # 输入文件参数
        command = [get_executable_path("ffmpeg"), "-y"]
        for file_path in file_list:
            command.extend(["-i", file_path])

        # 构建 xfade 视频滤镜链和 acrossfade 音频滤镜链
        video_filter_parts = []
        audio_filter_parts = []

        for i in range(file_count - 1):
            # 确定当前过渡的输入标签
            if i == 0:
                video_input_a = "[0:v]"
                audio_input_a = "[0:a]"
            else:
                video_input_a = f"[vfade{i}]"
                audio_input_a = f"[afade{i}]"

            video_input_b = f"[{i + 1}:v]"
            audio_input_b = f"[{i + 1}:a]"

            # 计算过渡偏移量
            cumulative_offset = (
                sum(durations[:i + 1])
                - i * transition_duration
                - transition_duration
            )
            if cumulative_offset < 0:
                cumulative_offset = 0

            # 确定输出标签（最后一个过渡输出到最终标签）
            if i < file_count - 2:
                video_output = f"[vfade{i + 1}]"
                audio_output = f"[afade{i + 1}]"
            else:
                video_output = "[vout]"
                audio_output = "[aout]"

            video_filter_parts.append(
                f"{video_input_a}{video_input_b}xfade=transition={transition_name}"
                f":duration={transition_duration}:offset={cumulative_offset:.3f}"
                f"{video_output}",
            )
            audio_filter_parts.append(
                f"{audio_input_a}{audio_input_b}acrossfade="
                f"d={transition_duration}{audio_output}",
            )

        # 如果启用了压缩的高级选项（分辨率/帧率），追加到滤镜链末尾
        extra_video_filters = []
        if self.concat_compress_enabled_var.get():
            extra_video_filters = self._build_concat_video_filters()

        if extra_video_filters:
            # 将 [vout] 改为中间标签，追加 scale/fps 滤镜后再输出 [vout]
            filter_complex = ";".join(video_filter_parts + audio_filter_parts)
            filter_complex = filter_complex.replace("[vout]", "[vpre]", 1)
            extra_chain = f"[vpre]{','.join(extra_video_filters)}[vout]"
            filter_complex = filter_complex + ";" + extra_chain
        else:
            filter_complex = ";".join(video_filter_parts + audio_filter_parts)

        command.extend(["-filter_complex", filter_complex])
        command.extend(["-map", "[vout]", "-map", "[aout]"])

        # 添加编码参数（xfade 必须转码）
        if self.concat_compress_enabled_var.get():
            crf_value = COMPRESS_QUALITY_PRESETS[self.concat_compress_quality_var.get()]
            command.extend([
                "-c:v", "libx264", "-crf", str(crf_value), "-preset", "medium",
            ])
            audio_bitrate = AUDIO_BITRATE_OPTIONS[self.concat_audio_bitrate_var.get()]
            if audio_bitrate:
                command.extend(["-b:a", audio_bitrate])
            else:
                command.extend(["-c:a", "aac"])
        else:
            command.extend([
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            ])
            command.extend(["-c:a", "aac"])

        command.append(output_path)
        return command

    def _build_concat_filter_command(
        self, file_list: list[str], output_path: str,
    ) -> list[str]:
        """
        使用 concat 滤镜构建拼接命令（无过渡动画 + 有压缩）。

        通过 ffmpeg 的 concat 滤镜将多个输入流合并为一个，
        然后使用 libx264 编码输出，支持自定义分辨率/帧率/音频码率。

        参数:
            file_list:   输入视频文件路径列表
            output_path: 输出文件路径

        返回:
            完整的 ffmpeg 命令参数列表
        """
        file_count = len(file_list)

        command = [get_executable_path("ffmpeg"), "-y"]
        for file_path in file_list:
            command.extend(["-i", file_path])

        # concat 滤镜 + 可选的 scale/fps 滤镜（合并到 filter_complex 中）
        input_labels = "".join(f"[{i}:v][{i}:a]" for i in range(file_count))
        video_filters = self._build_concat_video_filters()

        if video_filters:
            # 有额外滤镜时：concat 输出到中间标签，再追加 scale/fps
            filter_complex = (
                f"{input_labels}concat=n={file_count}:v=1:a=1[vpre][aout];"
                f"[vpre]{','.join(video_filters)}[vout]"
            )
        else:
            filter_complex = (
                f"{input_labels}concat=n={file_count}:v=1:a=1[vout][aout]"
            )

        command.extend(["-filter_complex", filter_complex])
        command.extend(["-map", "[vout]", "-map", "[aout]"])

        # 压缩参数
        crf_value = COMPRESS_QUALITY_PRESETS[self.concat_compress_quality_var.get()]
        command.extend([
            "-c:v", "libx264", "-crf", str(crf_value), "-preset", "medium",
        ])

        audio_bitrate = AUDIO_BITRATE_OPTIONS[self.concat_audio_bitrate_var.get()]
        if audio_bitrate:
            command.extend(["-b:a", audio_bitrate])
        else:
            command.extend(["-c:a", "aac"])

        command.append(output_path)
        return command

    def _build_concat_demuxer_command(
        self, file_list: list[str], output_path: str,
    ) -> list[str]:
        """
        使用 concat demuxer 构建拼接命令（无过渡动画 + 无压缩）。

        这是最快的拼接方式，通过 concat demuxer 直接流复制，
        不进行任何转码，因此无质量损失。
        通过临时文件列表传递输入文件路径给 ffmpeg。

        参数:
            file_list:   输入视频文件路径列表
            output_path: 输出文件路径

        返回:
            完整的 ffmpeg 命令参数列表
        """
        concat_list_content = "\n".join(
            f"file '{file_path}'" for file_path in file_list
        )
        # 创建临时文件（在 _execute_concat_ffmpeg 完成后清理）
        self._concat_temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="snipkin_concat_",
        )
        self._concat_temp_file.write(concat_list_content)
        self._concat_temp_file.close()

        command = [
            get_executable_path("ffmpeg"), "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", self._concat_temp_file.name,
            "-c", "copy",
            output_path,
        ]
        return command

    def _build_concat_video_filters(self) -> list[str]:
        """
        根据拼接 Tab 的高级选项构建视频滤镜列表。

        与截取 Tab 的 _build_video_filters 功能相同，
        但读取的是拼接 Tab 独立的状态变量（concat_ 前缀）。

        返回:
            滤镜字符串列表，为空表示不需要额外滤镜
        """
        filters = []

        scale_value = RESOLUTION_OPTIONS[self.concat_resolution_var.get()]
        if scale_value:
            filters.append(f"scale={scale_value}")

        fps_value = FRAMERATE_OPTIONS[self.concat_framerate_var.get()]
        if fps_value:
            filters.append(f"fps={fps_value}")

        return filters

    # ============================================================
    # 拼接命令执行
    # ============================================================

    def _execute_concat_ffmpeg(self, command: list[str]):
        """
        在子线程中执行拼接 ffmpeg 命令。

        执行完成后通过 _log_threadsafe 将结果写入日志，
        并通过 after(0, callback) 在主线程中恢复按钮状态。
        最后清理 concat demuxer 模式下创建的临时文件。

        参数:
            command: 完整的 ffmpeg 命令参数列表
        """
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1800,  # 拼接可能较慢，最长等待 30 分钟
            )

            if process.returncode == 0:
                output_path = self.concat_output_path.get()
                self._log_threadsafe(f"✅ 拼接成功！输出文件: {output_path}")
            else:
                error_message = (
                    process.stderr.strip() if process.stderr else "未知错误"
                )
                self._log_threadsafe(
                    f"❌ ffmpeg 拼接失败 (返回码 {process.returncode}):\n{error_message}",
                )

        except subprocess.TimeoutExpired:
            self._log_threadsafe("❌ 错误: ffmpeg 执行超时（超过 30 分钟），已终止。")
        except FileNotFoundError:
            self._log_threadsafe("❌ 错误: 无法找到 ffmpeg 可执行文件。")
        except Exception as unexpected_error:
            self._log_threadsafe(f"❌ 发生意外错误: {unexpected_error}")
        finally:
            # 恢复按钮状态（必须在主线程中操作 UI）
            self.after(
                0,
                lambda: self.concat_run_button.configure(
                    state="normal", text="🚀 开始拼接",
                ),
            )
            # 清理临时文件（concat demuxer 模式下创建的）
            if hasattr(self, "_concat_temp_file") and self._concat_temp_file:
                try:
                    os.unlink(self._concat_temp_file.name)
                except OSError:
                    pass
