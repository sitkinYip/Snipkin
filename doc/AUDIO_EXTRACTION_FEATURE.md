# 音频提取功能实现说明

## 功能概述

新增了一个"音频提取"Tab 页面，允许用户从视频文件中提取音频轨道，支持以下特性：

### 核心功能
- ✅ 选择视频文件作为输入
- ✅ 可选的输出路径和格式
- ✅ 支持 6 种音频格式：MP3、AAC、FLAC、WAV、M4A、OGG
- ✅ 音质选择：高品质 (320k)、标准品质 (192k)、低品质 (128k)
- ✅ 时间截取选项：
  - 提取完整音频（默认）
  - 自定义开始时间和结束时间
  - 或使用持续时长
- ✅ 与视频截取类似的界面风格和交互逻辑

## 文件结构

### 新增文件

1. **`snipkin/core/extract_audio_core.py`** - 核心业务逻辑层
   - `generate_audio_output_path()`: 生成默认输出路径
   - `validate_extract_params()`: 参数校验
   - `build_extract_ffmpeg_command()`: 构建 ffmpeg 命令
   - `execute_ffmpeg()`: 执行命令

2. **`snipkin/handlers/extract_audio_handler.py`** - 事件处理层
   - `on_input_file_picked()`: 输入文件选择回调
   - `on_output_file_picked()`: 输出路径选择回调
   - `handle_extract_run()`: 执行提取处理
   - `_log()`, `_show_snackbar()`: 日志和通知工具

3. **`snipkin/ui/extract_audio_tab.py`** - UI 界面层
   - `build_extract_audio_tab()`: 构建完整 Tab 界面
   - `_make_styled_textfield()`: 风格化输入框
   - `_make_styled_dropdown()`: 风格化下拉框
   - `_build_glow_run_button()`: 发光按钮

### 修改文件

1. **`snipkin/constants.py`**
   - 新增 `AUDIO_FORMATS` 列表：定义支持的音频格式
   - 新增 `AUDIO_QUALITY_PRESETS` 字典：定义音质预设

2. **`snipkin/app.py`**
   - `AppState` 数据类新增音频提取相关字段：
     - `audio_output_format`: 输出格式（默认"mp3"）
     - `audio_quality`: 音质等级（默认"标准品质（192k）"）
     - `audio_extract_full`: 是否提取完整音频（默认 True）
   - 更新 Tabs 配置，添加"音频提取"Tab（位于第 2 个位置）
   - Tab 图标使用 `ft.CupertinoIcons.MUSIC_NOTE_2`

3. **包初始化文件更新**
   - `snipkin/ui/__init__.py`: 导出 `build_extract_audio_tab`
   - `snipkin/handlers/__init__.py`: 导出音频提取 handler 函数
   - `snipkin/core/__init__.py`: 更新文档注释

4. **`DEVELOPMENT.md`**
   - 更新目录结构说明
   - 更新模块职责说明
   - 添加音频提取 Tab 的状态字段示例

## 技术实现细节

### FFmpeg 命令构建策略

#### 1. 完整音频提取（extract_full=True）
```bash
ffmpeg -y -i input.mp4 -vn -c:a libmp3lame -b:a 320k output.mp3
```
- `-vn`: 禁用视频流
- `-c:a`: 音频编码器（根据格式选择）
- `-b:a`: 音频比特率（仅对有损格式）

#### 2. 部分音频提取（extract_full=False）
```bash
ffmpeg -y -i input.mp4 -ss 00:00:10 -t 00:00:30 -vn -c:a libmp3lame -b:a 192k output.mp3
```
- `-ss`: 开始时间
- `-t`: 持续时长

### 音频编码器映射

```python
audio_codec_map = {
    "mp3": "libmp3lame",    # MP3 使用 LAME 编码器
    "aac": "aac",           # AAC 使用原生编码器
    "flac": "flac",         # FLAC 无损格式
    "wav": "pcm_s16le",     # WAV 使用 PCM 编码
    "m4a": "aac",           # M4A 容器使用 AAC 编码
    "ogg": "libvorbis",     # OGG 使用 Vorbis 编码器
}
```

### 比特率应用规则

- **有损格式**（MP3、AAC、M4A、OGG）：应用用户选择的比特率
- **无损格式**（FLAC、WAV）：忽略比特率设置，使用无损编码

## UI/UX 设计

