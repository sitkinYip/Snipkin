"""
测试音频提取功能的简单脚本
"""

from snipkin.core.extract_audio_core import (
    generate_audio_output_path,
    validate_extract_params,
    build_extract_ffmpeg_command,
)

# 测试生成输出路径
print("=== 测试 generate_audio_output_path ===")
test_path = "/path/to/video.mp4"
output = generate_audio_output_path(test_path, "mp3")
print(f"输入：{test_path}")
print(f"输出：{output}")
print()

# 测试参数校验（extract_full=True）
print("=== 测试 validate_extract_params (完整提取) ===")
params, error = validate_extract_params(
    input_path="/tmp/test.mp4",
    output_path="/tmp/output.mp3",
    start_time="0:00:00",
    end_time="",
    duration_value="10",
    duration_unit="秒",
    extract_full=True,
)
if error:
    print(f"错误：{error}")
else:
    print(f"参数校验通过：{params}")
print()

# 测试参数校验（截取部分）
print("=== 测试 validate_extract_params (截取部分) ===")
params, error = validate_extract_params(
    input_path="/tmp/test.mp4",
    output_path="/tmp/output.mp3",
    start_time="0:00:10",
    end_time="",
    duration_value="30",
    duration_unit="秒",
    extract_full=False,
)
if error:
    print(f"错误：{error}")
else:
    print(f"参数校验通过：{params}")
print()

# 测试构建命令（完整提取）
print("=== 测试 build_extract_ffmpeg_command (完整提取) ===")
command = build_extract_ffmpeg_command(
    input_path="/tmp/test.mp4",
    output_path="/tmp/output.mp3",
    start_seconds=0.0,
    duration_seconds=0.0,
    output_format="mp3",
    audio_bitrate="高品质（320k）",
    extract_full=True,
)
print(f"命令：{' '.join(command)}")
print()

# 测试构建命令（截取部分）
print("=== 测试 build_extract_ffmpeg_command (截取部分) ===")
command = build_extract_ffmpeg_command(
    input_path="/tmp/test.mp4",
    output_path="/tmp/output.mp3",
    start_seconds=10.0,
    duration_seconds=30.0,
    output_format="mp3",
    audio_bitrate="标准品质（192k）",
    extract_full=False,
)
print(f"命令：{' '.join(command)}")
print()

# 测试不同格式
print("=== 测试不同音频格式 ===")
for format in ["mp3", "flac", "wav", "aac", "m4a", "ogg"]:
    command = build_extract_ffmpeg_command(
        input_path="/tmp/test.mp4",
        output_path=f"/tmp/output.{format}",
        start_seconds=0.0,
        duration_seconds=0.0,
        output_format=format,
        audio_bitrate="高品质（320k）",
        extract_full=True,
    )
    print(f"{format}: {' '.join(command)}")

print("\n=== 所有测试完成 ===")
