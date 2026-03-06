"""
snipkin.core.concat_core - 视频拼接的核心业务逻辑（UI 无关）

本模块提供视频拼接功能的所有纯逻辑函数，包括：
- generate_concat_output_path:   根据首个输入文件自动生成带时间戳的默认输出路径
- validate_concat_params:        校验拼接参数（文件数量、存在性、过渡参数、输出路径）
- build_concat_ffmpeg_command:   构建 ffmpeg 拼接命令（策略分发入口）
- build_concat_video_filters:    构建拼接模式的视频滤镜列表
- execute_concat_ffmpeg:         执行拼接 ffmpeg 命令并通过回调通知结果

设计说明：
  所有函数只接收普通 Python 类型参数，不依赖任何 UI 框架。
  调用方（UI 层）负责从界面收集参数、调用这些函数、并将结果反馈到界面。
"""

import datetime
import os
import subprocess
import tempfile
from typing import Callable

from snipkin.constants import (
    AUDIO_BITRATE_OPTIONS,
    COMPRESS_QUALITY_PRESETS,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
    XFADE_TRANSITIONS,
)
from snipkin.utils import (
    check_ffmpeg_available,
    get_executable_path,
    get_video_duration,
    get_video_resolution,
)


def generate_concat_output_path(first_file_path: str, output_format: str) -> str:
    """
    根据首个输入文件路径自动生成带时间戳的默认输出路径。

    生成规则：与首个文件同目录，文件名格式为 "merged_output_{时间戳}.{格式}"。

    参数:
        first_file_path: 文件列表中第一个文件的绝对路径
        output_format:   输出格式（如 "mp4"、"mov"）

    返回:
        生成的默认输出文件路径
    """
    directory = os.path.dirname(first_file_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, f"merged_output_{timestamp}.{output_format}")


def validate_concat_params(
    file_list: list[str],
    output_path: str,
    transition_display_name: str,
    transition_duration_str: str,
) -> tuple[dict | None, str | None]:
    """
    校验视频拼接的所有参数，并解析出过渡动画的实际参数值。

    校验内容：
      1. ffmpeg 可用性
      2. 文件列表至少 2 个文件
      3. 所有文件存在
      4. 输出路径非空
      5. 输出目录可创建
      6. 过渡动画参数合法（如有）
      7. 获取各视频时长（xfade 模式需要）

    参数:
        file_list:               输入视频文件路径列表
        output_path:             输出文件路径
        transition_display_name: 过渡效果的显示名称（如 "淡入淡出 (fade)"）
        transition_duration_str: 过渡时长字符串（如 "1.0"）

    返回:
        (params_dict, None) — 校验通过，params_dict 包含解析后的参数：
            - "transition_name": str | None（ffmpeg xfade 参数值）
            - "transition_duration": float
            - "durations": list[float]（各视频时长，无过渡时为空列表）
            - "output_dir_created": str | None（如果自动创建了目录则返回路径）
        (None, error_message) — 校验失败，返回错误信息
    """
    if not check_ffmpeg_available():
        return None, "❌ 错误: 未检测到 ffmpeg，请先安装。"

    if len(file_list) < 2:
        return None, "❌ 错误: 请至少添加 2 个视频文件进行拼接。"

    for file_path in file_list:
        if not os.path.isfile(file_path):
            return None, f"❌ 错误: 文件不存在: {file_path}"

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

    # 解析过渡动画参数
    transition_name = XFADE_TRANSITIONS[transition_display_name]
    transition_duration = 0.0
    if transition_name:
        try:
            transition_duration = float(transition_duration_str.strip())
            if transition_duration <= 0:
                raise ValueError("过渡时长必须大于 0")
        except ValueError:
            return None, "❌ 错误: 过渡时长必须是一个正数（秒）。"

    # 获取每个视频的时长和分辨率（xfade 需要知道每段视频的时长来计算 offset，
    # 并且需要统一分辨率，因为 xfade 滤镜要求所有输入视频分辨率一致）
    durations: list[float] = []
    resolutions: list[tuple[int, int]] = []
    if transition_name:
        for file_path in file_list:
            duration = get_video_duration(file_path)
            if duration is None:
                return None, (
                    f"❌ 错误: 无法获取视频时长: {os.path.basename(file_path)}，"
                    f"请确保 ffprobe 可用。"
                )
            durations.append(duration)

            resolution_info = get_video_resolution(file_path)
            if resolution_info is None:
                return None, (
                    f"❌ 错误: 无法获取视频分辨率: {os.path.basename(file_path)}，"
                    f"请确保 ffprobe 可用。"
                )
            resolutions.append(resolution_info)

    return {
        "transition_name": transition_name,
        "transition_duration": transition_duration,
        "durations": durations,
        "resolutions": resolutions,
        "output_dir_created": output_dir_created,
    }, None


