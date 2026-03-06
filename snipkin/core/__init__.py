"""
snipkin.core - 与 UI 框架无关的核心业务逻辑

本包包含所有与 UI 框架解耦的纯业务逻辑函数，包括：
- clip_core:   视频截取的参数校验、ffmpeg 命令构建与执行
- concat_core: 视频拼接的参数校验、ffmpeg 命令构建与执行

这些函数只接收普通 Python 类型参数（str / float / bool / list），
只通过返回值或回调函数（Callable）与调用方交互，
不依赖任何特定 UI 框架（tkinter / Flet 等）。
"""
