"""项目数据模型"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import json

from .segment import Segment


@dataclass
class Project:
    """剪辑项目"""
    name: str = "未命名项目"

    # 片段列表
    segments: List[Segment] = field(default_factory=list)

    # 输出文件路径
    output_path: Optional[Path] = None

    # 输出格式
    output_format: str = "mp4"

    def add_segment(self, segment: Segment) -> None:
        """添加片段"""
        self.segments.append(segment)

    def remove_segment(self, segment_id: str) -> bool:
        """移除片段"""
        for i, seg in enumerate(self.segments):
            if seg.id == segment_id:
                self.segments.pop(i)
                return True
        return False

    def move_segment(self, from_index: int, to_index: int) -> bool:
        """移动片段顺序"""
        if 0 <= from_index < len(self.segments) and 0 <= to_index < len(self.segments):
            seg = self.segments.pop(from_index)
            self.segments.insert(to_index, seg)
            return True
        return False

    def get_total_duration(self) -> float:
        """获取总时长"""
        return sum(seg.duration for seg in self.segments if seg.duration > 0)

    def clear(self) -> None:
        """清空所有片段"""
        self.segments.clear()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "segments": [seg.to_dict() for seg in self.segments],
            "output_path": str(self.output_path) if self.output_path else None,
            "output_format": self.output_format,
            "total_duration": self.get_total_duration()
        }

    def save(self, path: Path) -> None:
        """保存项目到文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "Project":
        """从文件加载项目"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        project = cls(name=data.get("name", "未命名项目"))
        project.output_format = data.get("output_format", "mp4")

        if data.get("output_path"):
            project.output_path = Path(data["output_path"])

        for seg_data in data.get("segments", []):
            seg = Segment(
                source_path=Path(seg_data["source_path"]),
                start_time=seg_data.get("start_time", 0.0),
                end_time=seg_data.get("end_time"),
                id=seg_data.get("id", ""),
                name=seg_data.get("name"),
                volume_gain=seg_data.get("volume_gain", 0.0)
            )
            project.add_segment(seg)

        return project

    def __repr__(self) -> str:
        return f"Project(name={self.name}, segments={len(self.segments)}, duration={self.get_total_duration():.2f}s)"