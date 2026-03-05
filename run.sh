#!/usr/bin/env bash
# ============================================================
# Snipkin 一键启动脚本（macOS / Linux）
# 用法: ./run.sh
#
# 功能:
#   1. 检测操作系统（macOS / Linux）
#   2. 检测并安装包管理器（Homebrew / apt / dnf / pacman）
#   3. 检测并安装 Python >= 3.10
#   4. 检测并安装 ffmpeg
#   5. 创建虚拟环境并安装 pip 依赖
#   6. 启动 Snipkin
# ============================================================

set -euo pipefail

# ---- 颜色输出 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}ℹ️  $*${NC}"; }
success() { echo -e "${GREEN}✅ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $*${NC}"; }
error()   { echo -e "${RED}❌ $*${NC}"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=10

# ============================================================
# 工具函数
# ============================================================

detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        *)       error "不支持的操作系统: $(uname -s)。本脚本仅支持 macOS 和 Linux。" ;;
    esac
}

# 检查 Python 版本是否 >= 3.10
python_version_ok() {
    local python_bin="$1"
    if ! command -v "$python_bin" &>/dev/null; then
        return 1
    fi
    local version_output
    version_output=$("$python_bin" --version 2>&1) || return 1
    local major minor
    major=$(echo "$version_output" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 | cut -d. -f1)
    minor=$(echo "$version_output" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 | cut -d. -f2)
    [[ -n "$major" && -n "$minor" ]] || return 1
    if (( major > REQUIRED_PYTHON_MAJOR )) || { (( major == REQUIRED_PYTHON_MAJOR )) && (( minor >= REQUIRED_PYTHON_MINOR )); }; then
        return 0
    fi
    return 1
}

# 在多个候选名称中查找可用的 Python
find_python() {
    local candidates=("python3.13" "python3.12" "python3.11" "python3.10" "python3" "python")
    for candidate in "${candidates[@]}"; do
        if python_version_ok "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# 需要管理员权限时的提示与执行
run_privileged() {
    if [[ $EUID -eq 0 ]]; then
        "$@"
    elif command -v sudo &>/dev/null; then
        warn "需要管理员权限，请输入密码..."
        sudo "$@"
    else
        error "需要管理员权限但未找到 sudo，请以 root 用户运行此脚本。"
    fi
}

# ============================================================
# 包管理器检测与安装
# ============================================================

detect_linux_package_manager() {
    if command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v pacman &>/dev/null; then
        echo "pacman"
    else
        echo "unknown"
    fi
}

ensure_homebrew() {
    if command -v brew &>/dev/null; then
        success "Homebrew 已安装"
        return
    fi
    info "正在安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # 安装后将 brew 加入当前 session 的 PATH
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    command -v brew &>/dev/null || error "Homebrew 安装失败，请手动安装后重试。"
    success "Homebrew 安装完成"
}

install_package_linux() {
    local package_name="$1"
    local pkg_mgr
    pkg_mgr=$(detect_linux_package_manager)

    case "$pkg_mgr" in
        apt)
            run_privileged apt-get update -qq
            run_privileged apt-get install -y -qq "$package_name"
            ;;
        dnf)
            run_privileged dnf install -y -q "$package_name"
            ;;
        yum)
            run_privileged yum install -y -q "$package_name"
            ;;
        pacman)
            run_privileged pacman -Sy --noconfirm "$package_name"
            ;;
        *)
            error "未检测到支持的包管理器（apt/dnf/yum/pacman），请手动安装 $package_name。"
            ;;
    esac
}

# ============================================================
# Python 检测与安装
# ============================================================

