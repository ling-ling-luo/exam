"""执行器模块 - 协调 FFmpeg 操作"""
from pathlib import Path
from typing import Optional, Callable, List

from .project import Project
from .segment import Segment
from .validator import validate_file_exists, validate_video_format, validate_output_path, validate_segment
from ..errors import ExportError, ValidationError
from ..utils.ffmpeg import get_video_info, export_project, check_ffmpeg
from ..utils.config import config
from ..utils.logger import logger


class Executor:
    """剪辑执行器"""

    def __init__(self):
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """检查依赖"""
        if not check_ffmpeg():
            raise ValidationError("未找到 ffmpeg，请确保已安装并配置在 PATH 中")

    def get_media_info(self, path: Path) -> dict:
        """获取媒体信息"""
        validate_file_exists(path)
        return get_video_info(path)

    def create_segment(
        self,
        source_path: Path,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        name: Optional[str] = None
    ) -> Segment:
        """创建片段"""
        validate_file_exists(source_path)

        # 验证时间范围
        info = get_video_info(source_path)
        duration = info.get("duration", 0)

        if end_time is not None and end_time > duration:
            end_time = duration

        segment = Segment(
            source_path=source_path,
            start_time=start_time,
            end_time=end_time,
            name=name
        )

        validate_segment(segment)

        return segment

    def export(
        self,
        project: Project,
        output_path: Path,
        quality: int = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        params=None,
        cancel_event=None,
    ) -> None:
        """导出项目"""
        if not project.segments:
            raise ValidationError("项目没有片段")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        validate_output_path(output_path)

        if quality is None:
            quality = config.default_quality

        logger.info(f"开始导出到: {output_path}")

        export_project(project, output_path, quality, progress_callback, params, cancel_event)

    def preview_segment(self, segment: Segment) -> str:
        """生成片段预览信息"""
        duration = segment.duration if segment.duration > 0 else "未设置"
        return f"{segment.display_name}: {segment.start_time:.2f}s - {segment.end_time if segment.end_time else '结束'} ({duration}s)"