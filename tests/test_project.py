"""项目模块测试"""
import pytest
from pathlib import Path
import tempfile
import json

from src.core.project import Project
from src.core.segment import Segment


class TestSegment:
    """片段测试"""

    def test_create_segment(self):
        """创建片段"""
        segment = Segment(
            source_path=Path("test.mp4"),
            start_time=10.0,
            end_time=20.0
        )

        assert segment.source_path == Path("test.mp4")
        assert segment.start_time == 10.0
        assert segment.end_time == 20.0
        assert segment.duration == 10.0

    def test_segment_without_end(self):
        """无结束时间的片段"""
        segment = Segment(
            source_path=Path("test.mp4"),
            start_time=10.0
        )

        assert segment.duration == 0.0

    def test_display_name(self):
        """显示名称"""
        segment = Segment(
            source_path=Path("test.mp4"),
            name="自定义名称"
        )
        assert segment.display_name == "自定义名称"

        segment2 = Segment(source_path=Path("test.mp4"))
        assert segment2.display_name == "test.mp4"

    def test_segment_to_dict(self):
        """转换为字典"""
        segment = Segment(
            source_path=Path("test.mp4"),
            start_time=5.0,
            end_time=15.0,
            name="测试片段"
        )

        data = segment.to_dict()
        assert data["source_path"] == "test.mp4"
        assert data["start_time"] == 5.0
        assert data["end_time"] == 15.0
        assert data["name"] == "测试片段"
        assert data["duration"] == 10.0


class TestProject:
    """项目测试"""

    def test_create_project(self):
        """创建项目"""
        project = Project(name="测试项目")
        assert project.name == "测试项目"
        assert len(project.segments) == 0

    def test_add_segment(self):
        """添加片段"""
        project = Project()
        segment = Segment(source_path=Path("test.mp4"))

        project.add_segment(segment)
        assert len(project.segments) == 1
        assert project.segments[0] == segment

    def test_remove_segment(self):
        """移除片段"""
        project = Project()
        segment = Segment(source_path=Path("test.mp4"))
        project.add_segment(segment)

        # 通过 ID 移除
        result = project.remove_segment(segment.id)
        assert result is True
        assert len(project.segments) == 0

        # 移除不存在的片段
        result = project.remove_segment("not-exist")
        assert result is False

    def test_move_segment(self):
        """移动片段顺序"""
        project = Project()
        seg1 = Segment(source_path=Path("1.mp4"))
        seg2 = Segment(source_path=Path("2.mp4"))
        seg3 = Segment(source_path=Path("3.mp4"))

        project.add_segment(seg1)
        project.add_segment(seg2)
        project.add_segment(seg3)

        # 将第一个移动到最后
        result = project.move_segment(0, 2)
        assert result is True
        assert project.segments[0] == seg2
        assert project.segments[2] == seg1

    def test_invalid_move(self):
        """无效移动"""
        project = Project()
        seg1 = Segment(source_path=Path("1.mp4"))
        project.add_segment(seg1)

        # 越界移动
        assert project.move_segment(0, 5) is False
        assert project.move_segment(5, 0) is False

    def test_total_duration(self):
        """总时长计算"""
        project = Project()
        project.add_segment(Segment(source_path=Path("1.mp4"), start_time=0, end_time=10))
        project.add_segment(Segment(source_path=Path("2.mp4"), start_time=5, end_time=20))
        project.add_segment(Segment(source_path=Path("3.mp4"), start_time=0, end_time=None))  # 不计入

        assert project.get_total_duration() == 25.0

    def test_clear(self):
        """清空项目"""
        project = Project()
        project.add_segment(Segment(source_path=Path("1.mp4")))
        project.add_segment(Segment(source_path=Path("2.mp4")))

        project.clear()
        assert len(project.segments) == 0

    def test_save_and_load(self):
        """保存和加载项目"""
        project = Project(name="测试项目")
        project.add_segment(Segment(source_path=Path("input.mp4"), start_time=5.0, end_time=15.0))
        project.output_format = "mp4"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # 保存
            project.save(temp_path)

            # 加载
            loaded = Project.load(temp_path)

            assert loaded.name == "测试项目"
            assert len(loaded.segments) == 1
            assert loaded.segments[0].source_path == Path("input.mp4")
            assert loaded.segments[0].start_time == 5.0
            assert loaded.segments[0].end_time == 15.0

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_to_dict(self):
        """转换为字典"""
        project = Project(name="测试")
        project.add_segment(Segment(source_path=Path("test.mp4"), start_time=0, end_time=10))

        data = project.to_dict()
        assert data["name"] == "测试"
        assert len(data["segments"]) == 1
        assert data["total_duration"] == 10.0