"""
snipkin.core.clip_core - 视频截取的核心业务逻辑（UI 无关）

本模块提供视频截取功能的所有纯逻辑函数，包括：
- generate_clip_output_path:   根据输入文件自动生成带时间戳的默认输出路径
- validate_clip_params:        校验截取参数（文件存在性、时间格式、路径合法性）
- build_clip_ffmpeg_command:   构建 ffmpeg 截取命令
- build_video_filters:         构建视频滤镜列表（分辨率 + 帧率）
- execute_ffmpeg:              在当前线程中执行 ffmpeg 命令并通过回调通知结果

设计说明：
  所有函数只接收普通 Python 类型参数，不依赖任何 UI 框架。
  调用方（UI 层）负责从界面收集参数、调用这些函数、并将结果反馈到界面。
"""

import datetime
import os
import subprocess
from typing import Callable

from snipkin.constants import (
    AUDIO_BITRATE_OPTIONS,
    COMPRESS_QUALITY_PRESETS,
    DURATION_UNITS,
    FORMATS_REQUIRING_TRANSCODE,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
)
from snipkin.utils import (
    check_ffmpeg_available,
    format_seconds_to_timecode,
    get_executable_path,
    parse_timecode_to_seconds,
)


def generate_clip_output_path(input_path: str, output_format: str) -> str:
    """
    根据输入文件路径自动生成带时间戳的默认输出路径。

    生成规则：与输入文件同目录，文件名格式为 "{原始文件名}_clip_{时间戳}.{格式}"。

    参数:
        input_path:    输入视频文件的绝对路径
        output_format: 输出格式（如 "mp4"、"mov"）

    返回:
        生成的默认输出文件路径
    """
    directory = os.path.dirname(input_path)
    basename = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, f"{basename}_clip_{timestamp}.{output_format}")


def validate_clip_params(
    input_path: str,
    output_path: str,
    start_time: str,
    end_time: str,
    duration_value: str,
    duration_unit: str,
) -> tuple[dict | None, str | None]:
    """
    校验视频截取的所有参数，并解析出实际的秒数值。

    校验内容：
      1. ffmpeg 可用性
      2. 输入文件存在性
      3. 输出路径非空
      4. 输出目录可创建
      5. 开始时间格式合法
      6. 结束时间或持续时长的格式与逻辑合法

    参数:
        input_path:     输入视频文件路径
        output_path:    输出文件路径
        start_time:     开始时间字符串（如 "0:00:00"）
        end_time:       结束时间字符串（可为空，为空时使用持续时长）
        duration_value: 持续时长数值字符串（如 "10"）
        duration_unit:  持续时长单位（如 "秒"、"分钟"）

    返回:
        (params_dict, None) — 校验通过，params_dict 包含解析后的参数：
            - "start_seconds": float
            - "duration_seconds": float
            - "output_dir_created": str | None（如果自动创建了目录则返回路径）
        (None, error_message) — 校验失败，返回错误信息
    """
    if not check_ffmpeg_available():
        return None, "❌ 错误: 未检测到 ffmpeg，请先安装。"

    if not input_path or not os.path.isfile(input_path):
        return None, "❌ 错误: 请先选择一个有效的输入视频文件。"

    if not output_path:
        return None, "❌ 错误: 请先设置输出文件保存路径。"

    # 自动创建不存在的输出目录
    output_dir_created = None
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
            output_dir_created = out_dir
        except Exception as error:
            return None, f"❌ 错误: 无法创建输出文件夹: {error}"

    # 解析开始时间
    try:
        start_seconds = parse_timecode_to_seconds(start_time)
        if start_seconds < 0:
            raise ValueError("开始时间不能为负数")
    except ValueError as error:
        return None, f"❌ 错误: 开始时间格式无效（支持 H:MM:SS / MM:SS / 秒数）。{error}"

    # 优先使用结束时间，否则使用持续时长
    end_time_stripped = end_time.strip() if end_time else ""
    if end_time_stripped:
        try:
            end_seconds = parse_timecode_to_seconds(end_time_stripped)
            if end_seconds <= start_seconds:
                return None, "❌ 错误: 结束时间必须大于开始时间。"
            duration_seconds = end_seconds - start_seconds
        except ValueError as error:
            return None, f"❌ 错误: 结束时间格式无效。{error}"
    else:
        try:
            parsed_duration_value = float(duration_value)
            if parsed_duration_value <= 0:
                raise ValueError("持续时长必须大于 0")
        except ValueError:
            return None, "❌ 错误: 持续时长必须是一个正数。"

        unit_multiplier = DURATION_UNITS[duration_unit]
        duration_seconds = parsed_duration_value * unit_multiplier

    return {
        "start_seconds": start_seconds,
        "duration_seconds": duration_seconds,
        "output_dir_created": output_dir_created,
    }, None


