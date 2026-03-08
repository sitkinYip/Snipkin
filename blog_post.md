# 关于我开发了一个视频处理工具这件事

> **写在前面**：这是一个关于技术、需求和成长的故事。如果你也曾有过"为什么没有这样的工具"的疑问，或许能在这里找到共鸣。

---

## 一、故事的开始：为什么会有 Snipkin？

一开始 我需要在公司的电脑上切视频 把一些功能录屏 切割 拼接然后发给测试验证 但公司的拦截软件非常的愚蠢 不仅仅剪映之类的不给用 PR又不能用盗版 

连Shotcut/OpenShot之类的都会触发安全拦截，只有imove是可以用的，但作为一个专业不相关的人，imove功能真的太多了看的我头疼，也用不明白，在一堆密密麻麻的内容里把视频切好后在哪里导出都找不到，气得我骂骂咧咧，当然我也没有一怒之下就怒了一下，毕竟我是开发岗，所有开发环境相关的东西倒是不会拦截，于是我安装了FFmpeg，并且用python写了个简单的GUI，快速的完成了我的需求（我实在记不住也搞不清楚一堆FFmpeg 命令行，每次去查询一下，然后又忘了 所以干脆变成gui点两下即可）

那事已至此我又想到：

在这个短视频泛滥的时代，我们几乎每天都在和视频打交道：

- 从网上下载了一段教程视频，但只需要其中 5 分钟的精华部分
- 旅行时拍了很多零散的视频片段，想把它们拼接成一个完整的回忆
- 看到某个视频中有一段特别棒的背景音乐，想要提取出来作为手机铃声

市面上的视频编辑软件确实不少，但它们往往过于庞大复杂——为了截取一段 10 秒的视频，我需要打开一个几百 MB 的软件，等待漫长的加载，然后在一堆我用不到的功能中找到那个"导出"按钮。

**我就想：能不能有一个轻量、简洁、专注的工具，只做好几件最基础的事情？**

于是，**Snipkin** 诞生了。

---

## 二、Snipkin 是什么？

用一句话概括：**Snipkin 是一款基于 Python 与 FFmpeg 的轻量级桌面视频处理工具**。

它的核心功能非常聚焦：

### ✂️ 1. 视频截取
- 支持帧级时间轴切割
- 可以通过时间区间或持续时长提取视频片段
- 智能命名，自动附加时间戳防止覆盖

### 🔗 2. 视频拼接
- 多段视频无缝连接
- 内置 16 种过渡动画效果（淡入淡出、滑动等）
- 画面自然流畅，无需专业剪辑技能

### 🎵 3. 音频提取
- 从视频中提取高品质音频
- 支持 MP3、AAC、FLAC、WAV、M4A、OGG 六种格式
- 可选音质等级（高/中/低）

### 🗜️ 4. 智能压缩
- 一键式质量预设（高/中/低）
- 支持自定义分辨率、帧率及音频码率
- 统一输出文件规格

听起来很简单？是的，这就是我想要做到的——**把复杂的技术隐藏在简洁的界面之下**。

---

## 三、技术选型：为什么是这些技术栈？

### 🐍 Python：快速开发的利器

选择 Python 作为主要开发语言，主要是看中了它：

- **丰富的生态**：有现成的 FFmpeg 绑定库
- **跨平台特性**：一套代码可以在 macOS、Windows、Linux 上运行
- **开发效率高**：可以快速迭代和验证想法

### 🎨 Flet：现代化 UI 的新选择

在 UI 框架的选择上，我尝试过 CustomTkinter，但最终选择了 **Flet**（基于 Flutter 的 Python GUI 框架）。原因很简单：

1. **颜值即正义**：Flet 基于 Flutter，可以轻松实现现代化的毛玻璃效果、渐变背景、平滑动画
2. **跨平台一致**：同一套 UI 代码在所有平台上表现一致
3. **声明式编程**：代码结构清晰，易于维护

下面是 UI 设计的核心代码片段：

