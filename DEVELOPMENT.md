# Snipkin 开发规范

> 本文档面向 Snipkin 项目的开发者，定义了项目的架构设计、代码规范、模块职责与协作约定。
> 请在贡献代码前仔细阅读。

---

## 目录

- [项目架构](#项目架构)
- [目录结构](#目录结构)
- [模块职责说明](#模块职责说明)
- [架构设计：Mixin 模式](#架构设计mixin-模式)
- [代码风格规范](#代码风格规范)
- [命名规范](#命名规范)
- [注释规范](#注释规范)
- [新增功能指南](#新增功能指南)
- [常量管理规范](#常量管理规范)
- [线程安全规范](#线程安全规范)
- [Git 提交规范](#git-提交规范)
- [依赖管理](#依赖管理)
- [构建与发布](#构建与发布)

---

## 项目架构

Snipkin 是一个基于 **Python + CustomTkinter + FFmpeg** 的跨平台桌面视频处理工具。

- **UI 框架**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)（基于 Tkinter 的现代化 GUI 库）
- **视频处理引擎**: [FFmpeg](https://ffmpeg.org/)（通过 subprocess 调用本地 ffmpeg 命令行）
- **打包工具**: [PyInstaller](https://pyinstaller.org/)（将 Python 应用打包为独立可执行文件）
- **支持平台**: macOS / Windows / Linux

---

## 目录结构

```
Snipkin/
├── main.py                          # 程序入口（仅负责启动，不含业务逻辑）
├── requirements.txt                 # 运行时依赖
├── requirements-build.txt           # 构建打包依赖
├── run.sh / run.bat                 # 一键启动脚本
├── build_macos.sh / build_windows.bat  # 一键打包脚本
├── README.md                        # 用户文档
├── DEVELOPMENT.md                   # 开发规范（本文件）
│
└── snipkin/                         # 主业务包
    ├── __init__.py                  # 包初始化，定义版本号
    ├── constants.py                 # 全局常量与配置项
    ├── utils.py                     # 通用工具函数
    ├── app.py                       # 主窗口类（状态初始化 + UI 组装入口）
    │
    ├── ui/                          # UI 构建子包（纯界面，不含业务逻辑）
    │   ├── __init__.py
    │   ├── clip_tab.py              # 视频截取 Tab 的界面构建
    │   ├── concat_tab.py            # 视频拼接 Tab 的界面构建
    │   └── log_section.py           # 日志输出区域的界面与工具方法
    │
    └── handlers/                    # 业务逻辑子包（事件处理 + ffmpeg 命令构建）
        ├── __init__.py
        ├── clip_handler.py          # 视频截取的事件处理与核心逻辑
        └── concat_handler.py        # 视频拼接的事件处理与核心逻辑
```

---

## 模块职责说明

### `main.py` — 程序入口

- **唯一职责**: 导入 `VideoClipperApp` 并启动主循环
- **禁止**: 在此文件中添加任何业务逻辑、常量定义或工具函数

### `snipkin/constants.py` — 全局常量

- 集中管理所有 UI 下拉选项、文件类型过滤器、编码参数等配置
- 新增选项时只需在对应字典中添加一行，UI 会自动读取

### `snipkin/utils.py` — 工具函数

- 提供与 ffmpeg 交互和时间码处理相关的纯函数
- **不依赖任何 UI 组件**，可独立导入和测试
- 包括: `get_executable_path`、`check_ffmpeg_available`、`parse_timecode_to_seconds`、`format_seconds_to_timecode`、`get_video_duration`

### `snipkin/app.py` — 主窗口类

- 通过多继承组合所有 Mixin，是整个应用的"胶水类"
- 负责: 窗口配置、状态变量初始化、顶层 UI 框架搭建、ffmpeg 检测
- **禁止**: 在此文件中编写具体的 UI 构建代码或业务逻辑

### `snipkin/ui/` — UI 构建模块

- 每个文件定义一个 Mixin 类，只负责界面元素的创建和布局
- UI 交互逻辑（如开关切换、面板展开/收起）可以放在 UI Mixin 中
- **禁止**: 在 UI 模块中编写 ffmpeg 命令构建、文件校验等业务逻辑

### `snipkin/handlers/` — 业务逻辑模块

- 每个文件定义一个 Mixin 类，负责事件处理、参数校验、命令构建和执行
- **禁止**: 在 Handler 模块中创建 UI 组件

---

## 架构设计：Mixin 模式

本项目采用 **Mixin 多继承模式** 组织代码，核心思路：

```python
class VideoClipperApp(
    ClipTabMixin,        # 截取 Tab UI
    ConcatTabMixin,      # 拼接 Tab UI
    LogSectionMixin,     # 日志区域 UI + 工具方法
    ClipHandlerMixin,    # 截取业务逻辑
    ConcatHandlerMixin,  # 拼接业务逻辑
    ctk.CTk,             # CustomTkinter 主窗口基类
):
    ...
```

### 为什么选择 Mixin？

- **避免大量参数传递**: 所有 Mixin 通过 `self` 直接访问主窗口的状态变量和 UI 组件
- **职责清晰**: UI 构建和业务逻辑分离到不同文件，互不干扰
- **易于扩展**: 新增功能只需添加新的 Mixin 类并混入主窗口

### Mixin 编写规则

1. Mixin 类**不继承任何基类**（纯 Mixin）
2. Mixin 类**不定义 `__init__` 方法**，所有状态变量在 `app.py` 中初始化
3. Mixin 中通过 `self.xxx` 访问的属性，必须确保在 `app.py` 的 `__init__` 中已初始化
4. UI Mixin 的方法以 `_build_` 开头，Handler Mixin 的方法以 `_on_` 或 `_build_xxx_command` / `_execute_` 开头

---

## 代码风格规范

### 基本规则

- **Python 版本**: 3.8+（兼容 `list[str]` 等类型注解需 3.9+，如需兼容 3.8 请使用 `List[str]`）
- **缩进**: 4 个空格，禁止使用 Tab
- **行宽**: 建议不超过 100 字符
- **引号**: 统一使用双引号 `""`，docstring 使用三双引号 `"""`
- **尾部逗号**: 多行参数列表、字典、列表的最后一项后添加尾部逗号

### 导入顺序

按以下顺序分组，组间空一行：

```python
# 1. 标准库
import os
import subprocess

# 2. 第三方库
import customtkinter as ctk

# 3. 项目内部模块
from snipkin.constants import VIDEO_FILE_TYPES
from snipkin.utils import check_ffmpeg_available
```

### 类型注解

- 函数签名必须添加参数类型和返回值类型注解
- 类属性在 `__init__` 中通过赋值自动推断类型，无需额外注解
- 使用 `str | None` 而非 `Optional[str]`（Python 3.10+），如需兼容低版本使用 `Optional`

---

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块文件 | 小写下划线 | `clip_handler.py` |
| 类名 | 大驼峰 | `VideoClipperApp` |
| Mixin 类名 | 大驼峰 + `Mixin` 后缀 | `ClipTabMixin` |
| 函数/方法 | 小写下划线 | `parse_timecode_to_seconds` |
| 私有方法 | 单下划线前缀 | `_build_clip_tab` |
| 常量 | 全大写下划线 | `COMPRESS_QUALITY_PRESETS` |
| 状态变量 | 小写下划线 + 语义后缀 | `compress_enabled_var`、`output_format_var` |
| 拼接 Tab 变量 | `concat_` 前缀 | `concat_resolution_var` |

### 方法命名约定

| 前缀 | 用途 | 所在模块 |
|------|------|----------|
| `_build_` | 构建 UI 组件 | `ui/` |
| `_on_` | 事件处理回调 | `handlers/` 或 `ui/`（简单交互） |
| `_build_xxx_command` | 构建 ffmpeg 命令 | `handlers/` |
| `_execute_` | 执行 ffmpeg 命令 | `handlers/` |
| `_log` / `_log_threadsafe` | 日志写入 | `ui/log_section.py` |

---

## 注释规范

### 模块级注释

每个 `.py` 文件顶部必须包含模块级 docstring，说明：
- 模块的用途和职责
- 包含的主要类或函数
- 设计说明（如有）

```python
"""
snipkin.handlers.clip_handler - 视频截取的业务逻辑处理

本模块定义 ClipHandlerMixin 类，以 Mixin 模式提供视频截取功能的所有业务逻辑，包括：
- 输入文件选择事件处理
- ffmpeg 截取命令构建
- ...

设计说明：
  本模块不包含任何 UI 构建代码，仅处理业务逻辑。
"""
```

### 函数/方法注释

- 所有公开方法和复杂的私有方法必须包含 docstring
- 使用中文编写，说明功能、参数、返回值
- 复杂逻辑需补充"工作原理"或"策略说明"

```python
def _build_xfade_command(self, ...) -> list[str]:
    """
    使用 xfade 滤镜构建带过渡动画的拼接命令。

    工作原理：
      每两段视频之间插入一个 xfade 视频过渡和一个 acrossfade 音频过渡。
      offset 的计算公式：前面所有视频总时长 - 前面所有过渡占用的时长 - 当前过渡时长。

    参数:
        file_list: 输入视频文件路径列表
        ...

    返回:
        完整的 ffmpeg 命令参数列表
    """
```

### 行内注释

- 仅在逻辑不直观时添加，解释"为什么"而非"做了什么"
- 注释放在代码行上方，不使用行尾注释
- 使用 `# ====` 分隔符划分代码区域

---

## 新增功能指南

### 场景一：新增一个下拉选项（如新的分辨率）

1. 在 `snipkin/constants.py` 对应的字典中添加一行即可
2. UI 会自动读取字典的 keys 作为下拉菜单选项，无需修改 UI 代码

### 场景二：新增一个 Tab 页面

1. 在 `snipkin/ui/` 下创建新的 UI Mixin 文件（如 `convert_tab.py`）
2. 在 `snipkin/handlers/` 下创建对应的 Handler Mixin 文件（如 `convert_handler.py`）
3. 在 `snipkin/app.py` 中：
   - 将新 Mixin 加入 `VideoClipperApp` 的继承列表
   - 在 `_init_xxx_state()` 中初始化新 Tab 的状态变量
   - 在 `_build_ui()` 中添加新 Tab
4. 更新 `snipkin/ui/__init__.py` 和 `snipkin/handlers/__init__.py` 的导出

### 场景三：新增一个工具函数

1. 如果是通用工具函数（不依赖 UI），添加到 `snipkin/utils.py`
2. 如果是某个功能专用的辅助方法，放在对应的 Handler Mixin 中

---

## 常量管理规范

- 所有 UI 选项、文件类型、编码参数等**必须定义在 `constants.py`** 中
- **禁止**在 UI 或 Handler 代码中硬编码魔法数字或字符串
- 常量字典的 key 是用户可见的显示文本，value 是传给 ffmpeg 的实际参数值
- 新增常量时必须添加中文注释说明用途

---

## 线程安全规范

- **UI 操作只能在主线程中执行**（Tkinter 的限制）
- ffmpeg 命令在子线程中通过 `threading.Thread(daemon=True)` 执行
- 子线程中写入日志必须使用 `self._log_threadsafe()`，禁止直接调用 `self._log()`
- 子线程中恢复按钮状态必须通过 `self.after(0, callback)` 调度到主线程

---

## Git 提交规范

### Commit Message 格式

```
<类型>: <简短描述>

<可选的详细说明>
```

### 类型列表

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 Bug |
| `refactor` | 重构（不改变功能） |
| `style` | 代码风格调整（不影响逻辑） |
| `docs` | 文档更新 |
| `build` | 构建/打包相关 |
| `chore` | 杂项（依赖更新等） |

### 示例

```
feat: 新增视频转码功能 Tab
refactor: 将 main.py 拆分为模块化包结构
fix: 修复拼接模式下过渡时长为 0 时的崩溃问题
```

---

## 依赖管理

- **运行时依赖**: 记录在 `requirements.txt` 中
- **构建打包依赖**: 记录在 `requirements-build.txt` 中
- 新增依赖时必须同步更新对应的 requirements 文件
- 尽量使用最小化依赖，避免引入不必要的第三方库

---

## 构建与发布

### macOS 打包

```bash
./build_macos.sh
```

### Windows 打包

```bat
build_windows.bat
```

打包脚本会自动从系统中寻找 `ffmpeg` 并将其嵌入最终的应用包中，确保分发给用户时开箱即用。

---

## 附录：MRO（方法解析顺序）

由于使用了多继承，Python 会按照 C3 线性化算法确定方法解析顺序。当前的 MRO 为：

```
VideoClipperApp
  → ClipTabMixin
  → ConcatTabMixin
  → LogSectionMixin
  → ClipHandlerMixin
  → ConcatHandlerMixin
  → ctk.CTk
  → ...
```

各 Mixin 的方法名不存在冲突（通过前缀区分），因此 MRO 不会影响功能。
如果未来新增 Mixin 导致方法名冲突，需要通过重命名或显式调用 `super()` 解决。
