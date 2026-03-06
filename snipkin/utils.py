"""
snipkin.utils - 通用工具函数

本模块提供与 ffmpeg 交互及时间码处理相关的工具函数，包括：
- get_executable_path:        获取可执行文件（ffmpeg / ffprobe）的绝对路径
- check_ffmpeg_available:     检测系统中是否存在可用的 ffmpeg
- parse_timecode_to_seconds:  将用户输入的时间码字符串解析为秒数
- format_seconds_to_timecode: 将秒数格式化为 ffmpeg 可识别的时间码
- get_video_duration:         通过 ffprobe 获取视频文件的时长

这些函数是纯工具函数，不依赖任何 UI 组件，可独立使用和测试。
"""

import os
import platform
import shutil
import subprocess
import sys


def get_executable_path(name: str) -> str:
    """
    获取可执行文件（如 ffmpeg、ffprobe）的绝对路径。

    查找优先级：
      1. PyInstaller 打包环境：从 sys._MEIPASS（打包资源目录）中查找
      2. 系统 PATH：通过 shutil.which 在环境变量中查找
      3. 兜底：直接返回命令名称，交由操作系统尝试执行

    参数:
        name: 可执行文件名称，如 "ffmpeg" 或 "ffprobe"

    返回:
        可执行文件的绝对路径，或在找不到时返回原始名称
    """
    is_windows = platform.system() == "Windows"
    filename = f"{name}.exe" if is_windows else name

    # 优先从 PyInstaller 打包目录中查找（打包后的独立应用场景）
    if hasattr(sys, "_MEIPASS"):
        bundled_path = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(bundled_path):
            return bundled_path

    # 从系统 PATH 中查找
    system_path = shutil.which(name)
    if system_path:
        return system_path

    # 兜底：返回原始名称，让后续调用自行处理 FileNotFoundError
    return name


def check_ffmpeg_available() -> bool:
    """
    检查系统或打包环境中是否存在可用的 ffmpeg。

    返回:
        True 表示 ffmpeg 可用，False 表示未找到
    """
    path = get_executable_path("ffmpeg")
    return path != "ffmpeg" or shutil.which("ffmpeg") is not None


def parse_timecode_to_seconds(timecode: str) -> float:
    """
    将用户输入的时间码字符串解析为秒数。

    支持以下格式：
      - "90"        → 90.0 秒
      - "1:30"      → 1 分 30 秒 = 90.0 秒
      - "1:30:50"   → 1 时 30 分 50 秒 = 5450.0 秒
      - "1:30:50.5" → 支持小数秒

    参数:
        timecode: 时间码字符串

    返回:
        对应的秒数（浮点数）

    异常:
        ValueError: 时间码为空或格式无法识别时抛出
    """
    timecode = timecode.strip()
    if not timecode:
        raise ValueError("时间不能为空")

    parts = timecode.split(":")
    if len(parts) == 1:
        # 纯秒数格式，如 "90" 或 "90.5"
        return float(parts[0])
    elif len(parts) == 2:
        # 分:秒 格式，如 "1:30"
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    elif len(parts) == 3:
        # 时:分:秒 格式，如 "1:30:50"
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError(f"无法识别的时间格式: {timecode}")


def format_seconds_to_timecode(seconds: float) -> str:
    """
    将秒数转换为 HH:MM:SS.mmm 格式的时间码，供 ffmpeg 命令使用。

    参数:
        seconds: 秒数（浮点数）

    返回:
        格式化后的时间码字符串，如 "01:30:50.000"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def get_video_duration(file_path: str) -> float | None:
    """
    使用 ffprobe 获取视频文件的时长。

    通过调用 ffprobe 命令读取视频的 format.duration 字段。
    主要用于拼接模式中计算 xfade 过渡动画的偏移量。

    参数:
        file_path: 视频文件的绝对路径

    返回:
        视频时长（秒），获取失败时返回 None
    """
    try:
        result = subprocess.run(
            [
                get_executable_path("ffprobe"),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return None
