"""
snipkin.handlers - 业务逻辑处理模块

本包包含所有事件处理函数：
- clip_handler:   视频截取的事件处理
- concat_handler: 视频拼接的事件处理
"""

from snipkin.handlers.clip_handler import (
    handle_clip_run,
    on_input_file_picked,
    on_output_file_picked,
)
from snipkin.handlers.concat_handler import (
    handle_concat_add_files_picked,
    handle_concat_clear,
    handle_concat_move_down,
    handle_concat_move_up,
    handle_concat_output_picked,
    handle_concat_remove_file,
    handle_concat_run,
)

__all__ = [
    "handle_clip_run",
    "on_input_file_picked",
    "on_output_file_picked",
    "handle_concat_add_files_picked",
    "handle_concat_clear",
    "handle_concat_move_down",
    "handle_concat_move_up",
    "handle_concat_output_picked",
    "handle_concat_remove_file",
    "handle_concat_run",
]
