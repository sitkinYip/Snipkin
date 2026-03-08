"""
snipkin.core.extract_audio_core - 音频提取的核心业务逻辑（UI 无关）

本模块提供音频提取功能的所有纯逻辑函数，包括：
- generate_audio_output_path:   根据输入文件自动生成默认输出路径
- validate_extract_params:      校验提取参数（文件存在性、时间格式等）
- build_extract_ffmpeg_command: 构建 ffmpeg 音频提取命令
- execute_ffmpeg:               执行 ffmpeg 命令并通过回调通知结果

设计说明：
  所有函数只接收普通 Python 类型参数，不依赖任何 UI 框架。
  调用方（UI 层）负责从界面收集参数、调用这些函数、并将结果反馈到界面。
"""

import datetime
import os
import subprocess
from typing import Callable

from snipkin.constants import (
    AUDIO_QUALITY_PRESETS,
    DURATION_UNITS,
)
from snipkin.utils import (
    check_ffmpeg_available,
    format_seconds_to_timecode,
    get_executable_path,
    parse_timecode_to_seconds,
)


def generate_audio_output_path(input_path: str, output_format: str) -> str:
    """
    根据输入文件路径自动生成带时间戳的默认输出路径。

    生成规则：与输入文件同目录，文件名格式为 "{原始文件名}_audio_{时间戳}.{格式}"。

    参数:
        input_path:    输入视频文件的绝对路径
        output_format: 输出格式（如 "mp3"、"wav"）

    返回:
        生成的默认输出文件路径
    """
    directory = os.path.dirname(input_path)
    basename = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, f"{basename}_audio_{timestamp}.{output_format}")


def validate_extract_params(
    input_path: str,
    output_path: str,
    start_time: str,
    end_time: str,
    duration_value: str,
    duration_unit: str,
    extract_full: bool,
) -> tuple[dict | None, str | None]:
    """
    校验音频提取的所有参数，并解析出实际的秒数值。

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
        end_time:       结束时间字符串（可为空）
        duration_value: 持续时长数值字符串（如 "10"）
        duration_unit:  持续时长单位（如 "秒"、"分钟"）
        extract_full:   是否提取完整音频（忽略时间参数）

    返回:
        (params_dict, None) — 校验通过，params_dict 包含解析后的参数：
            - "start_seconds": float
            - "duration_seconds": float
            - "output_dir_created": str | None（如果自动创建了目录则返回路径）
        (None, error_message) — 校验失败，返回错误信息
    """
    if not check_ffmpeg_available():
        return None, "❌ 错误：未检测到 ffmpeg，请先安装。"

    if not input_path or not os.path.isfile(input_path):
        return None, "❌ 错误：请先选择一个有效的输入视频文件。"

    if not output_path:
        return None, "❌ 错误：请先设置输出文件保存路径。"

    # 自动创建不存在的输出目录
    output_dir_created = None
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
            output_dir_created = out_dir
        except Exception as error:
            return None, f"❌ 错误：无法创建输出文件夹：{error}"

    # 如果提取完整音频，不需要校验时间参数
    if extract_full:
        return {
            "start_seconds": 0.0,
            "duration_seconds": 0.0,
            "output_dir_created": output_dir_created,
        }, None

    # 解析开始时间
    try:
        start_seconds = parse_timecode_to_seconds(start_time)
        if start_seconds < 0:
            raise ValueError("开始时间不能为负数")
    except ValueError as error:
        return None, f"❌ 错误：开始时间格式无效（支持 H:MM:SS / MM:SS / 秒数）。{error}"

    # 优先使用结束时间，否则使用持续时长
    end_time_stripped = end_time.strip() if end_time else ""
    if end_time_stripped:
        try:
            end_seconds = parse_timecode_to_seconds(end_time_stripped)
            if end_seconds <= start_seconds:
                return None, "❌ 错误：结束时间必须大于开始时间。"
            duration_seconds = end_seconds - start_seconds
        except ValueError as error:
            return None, f"❌ 错误：结束时间格式无效。{error}"
    else:
        try:
            parsed_duration_value = float(duration_value)
            if parsed_duration_value <= 0:
                raise ValueError("持续时长必须大于 0")
        except ValueError:
            return None, "❌ 错误：持续时长必须是一个正数。"

        unit_multiplier = DURATION_UNITS[duration_unit]
        duration_seconds = parsed_duration_value * unit_multiplier

    return {
        "start_seconds": start_seconds,
        "duration_seconds": duration_seconds,
        "output_dir_created": output_dir_created,
    }, None


def build_extract_ffmpeg_command(
    input_path: str,
    output_path: str,
    start_seconds: float,
    duration_seconds: float,
    output_format: str,
    audio_bitrate: str,
    extract_full: bool,
) -> list[str]:
    """
    构建音频提取的 ffmpeg 命令。

    根据输出格式和时间设置，构建对应的 ffmpeg 参数：
      - 提取完整音频：不使用 -ss 和 -t 参数
      - 截取部分音频：使用 -ss 和 -t 参数
      - 不同格式使用不同的音频编码器

    参数:
        input_path:       输入视频文件路径
        output_path:      输出文件路径
        start_seconds:    提取开始时间（秒），extract_full 时为 0
        duration_seconds: 提取持续时长（秒），extract_full 时为 0
        output_format:    输出格式（如 "mp3"、"flac"）
        audio_bitrate:    音频码率选项的显示名称（如 "高品质（320k）"）
        extract_full:     是否提取完整音频

    返回:
        完整的 ffmpeg 命令参数列表
    """
    command = [get_executable_path("ffmpeg"), "-y", "-i", input_path]

    # 如果不是提取完整音频，添加时间参数
    if not extract_full and start_seconds > 0:
        start_timecode = format_seconds_to_timecode(start_seconds)
        command.extend(["-ss", start_timecode])
        
        if duration_seconds > 0:
            duration_timecode = format_seconds_to_timecode(duration_seconds)
            command.extend(["-t", duration_timecode])

    # 根据输出格式选择编码器
    audio_codec_map = {
        "mp3": "libmp3lame",
        "aac": "aac",
        "flac": "flac",
        "wav": "pcm_s16le",
        "m4a": "aac",
        "ogg": "libvorbis",
    }
    
    audio_codec = audio_codec_map.get(output_format, "libmp3lame")
    command.extend(["-vn", "-c:a", audio_codec])

    # 对于有损压缩格式，添加比特率设置
    if output_format in ["mp3", "aac", "m4a", "ogg"]:
        bitrate_value = AUDIO_QUALITY_PRESETS[audio_bitrate]
        if bitrate_value:
            command.extend(["-b:a", bitrate_value])

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
        on_error(f"❌ 错误：ffmpeg 执行超时（超过 {timeout // 60} 分钟），已终止。")
    except FileNotFoundError:
        on_error("❌ 错误：无法找到 ffmpeg 可执行文件。")
    except Exception as unexpected_error:
        on_error(f"❌ 发生意外错误：{unexpected_error}")
    finally:
        on_complete()
