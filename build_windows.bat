@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo =========================================
echo   🚀 开始构建 Snipkin for Windows...
echo =========================================

:: 1. 设置虚拟环境并使用其中的 Python
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

:: 检查虚拟环境是否存在
if not exist "%VENV_PYTHON%" (
    echo [错误] 虚拟环境不存在：%VENV_PYTHON%
    echo 请先运行 run.bat 创建虚拟环境并安装依赖
    pause
    exit /b 1
)

echo [信息] 使用虚拟环境：%VENV_PYTHON%

:: 检查并安装必要的依赖
echo [信息] 检查并安装必要的依赖...
"%VENV_PYTHON%" -c "import flet; import flet_desktop; import PyInstaller" 2>nul
if errorlevel neq 0 (
    echo [警告] 虚拟环境中缺少必要的依赖，正在安装...
    "%VENV_PYTHON%" -m pip install --upgrade pip -q
    "%VENV_PYTHON%" -m pip install -r requirements.txt -q
    "%VENV_PYTHON%" -m pip install -r requirements-build.txt -q
)

:: 2. 检查系统中存在的 ffmpeg 和 ffprobe 用于后续绑定提取
where ffmpeg >nul 2>&1
if !errorlevel! neq 0 (
    echo [错误] 系统中未安装或找不到 ffmpeg.exe，无法将其打包为内置依赖。
    echo 请先将带有 ffmpeg.exe 的文件夹加入系统的环境变量 PATH
    pause
    exit /b 1
)

:: 获取它们的完整路径
for /f "delims=" %%i in ('where ffmpeg') do (
    set "FFMPEG_PATH=%%i"
    goto :found_ffmpeg
)
:found_ffmpeg

for /f "delims=" %%i in ('where ffprobe') do (
    set "FFPROBE_PATH=%%i"
    goto :found_ffprobe
)
:found_ffprobe

echo [OK] 检测到 ffmpeg 位于：%FFMPEG_PATH%
echo [OK] 检测到 ffprobe 位于：%FFPROBE_PATH%

:: 3. 清理旧的构建遗留文件
echo [信息] 清理此前构建遗留文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist Snipkin.spec del /q Snipkin.spec

:: 4. 组装并执行 PyInstaller 打包语句 (打包为单文件版本需要添加 --onefile 选项)
echo [信息] 📦 正在执行 PyInstaller 封装主程序并捆绑音视频组件...

:: 参数说明：
:: --noconfirm:         静默覆盖输出
:: --noconsole:         等同 --windowed 生成 GUI 程序，不附带后台 cmd 黑窗口
:: --onefile:           将全部环境压缩生成一个独立的 .exe，便于用户拷贝分享
:: --name:              指定输出名称
:: --icon:              指定带有透明属性的定制图标
:: --add-binary:        将依赖的 .exe 文件捆绑进去。格式: SRC;DEST

"%VENV_PYTHON%" -m PyInstaller --noconfirm --noconsole --onefile ^
    --name "Snipkin" ^
    --icon "assets/icon.ico" ^
    --add-data "assets;assets" ^
    --add-binary "%FFMPEG_PATH%;." ^
    --add-binary "%FFPROBE_PATH%;." ^
    --hidden-import "flet" ^
    --hidden-import "flet.core" ^
    --hidden-import "flet.core.controls" ^
    --hidden-import "flet.core.cupertino_icons" ^
    --hidden-import "flet_runtime" ^
    --hidden-import "flet_desktop" ^
    --hidden-import "PIL._tkinter_finder" ^
    --collect-all "flet" ^
    --collect-all "flet_runtime" ^
    --collect-all "flet_desktop" ^
    main.py

echo =========================================
echo 🎉 Windows exe 单文件生成完毕！
echo 你可以在该目录下的 dist 文件夹内找到 Snipkin.exe
echo =========================================

pause
endlocal
