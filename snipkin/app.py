"""
snipkin.app - 主应用构建

本模块提供 build_app 函数，负责：
  1. 配置 Flet Page 的窗口属性
  2. 初始化所有应用状态
  3. 构建 iOS 风格的毛玻璃 UI 骨架（渐变背景 + 模糊层 + Tabs + 日志区）
  4. 启动时检测 ffmpeg 可用性

架构设计：
  从 CustomTkinter 的 Mixin 多继承模式迁移为 Flet 的函数式组合模式。
  所有状态存储在 AppState 数据类中，通过参数传递给各 UI 构建函数和事件处理函数。
  core 层（clip_core / concat_core）和工具层（utils）保持不变。

视觉设计：
  - 主背景：深色渐变 Container
  - 毛玻璃层：ft.Blur(sigma_x=30, sigma_y=30) 覆盖
  - 配色：极简深灰暗黑模式 + Apple 蓝色高光按钮
  - 图标：全部使用 ft.cupertino_icons
  - 布局：顶部 Tabs（Segmented Control 风格）→ 中间功能区 → 底部日志区
"""

from dataclasses import dataclass, field

import flet as ft

from snipkin.utils import check_ffmpeg_available


# ============================================================
# 颜色常量（iOS 暗黑模式风格）
# ============================================================

BACKGROUND_GRADIENT_START = "#1a1a2e"
BACKGROUND_GRADIENT_END = "#16213e"
SURFACE_COLOR = "#1e1e1e"
SURFACE_ELEVATED_COLOR = "#2a2a2a"
TEXT_PRIMARY_COLOR = "#f0f0f0"
TEXT_SECONDARY_COLOR = "#8e8e93"
ACCENT_BLUE = "#0a84ff"
ACCENT_BLUE_HOVER = "#409cff"
DIVIDER_COLOR = "#3a3a3c"
LOG_BACKGROUND_COLOR = "#1c1c1e"
TAB_INDICATOR_COLOR = "#0a84ff"
TAB_UNSELECTED_COLOR = "#636366"


# ============================================================
# 应用状态
# ============================================================

@dataclass
class AppState:
    """
    应用全局状态容器。

    集中管理截取 Tab 和拼接 Tab 的所有状态值，
    替代原 CustomTkinter 版本中的 tk.StringVar / tk.BooleanVar。
    """

    # ---- 截取 Tab 状态 ----
    input_file_path: str = ""
    output_file_path: str = ""
    start_time: str = "0:00:00"
    end_time: str = ""
    duration_value: str = "10"
    duration_unit: str = "秒"
    output_format: str = "mp4"
    compress_enabled: bool = False
    compress_quality: str = "中质量（推荐）"
    advanced_visible: bool = False
    resolution: str = "原始分辨率"
    framerate: str = "原始帧率"
    audio_bitrate: str = "原始音频"

    # ---- 拼接 Tab 状态 ----
    concat_file_list: list[str] = field(default_factory=list)
    concat_output_path: str = ""
    concat_output_format: str = "mp4"
    concat_compress_enabled: bool = False
    concat_compress_quality: str = "中质量（推荐）"
    concat_advanced_visible: bool = False
    concat_resolution: str = "原始分辨率"
    concat_framerate: str = "原始帧率"
    concat_audio_bitrate: str = "原始音频"
    concat_transition: str = "无过渡"
    concat_transition_duration: str = "1.0"

    # ---- UI 控件引用（运行时绑定） ----
    log_text: ft.TextField | None = None
    clip_run_button: ft.Container | None = None
    concat_run_button: ft.ElevatedButton | None = None
    concat_listbox: ft.ListView | None = None
    page: ft.Page | None = None

    # ---- 截取 Tab 控件引用（运行时由 build_clip_tab 绑定） ----
    clip_input_path_field: ft.TextField | None = None
    clip_output_path_field: ft.TextField | None = None
    clip_start_time_field: ft.TextField | None = None
    clip_end_time_field: ft.TextField | None = None
    clip_duration_value_field: ft.TextField | None = None
    clip_duration_unit_dropdown: ft.Dropdown | None = None
    clip_output_format_dropdown: ft.Dropdown | None = None
    clip_resolution_dropdown: ft.Dropdown | None = None
    clip_framerate_dropdown: ft.Dropdown | None = None
    clip_audio_bitrate_dropdown: ft.Dropdown | None = None

    # ---- 拼接 Tab 控件引用（运行时由 build_concat_tab 绑定） ----
    concat_output_path_field: ft.TextField | None = None
    concat_output_format_dropdown: ft.Dropdown | None = None
    concat_transition_dropdown: ft.Dropdown | None = None
    concat_transition_duration_field: ft.TextField | None = None
    concat_quality_dropdown: ft.Dropdown | None = None
    concat_resolution_dropdown: ft.Dropdown | None = None
    concat_framerate_dropdown: ft.Dropdown | None = None
    concat_audio_bitrate_dropdown: ft.Dropdown | None = None
    concat_selected_index: int = -1


