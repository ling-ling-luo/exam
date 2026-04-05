from dataclasses import dataclass
from typing import Optional


@dataclass
class ExportParams:
    preset: str = "original"
    video_bitrate: Optional[str] = None   # None = 由 CRF 控制；"4000k" 等 = 固定码率
    audio_bitrate: str = "128k"
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None           # None = 保持源帧率


PRESETS: dict = {
    "original": ExportParams(preset="original"),
    "480p":  ExportParams(preset="480p",  width=854,  height=480,  video_bitrate="1500k"),
    "720p":  ExportParams(preset="720p",  width=1280, height=720,  video_bitrate="4000k"),
    "1080p": ExportParams(preset="1080p", width=1920, height=1080, video_bitrate="8000k"),
}
