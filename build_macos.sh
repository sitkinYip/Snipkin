#!/bin/bash
set -e

# Snipkin macOS 自动构建脚本

echo "========================================="
echo "  🚀 开始构建 Snipkin for macOS..."
echo "========================================="

# 1. 检查必要环境
if ! command -v pyinstaller &> /dev/null; then
    echo "⚠️  未找到 PyInstaller，正在安装构建依赖..."
    pip install -r requirements-build.txt
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "❌ 错误：系统中未安装 ffmpeg，无法将其打包为内置依赖。"
    echo "请先使用 Homebrew 安装：brew install ffmpeg"
    exit 1
fi

# 2. 获取系统中 ffmpeg 和 ffprobe 的实际绝对路径
FFMPEG_PATH=$(which ffmpeg)
FFPROBE_PATH=$(which ffprobe)

echo "✅ 检测到 ffmpeg 位于：$FFMPEG_PATH"
echo "✅ 检测到 ffprobe 位于：$FFPROBE_PATH"

# 3. 清理旧的构建产物
echo "🧹 清理此前构建遗留文件..."
rm -rf build/ dist/ Snipkin.spec

# 4. 执行 PyInstaller 打包命令
echo "📦 正在执行 PyInstaller 封装主程序并捆绑音视频组件..."

# 参数说明：
# --noconfirm:         静默覆盖输出
# --windowed:          生成 .app，不附带后台终端控制台窗口
# --name:              指定输出名称
# --icon:              指定应用图标
# --add-binary:        将指定文件原样拷贝进打包环境中 (格式: SRC:DEST)
#                      此处将系统里的二进制复制到应用内部，代码通过 sys._MEIPASS 获取

pyinstaller --noconfirm --windowed --name "Snipkin" \
    --icon "assets/icon.icns" \
    --add-binary "$FFMPEG_PATH:." \
    --add-binary "$FFPROBE_PATH:." \
    --hidden-import "PIL._tkinter_finder" \
    main.py

echo "✅ macOS .app 构建完成！位于 dist/Snipkin.app"

# 5. 将 .app 封装为 .dmg 磁盘映像
echo "💿 正在生成 DMG 磁盘映像..."

DMG_NAME="Snipkin.dmg"
DMG_PATH="dist/$DMG_NAME"
DMG_TEMP_DIR="dist/dmg_staging"

# 清理可能残留的旧 DMG 文件和临时目录
rm -f "$DMG_PATH"
rm -rf "$DMG_TEMP_DIR"

# 创建临时目录，放入 .app 和 Applications 快捷方式
mkdir -p "$DMG_TEMP_DIR"
cp -R dist/Snipkin.app "$DMG_TEMP_DIR/"
ln -s /Applications "$DMG_TEMP_DIR/Applications"

# 使用 hdiutil 创建 DMG
hdiutil create -volname "Snipkin" \
    -srcfolder "$DMG_TEMP_DIR" \
    -ov -format UDZO \
    "$DMG_PATH"

# 清理临时目录
rm -rf "$DMG_TEMP_DIR"

echo "========================================="
echo "🎉 macOS 构建全部完成！"
echo "   .app 位于: dist/Snipkin.app"
echo "   .dmg 位于: dist/$DMG_NAME"
echo "========================================="