```python
# 根布局：三层叠加实现毛玻璃效果
def _build_root_layout(state: AppState) -> ft.Stack:
    # Layer 1: 渐变背景
    gradient_background = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=[BACKGROUND_GRADIENT_START, BACKGROUND_GRADIENT_END, "#0f3460"],
        ),
    )
    
    # Layer 2: 毛玻璃模糊层
    blur_overlay = ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.3, "#1e1e2e"),
        blur=ft.Blur(sigma_x=30, sigma_y=30),
    )
    
    # Layer 3: 内容层
    content_layer = ft.Container(
        expand=True,
        padding=ft.padding.all(16),
        content=_build_content(state),
    )
    
    return ft.Stack(
        controls=[gradient_background, blur_overlay, content_layer],
        expand=True,
    )
```

### ⚙️ FFmpeg：强大的底层引擎

FFmpeg 是视频处理领域的"瑞士军刀"，几乎所有视频处理软件都在用它。Snipkin 通过 subprocess 调用本地 ffmpeg 命令行，实现了：

- **高性能**：直接调用系统级工具，处理速度快
- **功能强大**：支持几乎所有主流视频格式和编码
- **稳定可靠**：经过多年验证的成熟工具

### 📦 PyInstaller：一键打包分发

为了让用户无需安装 Python 环境就能使用，我使用 PyInstaller 将应用打包为独立的可执行文件：

- **macOS**: 生成 `.dmg` 安装包
- **Windows**: 生成单文件 `.exe`
- **Linux**: 生成可执行二进制文件

打包脚本会自动从系统中寻找 `ffmpeg` 并将其嵌入最终的应用包中，确保用户开箱即用。

---

## 四、架构设计：如何组织代码？

在开发过程中，我特别注重代码的可维护性和可扩展性。Snipkin 采用了**三层架构 + 函数式组合**的设计模式：

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

### 核心设计理念

1. **状态集中管理**：所有应用状态集中在 `AppState` 数据类中，避免状态散落在各处

```python
@dataclass
class AppState:
    """应用全局状态容器"""
    # 截取 Tab 状态
    input_file_path: str = ""
    output_file_path: str = ""
    start_time: str = "0:00:00"
    compress_enabled: bool = False
    
    # 拼接 Tab 状态
    concat_file_list: list[str] = field(default_factory=list)
    concat_transition: str = "无过渡"
    
    # UI 控件引用
    log_text: ft.ListView | None = None
    page: ft.Page | None = None
```

2. **函数式组合**：每个功能模块都是纯函数，接收明确的参数，返回确定的结果

```python
# UI 构建函数
def build_clip_tab(state: AppState) -> ft.Container: ...

# 事件处理函数
def handle_clip_run(state: AppState) -> None: ...

# 核心业务逻辑（完全不依赖 UI 框架）
def build_clip_ffmpeg_command(...) -> list[str]: ...
```

3. **Core 层完全解耦**：核心业务逻辑不依赖任何 UI 框架，可以独立测试，甚至未来可以轻松迁移到其他 UI 框架

这种架构带来的好处是：

- ✅ **代码清晰**：每个模块职责明确，依赖关系简单
- ✅ **易于测试**：Core 层可以独立进行单元测试
- ✅ **便于扩展**：新增功能只需添加对应的三个模块
- ✅ **利于维护**：修改 UI 不影响业务逻辑，反之亦然

---

## 五、UI/UX 设计：如何做到既好看又好用？

在设计 Snipkin 的界面时，我参考了 iOS 17 和 macOS Sonoma 的设计风格，追求**现代简约 + 毛玻璃效果**。

### 设计原则

1. **留白的艺术**：给每个元素足够的呼吸空间
2. **层级的呈现**：通过阴影、模糊、颜色深浅来区分不同层级
3. **直觉的操作**：符合用户已有的操作习惯，不需要学习成本

### 配色方案

| 用途 | 色值 | 说明 |
|------|------|------|
| 背景渐变起始 | `#1C1C1E` | 深灰黑 |
| 背景渐变终止 | `#000000` | 纯黑 |
| 强调蓝 | `#007AFF` | Apple 蓝，用于主按钮 |
| 成功绿 | `#34C759` | 操作成功反馈 |
| 错误红 | `#FF3B30` | 错误提示 |

### 交互细节

- **按钮悬停**：轻微放大（scale: 1.02）+ 蓝色外发光
- **按钮点击**：轻微缩小（scale: 0.95），模拟物理压感
- **面板展开**：平滑的展开动画，箭头旋转 90°
- **日志输出**：实时滚动显示，支持折叠/展开和拖拽调整高度

