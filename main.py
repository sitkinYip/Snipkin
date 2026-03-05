"""
Snipkin - 跨平台视频处理工具
基于 CustomTkinter 构建的现代化 GUI，调用本地 ffmpeg 实现视频截取、拼接与导出。
支持 macOS / Windows / Linux，通过 run.sh（macOS/Linux）或 run.bat（Windows）一键启动。
"""

import os
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# ============================================================
# 工具函数
# ============================================================

def check_ffmpeg_available() -> bool:
    """检查系统 PATH 中是否存在 ffmpeg"""
    return shutil.which("ffmpeg") is not None

def parse_timecode_to_seconds(timecode: str) -> float:
    """
    将用户输入的时间码解析为秒数。
    支持以下格式：
      - "90"       → 90 秒
      - "1:30"     → 1 分 30 秒 = 90 秒
      - "1:30:50"  → 1 时 30 分 50 秒 = 5450 秒
    """
    timecode = timecode.strip()
    if not timecode:
        raise ValueError("时间不能为空")

    parts = timecode.split(":")
    if len(parts) == 1:
        return float(parts[0])
    elif len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError(f"无法识别的时间格式: {timecode}")

def format_seconds_to_timecode(seconds: float) -> str:
    """将秒数转换为 HH:MM:SS.mmm 格式的时间码，供 ffmpeg 使用"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def get_video_duration(file_path: str) -> float | None:
    """使用 ffprobe 获取视频时长（秒），失败返回 None"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return None

# 持续时长的单位选项及其对应的秒数倍率
DURATION_UNITS = {"秒": 1, "分钟": 60, "小时": 3600}

# 需要转码的输出格式（无法使用 -c copy 直接流复制）
FORMATS_REQUIRING_TRANSCODE = {"gif"}

# 支持的输出格式列表
SUPPORTED_FORMATS = ["mp4", "mov", "mkv", "gif"]

# 拼接模式支持的输出格式（不含 gif）
CONCAT_SUPPORTED_FORMATS = ["mp4", "mov", "mkv"]

