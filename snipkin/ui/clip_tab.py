"""
snipkin.ui.clip_tab - 视频截取 Tab 的界面构建

本模块定义 ClipTabMixin 类，以 Mixin 模式提供视频截取 Tab 的所有 UI 构建方法。
通过多继承混入 VideoClipperApp 主窗口类中使用。

包含的 UI 区域：
- 输入文件选择区域（文件路径 + 浏览按钮）
- 时间设置区域（开始时间 + 结束时间 + 持续时长）
- 视频压缩设置区域（开关 + 质量预设 + 高级选项：分辨率/帧率/音频码率）
- 输出设置区域（格式选择 + 保存路径）
- 执行按钮区域

设计说明：
  所有方法通过 self 访问主窗口的状态变量（如 self.input_file_path、self.compress_enabled_var 等），
  这些变量在 VideoClipperApp.__init__ 中初始化。
"""

import tkinter as tk

import customtkinter as ctk

from snipkin.constants import (
    AUDIO_BITRATE_OPTIONS,
    COMPRESS_QUALITY_PRESETS,
    DURATION_UNITS,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
    SUPPORTED_FORMATS,
)


class ClipTabMixin:
    """
    视频截取 Tab 的 UI 构建 Mixin。

    提供截取 Tab 中所有界面元素的构建方法，以及压缩开关、高级选项展开/收起的交互逻辑。
    混入 VideoClipperApp 后，通过 self 访问主窗口实例的属性和方法。
    """

    def _build_clip_tab(self, parent):
        """
        构建视频截取 Tab 的完整内容。

        按从上到下的顺序依次构建：输入文件 → 时间设置 → 压缩设置 → 输出设置 → 执行按钮。

        参数:
            parent: 父容器（Tab 页面的根 Frame）
        """
        scroll_frame = ctk.CTkFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        self._build_input_section(scroll_frame)
        self._build_time_section(scroll_frame)
        self._build_compress_section(scroll_frame)
        self._build_output_section(scroll_frame)
        self._build_clip_action_section(scroll_frame)

    def _build_input_section(self, parent):
        """
        构建输入文件选择区域。

        包含一个只读的文件路径输入框和一个"选择文件"按钮。
        点击按钮后触发 self._on_select_input_file 事件（定义在 ClipHandlerMixin 中）。

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        label = ctk.CTkLabel(
            section, text="📂 输入视频文件",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(anchor="w", padx=12, pady=(10, 4))

        row = ctk.CTkFrame(section, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))

        # 文件路径显示（只读）
        path_entry = ctk.CTkEntry(
            row, textvariable=self.input_file_path,
            state="readonly", width=440,
        )
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # 选择文件按钮
        browse_button = ctk.CTkButton(
            row, text="选择文件", width=100,
            command=self._on_select_input_file,
        )
        browse_button.pack(side="right")

    def _build_time_section(self, parent):
        """
        构建时间设置区域。

        包含两行：
          第一行：开始时间 + 结束时间（格式 H:MM:SS）
          第二行：持续时长（数值 + 单位下拉），当结束时间为空时使用持续时长

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        label = ctk.CTkLabel(
            section, text="⏱ 时间设置",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(anchor="w", padx=12, pady=(10, 4))

        # 第一行：开始时间 + 结束时间
        time_row = ctk.CTkFrame(section, fg_color="transparent")
        time_row.pack(fill="x", padx=12, pady=(0, 6))

        start_label = ctk.CTkLabel(time_row, text="开始时间:")
        start_label.pack(side="left", padx=(0, 4))

        start_entry = ctk.CTkEntry(
            time_row, textvariable=self.start_time_var,
            width=110, placeholder_text="0:00:00",
        )
        start_entry.pack(side="left", padx=(0, 20))

        end_label = ctk.CTkLabel(time_row, text="结束时间:")
        end_label.pack(side="left", padx=(0, 4))

        end_entry = ctk.CTkEntry(
            time_row, textvariable=self.end_time_var,
            width=110, placeholder_text="留空则用持续时长",
        )
        end_entry.pack(side="left")

        # 第二行：持续时长（数字 + 单位下拉）
        duration_row = ctk.CTkFrame(section, fg_color="transparent")
        duration_row.pack(fill="x", padx=12, pady=(0, 10))

        duration_label = ctk.CTkLabel(duration_row, text="持续时长:")
        duration_label.pack(side="left", padx=(0, 4))

        duration_entry = ctk.CTkEntry(
            duration_row, textvariable=self.duration_value_var,
            width=80, placeholder_text="10",
        )
        duration_entry.pack(side="left", padx=(0, 6))

        duration_unit_menu = ctk.CTkOptionMenu(
            duration_row,
            values=list(DURATION_UNITS.keys()),
            variable=self.duration_unit_var,
            width=80,
        )
        duration_unit_menu.pack(side="left", padx=(0, 12))

        hint_label = ctk.CTkLabel(
            duration_row,
            text="💡 填了结束时间则忽略持续时长",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        hint_label.pack(side="left")

    def _build_compress_section(self, parent):
        """
        构建视频压缩设置区域。

        包含：
          - 标题行：标题 + 压缩启用开关
          - 压缩选项容器（默认隐藏，开关打开后显示）：
            - 质量预设下拉菜单
            - 高级选项展开按钮
            - 高级选项面板（分辨率 + 帧率 + 音频码率）

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        # 标题行：标题 + 压缩开关
        title_row = ctk.CTkFrame(section, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(10, 4))

        label = ctk.CTkLabel(
            title_row, text="🗜 视频压缩",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(side="left")

        compress_switch = ctk.CTkSwitch(
            title_row, text="启用压缩",
            variable=self.compress_enabled_var,
            command=self._on_compress_toggle,
        )
        compress_switch.pack(side="right")

        # 压缩选项容器（默认隐藏，开关打开后显示）
        self.compress_options_frame = ctk.CTkFrame(section, fg_color="transparent")

        # 第一行：质量预设下拉
        quality_row = ctk.CTkFrame(self.compress_options_frame, fg_color="transparent")
        quality_row.pack(fill="x", padx=0, pady=(0, 6))

        quality_label = ctk.CTkLabel(quality_row, text="压缩质量:")
        quality_label.pack(side="left", padx=(0, 4))

        quality_menu = ctk.CTkOptionMenu(
            quality_row,
            values=list(COMPRESS_QUALITY_PRESETS.keys()),
            variable=self.compress_quality_var,
            width=200,
        )
        quality_menu.pack(side="left", padx=(0, 12))

        # 高级选项展开按钮
        self.advanced_toggle_button = ctk.CTkButton(
            quality_row,
            text="▶ 高级选项",
            width=100,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray28"),
            command=self._on_advanced_toggle,
        )
        self.advanced_toggle_button.pack(side="left")

        # 高级选项面板（默认隐藏）
        self.advanced_frame = ctk.CTkFrame(self.compress_options_frame, fg_color="transparent")

        # 高级选项第一行：分辨率 + 帧率
        advanced_row1 = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        advanced_row1.pack(fill="x", pady=(0, 6))

        resolution_label = ctk.CTkLabel(advanced_row1, text="分辨率:")
        resolution_label.pack(side="left", padx=(0, 4))

        resolution_menu = ctk.CTkOptionMenu(
            advanced_row1,
            values=list(RESOLUTION_OPTIONS.keys()),
            variable=self.resolution_var,
            width=130,
        )
        resolution_menu.pack(side="left", padx=(0, 16))

        framerate_label = ctk.CTkLabel(advanced_row1, text="帧率:")
        framerate_label.pack(side="left", padx=(0, 4))

        framerate_menu = ctk.CTkOptionMenu(
            advanced_row1,
            values=list(FRAMERATE_OPTIONS.keys()),
            variable=self.framerate_var,
            width=120,
        )
        framerate_menu.pack(side="left")

        # 高级选项第二行：音频码率
        advanced_row2 = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        advanced_row2.pack(fill="x", pady=(0, 4))

        audio_label = ctk.CTkLabel(advanced_row2, text="音频码率:")
        audio_label.pack(side="left", padx=(0, 4))

        audio_menu = ctk.CTkOptionMenu(
            advanced_row2,
            values=list(AUDIO_BITRATE_OPTIONS.keys()),
            variable=self.audio_bitrate_var,
            width=150,
        )
        audio_menu.pack(side="left")

    def _on_compress_toggle(self):
        """
        压缩开关切换事件处理。

        开关打开时显示压缩选项容器，关闭时隐藏并同时收起高级选项面板。
        """
        if self.compress_enabled_var.get():
            self.compress_options_frame.pack(fill="x", padx=12, pady=(0, 10))
        else:
            self.compress_options_frame.pack_forget()
            # 隐藏时同时收起高级选项
            self.advanced_frame.pack_forget()
            self.advanced_visible = False
            self.advanced_toggle_button.configure(text="▶ 高级选项")

    def _on_advanced_toggle(self):
        """
        高级选项展开/收起切换。

        控制分辨率、帧率、音频码率面板的显示与隐藏，
        同时更新按钮文字（▶ / ▼）以指示当前状态。
        """
        if self.advanced_visible:
            self.advanced_frame.pack_forget()
            self.advanced_toggle_button.configure(text="▶ 高级选项")
        else:
            self.advanced_frame.pack(fill="x", pady=(0, 4))
            self.advanced_toggle_button.configure(text="▼ 高级选项")
        self.advanced_visible = not self.advanced_visible

    def _build_output_section(self, parent):
        """
        构建输出设置区域。

        包含：
          - 输出格式下拉选择（mp4 / mov / mkv / gif）
          - 输出文件路径输入框（可手动编辑）+ "保存路径"按钮

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        label = ctk.CTkLabel(
            section, text="💾 输出设置",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(anchor="w", padx=12, pady=(10, 4))

        # 第一行：格式选择
        format_row = ctk.CTkFrame(section, fg_color="transparent")
        format_row.pack(fill="x", padx=12, pady=(0, 6))

        format_label = ctk.CTkLabel(format_row, text="输出格式:")
        format_label.pack(side="left", padx=(0, 4))

        format_menu = ctk.CTkOptionMenu(
            format_row,
            values=SUPPORTED_FORMATS,
            variable=self.output_format_var,
            width=100,
        )
        format_menu.pack(side="left")

        # 第二行：保存路径
        path_row = ctk.CTkFrame(section, fg_color="transparent")
        path_row.pack(fill="x", padx=12, pady=(0, 10))

        output_entry = ctk.CTkEntry(
            path_row, textvariable=self.output_file_path, width=440,
        )
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        save_button = ctk.CTkButton(
            path_row, text="保存路径", width=100,
            command=self._on_select_output_file,
        )
        save_button.pack(side="right")

    def _build_clip_action_section(self, parent):
        """
        构建截取 Tab 的执行按钮区域。

        点击按钮后触发 self._on_run 事件（定义在 ClipHandlerMixin 中）。

        参数:
            parent: 父容器
        """
        self.run_button = ctk.CTkButton(
            parent,
            text="🚀 开始截取",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=40,
            command=self._on_run,
        )
        self.run_button.pack(fill="x", pady=(0, 12))