ensure_python() {
    info "检测 Python 环境..."

    local python_bin
    if python_bin=$(find_python); then
        local version
        version=$("$python_bin" --version 2>&1)
        success "找到 $version ($python_bin)"
        PYTHON_BIN="$python_bin"
        return
    fi

    warn "未找到 Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}，正在安装..."

    local os_type
    os_type=$(detect_os)

    if [[ "$os_type" == "macos" ]]; then
        ensure_homebrew
        brew install python@3.13
        # Homebrew Python 路径
        if [[ -f /opt/homebrew/bin/python3.13 ]]; then
            PYTHON_BIN="/opt/homebrew/bin/python3.13"
        elif [[ -f /usr/local/bin/python3.13 ]]; then
            PYTHON_BIN="/usr/local/bin/python3.13"
        else
            PYTHON_BIN="python3.13"
        fi
    else
        # Linux: 尝试安装 python3 + python3-venv
        local pkg_mgr
        pkg_mgr=$(detect_linux_package_manager)
        case "$pkg_mgr" in
            apt)
                # Debian/Ubuntu: 需要 deadsnakes PPA 或系统自带版本
                run_privileged apt-get update -qq
                run_privileged apt-get install -y -qq software-properties-common
                run_privileged add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
                run_privileged apt-get update -qq
                run_privileged apt-get install -y -qq python3.12 python3.12-venv python3.12-tk
                PYTHON_BIN="python3.12"
                ;;
            dnf|yum)
                install_package_linux python3
                install_package_linux python3-tkinter
                PYTHON_BIN="python3"
                ;;
            pacman)
                install_package_linux python
                install_package_linux tk
                PYTHON_BIN="python3"
                ;;
            *)
                error "无法自动安装 Python，请手动安装 Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}。"
                ;;
        esac
    fi

    # 验证安装结果
    if ! python_version_ok "$PYTHON_BIN"; then
        error "Python 安装后版本仍不满足要求 (>= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR})，请手动安装。"
    fi

    local version
    version=$("$PYTHON_BIN" --version 2>&1)
    success "Python 安装完成: $version"
}

# ============================================================
# ffmpeg 检测与安装
# ============================================================

ensure_ffmpeg() {
    info "检测 ffmpeg..."

    if command -v ffmpeg &>/dev/null; then
        local version
        version=$(ffmpeg -version 2>&1 | head -1)
        success "ffmpeg 已安装: $version"
        return
    fi

    warn "未找到 ffmpeg，正在安装..."

    local os_type
    os_type=$(detect_os)

    if [[ "$os_type" == "macos" ]]; then
        ensure_homebrew
        brew install ffmpeg
    else
        local pkg_mgr
        pkg_mgr=$(detect_linux_package_manager)
        install_package_linux ffmpeg
    fi

    command -v ffmpeg &>/dev/null || error "ffmpeg 安装失败，请手动安装后重试。"
    success "ffmpeg 安装完成"
}

# ============================================================
# 虚拟环境与依赖
# ============================================================

ensure_venv() {
    local venv_python="$VENV_DIR/bin/python"

    if [[ -f "$venv_python" ]]; then
        success "虚拟环境已存在"
        VENV_PYTHON="$venv_python"
        return
    fi

    info "正在创建虚拟环境..."
    "$PYTHON_BIN" -m venv "$VENV_DIR" || {
        # 某些 Linux 发行版需要单独安装 python3-venv
        warn "venv 模块不可用，尝试安装..."
        local os_type
        os_type=$(detect_os)
        if [[ "$os_type" == "linux" ]]; then
            local pkg_mgr
            pkg_mgr=$(detect_linux_package_manager)
            if [[ "$pkg_mgr" == "apt" ]]; then
                local python_version
                python_version=$("$PYTHON_BIN" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
                run_privileged apt-get install -y -qq "python${python_version}-venv"
            fi
        fi
        "$PYTHON_BIN" -m venv "$VENV_DIR" || error "无法创建虚拟环境，请检查 Python 安装。"
    }

    VENV_PYTHON="$venv_python"
    success "虚拟环境创建完成"
}

install_dependencies() {
    info "检查 pip 依赖..."

    # 升级 pip
    "$VENV_PYTHON" -m pip install --upgrade pip -q 2>/dev/null

    # 安装 requirements.txt
    if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
        "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" -q
        success "依赖安装完成"
    else
        warn "未找到 requirements.txt，跳过依赖安装。"
    fi
}

# ============================================================
# 主流程
# ============================================================

main() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       Snipkin 一键启动脚本          ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo ""

    local os_type
    os_type=$(detect_os)
    info "检测到操作系统: $os_type"

    # Step 1: 确保 Python 可用
    ensure_python

    # Step 2: 确保 ffmpeg 可用
    ensure_ffmpeg

    # Step 3: 创建虚拟环境
    ensure_venv

    # Step 4: 安装依赖
    install_dependencies

    # Step 5: 启动应用
    echo ""
    success "环境就绪，正在启动 Snipkin..."
    echo ""
    exec "$VENV_PYTHON" "$SCRIPT_DIR/main.py" "$@"
}

main "$@"
pao