def build_concat_video_filters(resolution: str, framerate: str) -> list[str]:
    """
    根据分辨率和帧率选项构建拼接模式的视频滤镜列表。

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


def build_concat_ffmpeg_command(
    file_list: list[str],
    output_path: str,
    transition_name: str | None,
    transition_duration: float,
    durations: list[float],
    resolutions: list[tuple[int, int]],
    compress_enabled: bool,
    quality_preset: str,
    resolution: str,
    framerate: str,
    audio_bitrate: str,
) -> tuple[list[str], str | None]:
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
        resolutions:          各视频的分辨率列表（xfade 模式需要）
        compress_enabled:     是否启用压缩
        quality_preset:       压缩质量预设的显示名称
        resolution:           分辨率选项的显示名称
        framerate:            帧率选项的显示名称
        audio_bitrate:        音频码率选项的显示名称

    返回:
        (command, temp_file_path) 元组：
          - command: 完整的 ffmpeg 命令参数列表
          - temp_file_path: 临时文件路径（仅 demuxer 模式有值，其他模式为 None）
    """
    if transition_name:
        return _build_xfade_command(
            file_list, output_path, transition_name,
            transition_duration, durations, resolutions,
            compress_enabled, quality_preset, resolution, framerate, audio_bitrate,
        ), None
    elif compress_enabled:
        return _build_concat_filter_command(
            file_list, output_path,
            quality_preset, resolution, framerate, audio_bitrate,
        ), None
    else:
        return _build_concat_demuxer_command(file_list, output_path)


