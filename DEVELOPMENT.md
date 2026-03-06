# Snipkin 开发规范

> 本文档面向 Snipkin 项目的开发者，定义了项目的架构设计、代码规范、UI/UX 设计规范、模块职责与协作约定。
> 请在贡献代码前仔细阅读。

---

## 目录

- [项目架构](#项目架构)
- [目录结构](#目录结构)
- [模块职责说明](#模块职责说明)
- [架构设计：函数式组合 + AppState](#架构设计函数式组合--appstate)
- [UI/UX 设计规范](#uiux-设计规范)
- [代码风格规范](#代码风格规范)
- [命名规范](#命名规范)
- [注释规范](#注释规范)
- [新增功能指南](#新增功能指南)
- [常量管理规范](#常量管理规范)
- [线程安全规范](#线程安全规范)
- [Flet API 使用规范](#flet-api-使用规范)
- [Git 提交规范](#git-提交规范)
- [依赖管理](#依赖管理)
- [构建与发布](#构建与发布)

---

## 项目架构

Snipkin 是一个基于 **Python + Flet + FFmpeg** 的跨平台桌面视频处理工具。

- **UI 框架**: [Flet](https://flet.dev/)（基于 Flutter 的 Python GUI 框架，支持现代化 UI 与动画）
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
    ├── utils.py                     # 通用工具函数（ffmpeg 路径、时间码解析等）
    ├── app.py                       # 主应用构建（Page 配置 + AppState + UI 骨架 + 通用组件工厂）
    │
    ├── ui/                          # UI 构建子包（纯界面，不含业务逻辑）
    │   ├── __init__.py
    │   ├── clip_tab.py              # 视频截取 Tab 的界面构建
    │   └── concat_tab.py            # 视频拼接 Tab 的界面构建
    │
    ├── handlers/                    # 事件处理子包（UI 事件 → core 调用的桥梁层）
    │   ├── __init__.py
    │   ├── clip_handler.py          # 视频截取的事件处理
    │   └── concat_handler.py        # 视频拼接的事件处理
    │
    └── core/                        # 核心业务逻辑子包（与 UI 框架完全解耦）
        ├── __init__.py
        ├── clip_core.py             # 视频截取的参数校验、命令构建与执行
        └── concat_core.py           # 视频拼接的参数校验、命令构建与执行
```

---

## 模块职责说明

### `main.py` — 程序入口

- **唯一职责**: 导入 `build_app` 函数并通过 `ft.app(target=main)` 启动 Flet 应用
- **禁止**: 在此文件中添加任何业务逻辑、常量定义或工具函数

### `snipkin/constants.py` — 全局常量

- 集中管理所有 UI 下拉选项、文件类型过滤器、编码参数等配置
- 新增选项时只需在对应字典中添加一行，UI 会自动读取

### `snipkin/utils.py` — 工具函数

- 提供与 ffmpeg 交互和时间码处理相关的纯函数
- **不依赖任何 UI 组件**，可独立导入和测试
- 包括: `get_executable_path`、`check_ffmpeg_available`、`parse_timecode_to_seconds`、`format_seconds_to_timecode`、`get_video_duration`、`get_video_resolution`

### `snipkin/app.py` — 主应用构建

- 提供 `build_app(page)` 函数，是整个应用的组装入口
- 负责: Flet Page 窗口配置、`AppState` 数据类定义、颜色常量定义、根布局构建（渐变背景 + 毛玻璃层 + 内容层）、日志区域构建、ffmpeg 可用性检测
- 提供通用 UI 组件工厂函数: `_build_section_card`、`_build_action_button`、`_build_primary_button`
- **禁止**: 在此文件中编写具体 Tab 的 UI 构建代码或业务逻辑

### `snipkin/ui/` — UI 构建模块

- 每个文件提供一个 `build_xxx_tab(state)` 函数，只负责界面元素的创建和布局
- UI 交互逻辑（如开关切换、面板展开/收起动画）可以放在 UI 模块中
- 可定义模块内的辅助函数（如 `_make_styled_textfield`、`_build_compress_section`）
- **禁止**: 在 UI 模块中编写 ffmpeg 命令构建、文件校验等业务逻辑

### `snipkin/handlers/` — 事件处理模块

- 每个文件提供独立的事件处理函数，作为 UI 事件与 core 层之间的桥梁
- 负责: 从 `AppState` 收集参数、调用 core 层校验和构建命令、管理子线程执行、更新 UI 状态
- **禁止**: 在 Handler 模块中创建 UI 组件或直接编写 ffmpeg 命令构建逻辑

### `snipkin/core/` — 核心业务逻辑模块

- 每个文件提供纯函数，只接收普通 Python 类型参数（`str` / `float` / `bool` / `list`）
- 负责: 参数校验、ffmpeg 命令构建、命令执行（通过回调函数通知结果）
- **不依赖任何 UI 框架**（Flet / tkinter 等），可独立测试
- **禁止**: 在 core 模块中导入 `flet` 或访问任何 UI 控件

---

## 架构设计：函数式组合 + AppState

本项目采用 **函数式组合 + 集中状态管理** 模式组织代码，核心思路：

```python
# app.py 中定义集中状态容器
@dataclass
class AppState:
    """应用全局状态容器，替代原 Mixin 模式中通过 self 共享的状态变量。"""
    input_file_path: str = ""
    output_file_path: str = ""
    compress_enabled: bool = False
    log_text: ft.ListView | None = None
    page: ft.Page | None = None
    ...

# 各模块通过参数接收 state
def build_clip_tab(state: AppState) -> ft.Container: ...      # ui/
def handle_clip_run(state: AppState) -> None: ...              # handlers/
def build_clip_ffmpeg_command(...) -> list[str]: ...            # core/（不接收 state）
```

### 三层架构

```
┌─────────────────────────────────────────────────────┐
│  UI 层 (ui/)                                        │
│  纯界面构建，通过 state 绑定控件引用                    │
├─────────────────────────────────────────────────────┤
│  Handler 层 (handlers/)                              │
│  事件处理桥梁，从 state 收集参数 → 调用 core → 更新 UI  │
├─────────────────────────────────────────────────────┤
│  Core 层 (core/)                                     │
│  纯业务逻辑，不依赖任何 UI 框架，可独立测试             │
└─────────────────────────────────────────────────────┘
```

### 为什么选择函数式组合？

- **解耦彻底**: core 层完全不依赖 UI 框架，便于单元测试和未来框架迁移
- **状态集中**: 所有状态集中在 `AppState` 数据类中，避免散落在各处
- **依赖清晰**: 函数签名明确声明所需参数，不存在隐式的 `self.xxx` 依赖
- **易于扩展**: 新增功能只需添加对应的 UI 函数、Handler 函数和 Core 函数

### 数据流向

```
用户操作 → UI 层（事件绑定）→ Handler 层（收集参数 + 调用 core）→ Core 层（校验 + 构建命令 + 执行）
                                    ↓                                        ↓
                              更新 AppState                            通过回调通知结果
                                    ↓                                        ↓
                              刷新 UI 显示  ←────────────────────────── Handler 层接收回调
```

### AppState 编写规则

1. 所有应用状态字段在 `AppState` 数据类中声明，使用 `@dataclass` 装饰器
2. UI 控件引用字段类型标注为 `ft.XxxControl | None`，默认值为 `None`，运行时由 UI 构建函数绑定
3. 拼接 Tab 的状态字段统一使用 `concat_` 前缀
4. `page` 字段在 `build_app` 中初始化，供各层通过 `state.page.update()` 刷新 UI

---

## UI/UX 设计规范

### 核心视觉哲学

- **设计风格**: 现代极致简约 (Modern Minimalism) + 毛玻璃 (Glassmorphism)
- **设计参考**: iOS 17 / macOS Sonoma
- **关键特质**: 呼吸感（留白）、层级感（阴影与模糊）、直觉感（符合 Web 操作习惯）

### 配色方案

| 用途 | 色值 | 说明 |
|------|------|------|
| 背景渐变起始 | `"#1C1C1E"` | 深灰黑 |
| 背景渐变终止 | `"#000000"` | 纯黑 |
| 强调蓝 (Primary) | `"#007AFF"` | Apple 蓝，用于按钮、高亮、Tab 指示器 |
| 成功绿 | `"#34C759"` | 操作成功反馈 |
| 警告红 | `"#FF3B30"` | 错误提示 |
| 边框色 | `ft.Colors.with_opacity(0.1, ft.Colors.WHITE)` | 极细半透明白 |
| 文本主色 | `"#f0f0f0"` | 标题与正文 |
| 文本次色 | `"#8e8e93"` | 标签与提示 |

> **注意**: 项目中的颜色常量统一定义在 `snipkin/app.py` 顶部（如 `ACCENT_BLUE`、`TEXT_PRIMARY_COLOR` 等），
> UI 模块通过 `from snipkin.app import ACCENT_BLUE` 引用，**禁止**在 UI 文件中硬编码色值。

### 字体与图标

- **字体**: 优先使用系统默认字体。macOS 为 SF Pro，Windows 为 Segoe UI
- **图标库**: **绝对禁用 Emoji**，统一使用 `ft.CupertinoIcons`
- **图标示例**:

| 场景 | 图标 |
|------|------|
| 视频/影片 | `ft.CupertinoIcons.FILM` |
| 文件夹 | `ft.CupertinoIcons.FOLDER_OPEN` |
| 计时器 | `ft.CupertinoIcons.TIMER` |
| 压缩/归档 | `ft.CupertinoIcons.ARCHIVEBOX` |
| 下载/导出 | `ft.CupertinoIcons.TRAY_ARROW_DOWN` |
| 日志/文档 | `ft.CupertinoIcons.DOC_TEXT` |
| 播放 | `ft.CupertinoIcons.PLAY_ARROW_SOLID` |
| 设置 | `ft.CupertinoIcons.GEAR_ALT` |

### 组件规范

#### 毛玻璃容器 (Glass Container)

所有功能面板必须包裹在"玻璃容器"中，根布局使用 `ft.Stack` 实现三层叠加：

```python
# Layer 1: 渐变背景
ft.Container(
    gradient=ft.LinearGradient(
        begin=ft.Alignment(-1, -1),
        end=ft.Alignment(1, 1),
        colors=[BACKGROUND_GRADIENT_START, BACKGROUND_GRADIENT_END, "#0f3460"],
    ),
)

# Layer 2: 毛玻璃模糊层
ft.Container(
    bgcolor=ft.Colors.with_opacity(0.3, "#1e1e2e"),
    blur=ft.Blur(sigma_x=30, sigma_y=30),
)

# Layer 3: 内容层
ft.Container(content=..., padding=ft.padding.all(16))
```

功能卡片区域使用统一的 `_build_section_card` 工厂函数构建：

```python
ft.Container(
    bgcolor=ft.Colors.with_opacity(0.4, SURFACE_COLOR),
    border_radius=ft.border_radius.all(12),
    padding=ft.padding.all(16),
    border=ft.border.all(1, ft.Colors.with_opacity(0.1, "#ffffff")),
)
```

#### 交互按钮 (Interactive Buttons)

- **基础态**: 强调蓝背景 + 圆角 + 白色文字
- **悬停态 (Hover)**:
  - `scale: 1.02 ~ 1.05`
  - 添加蓝色 `BoxShadow` 外发光（`blur_radius=15 ~ 16`）
- **点击态 (Click)**:
  - `scale: 0.95`（模拟物理压感）
- **禁用态**: `disabled=True`，文字切换为"处理中..."

主操作按钮（开始截取/开始拼接）使用 `_build_glow_run_button` 构建，自带 Hover 光效和缩放动画。

#### 输入控件 (Input Fields)

- **风格**: 圆角半透明底色，默认边框为 `DIVIDER_COLOR`
- **交互**: 获得焦点时边框高亮为强调蓝 (`focused_border_color=ACCENT_BLUE`)
- **圆角**: `border_radius=10`
- **文本大小**: `size=13`

使用 `_make_styled_textfield` 和 `_make_styled_dropdown` 工厂函数确保风格统一。

#### 开关控件 (Switch)

- 使用 `ft.CupertinoSwitch`，激活轨道颜色为强调蓝
- 用于压缩功能的启用/禁用

### 布局与层级

#### 结构定义

```
┌─────────────────────────────────────────┐
│  Title Bar: 图标 + "Snipkin" + 副标题    │  ← 标题居左
├─────────────────────────────────────────┤
│  TabBar (Segmented Control 风格)         │  ← 视频截取 | 视频拼接
│  ┌─────────────────────────────────────┐│
│  │  TabBarView 内容区域                 ││  ← scroll=AUTO
│  │  ┌─────────────────────────────────┐││
│  │  │  Section Card: 输入文件          │││
│  │  ├─────────────────────────────────┤││
│  │  │  Section Card: 时间设置          │││
│  │  ├─────────────────────────────────┤││
│  │  │  Section Card: 压缩设置          │││
│  │  ├─────────────────────────────────┤││
│  │  │  Section Card: 输出设置          │││
│  │  ├─────────────────────────────────┤││
│  │  │  主操作按钮                      │││
│  │  └─────────────────────────────────┘││
│  └─────────────────────────────────────┘│
├─────────────────────────────────────────┤
│  Bottom Log: 执行日志                    │  ← 独立层级，背景更深
│  ┌─────────────────────────────────────┐│
│  │  ListView (auto_scroll=True)         ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

#### 间距规范

| 类型 | 数值 | 说明 |
|------|------|------|
| 根布局内边距 | `16px` | `ft.padding.all(16)` |
| 卡片内间距 | `16px` | `ft.padding.all(16)` |
| 卡片间距 | `10px` | `spacing=10` |
| 行内组件间距 | `8px` | `spacing=8` |
| 日志区上边距 | `8px` | `ft.padding.only(top=8)` |

### 动画与过渡

#### 全局动画参数

| 类型 | 曲线 | 时长 |
|------|------|------|
| 微交互（悬停缩放） | `ft.AnimationCurve.EASE_OUT` | `200ms` |
| 面板展开/收起 | `ft.AnimationCurve.EASE_IN_OUT` | `300ms` |
| 页面切换 | Flet Tabs 内置 | `300ms` |

#### 关键动效

- **高级选项展开**: 使用 `animate_size` + `animate_opacity` 配合 `height` 和 `opacity` 变化，实现平滑推开下方组件的效果。展开时箭头图标旋转 90°（`ft.Rotate(1.5708)`）
- **压缩选项展开**: 使用 `ft.CupertinoSwitch` 切换，展开/收起压缩选项面板。收起时同时收起内部的高级选项
- **执行按钮状态反馈**: 点击"开始"后，按钮文字切换为"处理中..."，图标切换为 `HOURGLASS`，按钮设为 `disabled`。执行完成后恢复原始状态

---

## 代码风格规范

### 基本规则

- **Python 版本**: 3.10+（使用 `str | None` 联合类型语法、`list[str]` 内置泛型）
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
import flet as ft

# 3. 项目内部模块
from snipkin.constants import VIDEO_FILE_TYPES
from snipkin.utils import check_ffmpeg_available
from snipkin.app import AppState, ACCENT_BLUE
```

### 类型注解

- 函数签名必须添加参数类型和返回值类型注解
- `AppState` 数据类字段通过 `@dataclass` 自动推断类型
- 使用 `str | None` 联合类型语法（Python 3.10+）
- 在存在循环导入风险时，使用 `from __future__ import annotations` + `TYPE_CHECKING` 守卫

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snipkin.app import AppState
```

---

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块文件 | 小写下划线 | `clip_handler.py` |
| 数据类 | 大驼峰 | `AppState` |
| 函数（公开） | 小写下划线 | `build_clip_tab`、`handle_clip_run` |
| 函数（私有） | 单下划线前缀 | `_build_section_card`、`_log` |
| 常量 | 全大写下划线 | `COMPRESS_QUALITY_PRESETS`、`ACCENT_BLUE` |
| AppState 字段 | 小写下划线 + 语义 | `compress_enabled`、`output_format` |
| 拼接 Tab 字段 | `concat_` 前缀 | `concat_resolution`、`concat_file_list` |
| UI 控件引用字段 | 模块前缀 + 控件类型 | `clip_input_path_field`、`concat_output_format_dropdown` |

### 函数命名约定

| 前缀/模式 | 用途 | 所在模块 |
|-----------|------|----------|
| `build_xxx_tab` | 构建 Tab 完整内容 | `ui/` |
| `_build_xxx` | 构建 UI 子组件 | `ui/` 或 `app.py` |
| `_make_styled_xxx` | 创建风格化控件 | `ui/` |
| `handle_xxx` / `on_xxx` | 事件处理回调 | `handlers/` |
| `build_xxx_ffmpeg_command` | 构建 ffmpeg 命令 | `core/` |
| `validate_xxx_params` | 参数校验 | `core/` |
| `execute_ffmpeg` | 执行 ffmpeg 命令 | `core/` |
| `_log` | 日志写入 | `handlers/` |

---

## 注释规范

### 模块级注释

每个 `.py` 文件顶部必须包含模块级 docstring，说明：
- 模块的用途和职责
- 包含的主要函数
- 设计说明（如有）

```python
"""
snipkin.handlers.clip_handler - 视频截取的事件处理层（Flet 版）

本模块提供视频截取功能的所有事件处理函数，包括：
- on_input_file_picked:  输入文件选择完成后的回调处理
- on_output_file_picked: 输出路径选择完成后的回调处理
- handle_clip_run:       "开始截取"按钮点击处理

设计说明：
  所有函数接收 AppState 实例和 UI 控件引用作为参数，
  核心的参数校验、ffmpeg 命令构建、命令执行逻辑由 snipkin.core.clip_core 提供。
"""
```

### 函数/方法注释

- 所有公开函数和复杂的私有函数必须包含 docstring
- 使用中文编写，说明功能、参数、返回值
- 复杂逻辑需补充"工作原理"或"策略说明"

```python
def build_clip_ffmpeg_command(
    input_path: str,
    output_path: str,
    start_seconds: float,
    duration_seconds: float,
    ...
) -> list[str]:
    """
    构建视频截取的 ffmpeg 命令。

    根据压缩设置和输出格式，决定使用以下策略之一：
      - 需要转码的格式（如 GIF）：强制使用转码
      - 启用压缩：使用 libx264 编码 + CRF 质量控制 + 可选滤镜
      - 不压缩：使用流复制（-c copy），速度最快，无质量损失

    参数:
        input_path:       输入视频文件路径
        output_path:      输出文件路径
        start_seconds:    截取开始时间（秒）
        duration_seconds: 截取持续时长（秒）
        ...

    返回:
        完整的 ffmpeg 命令参数列表
    """
```

### 行内注释

- 仅在逻辑不直观时添加，解释"为什么"而非"做了什么"
- 注释放在代码行上方，不使用行尾注释
- 使用 `# ====` 分隔符划分代码区域（如颜色常量区、状态区、UI 构建区）

---

## 新增功能指南

### 场景一：新增一个下拉选项（如新的分辨率）

1. 在 `snipkin/constants.py` 对应的字典中添加一行即可
2. UI 会自动读取字典的 keys 作为下拉菜单选项，无需修改 UI 代码

### 场景二：新增一个 Tab 页面

1. 在 `snipkin/core/` 下创建核心逻辑文件（如 `convert_core.py`），定义参数校验、命令构建、执行函数
2. 在 `snipkin/handlers/` 下创建事件处理文件（如 `convert_handler.py`），桥接 UI 事件与 core 层
3. 在 `snipkin/ui/` 下创建 UI 构建文件（如 `convert_tab.py`），提供 `build_convert_tab(state)` 函数
4. 在 `snipkin/app.py` 中：
   - 在 `AppState` 数据类中添加新 Tab 的状态字段
   - 在 `_build_content` 中添加新 Tab 到 `ft.Tabs`
5. 更新各子包的 `__init__.py` 导出

### 场景三：新增一个工具函数

1. 如果是通用工具函数（不依赖 UI），添加到 `snipkin/utils.py`
2. 如果是某个功能专用的辅助方法，放在对应的 `core/` 模块中

---

## 常量管理规范

- 所有 UI 选项、文件类型、编码参数等**必须定义在 `constants.py`** 中
- 颜色常量定义在 `app.py` 顶部，UI 模块通过导入引用
- **禁止**在 UI 或 Handler 代码中硬编码魔法数字或字符串
- 常量字典的 key 是用户可见的显示文本，value 是传给 ffmpeg 的实际参数值
- 新增常量时必须添加中文注释说明用途

---

## 线程安全规范

- **UI 操作只能在主线程中执行**（Flet 的限制）
- ffmpeg 命令在子线程中通过 `threading.Thread(daemon=True)` 执行
- 子线程中更新 UI（写入日志、恢复按钮状态等）通过 `state.page.update()` 调度
- core 层的 `execute_ffmpeg` 通过回调函数（`on_log` / `on_success` / `on_error` / `on_complete`）将结果传递给 handler 层，由 handler 层负责 UI 更新

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
refactor: 从 Mixin 模式迁移为函数式组合 + AppState 架构
fix: 修复拼接模式下过渡时长为 0 时的崩溃问题
```

---

## Flet API 使用规范

> **重要**: 本项目使用 Flet `>=0.25.0`（当前安装版本为 0.25.x / 0.8x 系列）。
> Flet 版本间 API 变动较大，**严禁**使用网上搜索到的旧版或新版 API，必须以本章节为准。
> 新增 Flet 功能前，必须先在本地 Python 环境中验证 API 可用性。

### 剪贴板操作

```python
# ✅ 正确：通过属性赋值写入剪贴板
page.clipboard = "要复制的文本"
page.update()

# ❌ 错误：set_clipboard 方法不存在
page.set_clipboard("文本")
```

### SnackBar 通知

```python
# ✅ 正确：通过 overlay 添加 SnackBar
snackbar = ft.SnackBar(
    content=ft.Text("消息内容", color="#ffffff"),
    bgcolor="#34C759",
    duration=3000,
    open=True,
)
page.overlay.append(snackbar)
page.update()

# ❌ 错误：page.open() 方法不存在
page.open(ft.SnackBar(...))
```

### AlertDialog 对话框

```python
# ✅ 正确：通过 overlay 添加 Dialog
dialog = ft.AlertDialog(
    title=ft.Text("标题"),
    content=ft.Text("内容"),
    open=True,
)
def close_dialog(_event):
    dialog.open = False
    page.update()
dialog.actions = [ft.TextButton("确定", on_click=close_dialog)]
page.overlay.append(dialog)
page.update()

# ❌ 错误：page.open() / page.close() 方法不存在
page.open(ft.AlertDialog(...))
page.close(dialog)
```

### Tab 标签页

```python
# ✅ 正确：使用 label + icon 属性
ft.Tab(label="视频截取", icon=ft.CupertinoIcons.SCISSORS)

# ❌ 错误：tab_content 参数不存在
ft.Tab(tab_content=ft.Row(...))

# ❌ 错误：禁止使用 Emoji
ft.Tab(label="✂️ 视频截取")
```

### GestureDetector 拖拽事件

```python
# ✅ 正确：使用 local_delta 对象访问增量
def on_drag_update(event: ft.DragUpdateEvent):
    delta_y = event.local_delta.y
    delta_x = event.local_delta.x

# ❌ 错误：delta_y 不是顶层属性
event.delta_y
event.delta_x
```

### GestureDetector 鼠标光标

```python
# ✅ 正确：mouse_cursor 设置在 GestureDetector 上
ft.GestureDetector(
    mouse_cursor=ft.MouseCursor.RESIZE_ROW,
    on_vertical_drag_update=on_drag,
    content=ft.Container(...),
)

# ❌ 错误：Container 不支持 cursor 参数
ft.Container(cursor=ft.MouseCursor.RESIZE_ROW)
```

### 控件属性速查表

| 操作 | 正确用法 | 错误用法 |
|------|----------|----------|
| 写入剪贴板 | `page.clipboard = text` | `page.set_clipboard(text)` |
| 显示 SnackBar | `page.overlay.append(sb)` + `sb.open = True` | `page.open(sb)` |
| 显示 Dialog | `page.overlay.append(dlg)` + `dlg.open = True` | `page.open(dlg)` |
| 关闭 Dialog | `dlg.open = False` + `page.update()` | `page.close(dlg)` |
| Tab 自定义图标 | `ft.Tab(label=..., icon=...)` | `ft.Tab(tab_content=...)` |
| 拖拽增量 | `event.local_delta.y` | `event.delta_y` |
| 鼠标光标 | `GestureDetector(mouse_cursor=...)` | `Container(cursor=...)` |

### 开发前验证

当不确定某个 Flet API 是否可用时，在项目虚拟环境中执行以下命令验证：

```bash
.venv/bin/python3 -c "import flet as ft; print(dir(ft.Page))" | tr ',' '\n' | grep "关键词"
```

---

## 依赖管理

- **运行时依赖**: 记录在 `requirements.txt` 中（当前仅 `flet>=0.25.0`）
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