### 图标选择

**绝对禁用 Emoji**，全部使用 `ft.CupertinoIcons` 图标库，确保在不同平台上显示一致：

- 视频截取：`ft.CupertinoIcons.SCISSORS`（剪刀）
- 音频提取：`ft.CupertinoIcons.MUSIC_NOTE_2`（音符）
- 视频拼接：`ft.CupertinoIcons.LINK`（链接）
- 执行日志：`ft.CupertinoIcons.DOC_TEXT`（文档）

---

## 六、遇到的挑战与解决方案

### 挑战 1：FFmpeg 命令参数的复杂性

FFmpeg 的命令参数极其丰富，不同的功能需要不同的参数组合。比如视频截取就有两种策略：

- **流复制模式**（`-c copy`）：不重新编码，速度快，无质量损失，但精度有限
- **转码模式**：重新编码，速度较慢，但可以精确到帧级，还能同时压缩

**解决方案**：在 Core 层封装多个命令构建函数，根据用户设置自动选择最优策略。

```python
def build_clip_ffmpeg_command(
    input_path: str,
    output_path: str,
    start_seconds: float,
    duration_seconds: float,
    compress_enabled: bool,
    output_format: str,
) -> list[str]:
    """根据压缩设置选择最优策略"""
    if compress_enabled or output_format == "gif":
        # 使用转码模式
        return build_transcode_command(...)
    else:
        # 使用流复制模式
        return build_copy_command(...)
```

### 挑战 2：跨平台的兼容性

不同操作系统对路径的处理方式不同，FFmpeg 的可执行文件位置也不同。

**解决方案**：

1. 使用 `os.path` 模块处理所有路径，自动适配不同平台
2. 提供多种 FFmpeg 查找策略：
   - 优先使用应用内置的 FFmpeg（打包版本）
   - 其次查找系统 PATH 中的 ffmpeg
   - 允许用户手动指定路径

### 挑战 3：子线程执行与 UI 更新的协调

FFmpeg 命令执行耗时较长，必须在子线程中运行，但 Flet 要求 UI 操作只能在主线程执行。

**解决方案**：通过回调函数机制，子线程执行完成后通过 `state.page.update()` 调度 UI 更新。

```python
def execute_ffmpeg(command: list[str], on_complete: callable):
    """在子线程中执行 ffmpeg 命令"""
    def run():
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # 执行完成后回调
            on_complete(success=True, message="处理完成")
        except Exception as e:
            on_complete(success=False, message=str(e))
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
```

### 挑战 4：Flet API 的版本兼容性

Flet 是一个快速发展的框架，API 变动较大。网上搜索到的很多示例代码都已经过时。

**解决方案**：

1. 在项目中锁定 Flet 版本（`>=0.25.0`）
2. 在开发文档中记录已验证可用的 API 用法
3. 新增 Flet 功能前，先在本地环境中验证 API 可用性

---

## 七、版本演进：从 1.0 到 2.1

Snipkin 的成长历程：

### v1.0 - 初版发布
- 基础视频截取功能
- 简单的命令行界面

### v1.5 - GUI 化
- 迁移到 CustomTkinter GUI
- 添加视频拼接功能
- 支持过渡效果

### v2.0 - 架构重构
- 迁移到 Flet 框架
- 采用三层架构 + AppState 模式
- UI/UX 全面升级

### v2.1 - 功能完善
- 新增音频提取功能
- 支持 6 种音频格式
- 优化日志输出体验

---

## 八、使用场景：谁需要 Snipkin？

Snipkin 适合以下人群：

### 📹 内容创作者
- 快速截取视频素材
- 拼接多个拍摄片段
- 提取视频中的背景音乐

### 👨‍🏫 教育工作者
- 从长视频课程中提取关键片段
- 制作精简版教学视频

### 🎬 视频爱好者
- 制作个人视频集锦
- 为视频添加过渡效果
- 提取电影中的经典配乐

### 💼 办公人员
- 压缩视频文件大小以便邮件发送
- 统一多个视频的格式和分辨率

---

## 九、快速上手：如何使用 Snipkin？

