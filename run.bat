@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================
:: Snipkin ???????Windows?
:: ??: ?? run.bat ????????
::
:: ??:
::   1. ?? Windows ??
::   2. ????? Python >= 3.10??? winget?
::   3. ????? ffmpeg??? winget?
::   4. ????????? pip ??
::   5. ?? Snipkin
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIRED_MAJOR=3"
set "REQUIRED_MINOR=10"

echo.
echo ????????????????????????????????????????
echo ?       Snipkin ??????          ?
echo ????????????????????????????????????????
echo.

:: ============================================================
:: Step 1: ?? Python
:: ============================================================
call :find_python
if defined PYTHON_BIN (
    echo [OK] ?? Python: !PYTHON_BIN!
    goto :check_ffmpeg
)

echo [!!] ??? Python ^>= %REQUIRED_MAJOR%.%REQUIRED_MINOR%?????...

:: ?? winget ????
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] ??? winget ?????
    echo     ?? Microsoft Store ?? "??????"?????? Python:
    echo     https://www.python.org/downloads/
    echo.
    echo     ??????????????
    pause
    exit /b 1
)

echo [..] ???? winget ?? Python 3.13...
winget install Python.Python.3.13 --accept-source-agreements --accept-package-agreements --silent
if %errorlevel% neq 0 (
    echo [XX] Python ??????????: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ?? PATH?winget ??? PATH ????????
call :refresh_path

:: ???? Python
call :find_python
if not defined PYTHON_BIN (
    echo [XX] Python ??????????????????
    pause
    exit /b 1
)
echo [OK] Python ????: !PYTHON_BIN!

:: ============================================================
:: Step 2: ?? ffmpeg
:: ============================================================
:check_ffmpeg
echo [..] ?? ffmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ffmpeg ???
    goto :setup_venv
)

echo [!!] ??? ffmpeg?????...

where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo [XX] ??? winget??????? ffmpeg?
    echo     ????? ffmpeg: https://ffmpeg.org/download.html
    echo     ??? ffmpeg ?????? PATH ??
    pause
    exit /b 1
)

winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements --silent
if %errorlevel% neq 0 (
    echo [!!] winget ?? ffmpeg ????????...
    winget install FFmpeg.FFmpeg --accept-source-agreements --accept-package-agreements --silent
    if %errorlevel% neq 0 (
        echo [XX] ffmpeg ??????????: https://ffmpeg.org/download.html
        pause
        exit /b 1
    )
)

call :refresh_path

where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] ffmpeg ??????? PATH ?????????????
    pause
    exit /b 1
)
echo [OK] ffmpeg ????

:: ============================================================
:: Step 3: ??????
:: ============================================================
:setup_venv
if exist "%VENV_PYTHON%" (
    echo [OK] ???????
    goto :install_deps
)

echo [..] ????????...
"!PYTHON_BIN!" -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo [XX] ???????????? Python ???
    pause
    exit /b 1
)
echo [OK] ????????

:: ============================================================
:: Step 4: ????
:: ============================================================
:install_deps
echo [..] ????...
"%VENV_PYTHON%" -m pip install --upgrade pip -q 2>nul

if exist "%SCRIPT_DIR%requirements.txt" (
    "%VENV_PYTHON%" -m pip install -r "%SCRIPT_DIR%requirements.txt" -q
    echo [OK] ??????
) else (
    echo [!!] ??? requirements.txt????????
)

:: ============================================================
:: Step 5: ????
:: ============================================================
echo.
echo [OK] ????????? Snipkin...
echo.
"%VENV_PYTHON%" "%SCRIPT_DIR%main.py" %*
if %errorlevel% neq 0 (
    echo.
    echo [XX] Snipkin ???????????????
    pause
    exit /b 1
)
goto :eof

:: ============================================================
:: ????
:: ============================================================

:find_python
:: ????????????? Python
set "PYTHON_BIN="
for %%P in (python3 python py) do (
    where %%P >nul 2>&1
    if !errorlevel! equ 0 (
        call :check_python_version "%%P"
        if defined PYTHON_BIN goto :eof
    )
)

:: Windows ? py launcher ??????
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

:: ????????
for %%V in (313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "CANDIDATE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        call :check_python_version "!CANDIDATE!"
        if defined PYTHON_BIN goto :eof
    )
)
goto :eof

:check_python_version
:: ???? Python ????????
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
:: ?? py launcher ?????
set "PY_VER=%~1"
set "PYTHON_BIN=py -%PY_VER%"
goto :eof

:refresh_path
:: ????????????? PATH????????????
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%B"
if defined SYS_PATH if defined USR_PATH (
    set "PATH=!SYS_PATH!;!USR_PATH!"
)
goto :eof
