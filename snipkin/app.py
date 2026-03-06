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
    page.window.resizable = True
    page.bgcolor = ft.Colors.TRANSPARENT
    page.padding = 0
    page.assets_dir = "assets"
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
        ffmpeg_dialog = ft.AlertDialog(
            title=ft.Text("ffmpeg 未找到"),
            content=ft.Text(
                "未在系统 PATH 中检测到 ffmpeg。\n"
                "请先安装 ffmpeg（推荐使用 Homebrew: brew install ffmpeg），"
                "然后重新启动本工具。",
            ),
            open=True,
        )

        def close_dialog(_event):
            ffmpeg_dialog.open = False
            page.update()

        ffmpeg_dialog.actions = [
            ft.TextButton(content=ft.Text("知道了"), on_click=close_dialog),
        ]
        page.overlay.append(ffmpeg_dialog)
        page.update()


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
                ft.Image(
                    src="icon.png",
                    width=24,
                    height=24,
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
        padding=ft.padding.only(bottom=6),
    )

    # ---- Tabs（Segmented Control 风格） ----
    from snipkin.ui.clip_tab import build_clip_tab
    from snipkin.ui.concat_tab import build_concat_tab
    clip_tab_content = build_clip_tab(state)
    concat_tab_content = build_concat_tab(state)

    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(
                label="视频截取",
                icon=ft.CupertinoIcons.SCISSORS,
            ),
            ft.Tab(
                label="视频拼接",
                icon=ft.CupertinoIcons.LINK,
            ),
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

def _show_page_snackbar(page: ft.Page, message: str, color: str) -> None:
    """
    通过 page.overlay 显示 SnackBar 通知。

    参数:
        page:    Flet Page 实例
        message: 通知消息文本
        color:   SnackBar 背景色
    """
    snackbar = ft.SnackBar(
        content=ft.Text(message, color="#ffffff", weight=ft.FontWeight.W_500),
        bgcolor=color,
        duration=3000,
        open=True,
    )
    page.overlay.append(snackbar)
    page.update()

def _copy_all_logs(state: AppState, log_list_view: ft.ListView) -> None:
    """
    将日志 ListView 中的所有文本复制到系统剪贴板。

    遍历 ListView 中的所有 Text 控件，拼接为完整文本后写入剪贴板，
    并通过 SnackBar 通知用户复制结果。

    参数:
        state:         应用状态实例
        log_list_view: 日志 ListView 控件引用
    """
    log_lines = []
    for control in log_list_view.controls:
        if isinstance(control, ft.Text) and control.value:
            log_lines.append(control.value)

    if not log_lines:
        _show_page_snackbar(state.page, "暂无日志内容", "#636366")
        return

    full_log_text = "\n".join(log_lines)
    state.page.clipboard = full_log_text
    _show_page_snackbar(
        state.page,
        f"已复制 {len(log_lines)} 条日志到剪贴板",
        "#34C759",
    )