### 方案一：直接下载应用（推荐）

前往 [GitHub Releases](https://github.com/sitkinYip/Snipkin/releases) 下载预编译版本：

- **macOS**: 下载 `Snipkin.dmg`，拖入 Applications 文件夹
- **Windows**: 下载 `Snipkin.exe`，双击即可运行

### 方案二：源码运行

```bash
# 1. 克隆项目
git clone https://github.com/sitkinYip/Snipkin.git
cd Snipkin

# 2. 启动应用
# Windows 用户直接双击运行 run.bat
# macOS/Linux 用户执行 ./run.sh
```

### 使用示例：截取视频片段

1. 点击 **选择文件** 载入源视频
2. 设置 **开始时间** 与 **结束时间**（或只写**持续时长**）
3. （可选）勾选 **视频压缩**，按需调整质量
4. 点击 **开始截取**，搞定！

### 使用示例：提取音频

1. 切换到 **音频提取** Tab，选择视频文件
2. 选择输出格式（如 MP3）
3. 选择音质等级（推荐 320k 高品质）
4. 点击 **开始提取**，坐等完成

---

## 十、未来规划：Snipkin 还会变得更好

目前 Snipkin 还在持续开发中，未来的计划包括：

### 🎯 短期目标（v2.2-v2.5）
- [ ] 批量处理：一次性处理多个视频文件
- [ ] 预设模板：保存常用的参数组合
- [ ] 进度条显示：实时显示处理进度百分比
- [ ] 快捷键支持：提升操作效率

### 🚀 中期目标（v3.0）
- [ ] 视频转码功能：支持更多格式转换
- [ ] 滤镜系统：添加常见的视频滤镜（黑白、复古等）
- [ ] 字幕处理：支持硬编码字幕和软字幕提取
- [ ] 多语言界面：英文、日文等

### 🌟 长期愿景
- [ ] 插件系统：允许开发者扩展新功能
- [ ] 云端协作：支持多人在线编辑同一个项目
- [ ] AI 辅助：智能识别视频精彩片段，自动推荐截取点

---

## 十一、参与贡献：让 Snipkin 变得更好

如果你在使用中发现 Bug，或者有更好的功能建议，欢迎通过以下方式参与：

### 🐛 提交 Issue
在 [GitHub Issues](https://github.com/sitkinYip/Snipkin/issues) 中详细描述问题

### 🔧 提交 PR
1. Fork 本项目
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'feat: 新增超棒的功能'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 创建 Pull Request

### 📝 开发资源
- 详细开发规范请查看 [DEVELOPMENT.md](https://github.com/sitkinYip/Snipkin/blob/main/DEVELOPMENT.md)
- 项目使用 MIT 许可证，完全开源免费

---

## 十二、写在最后

开发 Snipkin 的过程，也是我重新思考"工具"本质的过程。

**好的工具应该是什么样的？**

我认为，它应该像一把趁手的瑞士军刀——平时感觉不到它的存在，需要时伸手就能拿到，用起来顺手又高效。它不应该喧宾夺主，不应该让用户为了完成一个简单的任务而去学习复杂的操作。

Snipkin 还远不完美，但它正在朝着这个方向努力。

如果你也喜欢这个理念，或者在使用过程中有任何想法，欢迎和我交流。毕竟，**开源的魅力就在于，一个人的灵感可以变成一群人的创造**。

---

## 附录：技术栈总览

| 组件 | 技术 | 版本 |
|------|------|------|
| 编程语言 | Python | 3.10+ |
| UI 框架 | Flet | >=0.25.0 |
| 视频引擎 | FFmpeg | 最新稳定版 |
| 打包工具 | PyInstaller | 最新稳定版 |
| 支持平台 | macOS / Windows / Linux | 全平台 |

### 项目地址
- **GitHub**: https://github.com/sitkinYip/Snipkin
- **Releases**: https://github.com/sitkinYip/Snipkin/releases

### 联系方式
- **邮箱**: sitkinyipmail@gmail.com
- **Issue**: https://github.com/sitkinYip/Snipkin/issues

---

<div align="center">

**感谢阅读！如果觉得有用，欢迎 Star 支持 ⭐**

_「定格时光的切片，编织光影的诗篇」_

</div>