# 支持的输入视频文件扩展名（用于文件选择对话框过滤）
VIDEO_FILE_TYPES = [
    ("视频文件", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv *.webm *.ts *.m4v"),
    ("所有文件", "*.*"),
]

# 压缩质量预设：名称 → CRF 值（CRF 越小质量越高、文件越大）
COMPRESS_QUALITY_PRESETS = {
    "高质量（文件较大）": 18,
    "中质量（推荐）": 23,
    "低质量（文件最小）": 28,
}

# 分辨率选项：显示名称 → ffmpeg scale 滤镜值（-1 表示按比例自适应）
RESOLUTION_OPTIONS = {
    "原始分辨率": None,
    "1080p": "1920:-1",
    "720p": "1280:-1",
    "480p": "854:-1",
    "360p": "640:-1",
}

# 帧率选项：显示名称 → fps 数值
FRAMERATE_OPTIONS = {
    "原始帧率": None,
    "60 fps": "60",
    "30 fps": "30",
    "24 fps": "24",
    "15 fps": "15",
}

# 音频码率选项
AUDIO_BITRATE_OPTIONS = {
    "原始音频": None,
    "320k（高品质）": "320k",
    "192k（标准）": "192k",
    "128k（较小）": "128k",
    "64k（最小）": "64k",
}

# xfade 过渡效果选项：显示名称 → ffmpeg xfade transition 值
XFADE_TRANSITIONS = {
    "无过渡": None,
    "淡入淡出 (fade)": "fade",
    "向左擦除 (wipeleft)": "wipeleft",
    "向右擦除 (wiperight)": "wiperight",
    "向上擦除 (wipeup)": "wipeup",
    "向下擦除 (wipedown)": "wipedown",
    "向左滑入 (slideleft)": "slideleft",
    "向右滑入 (slideright)": "slideright",
    "圆形扩散 (circleopen)": "circleopen",
    "圆形收缩 (circleclose)": "circleclose",
    "溶解 (dissolve)": "dissolve",
    "水平切片 (hlslice)": "hlslice",
    "垂直切片 (vrslice)": "vrslice",
    "水平展开 (horzopen)": "horzopen",
    "水平合拢 (horzclose)": "horzclose",
    "垂直展开 (vertopen)": "vertopen",
    "垂直合拢 (vertclose)": "vertclose",
}
# ============================================================
# 主应用窗口
# ============================================================
class VideoClipperApp(ctk.CTk):
    """视频处理工具主窗口（截取 + 拼接）"""

    def __init__(self):
        super().__init__()

        # ---- 窗口基本设置 ----
        self.title("Snipkin - 视频处理工具")
        self.geometry("660x780")
        self.resizable(False, False)

        # 设置 macOS 风格的外观主题
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # ---- 截取 Tab 状态变量 ----
        self.input_file_path = tk.StringVar(value="")
        self.output_file_path = tk.StringVar(value="")
        self.start_time_var = tk.StringVar(value="0:00:00")
        self.end_time_var = tk.StringVar(value="")
        self.duration_value_var = tk.StringVar(value="10")
        self.duration_unit_var = tk.StringVar(value="秒")
        self.output_format_var = tk.StringVar(value="mp4")

        # ---- 截取 Tab 压缩相关状态变量 ----
        self.compress_enabled_var = tk.BooleanVar(value=False)
        self.compress_quality_var = tk.StringVar(value="中质量（推荐）")
        self.advanced_visible = False
        self.resolution_var = tk.StringVar(value="原始分辨率")
        self.framerate_var = tk.StringVar(value="原始帧率")
        self.audio_bitrate_var = tk.StringVar(value="原始音频")

        # ---- 拼接 Tab 状态变量 ----
        self.concat_file_list: list[str] = []
        self.concat_output_path = tk.StringVar(value="")
        self.concat_output_format_var = tk.StringVar(value="mp4")

        # ---- 拼接 Tab 压缩相关状态变量 ----
        self.concat_compress_enabled_var = tk.BooleanVar(value=False)
        self.concat_compress_quality_var = tk.StringVar(value="中质量（推荐）")
        self.concat_advanced_visible = False
        self.concat_resolution_var = tk.StringVar(value="原始分辨率")
        self.concat_framerate_var = tk.StringVar(value="原始帧率")
        self.concat_audio_bitrate_var = tk.StringVar(value="原始音频")

        # ---- 拼接 Tab 过渡动画状态变量 ----
        self.concat_transition_var = tk.StringVar(value="无过渡")
        self.concat_transition_duration_var = tk.StringVar(value="1.0")

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

    # ============================================================
    # UI 构建
    # ============================================================

    def _build_ui(self):
        """构建完整的用户界面（Tab 布局）"""

        # 主容器
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 视图
        self.tabview = ctk.CTkTabview(container, height=580)
        self.tabview.pack(fill="both", expand=True)

        # ---------- Tab 1: 视频截取 ----------
        clip_tab = self.tabview.add("✂️ 视频截取")
        self._build_clip_tab(clip_tab)

        # ---------- Tab 2: 视频拼接 ----------
        concat_tab = self.tabview.add("🔗 视频拼接")
        self._build_concat_tab(concat_tab)

        # ---------- 日志输出区域（两个 Tab 共享） ----------
        self._build_log_section(container)

    def _build_clip_tab(self, parent):
        """构建视频截取 Tab 的完整内容"""
        scroll_frame = ctk.CTkFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        self._build_input_section(scroll_frame)
        self._build_time_section(scroll_frame)
        self._build_compress_section(scroll_frame)
        self._build_output_section(scroll_frame)
        self._build_clip_action_section(scroll_frame)

    def _build_input_section(self, parent):
        """构建输入文件选择区域"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        label = ctk.CTkLabel(section, text="📂 输入视频文件", font=ctk.CTkFont(size=14, weight="bold"))
        label.pack(anchor="w", padx=12, pady=(10, 4))

        row = ctk.CTkFrame(section, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))

        # 文件路径显示
        path_entry = ctk.CTkEntry(row, textvariable=self.input_file_path, state="readonly", width=440)
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # 选择文件按钮
        browse_button = ctk.CTkButton(row, text="选择文件", width=100, command=self._on_select_input_file)
        browse_button.pack(side="right")

    def _build_time_section(self, parent):
        """构建时间设置区域（开始时间 + 结束时间 + 持续时长）"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        label = ctk.CTkLabel(section, text="⏱ 时间设置", font=ctk.CTkFont(size=14, weight="bold"))
        label.pack(anchor="w", padx=12, pady=(10, 4))

        # 第一行：开始时间 + 结束时间（格式 H:MM:SS）
        time_row = ctk.CTkFrame(section, fg_color="transparent")
        time_row.pack(fill="x", padx=12, pady=(0, 6))

        start_label = ctk.CTkLabel(time_row, text="开始时间:")
        start_label.pack(side="left", padx=(0, 4))

        start_entry = ctk.CTkEntry(time_row, textvariable=self.start_time_var, width=110, placeholder_text="0:00:00")
        start_entry.pack(side="left", padx=(0, 20))

        end_label = ctk.CTkLabel(time_row, text="结束时间:")
        end_label.pack(side="left", padx=(0, 4))

        end_entry = ctk.CTkEntry(time_row, textvariable=self.end_time_var, width=110, placeholder_text="留空则用持续时长")
        end_entry.pack(side="left")

        # 第二行：持续时长（数字 + 单位下拉）
        duration_row = ctk.CTkFrame(section, fg_color="transparent")
        duration_row.pack(fill="x", padx=12, pady=(0, 10))

        duration_label = ctk.CTkLabel(duration_row, text="持续时长:")
        duration_label.pack(side="left", padx=(0, 4))

        duration_entry = ctk.CTkEntry(duration_row, textvariable=self.duration_value_var, width=80, placeholder_text="10")
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
        """构建视频压缩设置区域（开关 + 质量预设 + 高级选项）"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        # 标题行：标题 + 压缩开关
        title_row = ctk.CTkFrame(section, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(10, 4))

        label = ctk.CTkLabel(title_row, text="🗜 视频压缩", font=ctk.CTkFont(size=14, weight="bold"))
        label.pack(side="left")

        compress_switch = ctk.CTkSwitch(
            title_row,
            text="启用压缩",
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
        """压缩开关切换事件：显示或隐藏压缩选项"""
        if self.compress_enabled_var.get():
            self.compress_options_frame.pack(fill="x", padx=12, pady=(0, 10))
        else:
            self.compress_options_frame.pack_forget()
            # 隐藏时同时收起高级选项
            self.advanced_frame.pack_forget()
            self.advanced_visible = False
            self.advanced_toggle_button.configure(text="▶ 高级选项")

    def _on_advanced_toggle(self):
        """高级选项展开/收起切换"""
        if self.advanced_visible:
            self.advanced_frame.pack_forget()
            self.advanced_toggle_button.configure(text="▶ 高级选项")
        else:
            self.advanced_frame.pack(fill="x", pady=(0, 4))
            self.advanced_toggle_button.configure(text="▼ 高级选项")
        self.advanced_visible = not self.advanced_visible

    def _build_output_section(self, parent):
        """构建输出设置区域（格式选择 + 保存路径）"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 12))

        label = ctk.CTkLabel(section, text="💾 输出设置", font=ctk.CTkFont(size=14, weight="bold"))
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

        output_entry = ctk.CTkEntry(path_row, textvariable=self.output_file_path, state="readonly", width=440)
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        save_button = ctk.CTkButton(path_row, text="保存路径", width=100, command=self._on_select_output_file)
        save_button.pack(side="right")

    def _build_clip_action_section(self, parent):
        """构建截取 Tab 的执行按钮区域"""
        self.run_button = ctk.CTkButton(
            parent,
            text="🚀 开始截取",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=40,
            command=self._on_run,
        )
        self.run_button.pack(fill="x", pady=(0, 12))

    # ============================================================
    # 拼接 Tab UI 构建
    # ============================================================

    def _build_concat_tab(self, parent):
        """构建视频拼接 Tab 的完整内容"""
        scroll_frame = ctk.CTkFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        self._build_concat_file_section(scroll_frame)
        self._build_concat_transition_section(scroll_frame)
        self._build_concat_compress_section(scroll_frame)
        self._build_concat_output_section(scroll_frame)
        self._build_concat_action_section(scroll_frame)

    def _build_concat_file_section(self, parent):
        """构建拼接 Tab 的多文件选择与排序区域"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

        label = ctk.CTkLabel(section, text="📂 视频文件列表", font=ctk.CTkFont(size=14, weight="bold"))
        label.pack(anchor="w", padx=12, pady=(10, 4))

        # 文件列表显示区域
        list_frame = ctk.CTkFrame(section, fg_color="transparent")
        list_frame.pack(fill="x", padx=12, pady=(0, 6))

        self.concat_listbox_frame = ctk.CTkFrame(list_frame, height=120)
        self.concat_listbox_frame.pack(fill="x")

        # 使用 Tkinter 原生 Listbox（CustomTkinter 没有 Listbox 组件）
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

        add_button = ctk.CTkButton(button_row, text="➕ 添加文件", width=100, command=self._on_concat_add_files)
        add_button.pack(side="left", padx=(0, 6))

        remove_button = ctk.CTkButton(button_row, text="🗑 移除选中", width=100, command=self._on_concat_remove_file,
                                       fg_color="#d9534f", hover_color="#c9302c")
        remove_button.pack(side="left", padx=(0, 6))

        move_up_button = ctk.CTkButton(button_row, text="⬆ 上移", width=70, command=self._on_concat_move_up)
        move_up_button.pack(side="left", padx=(0, 6))

        move_down_button = ctk.CTkButton(button_row, text="⬇ 下移", width=70, command=self._on_concat_move_down)
        move_down_button.pack(side="left", padx=(0, 6))

        clear_button = ctk.CTkButton(button_row, text="清空", width=60, command=self._on_concat_clear_files,
                                      fg_color="gray40", hover_color="gray30")
        clear_button.pack(side="left")

    def _build_concat_transition_section(self, parent):
        """构建拼接 Tab 的过渡动画设置区域"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

        label = ctk.CTkLabel(section, text="🎬 过渡动画（可选）", font=ctk.CTkFont(size=14, weight="bold"))
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
        """构建拼接 Tab 的压缩设置区域（与截取 Tab 结构一致）"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

        # 标题行：标题 + 压缩开关
        title_row = ctk.CTkFrame(section, fg_color="transparent")
        title_row.pack(fill="x", padx=12, pady=(10, 4))

        label = ctk.CTkLabel(title_row, text="🗜 视频压缩", font=ctk.CTkFont(size=14, weight="bold"))
        label.pack(side="left")

        compress_switch = ctk.CTkSwitch(
            title_row,
            text="启用压缩",
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
        self.concat_advanced_frame = ctk.CTkFrame(self.concat_compress_options_frame, fg_color="transparent")

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
        """拼接 Tab 压缩开关切换事件"""
        if self.concat_compress_enabled_var.get():
            self.concat_compress_options_frame.pack(fill="x", padx=12, pady=(0, 10))
        else:
            self.concat_compress_options_frame.pack_forget()
            self.concat_advanced_frame.pack_forget()
            self.concat_advanced_visible = False
            self.concat_advanced_toggle_button.configure(text="▶ 高级选项")

    def _on_concat_advanced_toggle(self):
        """拼接 Tab 高级选项展开/收起切换"""
        if self.concat_advanced_visible:
            self.concat_advanced_frame.pack_forget()
            self.concat_advanced_toggle_button.configure(text="▶ 高级选项")
        else:
            self.concat_advanced_frame.pack(fill="x", pady=(0, 4))
            self.concat_advanced_toggle_button.configure(text="▼ 高级选项")
        self.concat_advanced_visible = not self.concat_advanced_visible

    def _build_concat_output_section(self, parent):
        """构建拼接 Tab 的输出设置区域"""
        section = ctk.CTkFrame(parent)
        section.pack(fill="x", pady=(0, 10))

        label = ctk.CTkLabel(section, text="💾 输出设置", font=ctk.CTkFont(size=14, weight="bold"))
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

        output_entry = ctk.CTkEntry(path_row, textvariable=self.concat_output_path, state="readonly", width=440)
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        save_button = ctk.CTkButton(path_row, text="保存路径", width=100, command=self._on_concat_select_output)
        save_button.pack(side="right")

    def _build_concat_action_section(self, parent):
        """构建拼接 Tab 的执行按钮区域"""
        self.concat_run_button = ctk.CTkButton(
            parent,
            text="🚀 开始拼接",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=40,
            command=self._on_concat_run,
        )
        self.concat_run_button.pack(fill="x", pady=(0, 10))

    def _build_log_section(self, parent):
        """构建日志输出区域"""
        label = ctk.CTkLabel(parent, text="📋 执行日志", font=ctk.CTkFont(size=14, weight="bold"))
        label.pack(anchor="w", pady=(0, 4))

        self.log_textbox = ctk.CTkTextbox(parent, height=120, state="disabled", wrap="word")
        self.log_textbox.pack(fill="both", expand=True)

    # ============================================================
    # 事件处理
    # ============================================================

    def _on_select_input_file(self):
        """处理截取 Tab "选择文件"按钮点击事件"""
        file_path = filedialog.askopenfilename(
            title="选择输入视频文件",
            filetypes=VIDEO_FILE_TYPES,
        )
        if file_path:
            self.input_file_path.set(file_path)
            self._log(f"已选择输入文件: {file_path}")

            # 自动根据输入文件名生成默认输出路径
            directory = os.path.dirname(file_path)
            basename = os.path.splitext(os.path.basename(file_path))[0]
            output_format = self.output_format_var.get()
            default_output = os.path.join(directory, f"{basename}_clip.{output_format}")
            self.output_file_path.set(default_output)

    def _on_select_output_file(self):
        """处理截取 Tab "保存路径"按钮点击事件"""
        output_format = self.output_format_var.get()
        file_path = filedialog.asksaveasfilename(
            title="选择输出文件保存位置",
            defaultextension=f".{output_format}",
            filetypes=[(f"{output_format.upper()} 文件", f"*.{output_format}"), ("所有文件", "*.*")],
        )
        if file_path:
            self.output_file_path.set(file_path)
            self._log(f"输出路径已设置: {file_path}")

    def _on_run(self):
        """处理"开始截取"按钮点击事件，校验参数后在子线程中执行 ffmpeg"""

        # ---- 参数校验 ----
        if not check_ffmpeg_available():
            self._log("❌ 错误: 未检测到 ffmpeg，请先安装。")
            return

        input_path = self.input_file_path.get().strip()
        if not input_path or not os.path.isfile(input_path):
            self._log("❌ 错误: 请先选择一个有效的输入视频文件。")
            return

        output_path = self.output_file_path.get().strip()
        if not output_path:
            self._log("❌ 错误: 请先设置输出文件保存路径。")
            return

        # 解析开始时间（支持 H:MM:SS / MM:SS / SS 格式）
        try:
            start_seconds = parse_timecode_to_seconds(self.start_time_var.get())
            if start_seconds < 0:
                raise ValueError("开始时间不能为负数")
        except ValueError as error:
            self._log(f"❌ 错误: 开始时间格式无效（支持 H:MM:SS / MM:SS / 秒数）。{error}")
            return

        # 优先使用结束时间，否则使用持续时长
        end_time_text = self.end_time_var.get().strip()
        if end_time_text:
            # 用户填写了结束时间，计算持续时长
            try:
                end_seconds = parse_timecode_to_seconds(end_time_text)
                if end_seconds <= start_seconds:
                    self._log("❌ 错误: 结束时间必须大于开始时间。")
                    return
                duration_seconds = end_seconds - start_seconds
            except ValueError as error:
                self._log(f"❌ 错误: 结束时间格式无效（支持 H:MM:SS / MM:SS / 秒数）。{error}")
                return
        else:
            # 使用持续时长 + 单位
            try:
                duration_value = float(self.duration_value_var.get().strip())
                if duration_value <= 0:
                    raise ValueError("持续时长必须大于 0")
                unit_multiplier = DURATION_UNITS[self.duration_unit_var.get()]
                duration_seconds = duration_value * unit_multiplier
            except ValueError:
                self._log("❌ 错误: 持续时长必须是一个正数。")
                return

        # ---- 构建 ffmpeg 命令 ----
        output_format = self.output_format_var.get()
        command = self._build_ffmpeg_command(
            input_path=input_path,
            output_path=output_path,
            start_seconds=start_seconds,
            duration_seconds=duration_seconds,
            output_format=output_format,
        )

        self._log(f"▶ 执行命令: {' '.join(command)}")

        # 禁用按钮，防止重复点击
        self.run_button.configure(state="disabled", text="⏳ 处理中...")

        # 在子线程中执行 ffmpeg，避免阻塞 UI
        thread = threading.Thread(target=self._execute_ffmpeg, args=(command,), daemon=True)
        thread.start()

    # ============================================================
    # 核心逻辑
    # ============================================================

    def _build_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        duration_seconds: float,
        output_format: str,
    ) -> list[str]:
        """
        根据用户参数构建 ffmpeg 命令列表。

        构建策略：
          - GIF 格式：使用专用滤镜链
          - 压缩开启：使用 libx264 + CRF 转码，可叠加分辨率/帧率/音频码率
          - 其他情况：使用 -c copy 流复制（最快）
        """
        start_timecode = format_seconds_to_timecode(start_seconds)
        duration_timecode = format_seconds_to_timecode(duration_seconds)

        # 基础命令：覆盖输出 + 定位 + 时长 + 输入
        command = [
            "ffmpeg",
            "-y",
            "-ss", start_timecode,
            "-t", duration_timecode,
            "-i", input_path,
        ]

        if output_format in FORMATS_REQUIRING_TRANSCODE:
            # GIF 需要特殊处理：使用调色板滤镜以获得更好的画质
            command.extend([
                "-vf", "fps=15,scale=480:-1:flags=lanczos",
                "-gifflags", "+transdiff",
            ])
        elif self.compress_enabled_var.get():
            # 压缩模式：使用 H.264 编码 + CRF 质量控制
            crf_value = COMPRESS_QUALITY_PRESETS[self.compress_quality_var.get()]
            command.extend(["-c:v", "libx264", "-crf", str(crf_value), "-preset", "medium"])

            # 构建视频滤镜链（分辨率 + 帧率可叠加）
            video_filters = self._build_video_filters()
            if video_filters:
                command.extend(["-vf", ",".join(video_filters)])

            # 音频码率设置
            audio_bitrate = AUDIO_BITRATE_OPTIONS[self.audio_bitrate_var.get()]
            if audio_bitrate:
                command.extend(["-b:a", audio_bitrate])
            else:
                command.extend(["-c:a", "aac"])
        else:
            # 不压缩：流复制（速度最快，无质量损失）
            command.extend(["-c", "copy"])

        command.append(output_path)
        return command

    def _build_video_filters(self) -> list[str]:
        """
        根据高级选项构建视频滤镜列表。
        分辨率和帧率可以叠加使用。
        """
        filters = []

        # 分辨率缩放
        scale_value = RESOLUTION_OPTIONS[self.resolution_var.get()]
        if scale_value:
            filters.append(f"scale={scale_value}")

        # 帧率限制
        fps_value = FRAMERATE_OPTIONS[self.framerate_var.get()]
        if fps_value:
            filters.append(f"fps={fps_value}")

        return filters

    def _execute_ffmpeg(self, command: list[str]):
        """
        在子线程中执行 ffmpeg 命令，并将输出实时写入日志区域。
        执行完成后恢复按钮状态。
        """
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600,  # 最长等待 10 分钟
            )

            if process.returncode == 0:
                output_path = self.output_file_path.get()
                self._log_threadsafe(f"✅ 截取成功！输出文件: {output_path}")
            else:
                # ffmpeg 的错误信息通常输出到 stderr
                error_message = process.stderr.strip() if process.stderr else "未知错误"
                self._log_threadsafe(f"❌ ffmpeg 执行失败 (返回码 {process.returncode}):\n{error_message}")

        except subprocess.TimeoutExpired:
            self._log_threadsafe("❌ 错误: ffmpeg 执行超时（超过 10 分钟），已终止。")
        except FileNotFoundError:
            self._log_threadsafe("❌ 错误: 无法找到 ffmpeg 可执行文件。")
        except Exception as unexpected_error:
            self._log_threadsafe(f"❌ 发生意外错误: {unexpected_error}")
        finally:
            # 恢复按钮状态（必须在主线程中操作 UI）
            self.after(0, lambda: self.run_button.configure(state="normal", text="🚀 开始截取"))

    # ============================================================
    # 拼接 Tab 事件处理
    # ============================================================

    def _on_concat_add_files(self):
        """处理拼接 Tab "添加文件"按钮点击事件，支持多选"""
        file_paths = filedialog.askopenfilenames(
            title="选择要拼接的视频文件（可多选）",
            filetypes=VIDEO_FILE_TYPES,
        )
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.concat_file_list:
                    self.concat_file_list.append(file_path)
            self._refresh_concat_listbox()
            self._log(f"已添加 {len(file_paths)} 个文件，当前共 {len(self.concat_file_list)} 个")

            # 自动生成默认输出路径（基于第一个文件的目录）
            if self.concat_file_list and not self.concat_output_path.get():
                first_file = self.concat_file_list[0]
                directory = os.path.dirname(first_file)
                output_format = self.concat_output_format_var.get()
                default_output = os.path.join(directory, f"merged_output.{output_format}")
                self.concat_output_path.set(default_output)

    def _on_concat_remove_file(self):
        """移除拼接列表中选中的文件"""
        selection = self.concat_listbox.curselection()
        if not selection:
            self._log("⚠️ 请先在列表中选中要移除的文件。")
            return
        index = selection[0]
        removed_file = self.concat_file_list.pop(index)
        self._refresh_concat_listbox()
        self._log(f"已移除: {os.path.basename(removed_file)}")

    def _on_concat_move_up(self):
        """将选中的文件在列表中上移一位"""
        selection = self.concat_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index <= 0:
            return
        self.concat_file_list[index], self.concat_file_list[index - 1] = (
            self.concat_file_list[index - 1], self.concat_file_list[index]
        )
        self._refresh_concat_listbox()
        self.concat_listbox.selection_set(index - 1)

    def _on_concat_move_down(self):
        """将选中的文件在列表中下移一位"""
        selection = self.concat_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(self.concat_file_list) - 1:
            return
        self.concat_file_list[index], self.concat_file_list[index + 1] = (
            self.concat_file_list[index + 1], self.concat_file_list[index]
        )
        self._refresh_concat_listbox()
        self.concat_listbox.selection_set(index + 1)

    def _on_concat_clear_files(self):
        """清空拼接文件列表"""
        self.concat_file_list.clear()
        self._refresh_concat_listbox()
        self._log("已清空文件列表。")

    def _refresh_concat_listbox(self):
        """刷新拼接文件列表的显示内容"""
        self.concat_listbox.delete(0, tk.END)
        for index, file_path in enumerate(self.concat_file_list):
            display_name = f"{index + 1}. {os.path.basename(file_path)}"
            self.concat_listbox.insert(tk.END, display_name)

    def _on_concat_select_output(self):
        """处理拼接 Tab "保存路径"按钮点击事件"""
        output_format = self.concat_output_format_var.get()
        file_path = filedialog.asksaveasfilename(
            title="选择拼接输出文件保存位置",
            defaultextension=f".{output_format}",
            filetypes=[(f"{output_format.upper()} 文件", f"*.{output_format}"), ("所有文件", "*.*")],
        )
        if file_path:
            self.concat_output_path.set(file_path)
            self._log(f"拼接输出路径已设置: {file_path}")

    def _on_concat_run(self):
        """处理"开始拼接"按钮点击事件，校验参数后在子线程中执行 ffmpeg"""

        # ---- 参数校验 ----
        if not check_ffmpeg_available():
            self._log("❌ 错误: 未检测到 ffmpeg，请先安装。")
            return

        if len(self.concat_file_list) < 2:
            self._log("❌ 错误: 请至少添加 2 个视频文件进行拼接。")
            return

        for file_path in self.concat_file_list:
            if not os.path.isfile(file_path):
                self._log(f"❌ 错误: 文件不存在: {file_path}")
                return

        output_path = self.concat_output_path.get().strip()
        if not output_path:
            self._log("❌ 错误: 请先设置输出文件保存路径。")
            return

        # 解析过渡动画参数
        transition_name = XFADE_TRANSITIONS[self.concat_transition_var.get()]
        transition_duration = 0.0
        if transition_name:
            try:
                transition_duration = float(self.concat_transition_duration_var.get().strip())
                if transition_duration <= 0:
                    raise ValueError("过渡时长必须大于 0")
            except ValueError:
                self._log("❌ 错误: 过渡时长必须是一个正数（秒）。")
                return

        # 获取每个视频的时长（xfade 需要知道每段视频的时长来计算 offset）
        if transition_name:
            self._log("⏳ 正在获取视频时长信息...")
            durations = []
            for file_path in self.concat_file_list:
                duration = get_video_duration(file_path)
                if duration is None:
                    self._log(f"❌ 错误: 无法获取视频时长: {os.path.basename(file_path)}，请确保 ffprobe 可用。")
                    return
                durations.append(duration)
                self._log(f"  📎 {os.path.basename(file_path)}: {duration:.2f}s")
        else:
            durations = []

        # ---- 构建 ffmpeg 命令 ----
        command = self._build_concat_ffmpeg_command(
            file_list=self.concat_file_list,
            output_path=output_path,
            transition_name=transition_name,
            transition_duration=transition_duration,
            durations=durations,
        )

        self._log(f"▶ 执行命令: {' '.join(command)}")

        # 禁用按钮，防止重复点击
        self.concat_run_button.configure(state="disabled", text="⏳ 处理中...")

        # 在子线程中执行
        thread = threading.Thread(
            target=self._execute_concat_ffmpeg, args=(command,), daemon=True
        )
        thread.start()

    # ============================================================
    # 拼接核心逻辑
    # ============================================================

    def _build_concat_ffmpeg_command(
        self,
        file_list: list[str],
        output_path: str,
        transition_name: str | None,
        transition_duration: float,
        durations: list[float],
    ) -> list[str]:
        """
        构建视频拼接的 ffmpeg 命令。

        策略：
          - 有过渡动画：使用 xfade 滤镜链逐段拼接视频 + acrossfade 拼接音频
          - 无过渡动画 + 无压缩：使用 concat demuxer（最快）
          - 无过渡动画 + 有压缩：使用 concat 滤镜 + 编码参数
        """
        if transition_name:
            return self._build_xfade_command(
                file_list, output_path, transition_name, transition_duration, durations
            )
        elif self.concat_compress_enabled_var.get():
            return self._build_concat_filter_command(file_list, output_path)
        else:
            return self._build_concat_demuxer_command(file_list, output_path)

    def _build_xfade_command(
        self,
        file_list: list[str],
        output_path: str,
        transition_name: str,
        transition_duration: float,
        durations: list[float],
    ) -> list[str]:
        """
        使用 xfade 滤镜构建带过渡动画的拼接命令。
        每两段视频之间插入一个 xfade 过渡，音频使用 acrossfade 对应衔接。
        """
        file_count = len(file_list)

        # 输入文件参数
        command = ["ffmpeg", "-y"]
        for file_path in file_list:
            command.extend(["-i", file_path])

        # 构建 xfade 视频滤镜链
        video_filter_parts = []
        audio_filter_parts = []

        # 计算每个过渡点的 offset（前一段视频结束前 transition_duration 秒开始过渡）
        # offset_i = sum(durations[0..i]) - i * transition_duration - transition_duration
        cumulative_offset = 0.0

        for i in range(file_count - 1):
            if i == 0:
                video_input_a = "[0:v]"
                audio_input_a = "[0:a]"
            else:
                video_input_a = f"[vfade{i}]"
                audio_input_a = f"[afade{i}]"

            video_input_b = f"[{i + 1}:v]"
            audio_input_b = f"[{i + 1}:a]"

            # offset = 前面所有视频的总时长 - 前面所有过渡占用的时长 - 当前过渡时长
            cumulative_offset = sum(durations[:i + 1]) - i * transition_duration - transition_duration

            if cumulative_offset < 0:
                cumulative_offset = 0

            if i < file_count - 2:
                video_output = f"[vfade{i + 1}]"
                audio_output = f"[afade{i + 1}]"
            else:
                video_output = "[vout]"
                audio_output = "[aout]"

            video_filter_parts.append(
                f"{video_input_a}{video_input_b}xfade=transition={transition_name}"
                f":duration={transition_duration}:offset={cumulative_offset:.3f}{video_output}"
            )
            audio_filter_parts.append(
                f"{audio_input_a}{audio_input_b}acrossfade=d={transition_duration}{audio_output}"
            )

        # 如果启用了压缩的高级选项（分辨率/帧率），需要将滤镜追加到 filter_complex 链末尾
        # 因为 ffmpeg 不允许 -filter_complex 和 -vf 同时作用于同一个流
        extra_video_filters = []
        if self.concat_compress_enabled_var.get():
            extra_video_filters = self._build_concat_video_filters()

        if extra_video_filters:
            # 将 [vout] 改为中间标签，追加 scale/fps 滤镜后再输出 [vout]
            filter_complex = ";".join(video_filter_parts + audio_filter_parts)
            filter_complex = filter_complex.replace("[vout]", "[vpre]", 1)
            extra_chain = f"[vpre]{','.join(extra_video_filters)}[vout]"
            filter_complex = filter_complex + ";" + extra_chain
        else:
            filter_complex = ";".join(video_filter_parts + audio_filter_parts)

        command.extend(["-filter_complex", filter_complex])
        command.extend(["-map", "[vout]", "-map", "[aout]"])

        # 添加编码参数（xfade 必须转码）
        if self.concat_compress_enabled_var.get():
            crf_value = COMPRESS_QUALITY_PRESETS[self.concat_compress_quality_var.get()]
            command.extend(["-c:v", "libx264", "-crf", str(crf_value), "-preset", "medium"])

            audio_bitrate = AUDIO_BITRATE_OPTIONS[self.concat_audio_bitrate_var.get()]
            if audio_bitrate:
                command.extend(["-b:a", audio_bitrate])
            else:
                command.extend(["-c:a", "aac"])
        else:
            command.extend(["-c:v", "libx264", "-crf", "18", "-preset", "medium"])
            command.extend(["-c:a", "aac"])

        command.append(output_path)
        return command

    def _build_concat_filter_command(self, file_list: list[str], output_path: str) -> list[str]:
        """
        使用 concat 滤镜构建拼接命令（无过渡动画 + 有压缩）。
        """
        file_count = len(file_list)

        command = ["ffmpeg", "-y"]
        for file_path in file_list:
            command.extend(["-i", file_path])

        # concat 滤镜 + 可选的 scale/fps 滤镜（合并到 filter_complex 中）
        input_labels = "".join(f"[{i}:v][{i}:a]" for i in range(file_count))
        video_filters = self._build_concat_video_filters()

        if video_filters:
            # 有额外滤镜时：concat 输出到中间标签，再追加 scale/fps
            filter_complex = (
                f"{input_labels}concat=n={file_count}:v=1:a=1[vpre][aout];"
                f"[vpre]{','.join(video_filters)}[vout]"
            )
        else:
            filter_complex = f"{input_labels}concat=n={file_count}:v=1:a=1[vout][aout]"

        command.extend(["-filter_complex", filter_complex])
        command.extend(["-map", "[vout]", "-map", "[aout]"])

        # 压缩参数
        crf_value = COMPRESS_QUALITY_PRESETS[self.concat_compress_quality_var.get()]
        command.extend(["-c:v", "libx264", "-crf", str(crf_value), "-preset", "medium"])

        audio_bitrate = AUDIO_BITRATE_OPTIONS[self.concat_audio_bitrate_var.get()]
        if audio_bitrate:
            command.extend(["-b:a", audio_bitrate])
        else:
            command.extend(["-c:a", "aac"])

        command.append(output_path)
        return command

    def _build_concat_demuxer_command(self, file_list: list[str], output_path: str) -> list[str]:
        """
        使用 concat demuxer 构建拼接命令（无过渡动画 + 无压缩，速度最快）。
        通过临时文件列表实现。
        """
        concat_list_content = "\n".join(
            f"file '{file_path}'" for file_path in file_list
        )
        # 创建临时文件
        self._concat_temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="snipkin_concat_"
        )
        self._concat_temp_file.write(concat_list_content)
        self._concat_temp_file.close()

        command = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", self._concat_temp_file.name,
            "-c", "copy",
            output_path,
        ]
        return command

    def _build_concat_video_filters(self) -> list[str]:
        """根据拼接 Tab 的高级选项构建视频滤镜列表"""
        filters = []

        scale_value = RESOLUTION_OPTIONS[self.concat_resolution_var.get()]
        if scale_value:
            filters.append(f"scale={scale_value}")

        fps_value = FRAMERATE_OPTIONS[self.concat_framerate_var.get()]
        if fps_value:
            filters.append(f"fps={fps_value}")

        return filters

    def _execute_concat_ffmpeg(self, command: list[str]):
        """在子线程中执行拼接 ffmpeg 命令"""
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1800,  # 拼接可能较慢，最长等待 30 分钟
            )

            if process.returncode == 0:
                output_path = self.concat_output_path.get()
                self._log_threadsafe(f"✅ 拼接成功！输出文件: {output_path}")
            else:
                error_message = process.stderr.strip() if process.stderr else "未知错误"
                self._log_threadsafe(f"❌ ffmpeg 拼接失败 (返回码 {process.returncode}):\n{error_message}")

        except subprocess.TimeoutExpired:
            self._log_threadsafe("❌ 错误: ffmpeg 执行超时（超过 30 分钟），已终止。")
        except FileNotFoundError:
            self._log_threadsafe("❌ 错误: 无法找到 ffmpeg 可执行文件。")
        except Exception as unexpected_error:
            self._log_threadsafe(f"❌ 发生意外错误: {unexpected_error}")
        finally:
            # 恢复按钮状态
            self.after(0, lambda: self.concat_run_button.configure(state="normal", text="🚀 开始拼接"))
            # 清理临时文件
            if hasattr(self, "_concat_temp_file") and self._concat_temp_file:
                try:
                    os.unlink(self._concat_temp_file.name)
                except OSError:
                    pass

    # ============================================================
    # 日志工具方法
    # ============================================================

    def _log(self, message: str):
        """向日志文本框追加一行消息（主线程调用）"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _log_threadsafe(self, message: str):
        """线程安全的日志方法，通过 after() 调度到主线程执行"""
        self.after(0, lambda: self._log(message))


# ============================================================
# 程序入口
# ============================================================

def main():
    """应用程序入口"""
    app = VideoClipperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