def _build_xfade_command(
    file_list: list[str],
    output_path: str,
    transition_name: str,
    transition_duration: float,
    durations: list[float],
    resolutions: list[tuple[int, int]],
    compress_enabled: bool,
    quality_preset: str,
    resolution: str,
    framerate: str,
    audio_bitrate: str,
) -> list[str]:
    """
    使用 xfade 滤镜构建带过渡动画的拼接命令。

    工作原理：
      1. 先检测各视频分辨率是否一致，如不一致则为每个输入添加 scale 预处理滤镜
         统一缩放到目标分辨率（用户指定的分辨率 > 第一个视频的分辨率）。
      2. 每两段视频之间插入一个 xfade 视频过渡和一个 acrossfade 音频过渡。
      3. 通过链式连接多个 xfade 滤镜实现多段视频的连续过渡。
      4. offset 的计算公式：前面所有视频总时长 - 前面所有过渡占用的时长 - 当前过渡时长。

    参数:
        file_list:            输入视频文件路径列表
        output_path:          输出文件路径
        transition_name:      xfade 过渡效果名称
        transition_duration:  过渡时长（秒）
        durations:            各视频的时长列表
        resolutions:          各视频的分辨率列表 [(width, height), ...]
        compress_enabled:     是否启用压缩
        quality_preset:       压缩质量预设的显示名称
        resolution:           分辨率选项的显示名称
        framerate:            帧率选项的显示名称
        audio_bitrate:        音频码率选项的显示名称

    返回:
        完整的 ffmpeg 命令参数列表
    """
    file_count = len(file_list)

    # 输入文件参数
    command = [get_executable_path("ffmpeg"), "-y"]
    for file_path in file_list:
        command.extend(["-i", file_path])

    # xfade 滤镜要求所有输入视频的分辨率、帧率和 timebase 必须完全一致，
    # 因此始终为每个输入添加预处理滤镜来统一这些参数。

    # 确定目标分辨率：用户指定的分辨率优先，否则使用第一个视频的分辨率
    user_scale = RESOLUTION_OPTIONS[resolution] if compress_enabled else None
    if user_scale:
        # 用户指定了分辨率（如 "1920:-1"），解析为精确宽高
        scale_parts = user_scale.split(":")
        target_width = int(scale_parts[0])
        if scale_parts[1] == "-1":
            first_width, first_height = resolutions[0]
            target_height = int(target_width * first_height / first_width)
            # 确保高度是偶数（ffmpeg 编码要求）
            target_height = target_height + (target_height % 2)
        else:
            target_height = int(scale_parts[1])
    else:
        # 使用第一个视频的分辨率作为目标
        target_width, target_height = resolutions[0]

    # 确定目标帧率：用户指定的帧率优先，否则使用 24fps 作为统一标准
    user_fps = FRAMERATE_OPTIONS[framerate] if compress_enabled else None
    target_fps = user_fps if user_fps else "24"

    # 构建预处理滤镜和 xfade/acrossfade 滤镜链
    prescale_parts = []
    video_filter_parts = []
    audio_filter_parts = []

    # 为每个输入视频添加预处理滤镜链：
    # scale:  缩放到目标尺寸内（保持宽高比，不超出目标尺寸）
    # pad:    填充黑边到精确的目标尺寸（居中放置）
    # setsar: 统一像素宽高比为 1:1
    # fps:    统一帧率（解决 timebase 不匹配问题）
    # settb:  统一时间基准为 AVTB（1/AV_TIME_BASE）
    for i in range(file_count):
        prescale_parts.append(
            f"[{i}:v]scale={target_width}:{target_height}"
            f":force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:-1:-1:color=black,"
            f"setsar=1,fps={target_fps},settb=AVTB[v{i}]",
        )

    for i in range(file_count - 1):
        # 确定当前过渡的输入标签（始终使用预处理后的标签 [v0], [v1], ...）
        video_input_a = f"[v{i}]" if i == 0 else f"[vfade{i}]"
        audio_input_a = f"[{i}:a]" if i == 0 else f"[afade{i}]"
        video_input_b = f"[v{i + 1}]"
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

    # 分辨率和帧率已在预处理阶段统一处理，无需额外追加滤镜

    # 组合所有滤镜部分：预处理 + xfade + acrossfade
    all_filter_parts = prescale_parts + video_filter_parts + audio_filter_parts
    filter_complex = ";".join(all_filter_parts)

    command.extend(["-filter_complex", filter_complex])
    command.extend(["-map", "[vout]", "-map", "[aout]"])

    # 添加编码参数（xfade 必须转码）
    if compress_enabled:
        crf_value = COMPRESS_QUALITY_PRESETS[quality_preset]
        command.extend([
            "-c:v", "libx264", "-crf", str(crf_value), "-preset", "medium",
        ])
        audio_bitrate_value = AUDIO_BITRATE_OPTIONS[audio_bitrate]
        if audio_bitrate_value:
            command.extend(["-b:a", audio_bitrate_value])
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
    file_list: list[str],
    output_path: str,
    quality_preset: str,
    resolution: str,
    framerate: str,
    audio_bitrate: str,
) -> list[str]:
    """
    使用 concat 滤镜构建拼接命令（无过渡动画 + 有压缩）。

    通过 ffmpeg 的 concat 滤镜将多个输入流合并为一个，
    然后使用 libx264 编码输出，支持自定义分辨率/帧率/音频码率。

    参数:
        file_list:      输入视频文件路径列表
        output_path:    输出文件路径
        quality_preset: 压缩质量预设的显示名称
        resolution:     分辨率选项的显示名称
        framerate:      帧率选项的显示名称
        audio_bitrate:  音频码率选项的显示名称

    返回:
        完整的 ffmpeg 命令参数列表
    """
    file_count = len(file_list)

    command = [get_executable_path("ffmpeg"), "-y"]
    for file_path in file_list:
        command.extend(["-i", file_path])

    # concat 滤镜 + 可选的 scale/fps 滤镜（合并到 filter_complex 中）
    input_labels = "".join(f"[{i}:v][{i}:a]" for i in range(file_count))
    video_filters = build_concat_video_filters(resolution, framerate)

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
    crf_value = COMPRESS_QUALITY_PRESETS[quality_preset]
    command.extend([
        "-c:v", "libx264", "-crf", str(crf_value), "-preset", "medium",
    ])

    audio_bitrate_value = AUDIO_BITRATE_OPTIONS[audio_bitrate]
    if audio_bitrate_value:
        command.extend(["-b:a", audio_bitrate_value])
    else:
        command.extend(["-c:a", "aac"])

    command.append(output_path)
    return command


