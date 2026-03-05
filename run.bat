@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================
:: Snipkin 一键启动脚本（Windows）
:: 用法: 双击 run.bat 或在命令行中运行
::
:: 功能:
::   1. 检测 Windows 版本
::   2. 检测并安装 Python >= 3.10（通过 winget）
::   3. 检测并安装 ffmpeg（通过 winget）
::   4. 创建虚拟环境并安装 pip 依赖
::   5. 启动 Snipkin
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIRED_MAJOR=3"
set "REQUIRED_MINOR=10"

echo.
echo ╔══════════════════════════════════════╗
echo ║       Snipkin 一键启动脚本          ║
echo ╚══════════════════════════════════════╝
echo.

:: ============================================================
:: Step 1: 检测 Python
:: ============================================================
call :find_python
if defined PYTHON_BIN (
    echo [OK] 找到 Python: !PYTHON_BIN!
    goto :check_ffmpeg
)

echo [!!] 未找到 Python ^>= %REQUIRED_MAJOR%.%REQUIRED_MINOR%，正在安装...

:: 检查 winget 是否可用
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] 未找到 winget 包管理器。
    echo     请从 Microsoft Store 安装 "应用安装程序"，或手动安装 Python:
    echo     https://www.python.org/downloads/
    echo.
    echo     安装完成后请重新运行此脚本。
    pause
    exit /b 1
)

echo [..] 正在通过 winget 安装 Python 3.13...
winget install Python.Python.3.13 --accept-source-agreements --accept-package-agreements --silent
if %errorlevel% neq 0 (
    echo [XX] Python 安装失败，请手动安装: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 刷新 PATH（winget 安装后 PATH 可能未立即生效）
call :refresh_path

:: 再次查找 Python
call :find_python
if not defined PYTHON_BIN (
    echo [XX] Python 安装后仍无法找到，请重启终端后再试。
    pause
    exit /b 1
)
echo [OK] Python 安装完成: !PYTHON_BIN!

:: ============================================================
:: Step 2: 检测 ffmpeg
:: ============================================================
:check_ffmpeg
echo [..] 检测 ffmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ffmpeg 已安装
    goto :setup_venv
)

echo [!!] 未找到 ffmpeg，正在安装...

where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo [XX] 未找到 winget，无法自动安装 ffmpeg。
    echo     请手动安装 ffmpeg: https://ffmpeg.org/download.html
    echo     并确保 ffmpeg 已添加到系统 PATH 中。
    pause
    exit /b 1
)

winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements --silent
if %errorlevel% neq 0 (
    echo [!!] winget 安装 ffmpeg 失败，尝试备选源...
    winget install FFmpeg.FFmpeg --accept-source-agreements --accept-package-agreements --silent
    if %errorlevel% neq 0 (
        echo [XX] ffmpeg 安装失败，请手动安装: https://ffmpeg.org/download.html
        pause
        exit /b 1
    )
)

call :refresh_path

where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] ffmpeg 安装完成但未在 PATH 中找到，请重启终端后再试。
    pause
    exit /b 1
)
echo [OK] ffmpeg 安装完成

:: ============================================================
:: Step 3: 创建虚拟环境
:: ============================================================
:setup_venv
if exist "%VENV_PYTHON%" (
    echo [OK] 虚拟环境已存在
    goto :install_deps
)

echo [..] 正在创建虚拟环境...
"!PYTHON_BIN!" -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo [XX] 虚拟环境创建失败，请检查 Python 安装。
    pause
    exit /b 1
)
echo [OK] 虚拟环境创建完成

:: ============================================================
:: Step 4: 安装依赖
:: ============================================================
:install_deps
echo [..] 检查依赖...
"%VENV_PYTHON%" -m pip install --upgrade pip -q 2>nul

if exist "%SCRIPT_DIR%requirements.txt" (
    "%VENV_PYTHON%" -m pip install -r "%SCRIPT_DIR%requirements.txt" -q
    echo [OK] 依赖安装完成
) else (
    echo [!!] 未找到 requirements.txt，跳过依赖安装。
)

:: ============================================================
:: Step 5: 启动应用
:: ============================================================
echo.
echo [OK] 环境就绪，正在启动 Snipkin...
echo.
"%VENV_PYTHON%" "%SCRIPT_DIR%main.py" %*
if %errorlevel% neq 0 (
    echo.
    echo [XX] Snipkin 运行出错，请检查上方错误信息。
    pause
    exit /b 1
)
goto :eof

:: ============================================================
:: 工具函数
:: ============================================================

:find_python
:: 按优先级查找满足版本要求的 Python
set "PYTHON_BIN="
for %%P in (python3 python py) do (
    where %%P >nul 2>&1
    if !errorlevel! equ 0 (
        call :check_python_version "%%P"
        if defined PYTHON_BIN goto :eof
    )
)

:: Windows 上 py launcher 支持指定版本
where py >nul 2>&1
if %errorlevel% equ 0 (
    for %%V in (3.13 3.12 3.11 3.10) do (
        py -%%V --version >nul 2>&1
        if !errorlevel! equ 0 (
            call :check_py_launcher_version "%%V"
            if defined PYTHON_BIN goto :eof
        )
    )
)

:: 检查常见安装路径
for %%V in (313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "CANDIDATE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        call :check_python_version "!CANDIDATE!"
        if defined PYTHON_BIN goto :eof
    )
)
goto :eof

:check_python_version
:: 检查指定 Python 是否满足版本要求
set "CANDIDATE_BIN=%~1"
for /f "tokens=2 delims= " %%A in ('"%CANDIDATE_BIN%" --version 2^>^&1') do (
    for /f "tokens=1,2 delims=." %%M in ("%%A") do (
        set "PY_MAJOR=%%M"
        set "PY_MINOR=%%N"
    )
)
if not defined PY_MAJOR goto :eof
if !PY_MAJOR! gtr %REQUIRED_MAJOR% (
    set "PYTHON_BIN=%CANDIDATE_BIN%"
    goto :eof
)
if !PY_MAJOR! equ %REQUIRED_MAJOR% (
    if !PY_MINOR! geq %REQUIRED_MINOR% (
        set "PYTHON_BIN=%CANDIDATE_BIN%"
    )
)
goto :eof

:check_py_launcher_version
:: 使用 py launcher 的指定版本
set "PY_VER=%~1"
set "PYTHON_BIN=py -%PY_VER%"
goto :eof

:refresh_path
:: 从注册表重新读取系统和用户 PATH，使新安装的程序立即可用
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%B"
if defined SYS_PATH if defined USR_PATH (
    set "PATH=!SYS_PATH!;!USR_PATH!"
)
goto :eof