# ============================================================
# 主应用构建
# ============================================================

def build_app(page: ft.Page) -> None:
    """
    构建 Snipkin 的完整 Flet 应用。

    配置窗口属性、初始化状态、构建 iOS 风格毛玻璃 UI，
    并在启动时检测 ffmpeg 可用性。

    参数:
        page: Flet Page 实例
    """
    # ---- 窗口基本设置 ----
    page.title = "Snipkin - 视频处理工具"
    page.window.width = 700
    page.window.height = 820
    page.window.resizable = False
    page.bgcolor = ft.Colors.TRANSPARENT
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        color_scheme_seed=ACCENT_BLUE,
        font_family="SF Pro Display, Helvetica Neue, Arial",
    )

    # ---- 初始化应用状态 ----
    state = AppState(page=page)

    # ---- 构建 UI ----
    page.add(_build_root_layout(state))

    # ---- 启动时检测 ffmpeg ----
    if not check_ffmpeg_available():
        page.open(
            ft.AlertDialog(
                title=ft.Text("ffmpeg 未找到"),
                content=ft.Text(
                    "未在系统 PATH 中检测到 ffmpeg。\n"
                    "请先安装 ffmpeg（推荐使用 Homebrew: brew install ffmpeg），"
                    "然后重新启动本工具。",
                ),
                actions=[
                    ft.TextButton(
                        content=ft.Text("知道了"),
                        on_click=lambda event: page.close(event.control.parent),
                    ),
                ],
            ),
        )


def _build_root_layout(state: AppState) -> ft.Stack:
    """
    构建根布局：渐变背景 + 毛玻璃层 + 内容层。

    使用 ft.Stack 实现三层叠加：
      Layer 1: 深色渐变背景
      Layer 2: 毛玻璃模糊效果层
      Layer 3: 实际内容（Tabs + 功能区 + 日志区）

    参数:
        state: 应用状态实例

    返回:
        根布局的 Stack 组件
    """
    # Layer 1: 渐变背景
    gradient_background = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=[BACKGROUND_GRADIENT_START, BACKGROUND_GRADIENT_END, "#0f3460"],
        ),
    )

    # Layer 2: 毛玻璃模糊层
    blur_overlay = ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.3, "#1e1e2e"),
        blur=ft.Blur(sigma_x=30, sigma_y=30),
    )

    # Layer 3: 内容层
    content_layer = ft.Container(
        expand=True,
        padding=ft.padding.all(16),
        content=_build_content(state),
    )

    return ft.Stack(
        controls=[gradient_background, blur_overlay, content_layer],
        expand=True,
    )


def _build_content(state: AppState) -> ft.Column:
    """
    构建主内容区域：标题栏 + Tabs + 日志区。

    布局结构：
      ┌─────────────────────────────────┐
      │  Snipkin 标题栏                  │
      ├─────────────────────────────────┤
      │  Tabs (视频截取 | 视频拼接)       │
      │  ┌─────────────────────────────┐│
      │  │  Tab 内容区域（功能区）       ││
      │  └─────────────────────────────┘│
      ├─────────────────────────────────┤
      │  执行日志                        │
      │  ┌─────────────────────────────┐│
      │  │  日志文本区域                 ││
      │  └─────────────────────────────┘│
      └─────────────────────────────────┘

    参数:
        state: 应用状态实例

    返回:
        主内容的 Column 组件
    """
    # ---- 标题栏 ----
    title_bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.CupertinoIcons.FILM,
                    color=ACCENT_BLUE,
                    size=24,
                ),
                ft.Text(
                    "Snipkin",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=TEXT_PRIMARY_COLOR,
                ),
                ft.Text(
                    "视频处理工具",
                    size=14,
                    color=TEXT_SECONDARY_COLOR,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(bottom=12),
    )

    # ---- Tabs（Segmented Control 风格） ----
    from snipkin.ui.clip_tab import build_clip_tab
    from snipkin.ui.concat_tab import build_concat_tab
    clip_tab_content = build_clip_tab(state)
    concat_tab_content = build_concat_tab(state)

    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="✂️ 视频截取"),
            ft.Tab(label="🔗 视频拼接"),
        ],
        indicator_color=TAB_INDICATOR_COLOR,
        label_color=TEXT_PRIMARY_COLOR,
        unselected_label_color=TAB_UNSELECTED_COLOR,
        divider_height=0,
        label_padding=ft.padding.symmetric(horizontal=16, vertical=8),
        label_text_style=ft.TextStyle(
            size=14,
            weight=ft.FontWeight.W_600,
        ),
        unselected_label_text_style=ft.TextStyle(
            size=14,
            weight=ft.FontWeight.W_400,
        ),
    )

    tab_bar_view = ft.TabBarView(
        controls=[
            clip_tab_content,
            concat_tab_content,
        ],
        expand=True,
    )

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        length=2,
        content=ft.Column(
            controls=[tab_bar, tab_bar_view],
            spacing=0,
            expand=True,
        ),
        expand=True,
    )

    # ---- 日志区域 ----
    log_section = _build_log_section(state)

    return ft.Column(
        controls=[title_bar, tabs, log_section],
        spacing=0,
        expand=True,
    )


