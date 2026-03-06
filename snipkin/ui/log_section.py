"""
snipkin.ui.log_section - 日志输出区域的界面构建与工具方法

本模块定义 LogSectionMixin 类，以 Mixin 模式提供：
- 日志输出区域的 UI 构建（共享于截取和拼接两个 Tab）
- 日志写入的工具方法（主线程写入 + 线程安全写入）

设计说明：
  日志区域位于主窗口底部，两个 Tab 共享同一个日志文本框。
  子线程中的 ffmpeg 执行结果通过 _log_threadsafe 方法安全地写入日志。
"""

import customtkinter as ctk


class LogSectionMixin:
    """
    日志输出区域的 UI 构建与工具方法 Mixin。

    提供日志文本框的构建方法，以及主线程和子线程中写入日志的工具方法。
    混入 VideoClipperApp 后，通过 self 访问主窗口实例的属性和方法。
    """

    def _build_log_section(self, parent):
        """
        构建日志输出区域。

        包含一个标题标签和一个只读的文本框，用于显示操作日志和 ffmpeg 执行结果。
        文本框默认处于 disabled 状态，写入时临时切换为 normal。

        参数:
            parent: 父容器（主窗口的根 Frame）
        """
        label = ctk.CTkLabel(
            parent, text="📋 执行日志",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.pack(anchor="w", pady=(0, 4))

        self.log_textbox = ctk.CTkTextbox(
            parent, height=120, state="disabled", wrap="word",
        )
        self.log_textbox.pack(fill="both", expand=True)

    def _log(self, message: str):
        """
        向日志文本框追加一行消息（仅在主线程中调用）。

        写入流程：临时启用文本框 → 插入消息 → 滚动到底部 → 恢复禁用状态。

        参数:
            message: 要写入的日志消息文本
        """
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _log_threadsafe(self, message: str):
        """
        线程安全的日志写入方法。

        通过 tkinter 的 after(0, callback) 机制将日志写入操作调度到主线程执行，
        避免子线程直接操作 UI 组件导致的线程安全问题。

        参数:
            message: 要写入的日志消息文本
        """
        self.after(0, lambda: self._log(message))
