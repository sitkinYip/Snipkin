"""
snipkin.app - 主应用窗口

本模块定义 VideoClipperApp 类，它是整个应用的核心入口。
通过多继承（Mixin 模式）组合以下模块的功能：
- ClipTabMixin:       视频截取 Tab 的 UI 构建
- ConcatTabMixin:     视频拼接 Tab 的 UI 构建
- LogSectionMixin:    日志输出区域的 UI 构建与日志工具方法
- ClipHandlerMixin:   视频截取的事件处理与业务逻辑
- ConcatHandlerMixin: 视频拼接的事件处理与业务逻辑

架构设计：
  采用 Mixin 模式将 UI 构建和业务逻辑拆分到独立模块中，
  VideoClipperApp 作为"胶水类"通过多继承将它们组合在一起。
  所有 Mixin 通过 self 访问主窗口实例的属性和方法，
  状态变量（如 tk.StringVar、tk.BooleanVar）在本类的 __init__ 中统一初始化。
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from snipkin.handlers import ClipHandlerMixin, ConcatHandlerMixin
from snipkin.ui import ClipTabMixin, ConcatTabMixin, LogSectionMixin
from snipkin.utils import check_ffmpeg_available


class VideoClipperApp(
    ClipTabMixin,
    ConcatTabMixin,
    LogSectionMixin,
    ClipHandlerMixin,
    ConcatHandlerMixin,
    ctk.CTk,
):
    """
    视频处理工具主窗口。

    继承自 ctk.CTk（CustomTkinter 主窗口）和五个功能 Mixin，
    负责：
      1. 初始化所有状态变量（截取 Tab + 拼接 Tab）
      2. 构建顶层 UI 框架（Tab 视图 + 日志区域）
      3. 启动时检测 ffmpeg 可用性
    """

    def __init__(self):
        super().__init__()

        # ---- 窗口基本设置 ----
        self.title("Snipkin - 视频处理工具")
        self.geometry("660x780")
        self.resizable(False, False)

        # 设置 macOS 风格的外观主题（跟随系统深浅色）
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # ---- 初始化所有状态变量 ----
        self._init_clip_state()
        self._init_concat_state()

        # ---- 构建 UI ----
        self._build_ui()

        # ---- 启动时检测 ffmpeg ----
        if not check_ffmpeg_available():
            messagebox.showwarning(
                "ffmpeg 未找到",
                "未在系统 PATH 中检测到 ffmpeg。\n"
                "请先安装 ffmpeg（推荐使用 Homebrew: brew install ffmpeg），"
                "然后重新启动本工具。",
            )

    def _init_clip_state(self):
        """
        初始化截取 Tab 的所有状态变量。

        包括：输入/输出文件路径、时间设置、输出格式、
        压缩开关及参数（质量预设、分辨率、帧率、音频码率）。
        """
        # 文件路径
        self.input_file_path = tk.StringVar(value="")
        self.output_file_path = tk.StringVar(value="")

        # 时间设置
        self.start_time_var = tk.StringVar(value="0:00:00")
        self.end_time_var = tk.StringVar(value="")
        self.duration_value_var = tk.StringVar(value="10")
        self.duration_unit_var = tk.StringVar(value="秒")

        # 输出格式
        self.output_format_var = tk.StringVar(value="mp4")

        # 压缩相关
        self.compress_enabled_var = tk.BooleanVar(value=False)
        self.compress_quality_var = tk.StringVar(value="中质量（推荐）")
        self.advanced_visible = False
        self.resolution_var = tk.StringVar(value="原始分辨率")
        self.framerate_var = tk.StringVar(value="原始帧率")
        self.audio_bitrate_var = tk.StringVar(value="原始音频")

    def _init_concat_state(self):
        """
        初始化拼接 Tab 的所有状态变量。

        包括：文件列表、输出路径和格式、压缩开关及参数、过渡动画设置。
        与截取 Tab 的变量使用 concat_ 前缀区分，互不干扰。
        """
        # 文件列表
        self.concat_file_list: list[str] = []

        # 输出设置
        self.concat_output_path = tk.StringVar(value="")
        self.concat_output_format_var = tk.StringVar(value="mp4")

        # 压缩相关
        self.concat_compress_enabled_var = tk.BooleanVar(value=False)
        self.concat_compress_quality_var = tk.StringVar(value="中质量（推荐）")
        self.concat_advanced_visible = False
        self.concat_resolution_var = tk.StringVar(value="原始分辨率")
        self.concat_framerate_var = tk.StringVar(value="原始帧率")
        self.concat_audio_bitrate_var = tk.StringVar(value="原始音频")

        # 过渡动画
        self.concat_transition_var = tk.StringVar(value="无过渡")
        self.concat_transition_duration_var = tk.StringVar(value="1.0")

    def _build_ui(self):
        """
        构建完整的用户界面。

        顶层布局结构：
          ┌─────────────────────────────┐
          │  TabView                    │
          │  ┌───────────┬────────────┐ │
          │  │ ✂️ 视频截取 │ 🔗 视频拼接 │ │
          │  ├───────────┴────────────┤ │
          │  │  （各 Tab 的内容区域）   │ │
          │  └────────────────────────┘ │
          │  📋 执行日志                 │
          │  ┌────────────────────────┐ │
          │  │  （日志文本框）          │ │
          │  └────────────────────────┘ │
          └─────────────────────────────┘

        各 Tab 的具体内容由对应的 Mixin 构建。
        """
        # 主容器
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 视图
        self.tabview = ctk.CTkTabview(container, height=580)
        self.tabview.pack(fill="both", expand=True)

        # Tab 1: 视频截取（由 ClipTabMixin._build_clip_tab 构建）
        clip_tab = self.tabview.add("✂️ 视频截取")
        self._build_clip_tab(clip_tab)

        # Tab 2: 视频拼接（由 ConcatTabMixin._build_concat_tab 构建）
        concat_tab = self.tabview.add("🔗 视频拼接")
        self._build_concat_tab(concat_tab)

        # 日志输出区域（由 LogSectionMixin._build_log_section 构建，两个 Tab 共享）
        self._build_log_section(container)
