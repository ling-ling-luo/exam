#!/usr/bin/env python3
"""启动脚本"""
import sys
from pathlib import Path

# 确保可以导入 src 模块
sys.path.insert(0, str(Path(__file__).parent))

from src.cli import cli

if __name__ == "__main__":
    cli(obj={})