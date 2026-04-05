"""配置管理模块"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import os


@dataclass
class AppConfig:
    """应用配置"""
    # 视频资源目录
    video_dir: Path = field(default_factory=lambda: Path("video_res"))

    # 输出目录
    output_dir: Path = field(default_factory=lambda: Path("output"))

    # 支持的视频格式
    supported_formats: List[str] = field(default_factory=lambda: [
        "mp4", "avi", "mov", "flv", "mkv", "webm"
    ])

    # 默认导出格式
    default_export_format: str = "mp4"

    # 默认导出质量 (crf 值，越低越好)
    default_quality: int = 23

    # ffmpeg 路径
    ffmpeg_path: str = "ffmpeg"

    # ffprobe 路径
    ffprobe_path: str = "ffprobe"

    # 日志级别
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置"""
        config = cls()
        if "VIDEO_DIR" in os.environ:
            config.video_dir = Path(os.environ["VIDEO_DIR"])
        if "OUTPUT_DIR" in os.environ:
            config.output_dir = Path(os.environ["OUTPUT_DIR"])
        if "FFMPEG_PATH" in os.environ:
            config.ffmpeg_path = os.environ["FFMPEG_PATH"]
        return config


# 全局配置实例
config = AppConfig.from_env()