"""
snipkin.ui.concat_tab - 视频拼接 Tab 的界面构建

本模块定义 ConcatTabMixin 类，以 Mixin 模式提供视频拼接 Tab 的所有 UI 构建方法。
通过多继承混入 VideoClipperApp 主窗口类中使用。

包含的 UI 区域：
- 多文件选择与排序区域（文件列表 + 添加/移除/上移/下移/清空按钮）
- 过渡动画设置区域（效果选择 + 过渡时长）
- 视频压缩设置区域（与截取 Tab 结构一致）
- 输出设置区域（格式选择 + 保存路径）
- 执行按钮区域

设计说明：
  拼接 Tab 的压缩设置与截取 Tab 结构相同，但使用独立的状态变量
  （以 concat_ 前缀区分），互不干扰。
"""

import tkinter as tk

import customtkinter as ctk

from snipkin.constants import (
    AUDIO_BITRATE_OPTIONS,
    COMPRESS_QUALITY_PRESETS,
    CONCAT_SUPPORTED_FORMATS,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
    XFADE_TRANSITIONS,
)


class ConcatTabMixin:
    """
    视频拼接 Tab 的 UI 构建 Mixin。

    提供拼接 Tab 中所有界面元素的构建方法，以及压缩开关、高级选项展开/收起的交互逻辑。
    混入 VideoClipperApp 后，通过 self 访问主窗口实例的属性和方法。
    """

    def _build_concat_tab(self, parent):
        """
        构建视频拼接 Tab 的完整内容。

        按从上到下的顺序依次构建：文件列表 → 过渡动画 → 压缩设置 → 输出设置 → 执行按钮。

        参数:
            parent: 父容器（Tab 页面的根 Frame）
        """
        scroll_frame = ctk.CTkFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        self._build_concat_file_section(scroll_frame)
        self._build_concat_transition_section(scroll_frame)
        self._build_concat_compress_section(scroll_frame)
        self._build_concat_output_section(scroll_frame)
        self._build_concat_action_section(scroll_frame)

    def _build_concat_file_section(self, parent):
        """
        构建拼接 Tab 的多文件选择与排序区域。

        包含：
          - 文件列表显示区域（使用原生 Tkinter Listbox，因为 CustomTkinter 没有 Listbox 组件）
          - 操作按钮行：添加文件、移除选中、上移、下移、清空

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

        label = ctk.CTkLabel(
            section, text="📂 视频文件列表",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(anchor="w", padx=12, pady=(10, 4))

        # 文件列表显示区域
        list_frame = ctk.CTkFrame(section, fg_color="transparent")
        list_frame.pack(fill="x", padx=12, pady=(0, 6))

        self.concat_listbox_frame = ctk.CTkFrame(list_frame, height=120)
        self.concat_listbox_frame.pack(fill="x")

        # 使用 Tkinter 原生 Listbox（深色主题适配）
        self.concat_listbox = tk.Listbox(
            self.concat_listbox_frame,
            height=5,
            selectmode=tk.SINGLE,
            bg="#2b2b2b", fg="#dcdcdc",
            selectbackground="#1f6aa5", selectforeground="white",
            font=("SF Pro", 12),
            relief="flat", borderwidth=0,
            highlightthickness=0,
        )
        self.concat_listbox.pack(fill="x", padx=2, pady=2)

        # 操作按钮行
        button_row = ctk.CTkFrame(section, fg_color="transparent")
        button_row.pack(fill="x", padx=12, pady=(0, 10))

        add_button = ctk.CTkButton(
            button_row, text="➕ 添加文件", width=100,
            command=self._on_concat_add_files,
        )
        add_button.pack(side="left", padx=(0, 6))

        remove_button = ctk.CTkButton(
            button_row, text="🗑 移除选中", width=100,
            command=self._on_concat_remove_file,
            fg_color="#d9534f", hover_color="#c9302c",
        )
        remove_button.pack(side="left", padx=(0, 6))

        move_up_button = ctk.CTkButton(
            button_row, text="⬆ 上移", width=70,
            command=self._on_concat_move_up,
        )
        move_up_button.pack(side="left", padx=(0, 6))

        move_down_button = ctk.CTkButton(
            button_row, text="⬇ 下移", width=70,
            command=self._on_concat_move_down,
        )
        move_down_button.pack(side="left", padx=(0, 6))

        clear_button = ctk.CTkButton(
            button_row, text="清空", width=60,
            command=self._on_concat_clear_files,
            fg_color="gray40", hover_color="gray30",
        )
        clear_button.pack(side="left")

    def _build_concat_transition_section(self, parent):
        """
        构建拼接 Tab 的过渡动画设置区域。

        包含：
          - 过渡效果下拉选择（16 种 xfade 效果 + "无过渡"）
          - 过渡时长输入框（秒）

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

        label = ctk.CTkLabel(
            section, text="🎬 过渡动画（可选）",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(anchor="w", padx=12, pady=(10, 4))

        options_row = ctk.CTkFrame(section, fg_color="transparent")
        options_row.pack(fill="x", padx=12, pady=(0, 10))

        effect_label = ctk.CTkLabel(options_row, text="过渡效果:")
        effect_label.pack(side="left", padx=(0, 4))

        transition_menu = ctk.CTkOptionMenu(
            options_row,
            values=list(XFADE_TRANSITIONS.keys()),
            variable=self.concat_transition_var,
            width=220,
        )
        transition_menu.pack(side="left", padx=(0, 16))

        duration_label = ctk.CTkLabel(options_row, text="过渡时长(秒):")
        duration_label.pack(side="left", padx=(0, 4))

        duration_entry = ctk.CTkEntry(
            options_row,
            textvariable=self.concat_transition_duration_var,
            width=60,
            placeholder_text="1.0",
        )
        duration_entry.pack(side="left")

    def _build_concat_compress_section(self, parent):
        """
        构建拼接 Tab 的压缩设置区域。

        结构与截取 Tab 的压缩设置完全一致，但使用 concat_ 前缀的独立状态变量，
        确保两个 Tab 的压缩设置互不干扰。

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

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
            variable=self.concat_compress_enabled_var,
            command=self._on_concat_compress_toggle,
        )
        compress_switch.pack(side="right")

        # 压缩选项容器（默认隐藏）
        self.concat_compress_options_frame = ctk.CTkFrame(section, fg_color="transparent")

        # 质量预设下拉
        quality_row = ctk.CTkFrame(self.concat_compress_options_frame, fg_color="transparent")
        quality_row.pack(fill="x", padx=0, pady=(0, 6))

        quality_label = ctk.CTkLabel(quality_row, text="压缩质量:")
        quality_label.pack(side="left", padx=(0, 4))

        quality_menu = ctk.CTkOptionMenu(
            quality_row,
            values=list(COMPRESS_QUALITY_PRESETS.keys()),
            variable=self.concat_compress_quality_var,
            width=200,
        )
        quality_menu.pack(side="left", padx=(0, 12))

        # 高级选项展开按钮
        self.concat_advanced_toggle_button = ctk.CTkButton(
            quality_row,
            text="▶ 高级选项",
            width=100,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray28"),
            command=self._on_concat_advanced_toggle,
        )
        self.concat_advanced_toggle_button.pack(side="left")

        # 高级选项面板（默认隐藏）
        self.concat_advanced_frame = ctk.CTkFrame(
            self.concat_compress_options_frame, fg_color="transparent",
        )

        # 高级选项第一行：分辨率 + 帧率
        advanced_row1 = ctk.CTkFrame(self.concat_advanced_frame, fg_color="transparent")
        advanced_row1.pack(fill="x", pady=(0, 6))

        resolution_label = ctk.CTkLabel(advanced_row1, text="分辨率:")
        resolution_label.pack(side="left", padx=(0, 4))

        resolution_menu = ctk.CTkOptionMenu(
            advanced_row1,
            values=list(RESOLUTION_OPTIONS.keys()),
            variable=self.concat_resolution_var,
            width=130,
        )
        resolution_menu.pack(side="left", padx=(0, 16))

        framerate_label = ctk.CTkLabel(advanced_row1, text="帧率:")
        framerate_label.pack(side="left", padx=(0, 4))

        framerate_menu = ctk.CTkOptionMenu(
            advanced_row1,
            values=list(FRAMERATE_OPTIONS.keys()),
            variable=self.concat_framerate_var,
            width=120,
        )
        framerate_menu.pack(side="left")

        # 高级选项第二行：音频码率
        advanced_row2 = ctk.CTkFrame(self.concat_advanced_frame, fg_color="transparent")
        advanced_row2.pack(fill="x", pady=(0, 4))

        audio_label = ctk.CTkLabel(advanced_row2, text="音频码率:")
        audio_label.pack(side="left", padx=(0, 4))

        audio_menu = ctk.CTkOptionMenu(
            advanced_row2,
            values=list(AUDIO_BITRATE_OPTIONS.keys()),
            variable=self.concat_audio_bitrate_var,
            width=150,
        )
        audio_menu.pack(side="left")

    def _on_concat_compress_toggle(self):
        """
        拼接 Tab 压缩开关切换事件处理。

        开关打开时显示压缩选项容器，关闭时隐藏并同时收起高级选项面板。
        """
        if self.concat_compress_enabled_var.get():
            self.concat_compress_options_frame.pack(fill="x", padx=12, pady=(0, 10))
        else:
            self.concat_compress_options_frame.pack_forget()
            self.concat_advanced_frame.pack_forget()
            self.concat_advanced_visible = False
            self.concat_advanced_toggle_button.configure(text="▶ 高级选项")

    def _on_concat_advanced_toggle(self):
        """
        拼接 Tab 高级选项展开/收起切换。

        控制分辨率、帧率、音频码率面板的显示与隐藏，
        同时更新按钮文字（▶ / ▼）以指示当前状态。
        """
        if self.concat_advanced_visible:
            self.concat_advanced_frame.pack_forget()
            self.concat_advanced_toggle_button.configure(text="▶ 高级选项")
        else:
            self.concat_advanced_frame.pack(fill="x", pady=(0, 4))
            self.concat_advanced_toggle_button.configure(text="▼ 高级选项")
        self.concat_advanced_visible = not self.concat_advanced_visible

    def _build_concat_output_section(self, parent):
        """
        构建拼接 Tab 的输出设置区域。

        包含：
          - 输出格式下拉选择（mp4 / mov / mkv，不含 gif）
          - 输出文件路径输入框 + "保存路径"按钮

        参数:
            parent: 父容器
        """
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

        label = ctk.CTkLabel(
            section, text="💾 输出设置",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(anchor="w", padx=12, pady=(10, 4))

        # 格式选择
        format_row = ctk.CTkFrame(section, fg_color="transparent")
        format_row.pack(fill="x", padx=12, pady=(0, 6))

        format_label = ctk.CTkLabel(format_row, text="输出格式:")
        format_label.pack(side="left", padx=(0, 4))

        format_menu = ctk.CTkOptionMenu(
            format_row,
            values=CONCAT_SUPPORTED_FORMATS,
            variable=self.concat_output_format_var,
            width=100,
        )
        format_menu.pack(side="left")

        # 保存路径
        path_row = ctk.CTkFrame(section, fg_color="transparent")
        path_row.pack(fill="x", padx=12, pady=(0, 10))

        output_entry = ctk.CTkEntry(
            path_row, textvariable=self.concat_output_path, width=440,
        )
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        save_button = ctk.CTkButton(
            path_row, text="保存路径", width=100,
            command=self._on_concat_select_output,
        )
        save_button.pack(side="right")

    def _build_concat_action_section(self, parent):
        """
        构建拼接 Tab 的执行按钮区域。

        点击按钮后触发 self._on_concat_run 事件（定义在 ConcatHandlerMixin 中）。

        参数:
            parent: 父容器
        """
        self.concat_run_button = ctk.CTkButton(
            parent,
            text="🚀 开始拼接",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=40,
            command=self._on_concat_run,
        )
        self.concat_run_button.pack(fill="x", pady=(0, 10))
