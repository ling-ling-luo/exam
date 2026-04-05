"""输入验证模块"""
import re
from pathlib import Path
from typing import Tuple, Optional

from ..errors import FileNotFoundError, UnsupportedFormatError, InvalidTimeCodeError, ValidationError
from ..utils.config import config


# 时间码正则表达式 (支持 HH:MM:SS.ms 或 SS.ms 格式)
TIME_CODE_PATTERN = re.compile(r'^(\d{1,2}:)?(\d{1,2}):(\d{2})(?:\.(\d+))?$')


def validate_file_exists(path: Path) -> None:
    """验证文件是否存在"""
    if not path.exists():
        raise FileNotFoundError(str(path))
    if not path.is_file():
        raise ValidationError(f"路径不是文件: {path}", "path")


def validate_video_format(path: Path) -> None:
    """验证视频格式是否支持"""
    suffix = path.suffix.lstrip(".").lower()
    if suffix not in config.supported_formats:
        raise UnsupportedFormatError(suffix)


def parse_time_code(time_str: str) -> float:
    """解析时间码为秒数

    支持格式:
    - 10.5 (秒)
    - 1:30.5 (1分30.5秒)
    - 01:30:50.5 (1小时30分50.5秒)
    """
    time_str = time_str.strip()

    # 纯数字（秒）
    if time_str.replace(".", "").isdigit():
        return float(time_str)

    # 格式匹配
    match = TIME_CODE_PATTERN.match(time_str)
    if not match:
        raise InvalidTimeCodeError(time_str)

    hours = match.group(1)
    minutes = match.group(2)
    seconds = match.group(3)
    ms = match.group(4)

    total_seconds = 0.0

    if hours:
        total_seconds += int(hours.rstrip(":")) * 3600
    if minutes:
        total_seconds += int(minutes) * 60

    total_seconds += int(seconds)

    if ms:
        total_seconds += int(ms) / (10 ** len(ms))

    return total_seconds


def format_time_code(seconds: float) -> str:
    """将秒数格式化为时间码"""
    if seconds < 0:
        seconds = 0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 100)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}.{ms:02d}"


def validate_time_range(start_time: float, end_time: float, max_duration: float) -> None:
    """验证时间范围是否合法"""
    if start_time < 0:
        raise ValidationError("入点时间不能为负数", "start_time")

    if end_time is None:
        return

    if end_time < 0:
        raise ValidationError("出点时间不能为负数", "end_time")

    if start_time >= end_time:
        raise ValidationError("入点时间必须小于出点时间", "time_range")

    if end_time > max_duration:
        raise ValidationError(f"出点时间超出视频时长 ({max_duration:.2f}秒)", "end_time")


def validate_output_path(path: Path) -> None:
    """验证输出路径"""
    parent = path.parent
    if not parent.exists():
        raise ValidationError(f"输出目录不存在: {parent}", "output_path")

    suffix = path.suffix.lstrip(".").lower()
    if suffix not in config.supported_formats:
        raise UnsupportedFormatError(suffix)


def validate_segment(segment) -> None:
    """验证片段参数"""
    if segment.start_time < 0:
        raise ValidationError("入点时间不能为负数", "start_time")

    if segment.end_time is not None and segment.end_time <= segment.start_time:
        raise ValidationError("出点时间必须大于入点时间", "end_time")