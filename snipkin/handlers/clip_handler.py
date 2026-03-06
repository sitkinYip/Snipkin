"""
snipkin.handlers.clip_handler - 视频截取的业务逻辑处理

本模块定义 ClipHandlerMixin 类，以 Mixin 模式提供视频截取功能的所有业务逻辑，包括：
- 输入文件选择事件处理
- 输出路径选择事件处理
- 截取参数校验（文件存在性、时间格式、路径合法性等）
- ffmpeg 截取命令构建（支持流复制 / 压缩转码 / GIF 导出）
- 视频滤镜构建（分辨率缩放 + 帧率限制）
- ffmpeg 命令的子线程执行与结果回调

设计说明：
  本模块不包含任何 UI 构建代码，仅处理业务逻辑。
  通过 self 访问主窗口的状态变量和 UI 组件（由 VideoClipperApp 初始化）。
  ffmpeg 命令在子线程中执行，通过 _log_threadsafe 安全写入日志。
"""

import datetime
import os
import subprocess
import threading
from tkinter import filedialog

from snipkin.constants import (
    AUDIO_BITRATE_OPTIONS,
    COMPRESS_QUALITY_PRESETS,
    DURATION_UNITS,
    FORMATS_REQUIRING_TRANSCODE,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
    VIDEO_FILE_TYPES,
)
from snipkin.utils import (
    check_ffmpeg_available,
    format_seconds_to_timecode,
    get_executable_path,
    parse_timecode_to_seconds,
)


