@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo =========================================
echo   🚀 开始构建 Snipkin for Windows...
echo =========================================

:: 1. 检查必要环境
where pyinstaller >nul 2>&1
if !errorlevel! neq 0 (
    echo [警告] 未检测到 PyInstaller，正在使用 pip 安装构建依赖...
    pip install -r requirements-build.txt
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

pyinstaller --noconfirm --noconsole --onefile ^
    --name "Snipkin" ^
    --icon "assets/icon.png" ^
    --add-binary "%FFMPEG_PATH%;." ^
    --add-binary "%FFPROBE_PATH%;." ^
    --hidden-import "PIL._tkinter_finder" ^
    main.py

echo =========================================
echo 🎉 Windows exe 单文件生成完毕！
echo 你可以在该目录下的 dist 文件夹内找到 Snipkin.exe
echo =========================================

pause
endlocal
