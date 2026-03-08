"""
snipkin.ui.extract_audio_tab - 音频提取 Tab 的界面构建（Flet 版）

本模块提供 build_extract_audio_tab 函数，构建音频提取 Tab 的完整 UI，包括：
- 输入文件选择区域（使用 ft.FilePicker）
- 时间设置区域（开始时间 + 结束时间 + 持续时长，可选开关）
- 音质设置区域（输出音质选择）
- 输出设置区域（格式选择 + 保存路径）
- 执行按钮区域（Hover 光效 + 缩放动画）

设计说明：
  采用函数式组合模式，所有状态通过 AppState 实例传递，
  UI 控件引用存储在 state 中，事件处理逻辑由 snipkin.handlers.extract_audio_handler 提供。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from snipkin.app import (
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    DIVIDER_COLOR,
    SURFACE_COLOR,
    TEXT_PRIMARY_COLOR,
    TEXT_SECONDARY_COLOR,
    _build_action_button,
    _build_section_card,
)
from snipkin.constants import (
    AUDIO_FORMATS,
    AUDIO_QUALITY_PRESETS,
    DURATION_UNITS,
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


def build_extract_audio_tab(state: AppState) -> ft.Container:
    """
    构建音频提取 Tab 的完整内容。

    按从上到下的顺序依次构建：输入文件 → 时间设置 → 音质设置 → 输出设置 → 执行按钮。
    所有事件处理通过闭包绑定到 state 和 handler 函数。

    参数:
        state: 应用状态实例

    返回:
        音频提取 Tab 的完整 Container 组件
    """
    # 延迟导入避免循环依赖
    from snipkin.handlers.extract_audio_handler import (
        handle_extract_run,
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
        if result:
            on_input_file_picked(result, state, input_path_field, output_path_field)

    async def pick_output_file(_event):
        """异步选择输出文件保存路径"""
        result = await output_file_picker.save_file(
            dialog_title="选择输出文件保存位置",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=[state.audio_output_format],
            file_name=output_path_field.value.split("/")[-1]
            if output_path_field.value else None,
        )
        if result:
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

    # ---- 时间设置区域（带完整提取开关） ----
    # 时间设置相关控件（默认隐藏，开启部分截取时显示）
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

    # 部分截取模式的内容区域（使用 animate_size 实现平滑展开/收起）
    partial_extract_content = ft.Column(
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
    )

    partial_extract_container = ft.Container(
        content=partial_extract_content,
        height=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate_size=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
        animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
        opacity=0,
        padding=ft.padding.only(top=8),
    )

    # 完整提取开关
    def toggle_extract_full(event):
        """切换完整提取/部分截取模式"""
        # 开关开启（向右）= 提取完整音频 = audio_extract_full = True
        # 开关关闭（向左）= 部分截取 = audio_extract_full = False
        state.audio_extract_full = event.control.value
        if state.audio_extract_full:
            # 完整提取模式：隐藏时间设置
            partial_extract_container.height = 0
            partial_extract_container.opacity = 0
        else:
            # 部分截取模式：显示时间设置
            partial_extract_container.height = 120
            partial_extract_container.opacity = 1
        state.page.update()

    extract_full_switch = ft.CupertinoSwitch(
        value=True,  # 默认开启完整提取
        active_track_color=ACCENT_BLUE,
        on_change=toggle_extract_full,
    )

    time_section = _build_section_card(
        icon=ft.CupertinoIcons.TIMER,
        title="时间设置",
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        ft.Text(
                            "提取完整音频",
                            size=13,
                            color=TEXT_SECONDARY_COLOR,
                        ),
                        extract_full_switch,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.CupertinoIcons.INFO,
                            size=14,
                            color=TEXT_SECONDARY_COLOR,
                        ),
                        ft.Text(
                            "开启后将提取视频中的完整音频轨道",
                            size=12,
                            color=TEXT_SECONDARY_COLOR,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                partial_extract_container,
            ],
            spacing=8,
        ),
    )

    # ---- 音质设置区域 ----
    quality_dropdown = _make_styled_dropdown(
        value=state.audio_quality,
        options=list(AUDIO_QUALITY_PRESETS.keys()),
        width=200,
        on_select=lambda event: setattr(state, "audio_quality", event.control.value),
    )

    quality_section = _build_section_card(
        icon=ft.CupertinoIcons.MUSIC_NOTE_2,
        title="音质设置",
        content=ft.Row(
            controls=[
                ft.Text("输出音质:", size=13, color=TEXT_SECONDARY_COLOR),
                quality_dropdown,
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.CupertinoIcons.INFO,
                            size=14,
                            color=TEXT_SECONDARY_COLOR,
                        ),
                        ft.Text(
                            "仅对有损格式生效（MP3/AAC 等）",
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
    )

    # ---- 输出设置区域 ----
    output_format_dropdown = _make_styled_dropdown(
        value=state.audio_output_format,
        options=AUDIO_FORMATS,
        width=100,
        on_select=lambda event: setattr(state, "audio_output_format", event.control.value),
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
        text="开始提取",
        icon=ft.CupertinoIcons.MUSIC_NOTE,
        on_click=lambda _: handle_extract_run(state),
    )
    state.audio_run_button = run_button

    # 将控件引用存储到 state 中，供 handler 读取值
    state.clip_input_path_field = input_path_field
    state.clip_output_path_field = output_path_field
    state.clip_start_time_field = start_time_field
    state.clip_end_time_field = end_time_field
    state.clip_duration_value_field = duration_value_field
    state.clip_duration_unit_dropdown = duration_unit_dropdown

    return ft.Container(
        content=ft.Column(
            controls=[
                input_section,
                time_section,
                quality_section,
                output_section,
                ft.Container(content=run_button, padding=ft.padding.only(top=2)),
            ],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.only(top=8),
        expand=True,
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
