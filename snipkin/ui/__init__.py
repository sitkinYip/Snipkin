"""
snipkin.ui - 用户界面构建模块

本包包含所有 UI 构建相关的 Mixin 类：
- ClipTabMixin:   视频截取 Tab 的界面构建
- ConcatTabMixin: 视频拼接 Tab 的界面构建
- LogSectionMixin: 日志输出区域的界面构建与日志工具方法
"""

from snipkin.ui.clip_tab import ClipTabMixin
from snipkin.ui.concat_tab import ConcatTabMixin
from snipkin.ui.log_section import LogSectionMixin

__all__ = ["ClipTabMixin", "ConcatTabMixin", "LogSectionMixin"]
