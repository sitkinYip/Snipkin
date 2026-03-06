"""
snipkin.ui.concat_tab - 视频拼接 Tab 的界面构建（Flet 版）

本模块提供 build_concat_tab 函数，构建视频拼接 Tab 的完整 UI，包括：
- 多文件选择与排序区域（ft.ListView + ft.ListTile，每行带垃圾桶图标）
- 过渡动画设置区域（iOS 风格 ft.Dropdown）
- 视频压缩设置区域（开关 + 质量预设 + 高级选项动画展开）
- 输出设置区域（格式选择 + 保存路径）
- 执行按钮区域（Hover 光效 + 缩放动画）

设计说明：
  从 Mixin 模式迁移为函数式组合模式。
  所有状态通过 AppState 实例传递，UI 控件引用存储在 state 中。
  事件处理逻辑由 snipkin.handlers.concat_handler 提供。
"""

from __future__ import annotations

import os
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
    CONCAT_SUPPORTED_FORMATS,
    FRAMERATE_OPTIONS,
    RESOLUTION_OPTIONS,
    XFADE_TRANSITIONS,
)

if TYPE_CHECKING:
    from snipkin.app import AppState


def _make_styled_textfield(
    value: str = "",
    hint_text: str = "",
    width: int | None = None,
    read_only: bool = False,
    expand: bool = False,
    on_change=None,
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
    创建统一风格的 iOS 风格下拉选择框。

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


def build_concat_tab(state: AppState) -> ft.Container:
    """
    构建视频拼接 Tab 的完整内容。

    按从上到下的顺序依次构建：文件列表 → 过渡动画 → 压缩设置 → 输出设置 → 执行按钮。
    所有事件处理通过闭包绑定到 state 和 handler 函数。

    参数:
        state: 应用状态实例

    返回:
        拼接 Tab 的完整 Container 组件
    """
    from snipkin.handlers.concat_handler import (
        handle_concat_add_files_picked,
        handle_concat_clear,
        handle_concat_move_down,
        handle_concat_move_up,
        handle_concat_output_picked,
        handle_concat_run,
    )

    # ---- FilePicker 实例（Flet 0.82+ async API） ----
    concat_file_picker = ft.FilePicker()
    concat_output_picker = ft.FilePicker()

    async def pick_concat_files(_event):
        """异步选择要拼接的视频文件（多选）"""
        result = await concat_file_picker.pick_files(
            dialog_title="选择要拼接的视频文件（可多选）",
            allowed_extensions=[
                "mp4", "mov", "mkv", "avi", "flv",
                "wmv", "webm", "ts", "m4v",
            ],
            allow_multiple=True,
        )
        handle_concat_add_files_picked(result, state, file_list_view, output_path_field)

    async def pick_concat_output(_event):
        """异步选择拼接输出文件保存路径"""
        result = await concat_output_picker.save_file(
            dialog_title="选择拼接输出文件保存位置",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=[state.concat_output_format],
            file_name=output_path_field.value.split("/")[-1]
            if output_path_field.value else None,
        )
        handle_concat_output_picked(result, state, output_path_field)

    # ---- 文件列表区域 ----
    file_list_view = ft.ListView(
        height=140,
        spacing=4,
        padding=ft.padding.all(4),
    )
    state.concat_listbox = file_list_view

    # 空状态提示
    empty_hint = ft.Container(
        content=ft.Text(
            "暂无文件，请点击下方按钮添加",
            size=13,
            color=TEXT_SECONDARY_COLOR,
            text_align=ft.TextAlign.CENTER,
        ),
        bgcolor=LOG_BACKGROUND_COLOR,
        border_radius=ft.border_radius.all(8),
        padding=ft.padding.all(24),
        alignment=ft.Alignment(0, 0),
    )

    file_list_container = ft.Container(
        content=ft.Stack(
            controls=[
                empty_hint,
                file_list_view,
            ],
        ),
        bgcolor=ft.Colors.with_opacity(0.2, LOG_BACKGROUND_COLOR),
        border_radius=ft.border_radius.all(8),
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, "#ffffff")),
    )

    file_section = _build_section_card(
        icon=ft.CupertinoIcons.FOLDER_OPEN,
        title="视频文件列表",
        content=ft.Column(
            controls=[
                file_list_container,
                ft.Row(
                    controls=[
                        _build_action_button(
                            text="添加文件",
                            icon=ft.CupertinoIcons.PLUS,
                            on_click=pick_concat_files,
                        ),
                        _build_action_button(
                            text="上移",
                            icon=ft.CupertinoIcons.ARROW_UP,
                            on_click=lambda _: handle_concat_move_up(
                                state, file_list_view,
                            ),
                        ),
                        _build_action_button(
                            text="下移",
                            icon=ft.CupertinoIcons.ARROW_DOWN,
                            on_click=lambda _: handle_concat_move_down(
                                state, file_list_view,
                            ),
                        ),
                        _build_action_button(
                            text="清空",
                            icon=ft.CupertinoIcons.CLEAR,
                            color="#636366",
                            hover_color="#48484a",
                            on_click=lambda _: handle_concat_clear(
                                state, file_list_view,
                            ),
                        ),
                    ],
                    spacing=6,
                    wrap=True,
                ),
            ],
            spacing=10,
        ),
    )

    # ---- 过渡动画区域 ----
    transition_dropdown = _make_styled_dropdown(
        value=state.concat_transition,
        options=list(XFADE_TRANSITIONS.keys()),
        width=220,
        on_select=lambda event: setattr(
            state, "concat_transition", event.control.value,
        ),
    )
    state.concat_transition_dropdown = transition_dropdown

    transition_duration_field = _make_styled_textfield(
        value=state.concat_transition_duration,
        hint_text="1.0",
        width=70,
        on_change=lambda event: setattr(
            state, "concat_transition_duration", event.control.value,
        ),
    )
    state.concat_transition_duration_field = transition_duration_field

    transition_section = _build_section_card(
        icon=ft.CupertinoIcons.FILM,
        title="过渡动画（可选）",
        content=ft.Row(
            controls=[
                ft.Text("过渡效果:", size=13, color=TEXT_SECONDARY_COLOR),
                transition_dropdown,
                ft.Text("过渡时长(秒):", size=13, color=TEXT_SECONDARY_COLOR),
                transition_duration_field,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # ---- 压缩设置区域 ----
    compress_section = _build_concat_compress_section(state)

    # ---- 输出设置区域 ----
    output_format_dropdown = _make_styled_dropdown(
        value=state.concat_output_format,
        options=CONCAT_SUPPORTED_FORMATS,
        width=100,
        on_select=lambda event: setattr(
            state, "concat_output_format", event.control.value,
        ),
    )
    state.concat_output_format_dropdown = output_format_dropdown

    output_path_field = _make_styled_textfield(
        hint_text="输出文件路径...",
        expand=True,
        on_change=lambda event: setattr(
            state, "concat_output_path", event.control.value,
        ),
    )
    state.concat_output_path_field = output_path_field

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
                            on_click=pick_concat_output,
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=8,
        ),
    )

    # ---- 执行按钮（Hover 光效 + 缩放动画） ----
    from snipkin.ui.clip_tab import _build_glow_run_button
    run_button = _build_glow_run_button(
        text="开始拼接",
        icon=ft.CupertinoIcons.PLAY_ARROW_SOLID,
        on_click=lambda _: handle_concat_run(state),
    )
    state.concat_run_button = run_button

    return ft.Container(
        content=ft.Column(
            controls=[
                file_section,
                transition_section,
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


def _build_concat_compress_section(state: AppState) -> ft.Container:
    """
    构建拼接 Tab 的视频压缩设置区域，带平滑的高度动画展开效果。

    结构与截取 Tab 的压缩设置一致，但使用 concat_ 前缀的独立状态变量。

    参数:
        state: 应用状态实例

    返回:
        压缩设置区域的 Container 组件
    """
    quality_dropdown = _make_styled_dropdown(
        value=state.concat_compress_quality,
        options=list(COMPRESS_QUALITY_PRESETS.keys()),
        width=200,
        on_select=lambda event: setattr(
            state, "concat_compress_quality", event.control.value,
        ),
    )
    state.concat_quality_dropdown = quality_dropdown

    resolution_dropdown = _make_styled_dropdown(
        value=state.concat_resolution,
        options=list(RESOLUTION_OPTIONS.keys()),
        width=140,
        on_select=lambda event: setattr(
            state, "concat_resolution", event.control.value,
        ),
    )
    state.concat_resolution_dropdown = resolution_dropdown

    framerate_dropdown = _make_styled_dropdown(
        value=state.concat_framerate,
        options=list(FRAMERATE_OPTIONS.keys()),
        width=120,
        on_select=lambda event: setattr(
            state, "concat_framerate", event.control.value,
        ),
    )
    state.concat_framerate_dropdown = framerate_dropdown

    audio_bitrate_dropdown = _make_styled_dropdown(
        value=state.concat_audio_bitrate,
        options=list(AUDIO_BITRATE_OPTIONS.keys()),
        width=160,
        on_select=lambda event: setattr(
            state, "concat_audio_bitrate", event.control.value,
        ),
    )
    state.concat_audio_bitrate_dropdown = audio_bitrate_dropdown

    # 高级选项面板
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

    advanced_toggle_icon = ft.Icon(
        ft.CupertinoIcons.CHEVRON_RIGHT,
        size=14,
        color=TEXT_SECONDARY_COLOR,
        rotate=ft.Rotate(0),
        animate_rotation=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT),
    )

    def toggle_advanced(_event):
        """切换高级选项面板的展开/收起状态"""
        state.concat_advanced_visible = not state.concat_advanced_visible
        if state.concat_advanced_visible:
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

    # 压缩选项容器
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

    def toggle_compress(event):
        """切换压缩开关，展开/收起压缩选项"""
        state.concat_compress_enabled = event.control.value
        if state.concat_compress_enabled:
            compress_options_container.height = None
            compress_options_container.opacity = 1
        else:
            compress_options_container.height = 0
            compress_options_container.opacity = 0
            state.concat_advanced_visible = False
            advanced_container.height = 0
            advanced_container.opacity = 0
            advanced_toggle_icon.rotate = ft.Rotate(0)
        state.page.update()

    compress_switch = ft.CupertinoSwitch(
        value=state.concat_compress_enabled,
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


def build_file_list_tile(
    index: int,
    file_path: str,
    state: AppState,
    file_list_view: ft.ListView,
) -> ft.Container:
    """
    构建文件列表中的单个条目。

    每个条目是一个带圆角和半透明背景的 ListTile，
    左侧显示序号和文件名，右侧带垃圾桶删除图标。
    点击条目可选中该项（高亮显示），选中状态用于上移/下移操作。

    参数:
        index:          文件在列表中的索引
        file_path:      文件的绝对路径
        state:          应用状态实例
        file_list_view: ListView 控件引用（用于刷新）

    返回:
        文件条目的 Container 组件
    """
    from snipkin.handlers.concat_handler import handle_concat_remove_file

    file_name = os.path.basename(file_path)
    is_selected = state.concat_selected_index == index

    tile_container = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(
                    f"{index + 1}.",
                    size=12,
                    color=ACCENT_BLUE if is_selected else TEXT_SECONDARY_COLOR,
                    width=24,
                ),
                ft.Icon(
                    ft.CupertinoIcons.FILM,
                    size=14,
                    color=ACCENT_BLUE,
                ),
                ft.Text(
                    file_name,
                    size=13,
                    color=TEXT_PRIMARY_COLOR,
                    expand=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.IconButton(
                    icon=ft.CupertinoIcons.TRASH,
                    icon_size=16,
                    icon_color="#d9534f",
                    tooltip="移除此文件",
                    on_click=lambda _, idx=index: handle_concat_remove_file(
                        state, file_list_view, idx,
                    ),
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(4),
                    ),
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.with_opacity(0.5, ACCENT_BLUE)
        if is_selected
        else ft.Colors.with_opacity(0.3, SURFACE_COLOR),
        border_radius=ft.border_radius.all(8),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
        border=ft.border.all(
            1,
            ft.Colors.with_opacity(0.3, ACCENT_BLUE)
            if is_selected
            else ft.Colors.with_opacity(0.05, "#ffffff"),
        ),
        on_click=lambda _, idx=index: _select_file_item(
            state, file_list_view, idx,
        ),
        ink=True,
    )

    return tile_container


def _select_file_item(
    state: AppState,
    file_list_view: ft.ListView,
    index: int,
) -> None:
    """
    选中文件列表中的指定条目。

    更新 state.concat_selected_index 并刷新列表以反映选中高亮。
    再次点击已选中的条目会取消选中。

    参数:
        state:          应用状态实例
        file_list_view: ListView 控件引用
        index:          被点击的条目索引
    """
    from snipkin.handlers.concat_handler import _refresh_file_list

    if state.concat_selected_index == index:
        state.concat_selected_index = -1
    else:
        state.concat_selected_index = index
    _refresh_file_list(state, file_list_view)