def _build_concat_demuxer_command(
    file_list: list[str],
    output_path: str,
) -> tuple[list[str], str]:
    """
    使用 concat demuxer 构建拼接命令（无过渡动画 + 无压缩）。

    这是最快的拼接方式，通过 concat demuxer 直接流复制，
    不进行任何转码，因此无质量损失。
    通过临时文件列表传递输入文件路径给 ffmpeg。

    参数:
        file_list:   输入视频文件路径列表
        output_path: 输出文件路径

    返回:
        (command, temp_file_path) 元组：
          - command: 完整的 ffmpeg 命令参数列表
          - temp_file_path: 临时文件路径（调用方需在执行完成后清理）
    """
    concat_list_content = "\n".join(
        f"file '{file_path}'" for file_path in file_list
    )
    temp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="snipkin_concat_",
    )
    temp_file.write(concat_list_content)
    temp_file.close()

    command = [
        get_executable_path("ffmpeg"), "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", temp_file.name,
        "-c", "copy",
        output_path,
    ]
    return command, temp_file.name


def execute_concat_ffmpeg(
    command: list[str],
    on_log: Callable[[str], None],
    on_success: Callable[[], None],
    on_error: Callable[[str], None],
    on_complete: Callable[[], None],
    temp_file_path: str | None = None,
    timeout: int = 1800,
) -> None:
    """
    执行拼接 ffmpeg 命令并通过回调通知结果。

    本函数在当前线程中同步执行，调用方应自行决定是否放到子线程中运行。
    执行完成后自动清理 concat demuxer 模式下创建的临时文件。

    参数:
        command:        完整的 ffmpeg 命令参数列表
        on_log:         日志回调，用于输出执行过程中的信息
        on_success:     成功回调，命令执行成功时调用
        on_error:       错误回调，命令执行失败时调用，参数为错误信息
        on_complete:    完成回调，无论成功失败都会调用（用于恢复 UI 状态等）
        temp_file_path: concat demuxer 模式下的临时文件路径（可选，用于清理）
        timeout:        最长等待时间（秒），默认 1800 秒（30 分钟）
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
                f"❌ ffmpeg 拼接失败 (返回码 {process.returncode}):\n{error_message}",
            )

    except subprocess.TimeoutExpired:
        on_error(f"❌ 错误: ffmpeg 执行超时（超过 {timeout // 60} 分钟），已终止。")
    except FileNotFoundError:
        on_error("❌ 错误: 无法找到 ffmpeg 可执行文件。")
    except Exception as unexpected_error:
        on_error(f"❌ 发生意外错误: {unexpected_error}")
    finally:
        on_complete()
        # 清理临时文件（concat demuxer 模式下创建的）
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
