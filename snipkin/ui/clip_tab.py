"""
snipkin.ui.clip_tab - 视频截取 Tab 的界面构建（Flet 版）

本模块提供 build_clip_tab 函数，构建视频截取 Tab 的完整 UI，包括：
- 输入文件选择区域（使用 ft.FilePicker）
- 时间设置区域（开始时间 + 结束时间 + 持续时长）
- 视频压缩设置区域（开关 + 质量预设 + 高级选项动画展开）
- 输出设置区域（格式选择 + 保存路径）
- 执行按钮区域（Hover 光效 + 缩放动画）

设计说明：
  从 Mixin 模式迁移为函数式组合模式。
  所有状态通过 AppState 实例传递，UI 控件引用存储在 state 中。
  事件处理逻辑由 snipkin.handlers.clip_handler 提供。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from snipkin.app import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    DIVIDER_COLOR,
    LOG_BACKGROUND_COLOR,
    SURFACE_COLOR,
    TEXT_PRIMARY_COLOR,
    TEXT_SECONDARY_COLOR,
    _build_action_button,
    _build_section_card,
)
from snipkin.constants import (
    AUDIO_BITRATE_OPTIONS,
    COMPRESS_QUALITY_PRESETS,
    DURATION_UNITS,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
    SUPPORTED_FORMATS,
)

if TYPE_CHECKING:
    from snipkin.app import AppState


def _make_styled_textfield(
    value: str = "",
    hint_text: str = "",
    width: int | None = None,
    read_only: bool = False,
    expand: bool = False,
    on_change: ft.ControlEvent | None = None,
) -> ft.TextField:
    """
    创建统一风格的圆角半透明输入框。

    参数:
        value:     初始值
        hint_text: 占位提示文本
        width:     固定宽度（可选）
        read_only: 是否只读
        expand:    是否自动扩展
        on_change: 值变化回调

    返回:
        风格化的 TextField 组件
    """
    return ft.TextField(
        value=value,
        hint_text=hint_text,
        width=width,
        read_only=read_only,
        expand=expand,
        on_change=on_change,
        border_radius=ft.border_radius.all(10),
        border_color=DIVIDER_COLOR,
        focused_border_color=ACCENT_BLUE,
        bgcolor=ft.Colors.with_opacity(0.15, SURFACE_COLOR),
        text_style=ft.TextStyle(size=13, color=TEXT_PRIMARY_COLOR),
        hint_style=ft.TextStyle(size=13, color=TEXT_SECONDARY_COLOR),
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )


def _make_styled_dropdown(
    value: str,
    options: list[str],
    width: int,
    on_select=None,
) -> ft.Dropdown:
    """
    创建统一风格的下拉选择框。

    参数:
        value:     初始选中值
        options:   选项列表
        width:     固定宽度
        on_select: 选中回调

    返回:
        风格化的 Dropdown 组件
    """
    return ft.Dropdown(
        value=value,
        width=width,
        options=[ft.dropdown.Option(option) for option in options],
        on_select=on_select,
        border_radius=ft.border_radius.all(10),
        border_color=DIVIDER_COLOR,
        focused_border_color=ACCENT_BLUE,
        bgcolor=ft.Colors.with_opacity(0.15, SURFACE_COLOR),
        text_style=ft.TextStyle(size=13, color=TEXT_PRIMARY_COLOR),
        content_padding=ft.padding.symmetric(horizontal=12, vertical=6),
    )


def build_clip_tab(state: AppState) -> ft.Container:
    """
    构建视频截取 Tab 的完整内容。

    按从上到下的顺序依次构建：输入文件 → 时间设置 → 压缩设置 → 输出设置 → 执行按钮。
    所有事件处理通过闭包绑定到 state 和 handler 函数。

    参数:
        state: 应用状态实例

    返回:
        截取 Tab 的完整 Container 组件
    """
    # 延迟导入避免循环依赖
    from snipkin.handlers.clip_handler import (
        handle_clip_run,
        on_input_file_picked,
        on_output_file_picked,
    )

    # ---- FilePicker 实例（Flet 0.82+ async API） ----
    input_file_picker = ft.FilePicker()
    output_file_picker = ft.FilePicker()

    async def pick_input_file(_event):
        """异步选择输入视频文件"""
        result = await input_file_picker.pick_files(
            dialog_title="选择输入视频文件",
            allowed_extensions=[
                "mp4", "mov", "mkv", "avi", "flv",
                "wmv", "webm", "ts", "m4v",
            ],
            allow_multiple=False,
        )
        on_input_file_picked(result, state, input_path_field, output_path_field)

    async def pick_output_file(_event):
        """异步选择输出文件保存路径"""
        result = await output_file_picker.save_file(
            dialog_title="选择输出文件保存位置",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=[state.output_format],
            file_name=output_path_field.value.split("/")[-1]
            if output_path_field.value else None,
        )
        on_output_file_picked(result, state, output_path_field)

    # ---- 输入文件区域 ----
    input_path_field = _make_styled_textfield(
        hint_text="选择输入视频文件...",
        read_only=True,
        expand=True,
    )

    input_section = _build_section_card(
        icon=ft.CupertinoIcons.FOLDER_OPEN,
        title="输入视频文件",
        content=ft.Row(
            controls=[
                input_path_field,
                _build_action_button(
                    text="选择文件",
                    icon=ft.CupertinoIcons.DOC_ON_DOC,
                    on_click=pick_input_file,
                ),
            ],
            spacing=8,
        ),
    )

    # ---- 时间设置区域 ----
    start_time_field = _make_styled_textfield(
        value=state.start_time,
        hint_text="0:00:00",
        width=120,
        on_change=lambda event: setattr(state, "start_time", event.control.value),
    )

    end_time_field = _make_styled_textfield(
        hint_text="留空则用持续时长",
        width=160,
        on_change=lambda event: setattr(state, "end_time", event.control.value),
    )

    duration_value_field = _make_styled_textfield(
        value=state.duration_value,
        hint_text="10",
        width=80,
        on_change=lambda event: setattr(state, "duration_value", event.control.value),
    )

    duration_unit_dropdown = _make_styled_dropdown(
        value=state.duration_unit,
        options=list(DURATION_UNITS.keys()),
        width=90,
        on_select=lambda event: setattr(state, "duration_unit", event.control.value),
    )

    time_section = _build_section_card(
        icon=ft.CupertinoIcons.TIMER,
        title="时间设置",
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("开始时间:", size=13, color=TEXT_SECONDARY_COLOR),
                        start_time_field,
                        ft.Text("结束时间:", size=13, color=TEXT_SECONDARY_COLOR),
                        end_time_field,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.Text("持续时长:", size=13, color=TEXT_SECONDARY_COLOR),
                        duration_value_field,
                        duration_unit_dropdown,
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.CupertinoIcons.INFO,
                                    size=14,
                                    color=TEXT_SECONDARY_COLOR,
                                ),
                                ft.Text(
                                    "填了结束时间则忽略持续时长",
                                    size=12,
                                    color=TEXT_SECONDARY_COLOR,
                                ),
                            ],
                            spacing=4,
                            tight=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
        ),
    )

    # ---- 压缩设置区域（带动画展开） ----
    compress_section = _build_compress_section(state)

    # ---- 输出设置区域 ----
    output_format_dropdown = _make_styled_dropdown(
        value=state.output_format,
        options=SUPPORTED_FORMATS,
        width=100,
        on_select=lambda event: setattr(state, "output_format", event.control.value),
    )

    output_path_field = _make_styled_textfield(
        hint_text="输出文件路径...",
        expand=True,
        on_change=lambda event: setattr(state, "output_file_path", event.control.value),
    )

    output_section = _build_section_card(
        icon=ft.CupertinoIcons.TRAY_ARROW_DOWN,
        title="输出设置",
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("输出格式:", size=13, color=TEXT_SECONDARY_COLOR),
                        output_format_dropdown,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        output_path_field,
                        _build_action_button(
                            text="保存路径",
                            icon=ft.CupertinoIcons.FLOPPY_DISK,
                            on_click=pick_output_file,
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=8,
        ),
    )

    # ---- 执行按钮（Hover 光效 + 缩放动画） ----
    run_button = _build_glow_run_button(
        text="开始截取",
        icon=ft.CupertinoIcons.PLAY_ARROW_SOLID,
        on_click=lambda _: handle_clip_run(state),
    )
    state.clip_run_button = run_button

    # 将控件引用存储到 state 中，供 handler 读取值
    state.clip_input_path_field = input_path_field
    state.clip_output_path_field = output_path_field
    state.clip_start_time_field = start_time_field
    state.clip_end_time_field = end_time_field
    state.clip_duration_value_field = duration_value_field
    state.clip_duration_unit_dropdown = duration_unit_dropdown
    state.clip_output_format_dropdown = output_format_dropdown

    return ft.Container(
        content=ft.Column(
            controls=[
                input_section,
                time_section,
                compress_section,
                output_section,
                ft.Container(content=run_button, padding=ft.padding.only(top=4)),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.only(top=12),
        expand=True,
    )


def _build_compress_section(state: AppState) -> ft.Container:
    """
    构建视频压缩设置区域，带平滑的高度动画展开效果。

    包含：
      - 标题行：标题 + 压缩启用开关
      - 压缩选项容器（使用 animate_size 实现平滑展开/收起）：
        - 质量预设下拉菜单
        - 高级选项展开按钮 + 高级选项面板（分辨率 + 帧率 + 音频码率）

    参数:
        state: 应用状态实例

    返回:
        压缩设置区域的 Container 组件
    """
    # 质量预设下拉
    quality_dropdown = _make_styled_dropdown(
        value=state.compress_quality,
        options=list(COMPRESS_QUALITY_PRESETS.keys()),
        width=200,
        on_select=lambda event: setattr(state, "compress_quality", event.control.value),
    )

    # 高级选项面板内容
    resolution_dropdown = _make_styled_dropdown(
        value=state.resolution,
        options=list(RESOLUTION_OPTIONS.keys()),
        width=140,
        on_select=lambda event: setattr(state, "resolution", event.control.value),
    )
    state.clip_resolution_dropdown = resolution_dropdown

    framerate_dropdown = _make_styled_dropdown(
        value=state.framerate,
        options=list(FRAMERATE_OPTIONS.keys()),
        width=120,
        on_select=lambda event: setattr(state, "framerate", event.control.value),
    )
    state.clip_framerate_dropdown = framerate_dropdown

    audio_bitrate_dropdown = _make_styled_dropdown(
        value=state.audio_bitrate,
        options=list(AUDIO_BITRATE_OPTIONS.keys()),
        width=160,
        on_select=lambda event: setattr(state, "audio_bitrate", event.control.value),
    )
    state.clip_audio_bitrate_dropdown = audio_bitrate_dropdown

    # 高级选项面板（使用 AnimatedContainer 实现平滑展开）
    advanced_content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("分辨率:", size=13, color=TEXT_SECONDARY_COLOR),
                    resolution_dropdown,
                    ft.Text("帧率:", size=13, color=TEXT_SECONDARY_COLOR),
                    framerate_dropdown,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                controls=[
                    ft.Text("音频码率:", size=13, color=TEXT_SECONDARY_COLOR),
                    audio_bitrate_dropdown,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=8,
    )

    advanced_container = ft.Container(
        content=advanced_content,
        height=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate_size=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
        opacity=0,
        padding=ft.padding.only(top=8),
    )

    # 高级选项展开按钮
    advanced_toggle_icon = ft.Icon(
        ft.CupertinoIcons.CHEVRON_RIGHT,
        size=14,
        color=TEXT_SECONDARY_COLOR,
        rotate=ft.Rotate(0),
        animate_rotation=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
    )

    def toggle_advanced(_event):
        """切换高级选项面板的展开/收起状态"""
        state.advanced_visible = not state.advanced_visible
        if state.advanced_visible:
            advanced_container.height = 90
            advanced_container.opacity = 1
            advanced_toggle_icon.rotate = ft.Rotate(1.5708)
        else:
            advanced_container.height = 0
            advanced_container.opacity = 0
            advanced_toggle_icon.rotate = ft.Rotate(0)
        state.page.update()

    advanced_toggle_button = ft.Container(
        content=ft.Row(
            controls=[
                advanced_toggle_icon,
                ft.Text("高级选项", size=13, color=TEXT_SECONDARY_COLOR),
            ],
            spacing=4,
            tight=True,
        ),
        on_click=toggle_advanced,
        ink=True,
        border_radius=ft.border_radius.all(6),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )

    # 压缩选项容器（使用 animate_size 实现平滑展开/收起）
    compress_options_content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("压缩质量:", size=13, color=TEXT_SECONDARY_COLOR),
                    quality_dropdown,
                    advanced_toggle_button,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            advanced_container,
        ],
        spacing=0,
    )

    compress_options_container = ft.Container(
        content=compress_options_content,
        height=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate_size=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
        opacity=0,
        padding=ft.padding.only(top=8),
    )

    # 压缩开关
    def toggle_compress(event):
        """切换压缩开关，展开/收起压缩选项"""
        state.compress_enabled = event.control.value
        if state.compress_enabled:
            compress_options_container.height = None
            compress_options_container.opacity = 1
        else:
            compress_options_container.height = 0
            compress_options_container.opacity = 0
            # 收起时同时收起高级选项
            state.advanced_visible = False
            advanced_container.height = 0
            advanced_container.opacity = 0
            advanced_toggle_icon.rotate = ft.Rotate(0)
        state.page.update()

    compress_switch = ft.CupertinoSwitch(
        value=state.compress_enabled,
        active_track_color=ACCENT_BLUE,
        on_change=toggle_compress,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.CupertinoIcons.ARCHIVEBOX,
                            size=16,
                            color=ACCENT_BLUE,
                        ),
                        ft.Text(
                            "视频压缩",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=TEXT_PRIMARY_COLOR,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            "启用压缩",
                            size=13,
                            color=TEXT_SECONDARY_COLOR,
                        ),
                        compress_switch,
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                compress_options_container,
            ],
            spacing=0,
        ),
        bgcolor=ft.Colors.with_opacity(0.4, SURFACE_COLOR),
        border_radius=ft.border_radius.all(12),
        padding=ft.padding.all(16),
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, "#ffffff")),
    )


def _build_glow_run_button(
    text: str,
    icon: str,
    on_click: ft.ControlEvent | None = None,
) -> ft.Container:
    """
    构建带 Hover 光效和缩放动画的主操作按钮。

    鼠标悬停时：
      - 按钮背景产生微弱的蓝色 BoxShadow 发光效果
      - 按钮整体微微放大（scale 1.0 → 1.02）

    参数:
        text:     按钮文本
        icon:     Cupertino 图标名称
        on_click: 点击事件回调

    返回:
        带光效的按钮 Container 组件
    """
    button_content = ft.ElevatedButton(
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

    glow_container = ft.Container(
        content=button_content,
        border_radius=ft.border_radius.all(10),
        shadow=None,
        scale=ft.Scale(1.0),
        animate_scale=ft.Animation(duration=200, curve=ft.AnimationCurve.EASE_OUT),
    )

    def on_hover(event: ft.ControlEvent):
        """鼠标悬停时添加发光阴影并微微放大"""
        if event.data == "true":
            glow_container.shadow = ft.BoxShadow(
                spread_radius=2,
                blur_radius=16,
                color=ft.Colors.with_opacity(0.4, ACCENT_BLUE),
                offset=ft.Offset(0, 0),
            )
            glow_container.scale = ft.Scale(1.02)
        else:
            glow_container.shadow = None
            glow_container.scale = ft.Scale(1.0)
        glow_container.update()

    glow_container.on_hover = on_hover

    return glow_container