def build_video_filters(resolution: str, framerate: str) -> list[str]:
    """
    根据分辨率和帧率选项构建视频滤镜列表。

    参数:
        resolution: 分辨率选项的显示名称（如 "原始分辨率"、"1080p"）
        framerate:  帧率选项的显示名称（如 "原始帧率"、"30 fps"）

    返回:
        滤镜字符串列表，为空表示不需要额外滤镜
    """
    filters = []

    scale_value = RESOLUTION_OPTIONS[resolution]
    if scale_value:
        filters.append(f"scale={scale_value}")

    fps_value = FRAMERATE_OPTIONS[framerate]
    if fps_value:
        filters.append(f"fps={fps_value}")

    return filters


def build_clip_ffmpeg_command(
    input_path: str,
    output_path: str,
    start_seconds: float,
    duration_seconds: float,
    output_format: str,
    compress_enabled: bool,
    quality_preset: str,
    resolution: str,
    framerate: str,
    audio_bitrate: str,
) -> list[str]:
    """
    构建视频截取的 ffmpeg 命令。

    根据压缩设置和输出格式，决定使用以下策略之一：
      - 需要转码的格式（如 GIF）：强制使用转码
      - 启用压缩：使用 libx264 编码 + CRF 质量控制 + 可选滤镜
      - 不压缩：使用流复制（-c copy），速度最快，无质量损失

    参数:
        input_path:       输入视频文件路径
        output_path:      输出文件路径
        start_seconds:    截取开始时间（秒）
        duration_seconds: 截取持续时长（秒）
        output_format:    输出格式（如 "mp4"、"gif"）
        compress_enabled: 是否启用压缩
        quality_preset:   压缩质量预设的显示名称（如 "中质量（推荐）"）
        resolution:       分辨率选项的显示名称
        framerate:        帧率选项的显示名称
        audio_bitrate:    音频码率选项的显示名称

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

    needs_transcode = output_format in FORMATS_REQUIRING_TRANSCODE

    if needs_transcode or compress_enabled:
        # 需要转码：添加编码参数
        if output_format != "gif":
            crf_value = COMPRESS_QUALITY_PRESETS[quality_preset]
            command.extend([
                "-c:v", "libx264",
                "-crf", str(crf_value),
                "-preset", "medium",
            ])

        # 添加视频滤镜（分辨率缩放 + 帧率限制）
        video_filters = build_video_filters(resolution, framerate)
        if video_filters:
            command.extend(["-vf", ",".join(video_filters)])

        # 音频码率设置
        audio_bitrate_value = AUDIO_BITRATE_OPTIONS[audio_bitrate]
        if audio_bitrate_value:
            command.extend(["-b:a", audio_bitrate_value])
        else:
            command.extend(["-c:a", "aac"])
    else:
        # 不压缩：流复制（速度最快，无质量损失）
        command.extend(["-c", "copy"])

    command.append(output_path)
    return command


def execute_ffmpeg(
    command: list[str],
    on_log: Callable[[str], None],
    on_success: Callable[[], None],
    on_error: Callable[[str], None],
    on_complete: Callable[[], None],
    timeout: int = 600,
) -> None:
    """
    执行 ffmpeg 命令并通过回调通知结果。

    本函数在当前线程中同步执行，调用方应自行决定是否放到子线程中运行。

    参数:
        command:     完整的 ffmpeg 命令参数列表
        on_log:      日志回调，用于输出执行过程中的信息
        on_success:  成功回调，命令执行成功时调用
        on_error:    错误回调，命令执行失败时调用，参数为错误信息
        on_complete: 完成回调，无论成功失败都会调用（用于恢复 UI 状态等）
        timeout:     最长等待时间（秒），默认 600 秒（10 分钟）
    """
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if process.returncode == 0:
            on_success()
        else:
            error_message = process.stderr.strip() if process.stderr else "未知错误"
            on_error(
                f"❌ ffmpeg 执行失败 (返回码 {process.returncode}):\n{error_message}",
            )

    except subprocess.TimeoutExpired:
        on_error(f"❌ 错误: ffmpeg 执行超时（超过 {timeout // 60} 分钟），已终止。")
    except FileNotFoundError:
        on_error("❌ 错误: 无法找到 ffmpeg 可执行文件。")
    except Exception as unexpected_error:
        on_error(f"❌ 发生意外错误: {unexpected_error}")
    finally:
        on_complete()
