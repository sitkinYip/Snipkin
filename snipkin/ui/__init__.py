"""
snipkin.ui - 用户界面构建模块

本包包含所有 UI 构建函数：
- build_clip_tab:            视频截取 Tab 的界面构建
- build_concat_tab:          视频拼接 Tab 的界面构建
- build_extract_audio_tab:   音频提取 Tab 的界面构建
- build_compress_audio_tab:  音频压缩 Tab 的界面构建
"""

from snipkin.ui.clip_tab import build_clip_tab
from snipkin.ui.compress_audio_tab import build_compress_audio_tab
from snipkin.ui.concat_tab import build_concat_tab
from snipkin.ui.extract_audio_tab import build_extract_audio_tab

__all__ = [
    "build_clip_tab",
    "build_concat_tab",
    "build_extract_audio_tab",
    "build_compress_audio_tab",
]