class ClipHandlerMixin:
    """
    视频截取的业务逻辑 Mixin。

    提供截取功能的事件处理、参数校验、ffmpeg 命令构建与执行方法。
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
          2. 自动根据输入文件名和当前时间戳生成默认输出路径
          3. 在日志中记录操作
        """
        file_path = filedialog.askopenfilename(
            title="选择输入视频文件",
            filetypes=VIDEO_FILE_TYPES,
        )
        if file_path:
            self.input_file_path.set(file_path)
            self._log(f"已选择输入文件: {file_path}")

            # 自动根据输入文件名生成默认输出路径
            directory = os.path.dirname(file_path)
            basename = os.path.splitext(os.path.basename(file_path))[0]
            output_format = self.output_format_var.get()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_output = os.path.join(
                directory, f"{basename}_clip_{timestamp}.{output_format}",
            )
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
          1. 校验 ffmpeg 可用性
          2. 校验输入文件存在性
          3. 校验并创建输出目录
          4. 解析开始时间和结束时间/持续时长
          5. 构建 ffmpeg 命令
          6. 在子线程中执行命令
        """
        # ---- 参数校验 ----
        if not check_ffmpeg_available():
            self._log("❌ 错误: 未检测到 ffmpeg，请先安装。")
            return

        input_path = self.input_file_path.get().strip()
        if not input_path or not os.path.isfile(input_path):
            self._log("❌ 错误: 请先选择一个有效的输入视频文件。")
            return

        output_path = self.output_file_path.get().strip()
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

        # 解析开始时间（支持 H:MM:SS / MM:SS / 秒数 格式）
        try:
            start_seconds = parse_timecode_to_seconds(self.start_time_var.get())
            if start_seconds < 0:
                raise ValueError("开始时间不能为负数")
        except ValueError as error:
            self._log(f"❌ 错误: 开始时间格式无效（支持 H:MM:SS / MM:SS / 秒数）。{error}")
            return

        # 优先使用结束时间，否则使用持续时长
        end_time_text = self.end_time_var.get().strip()
        if end_time_text:
            # 用户填写了结束时间，计算持续时长
            try:
                end_seconds = parse_timecode_to_seconds(end_time_text)
                if end_seconds <= start_seconds:
                    self._log("❌ 错误: 结束时间必须大于开始时间。")
                    return
                duration_seconds = end_seconds - start_seconds
            except ValueError as error:
                self._log(f"❌ 错误: 结束时间格式无效。{error}")
                return
        else:
            # 使用持续时长
            try:
                duration_value = float(self.duration_value_var.get())
                if duration_value <= 0:
                    raise ValueError("持续时长必须大于 0")
            except ValueError:
                self._log("❌ 错误: 持续时长必须是一个正数。")
                return

            unit_multiplier = DURATION_UNITS[self.duration_unit_var.get()]
            duration_seconds = duration_value * unit_multiplier

        # ---- 构建 ffmpeg 命令 ----
        command = self._build_clip_ffmpeg_command(
            input_path=input_path,
            output_path=output_path,
            start_seconds=start_seconds,
            duration_seconds=duration_seconds,
        )

        self._log(f"▶ 执行命令: {' '.join(command)}")

        # 禁用按钮，防止重复点击
        self.run_button.configure(state="disabled", text="⏳ 处理中...")

        # 在子线程中执行 ffmpeg
        thread = threading.Thread(
            target=self._execute_ffmpeg, args=(command,), daemon=True,
        )
        thread.start()

    # ============================================================
    # 截取核心逻辑
    # ============================================================

    def _build_clip_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        duration_seconds: float,
    ) -> list[str]:
        """
        构建视频截取的 ffmpeg 命令。

        根据用户选择的压缩设置和输出格式，决定使用以下策略之一：
          - 需要转码的格式（如 GIF）：强制使用转码
          - 启用压缩：使用 libx264 编码 + CRF 质量控制 + 可选滤镜
          - 不压缩：使用流复制（-c copy），速度最快，无质量损失

        参数:
            input_path:       输入视频文件路径
            output_path:      输出文件路径
            start_seconds:    截取开始时间（秒）
            duration_seconds: 截取持续时长（秒）

        返回:
            完整的 ffmpeg 命令参数列表
        """
        start_timecode = format_seconds_to_timecode(start_seconds)
        duration_timecode = format_seconds_to_timecode(duration_seconds)

        command = [
            get_executable_path("ffmpeg"), "-y",
            "-ss", start_timecode,
            "-i", input_path,
            "-t", duration_timecode,
        ]

        output_format = self.output_format_var.get()
        needs_transcode = output_format in FORMATS_REQUIRING_TRANSCODE
        compress_enabled = self.compress_enabled_var.get()

        if needs_transcode or compress_enabled:
            # 需要转码：添加编码参数
            if output_format != "gif":
                crf_value = COMPRESS_QUALITY_PRESETS[self.compress_quality_var.get()]
                command.extend([
                    "-c:v", "libx264",
                    "-crf", str(crf_value),
                    "-preset", "medium",
                ])

            # 添加视频滤镜（分辨率缩放 + 帧率限制）
            video_filters = self._build_video_filters()
            if video_filters:
                command.extend(["-vf", ",".join(video_filters)])

            # 音频码率设置
            audio_bitrate = AUDIO_BITRATE_OPTIONS[self.audio_bitrate_var.get()]
            if audio_bitrate:
                command.extend(["-b:a", audio_bitrate])
            else:
                command.extend(["-c:a", "aac"])
        else:
            # 不压缩：流复制（速度最快，无质量损失）
            command.extend(["-c", "copy"])

        command.append(output_path)
        return command

    def _build_video_filters(self) -> list[str]:
        """
        根据高级选项构建视频滤镜列表。

        支持的滤镜：
          - scale: 分辨率缩放（如 1920:-1 表示宽度 1920，高度按比例自适应）
          - fps:   帧率限制（如 fps=30 表示限制为 30fps）

        多个滤镜可以叠加使用，通过逗号连接传给 ffmpeg 的 -vf 参数。

        返回:
            滤镜字符串列表，为空表示不需要额外滤镜
        """
        filters = []

        # 分辨率缩放
        scale_value = RESOLUTION_OPTIONS[self.resolution_var.get()]
        if scale_value:
            filters.append(f"scale={scale_value}")

        # 帧率限制
        fps_value = FRAMERATE_OPTIONS[self.framerate_var.get()]
        if fps_value:
            filters.append(f"fps={fps_value}")

        return filters

    def _execute_ffmpeg(self, command: list[str]):
        """
        在子线程中执行 ffmpeg 命令。

        执行完成后通过 _log_threadsafe 将结果写入日志，
        并通过 after(0, callback) 在主线程中恢复按钮状态。

        参数:
            command: 完整的 ffmpeg 命令参数列表
        """
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600,  # 最长等待 10 分钟
            )

            if process.returncode == 0:
                output_path = self.output_file_path.get()
                self._log_threadsafe(f"✅ 截取成功！输出文件: {output_path}")
            else:
                # ffmpeg 的错误信息通常输出到 stderr
                error_message = process.stderr.strip() if process.stderr else "未知错误"
                self._log_threadsafe(
                    f"❌ ffmpeg 执行失败 (返回码 {process.returncode}):\n{error_message}",
                )

        except subprocess.TimeoutExpired:
            self._log_threadsafe("❌ 错误: ffmpeg 执行超时（超过 10 分钟），已终止。")
        except FileNotFoundError:
            self._log_threadsafe("❌ 错误: 无法找到 ffmpeg 可执行文件。")
        except Exception as unexpected_error:
            self._log_threadsafe(f"❌ 发生意外错误: {unexpected_error}")
        finally:
            # 恢复按钮状态（必须在主线程中操作 UI）
            self.after(
                0,
                lambda: self.run_button.configure(state="normal", text="🚀 开始截取"),
            )