# ============================================================
# 日志区域
# ============================================================

def _build_log_section(state: AppState) -> ft.Container:
    """
    构建底部日志输出区域。

    包含标题行和一个只读的多行文本框，用于显示操作日志和 ffmpeg 执行结果。
    两个 Tab 共享同一个日志区域。

    参数:
        state: 应用状态实例

    返回:
        日志区域的 Container 组件
    """
    log_list_view = ft.ListView(
        height=120,
        spacing=2,
        padding=ft.padding.all(10),
        auto_scroll=True,
    )

    log_container = ft.Container(
        content=log_list_view,
        bgcolor=ft.Colors.with_opacity(0.7, "#0d0d0d"),
        border_radius=ft.border_radius.all(10),
        border=ft.border.all(1, ft.Colors.with_opacity(0.15, "#ffffff")),
    )

    # 将日志控件引用存储到 state 中，供 handler 层写入日志
    state.log_text = log_list_view

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.CupertinoIcons.DOC_TEXT,
                            size=16,
                            color=TEXT_SECONDARY_COLOR,
                        ),
                        ft.Text(
                            "执行日志",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=TEXT_PRIMARY_COLOR,
                        ),
                    ],
                    spacing=6,
                ),
                log_container,
            ],
            spacing=6,
        ),
        padding=ft.padding.only(top=8),
    )


# ============================================================
# 通用 UI 组件工厂函数
# ============================================================

def _build_section_card(
    icon: str,
    title: str,
    content: ft.Control,
) -> ft.Container:
    """
    构建一个 iOS 风格的卡片区域。

    每个功能区域（输入文件、时间设置、输出设置等）都使用统一的卡片样式，
    包含图标 + 标题头部和内容区域。

    参数:
        icon:    Cupertino 图标名称
        title:   区域标题文本
        content: 区域内容控件

    返回:
        卡片样式的 Container 组件
    """
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=16, color=ACCENT_BLUE),
                        ft.Text(
                            title,
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=TEXT_PRIMARY_COLOR,
                        ),
                    ],
                    spacing=6,
                ),
                content,
            ],
            spacing=8,
        ),
        bgcolor=ft.Colors.with_opacity(0.4, SURFACE_COLOR),
        border_radius=ft.border_radius.all(12),
        padding=ft.padding.all(16),
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, "#ffffff")),
    )


def _build_action_button(
    text: str,
    icon: str,
    on_click: ft.ControlEvent | None = None,
    color: str = ACCENT_BLUE,
    hover_color: str = ACCENT_BLUE_HOVER,
) -> ft.ElevatedButton:
    """
    构建一个 Apple 风格的操作按钮。

    参数:
        text:        按钮文本
        icon:        Cupertino 图标名称
        on_click:    点击事件回调（可选）
        color:       按钮背景色
        hover_color: 悬停背景色

    返回:
        ElevatedButton 组件
    """
    return ft.ElevatedButton(
        content=ft.Text(text, size=13, weight=ft.FontWeight.W_500),
        icon=icon,
        on_click=on_click,
        bgcolor=color,
        color="#ffffff",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        ),
        height=38,
    )


def _build_primary_button(
    text: str,
    icon: str,
    on_click: ft.ControlEvent | None = None,
) -> ft.ElevatedButton:
    """
    构建主操作按钮（开始截取 / 开始拼接）。

    使用更大的尺寸和更醒目的样式，作为每个 Tab 的核心执行按钮。

    参数:
        text:     按钮文本
        icon:     Cupertino 图标名称
        on_click: 点击事件回调（可选）

    返回:
        主操作 ElevatedButton 组件
    """
    return ft.ElevatedButton(
        content=ft.Text(text, size=15, weight=ft.FontWeight.W_600),
        icon=icon,
        on_click=on_click,
        bgcolor=ACCENT_BLUE,
        color="#ffffff",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
        ),
        height=46,
        width=float("inf"),
    )