### 界面布局
```
┌─────────────────────────────────────┐
│ 📁 输入视频文件                     │
│    [文件路径输入框] [选择文件]      │
├─────────────────────────────────────┤
│ ⏱️ 时间设置                         │
│    开始时间：[0:00:00]              │
│    结束时间：[留空则用持续时长]     │
│    持续时长：[10] [秒]              │
│               [提取完整音频 ◠]      │ ← 开关
├─────────────────────────────────────┤
│ 🎵 音质设置                         │
│    输出音质：[标准品质（192k）▼]   │
│    ℹ️ 仅对有损格式生效              │
├─────────────────────────────────────┤
│ 💾 输出设置                         │
│    输出格式：[mp3▼]                 │
│    [文件路径输入框] [保存路径]      │
├─────────────────────────────────────┤
│          [🎵 开始提取]              │ ← 主按钮
└─────────────────────────────────────┘
```

### 交互特性

1. **完整提取开关**
   - 默认开启（`extract_full=True`）
   - 开启时禁用所有时间输入控件
   - 关闭时启用时间设置，允许截取部分音频

2. **格式联动**
   - 切换输出格式时，自动更新保存对话框的文件扩展名过滤
   - 无损格式（FLAC、WAV）自动忽略音质设置

3. **按钮状态反馈**
   - 点击后按钮变为"处理中..."并禁用
   - 图标切换为沙漏（`HOURGLASS`）
   - 完成后恢复初始状态

## 数据流向

```
用户操作 → UI 层（build_extract_audio_tab）
              ↓
        AppState（状态存储）
              ↓
        Handler 层（handle_extract_run）
              ↓
              ├─→ 参数校验（validate_extract_params）
              ├─→ 命令构建（build_extract_ffmpeg_command）
              └─→ 命令执行（execute_ffmpeg）
                        ↓
                  子线程执行
                        ↓
              回调通知 Handler
                        ↓
              更新 UI（日志 + 通知）
```

## 测试方法

### 单元测试脚本
运行 `test_extract_audio.py` 验证核心功能：
```bash
python test_extract_audio.py
```

测试覆盖：
- ✅ 输出路径生成
- ✅ 参数校验（完整提取/部分提取）
- ✅ FFmpeg 命令构建
- ✅ 不同格式的编码器选择
- ✅ 比特率设置应用

### 集成测试
1. 启动应用：`python main.py`
2. 切换到"音频提取"Tab
3. 选择测试视频文件
4. 测试不同场景：
   - 完整提取为 MP3
   - 截取部分音频为 FLAC
   - 切换不同格式验证音质选项

## 与设计规范的符合性

### ✅ 三层架构
- **UI 层**: 纯界面构建，无业务逻辑
- **Handler 层**: 事件处理桥梁，不直接构建命令
- **Core 层**: 纯函数，不依赖任何 UI 框架

### ✅ 命名规范
- 模块文件：小写下划线（`extract_audio_core.py`）
- 函数命名：
  - UI: `build_extract_audio_tab()`
  - Handler: `handle_extract_run()`
  - Core: `build_extract_ffmpeg_command()`
- 常量：全大写下划线（`AUDIO_FORMATS`、`AUDIO_QUALITY_PRESETS`）

### ✅ 代码风格
- 类型注解：完整的参数和返回值类型
- 文档字符串：中文 docstring，详细说明功能
- 缩进：4 空格，行宽 < 100 字符
- 导入顺序：标准库 → 第三方库 → 内部模块

### ✅ UI/UX 规范
- 毛玻璃卡片：统一的 `_build_section_card()`
- 颜色方案：使用预定义的 `ACCENT_BLUE` 等常量
- 图标：全部使用 Cupertino Icons
- 动画：Hover 光效 + 缩放动画
- 输入控件：圆角半透明风格

## 已知限制与改进方向

### 当前限制
1. ⚠️ 无法检测视频文件的实际时长（可以添加此功能）
2. ⚠️ 没有进度条显示（FFmpeg 输出解析较复杂）
3. ⚠️ 批量处理能力（未来可扩展）

### 潜在改进
1. 📊 添加视频时长检测和显示
2. 📈 实现实时进度条（解析 FFmpeg stderr 输出）
3. 🔄 支持批量视频文件音频提取
4. 🎚️ 高级选项：采样率、声道数设置
5. 💾 预设保存：保存常用的提取配置

## 依赖要求

- Python >= 3.10
- Flet >= 0.25.0
- FFmpeg（系统 PATH 中需可用）

## 兼容性

- ✅ Windows 10/11
- ✅ macOS 12+
- ✅ Linux（主流发行版）

---

**实现日期**: 2026-03-08  
**版本**: v1.0  
**状态**: ✅ 完成