def _build_log_section(state: AppState) -> ft.Container:
    """
    构建底部日志输出区域，支持折叠/展开和拖拽调整高度。

    功能：
      - 点击标题栏可折叠/展开日志内容
      - 顶部拖拽手柄可上下拖动调整日志区高度
      - 折叠时仅显示标题栏，展开时显示日志内容
      - 两个 Tab 共享同一个日志区域

    参数:
        state: 应用状态实例

    返回:
        日志区域的 Container 组件
    """
    # 日志面板状态（默认收起，需要时手动展开）
    log_expanded = False
    log_panel_height = 100
    min_log_height = 60
    max_log_height = 400

    log_list_view = ft.ListView(
        height=log_panel_height,
        spacing=2,
        padding=ft.padding.all(8),
        auto_scroll=True,
    )

    log_container = ft.Container(
        content=log_list_view,
        bgcolor=ft.Colors.with_opacity(0.7, "#0d0d0d"),
        border_radius=ft.border_radius.all(10),
        border=ft.border.all(1, ft.Colors.with_opacity(0.15, "#ffffff")),
    )

    # 日志内容区域（默认收起）
    log_body = ft.Container(
        content=log_container,
        height=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate_size=ft.Animation(duration=250, curve=ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.Animation(duration=250, curve=ft.AnimationCurve.EASE_IN_OUT),
        opacity=0,
    )

    # 将日志控件引用存储到 state 中，供 handler 层写入日志
    state.log_text = log_list_view

    # 折叠/展开箭头图标（默认收起状态，箭头朝上表示可展开）
    toggle_icon = ft.Icon(
        ft.CupertinoIcons.CHEVRON_DOWN,
        size=14,
        color=TEXT_SECONDARY_COLOR,
        rotate=ft.Rotate(3.14159),
        animate_rotation=ft.Animation(duration=250, curve=ft.AnimationCurve.EASE_IN_OUT),
    )

    def toggle_log_panel(_event):
        """切换日志面板的折叠/展开状态"""
        nonlocal log_expanded
        log_expanded = not log_expanded
        if log_expanded:
            log_body.height = log_list_view.height + 16
            log_body.opacity = 1
            toggle_icon.rotate = ft.Rotate(0)
        else:
            log_body.height = 0
            log_body.opacity = 0
            toggle_icon.rotate = ft.Rotate(3.14159)
        state.page.update()

    # 拖拽手柄（位于日志区顶部，可上下拖动调整高度）
    def on_drag_start(_event):
        """拖拽开始时禁用动画，避免动画与频繁更新冲突"""
        log_body.animate_size = None

    def on_drag_update(event: ft.DragUpdateEvent):
        """拖拽手柄时动态调整日志区高度"""
        nonlocal log_panel_height
        if not log_expanded:
            return
        new_height = log_panel_height - event.local_delta.y
        new_height = max(min_log_height, min(max_log_height, new_height))
        log_panel_height = new_height
        log_list_view.height = log_panel_height
        log_body.height = log_panel_height + 16
        log_body.update()

    def on_drag_end(_event):
        """拖拽结束后恢复动画"""
        log_body.animate_size = ft.Animation(
            duration=250, curve=ft.AnimationCurve.EASE_IN_OUT,
        )

    drag_handle = ft.GestureDetector(
        content=ft.Container(
            content=ft.Container(
                width=36,
                height=4,
                border_radius=ft.border_radius.all(2),
                bgcolor=ft.Colors.with_opacity(0.3, "#ffffff"),
            ),
            alignment=ft.Alignment(0, 0),
            height=14,
        ),
        mouse_cursor=ft.MouseCursor.RESIZE_ROW,
        drag_interval=50,
        on_vertical_drag_start=on_drag_start,
        on_vertical_drag_update=on_drag_update,
        on_vertical_drag_end=on_drag_end,
    )

    # 复制日志按钮（仅展开时显示）
    copy_button = ft.IconButton(
        icon=ft.CupertinoIcons.DOC_ON_CLIPBOARD,
        icon_size=14,
        icon_color=TEXT_SECONDARY_COLOR,
        tooltip="复制全部日志",
        visible=False,
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
        on_click=lambda _: _copy_all_logs(state, log_list_view),
    )

    def toggle_log_panel_with_copy(_event):
        """切换日志面板并同步复制按钮可见性"""
        toggle_log_panel(_event)
        copy_button.visible = log_expanded
        copy_button.update()

    # 标题栏（可点击折叠/展开）
    title_row = ft.Container(
        content=ft.Row(
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
                ft.Container(expand=True),
                copy_button,
                toggle_icon,
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=toggle_log_panel_with_copy,
        ink=True,
        border_radius=ft.border_radius.all(6),
        padding=ft.padding.symmetric(horizontal=4, vertical=2),
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                drag_handle,
                title_row,
                log_body,
            ],
            spacing=2,
        ),
        padding=ft.padding.only(top=4),
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
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
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