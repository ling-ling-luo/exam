"""片段数据模型"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import uuid


@dataclass
class Segment:
    """视频片段"""
    # 源文件路径
    source_path: Path

    # 入点时间（秒）
    start_time: float = 0.0

    # 出点时间（秒）
    end_time: Optional[float] = None

    # 唯一标识
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # 片段名称（可选）
    name: Optional[str] = None

    # 音量增益 (dB)
    volume_gain: float = 0.0

    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.source_path, str):
            self.source_path = Path(self.source_path)

    @property
    def duration(self) -> float:
        """获取片段时长"""
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def display_name(self) -> str:
        """获取显示名称"""
        if self.name:
            return self.name
        return self.source_path.name

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "source_path": str(self.source_path),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "name": self.name,
            "volume_gain": self.volume_gain
        }

    def __repr__(self) -> str:
        return f"Segment(id={self.id}, source={self.source_path.name}, {self.start_time:.2f}-{self.end_time})"