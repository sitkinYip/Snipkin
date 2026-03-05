<div align="center">

# 🎬 Snipkin

_「定格时光的切片，编织光影的诗篇」_

**跨平台 · 现代化 GUI · 高性能视频处理利器**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg?style=flat-square)](https://www.python.org/)
[![CustomTkinter](https://img.shields.io/badge/Interface-CustomTkinter-42a5f5.svg?style=flat-square)](https://github.com/TomSchimansky/CustomTkinter)
[![FFmpeg](https://img.shields.io/badge/Powered%20by-FFmpeg-5fb151.svg?style=flat-square)](https://ffmpeg.org/)

</div>

## 📖 序言 | Introduction

> **这是一款基于 Python 与 FFmpeg 的轻量级桌面应用，专为视频的高效截取、多段无缝拼接以及格式压缩而设计。**

在这个影像泛滥的时代，我们比以往任何时候都更需要一款纯粹、轻量、且优雅的工具，来修剪冗余的片段，将散落的记忆串联成珠。

**Snipkin** 诞生于此。它是一把数字化的精工剪刀，基于强大的底层引擎 `ffmpeg` 构建，却隐藏了命令行的冰冷与繁琐。通过现代化、类 macOS 风格的用户界面，Snipkin 致力于为您提供丝滑如水的视频截取与拼接体验。

无论您是想要珍藏某个惊艳的瞬间，还是将多段旅途见闻融合为一部光影集锦，Snipkin 都能以极简的操作流，助您轻松达成。

---

## ✨ 核心亮点 | Features

- ✂️ **精准截取**：支持帧级时间轴切割，可通过时间区间或持续时长提取视频片段。
- 🔗 **无缝拼接**：多段视频完美连接，内置 16 种（如淡入淡出、滑动等）过渡动画，画面自然流畅。
- 🗜️ **智能压缩**：提供一键式质量预设（高/中/低），支持自定义分辨率、帧率及音频码率。
- 🚀 **智能命名与导出**：文件名自动附加时间戳防止覆盖，支持手动编辑保存路径，并能自动创建不存在的输出文件夹。
- 🎨 **现代化交互**：深浅色主题自适应切换，保存路径对话框智能记忆当前输入的内容。
- 🌐 **多端适用**：全面兼容 macOS、Windows 与 Linux 操作系统。

---

---

## ⚡ 快速开始 | Quick Start

### 🚀 方案一：独立应用（推荐 - 无需环境配置）

如果您不想安装 Python 或配置 FFmpeg 环境变量，可以直接前往 **[Releases](https://github.com/sitkinYip/Snipkin/releases)** 页面下载预编译好的版本：

- **macOS**: 下载最新的 `Snipkin.dmg`，将图标拖入应用文件夹。程序已内置专用 FFmpeg。
- **Windows**: 下载最新的 `Snipkin.exe`（单文件直接运行版）。

### 🛠️ 方案二：源码运行与构建 (For Developers)

#### 1. 环境依赖 (Prerequisites)

使用源码运行时，请确保系统中已安装 `ffmpeg`：

- **macOS**: `brew install ffmpeg`
- **Windows**: `winget install ffmpeg` 或手动配置 PATH。
- **Linux**: `sudo apt install ffmpeg`
- **Python**: 建议 3.8 及以上版本。

#### 2. 克隆与启动 (Installation & Run)

```bash
# 1. 克隆项目
git clone https://github.com/sitkinYip/Snipkin.git
cd Snipkin

# 2. 赋予脚本执行权限 (仅 macOS/Linux 需要)
chmod +x run.sh

# 3. 启动
# macOS / Linux 用户执行：
./run.sh
# Windows 用户直接双击运行 run.bat 即可
```

#### 3. 自行打包 (Building your own App)

项目内置了一键打包脚本，可将代码封装为包含内置 FFmpeg 的独立软件：

- **生成 macOS App**: 执行 `./build_macos.sh`
- **生成 Windows Exe**: 执行 `build_windows.bat` (需在 Win 环境下)

> [!TIP]
> 打包脚本会自动从您的系统中寻找 `ffmpeg` 并将其“缝合”进最终的 App 包内，确保分发给他人时开箱即用。

---

## 📖 使用指南 | Usage Guide

### 🎬 任务一：视频截取 (Clip)

1. 点击 **选择文件** 载入源视频。
2. 设置 **开始时间** 与 **结束时间**（或只写**持续时长**）。
3. （可选）勾选 **视频压缩**，按需调整质量、分辨率、帧率等选项。
4. 确认 **输出设置**：系统会自动生成带时间戳的文件名，您也可以**手动直接编辑**输入框中的路径。
5. 点击 **保存路径**（可选）或直接点击 **开始截取**。如果手动填写的文件夹不存在，系统将自动为您创建。

### 🔗 任务二：视频拼接 (Concat)

1. 点击 **添加文件** 导入多段零散的视频。可通过**上移/下移**调整合并顺序。
2. （可选）为拼接处选择一种 **过渡效果** (如淡入淡出等) 并可设置过渡时间。
3. （可选）勾选 **视频压缩** 以统一最终输出的文件规格。
4. 点击 **开始拼接**。

---

## 🤝 参与贡献 | Contributing

在使用过程中，若是发现了任何可以打磨的毛刺，或是对功能有更好的建议，欢迎提交 Issue 交流意见，或直接提交 Pull Request！
