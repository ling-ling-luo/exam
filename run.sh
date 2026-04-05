#!/bin/bash
# 启动脚本

set -e

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python 3"
    exit 1
fi

# 检查并安装依赖
if [ ! -d "venv" ] && [ ! -f "requirements.txt" ] || [ -f "requirements.txt" ]; then
    if ! python3 -c "import rich" 2>/dev/null; then
        echo "安装依赖..."
        pip3 install -r requirements.txt
    fi
fi

# 检查 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "警告: 未找到 ffmpeg，请确保已安装"
fi

# 创建输出目录
mkdir -p output

# 显示帮助
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "用法: ./run.sh [命令]"
    echo ""
    echo "命令:"
    echo "  (无参数)   启动 TUI 交互界面"
    echo "  check      检查系统依赖"
    echo "  split      切分视频"
    echo "  concat     拼接视频"
    echo ""
    echo "示例:"
    echo "  ./run.sh              # 启动 TUI"
    echo "  ./run.sh check        # 检查依赖"
    echo "  ./run.sh split video_res/input.mp4 --start 0 --end 10"
    exit 0
fi

# 执行命令
if [ -z "$1" ]; then
    echo "启动 TUI 交互界面..."
    python3 run.py tui
else
    python3 run.py "$@"
fi