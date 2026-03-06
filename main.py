"""
Snipkin - 跨平台视频处理工具

基于 Flet 构建的现代化 GUI 桌面应用，
调用本地 ffmpeg 实现视频截取、拼接与导出。
支持 macOS / Windows / Linux。

本文件为程序入口，实际业务逻辑已拆分至 snipkin 包中：
  - snipkin/constants.py        全局常量与配置项
  - snipkin/utils.py            工具函数（ffmpeg 路径、时间码解析等）
  - snipkin/app.py              主应用构建（Page 配置 + UI 组装）
  - snipkin/ui/clip_tab.py      截取 Tab 界面构建
  - snipkin/ui/concat_tab.py    拼接 Tab 界面构建
  - snipkin/ui/log_section.py   日志区域界面与工具方法
  - snipkin/handlers/clip_handler.py    截取业务逻辑
  - snipkin/handlers/concat_handler.py  拼接业务逻辑

启动方式：
  python main.py
  或通过 run.sh / run.bat 一键启动
"""

import flet as ft

from snipkin.app import build_app


def main(page: ft.Page):
    """Flet 应用程序入口"""
    build_app(page)


if __name__ == "__main__":
    ft.app(target=main)