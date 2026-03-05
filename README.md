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
- 🎨 **现代化交互**：深浅色主题自适应切换，符合直觉的排版逻辑，所见即所得。
- 🌐 **多端适用**：全面兼容 macOS、Windows 与 Linux 操作系统。

---

## 🛠️ 快速开始 | Quick Start

### 1. 环境依赖 (Prerequisites)

Snipkin 底层依赖 `ffmpeg` 进行视频处理，请先确保系统中已安装：

- **macOS**: `brew install ffmpeg`
- **Windows**: 使用 `winget install ffmpeg`，或从官网将其下载并配置到环境变量。
- **Linux**: `sudo apt install ffmpeg`
- **Python**: 建议 3.8 及以上版本

### 2. 克隆与运行 (Installation & Run)

```bash
# 1. 克隆项目到本地
git clone https://github.com/sitkinYip/Snipkin.git
cd Snipkin

# 2. 赋予脚本执行权限 (仅 macOS/Linux 需要)
chmod +x run.sh

# 3. 启动应用
# macOS / Linux 用户执行：
./run.sh

# Windows 用户直接双击运行 run.bat 即可
```

_(备选方案：也可手动执行 `pip install -r requirements.txt` 然后运行 `python main.py`)_

---

## 📖 使用指南 | Usage Guide

### 🎬 任务一：视频截取 (Clip)

1. 点击 **选择文件** 载入源视频。
2. 设置 **开始时间** 与 **结束时间**（或只写**持续时长**）。
3. （可选）勾选 **视频压缩**，按需调整质量、分辨率、帧率等选项。
4. 选择需要的 **输出格式** (如 MP4/MOV/GIF 等)。
5. 点击 **开始截取**。

### 🔗 任务二：视频拼接 (Concat)

1. 点击 **添加文件** 导入多段零散的视频。可通过**上移/下移**调整合并顺序。
2. （可选）为拼接处选择一种 **过渡效果** (如淡入淡出等) 并可设置过渡时间。
3. （可选）勾选 **视频压缩** 以统一最终输出的文件规格。
4. 点击 **开始拼接**。

---

## 🤝 参与贡献 | Contributing

在使用过程中，若是发现了任何可以打磨的毛刺，或是对功能有更好的建议，欢迎提交 Issue 交流意见，或直接提交 Pull Request！
