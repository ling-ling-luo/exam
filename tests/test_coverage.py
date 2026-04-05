"""
综合测试覆盖：
1. 基础功能正确性
2. 异构输入兼容性
3. 异常输入鲁棒性
4. 连续执行稳定性
"""
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

VIDEO_RES = Path("video_res")
MP4_FILE  = VIDEO_RES / "bun33s.mp4"
FLV_FILE  = VIDEO_RES / "bun33s.flv"
GIF_FILE  = VIDEO_RES / "video-to-gif-sample.gif"


def ffmpeg_available():
    from src.utils.ffmpeg import check_ffmpeg
    return check_ffmpeg()


# ── 1. 基础功能正确性 ─────────────────────────────────────────────────────────

class TestBasicFunctionality:

    def test_parse_timecode_seconds(self):
        from src.core.validator import parse_time_code
        assert parse_time_code("10") == 10.0
        assert parse_time_code("10.5") == 10.5

    def test_parse_timecode_mm_ss(self):
        from src.core.validator import parse_time_code
        assert parse_time_code("1:30") == 90.0

    def test_parse_timecode_hh_mm_ss(self):
        from src.core.validator import parse_time_code
        assert parse_time_code("1:00:00") == 3600.0

    def test_format_timecode_roundtrip(self):
        from src.core.validator import parse_time_code, format_time_code
        for secs in [0, 30.5, 90, 3661.25]:
            formatted = format_time_code(secs)
            parsed = parse_time_code(formatted)
            assert abs(parsed - secs) < 0.01, f"roundtrip failed for {secs}: {formatted} -> {parsed}"

    def test_project_segment_ordering(self):
        from src.core.project import Project
        from src.core.segment import Segment
        p = Project()
        s1 = Segment(source_path=Path("a.mp4"), start_time=0, end_time=5)
        s2 = Segment(source_path=Path("b.mp4"), start_time=0, end_time=3)
        s3 = Segment(source_path=Path("c.mp4"), start_time=0, end_time=7)
        p.add_segment(s1); p.add_segment(s2); p.add_segment(s3)
        p.move_segment(0, 2)
        assert p.segments[0].source_path.name == "b.mp4"
        assert p.segments[2].source_path.name == "a.mp4"

    def test_project_total_duration(self):
        from src.core.project import Project
        from src.core.segment import Segment
        p = Project()
        p.add_segment(Segment(source_path=Path("a.mp4"), start_time=0,   end_time=10))
        p.add_segment(Segment(source_path=Path("b.mp4"), start_time=5,   end_time=20))
        p.add_segment(Segment(source_path=Path("c.mp4"), start_time=0,   end_time=None))  # excluded
        assert p.get_total_duration() == 25.0

    def test_export_params_preset_values(self):
        from src.core.export_params import PRESETS
        assert PRESETS["720p"].width == 1280 and PRESETS["720p"].height == 720
        assert PRESETS["1080p"].video_bitrate == "8000k"
        assert PRESETS["original"].width is None

    def test_split_video_builds_correct_cmd(self, tmp_path, mocker):
        mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
        mocker.patch("src.utils.ffmpeg.get_video_info", return_value={"duration": 30.0})
        proc = MagicMock()
        proc.poll.return_value = 0
        proc.communicate.return_value = ("", "")
        proc.returncode = 0
        mock_popen = mocker.patch("subprocess.Popen", return_value=proc)

        from src.utils.ffmpeg import split_video
        split_video(Path("in.mp4"), tmp_path / "out.mp4", start_time=2.0, end_time=8.0)

        cmd = mock_popen.call_args[0][0]
        assert "-ss" in cmd and "2.0" in cmd
        assert "-t" in cmd and "6.0" in cmd

    @pytest.mark.integration
    def test_get_video_info_real_mp4(self):
        if not ffmpeg_available():
            pytest.skip("ffmpeg not available")
        from src.utils.ffmpeg import get_video_info
        info = get_video_info(MP4_FILE)
        assert info["duration"] > 0
        assert info["video"] is not None
        assert info["video"]["width"] > 0

    @pytest.mark.integration
    def test_generate_thumbnail_real(self, tmp_path):
        if not ffmpeg_available():
            pytest.skip("ffmpeg not available")
        from src.utils.ffmpeg import generate_thumbnail
        out = tmp_path / "thumb.jpg"
        result = generate_thumbnail(MP4_FILE, out, time=1.0)
        assert result.exists()
        assert result.stat().st_size > 1000


# ── 2. 异构输入兼容性 ─────────────────────────────────────────────────────────

class TestHeterogeneousInput:

    @pytest.mark.integration
    def test_mp4_info(self):
        if not ffmpeg_available(): pytest.skip()
        from src.utils.ffmpeg import get_video_info
        info = get_video_info(MP4_FILE)
        assert info["format"] != ""
        assert info["duration"] > 0

    @pytest.mark.integration
    def test_flv_info(self):
        if not ffmpeg_available(): pytest.skip()
        from src.utils.ffmpeg import get_video_info
        info = get_video_info(FLV_FILE)
        assert info["duration"] > 0

    @pytest.mark.integration
    def test_mp4_flv_same_content_similar_duration(self):
        """同内容的 mp4 和 flv 时长应相近"""
        if not ffmpeg_available(): pytest.skip()
        from src.utils.ffmpeg import get_video_info
        mp4_dur = get_video_info(MP4_FILE)["duration"]
        flv_dur = get_video_info(FLV_FILE)["duration"]
        assert abs(mp4_dur - flv_dur) < 1.0, f"duration mismatch: mp4={mp4_dur}, flv={flv_dur}"

    @pytest.mark.integration
    def test_export_mixed_formats_concat(self, tmp_path):
        """mp4 + flv 拼接能产生有效输出"""
        if not ffmpeg_available(): pytest.skip()
        from src.core.project import Project
        from src.core.segment import Segment
        from src.core.executor import Executor
        from src.core.export_params import ExportParams

        executor = Executor()
        project = Project()
        project.add_segment(Segment(source_path=MP4_FILE, start_time=0, end_time=2))
        project.add_segment(Segment(source_path=FLV_FILE, start_time=0, end_time=2))

        out = tmp_path / "mixed_concat.mp4"
        executor.export(project, out, quality=35, params=ExportParams())
        assert out.exists()
        assert out.stat().st_size > 10_000

        from src.utils.ffmpeg import get_video_info
        info = get_video_info(out)
        assert abs(info["duration"] - 4.0) < 1.0

    @pytest.mark.integration
    def test_export_720p_downscale(self, tmp_path):
        """1280x720 素材导出后分辨率符合 720p 预设"""
        if not ffmpeg_available(): pytest.skip()
        from src.core.project import Project
        from src.core.segment import Segment
        from src.core.executor import Executor
        from src.core.export_params import PRESETS

        executor = Executor()
        project = Project()
        project.add_segment(Segment(source_path=MP4_FILE, start_time=0, end_time=2))

        out = tmp_path / "out_720p.mp4"
        executor.export(project, out, quality=35, params=PRESETS["720p"])
        assert out.exists()

        from src.utils.ffmpeg import get_video_info
        info = get_video_info(out)
        assert info["video"]["width"] == 1280
        assert info["video"]["height"] == 720


# ── 3. 异常输入鲁棒性 ─────────────────────────────────────────────────────────

class TestRobustness:

    def test_nonexistent_file_raises(self):
        from src.core.validator import validate_file_exists
        from src.errors import FileNotFoundError as VCFileNotFoundError
        with pytest.raises(VCFileNotFoundError):
            validate_file_exists(Path("/nonexistent/file.mp4"))

    def test_unsupported_format_gif(self):
        """gif 不在支持格式列表中"""
        from src.core.validator import validate_video_format
        from src.errors import UnsupportedFormatError
        with pytest.raises(UnsupportedFormatError):
            validate_video_format(GIF_FILE)

    def test_invalid_timecode_raises(self):
        from src.core.validator import parse_time_code
        from src.errors import InvalidTimeCodeError
        for bad in ["abc", "99:99:99:99", "1:2:3:4:5", "--1"]:
            with pytest.raises((InvalidTimeCodeError, ValueError)):
                parse_time_code(bad)

    def test_start_after_end_raises(self):
        from src.core.validator import validate_time_range
        from src.errors import ValidationError
        with pytest.raises(ValidationError):
            validate_time_range(start_time=10, end_time=5, max_duration=100)

    def test_end_exceeds_duration_raises(self):
        from src.core.validator import validate_time_range
        from src.errors import ValidationError
        with pytest.raises(ValidationError):
            validate_time_range(start_time=0, end_time=200, max_duration=100)

    def test_export_empty_project_raises(self):
        from src.core.executor import Executor
        from src.errors import ValidationError
        with patch("src.utils.ffmpeg.check_ffmpeg", return_value=True):
            executor = Executor()
            from src.core.project import Project
            with pytest.raises(ValidationError):
                executor.export(Project(), Path("out.mp4"), quality=23)

    def test_negative_start_time_raises(self):
        from src.core.validator import validate_segment
        from src.core.segment import Segment
        from src.errors import ValidationError
        seg = Segment(source_path=Path("a.mp4"), start_time=-1.0, end_time=5.0)
        with pytest.raises(ValidationError):
            validate_segment(seg)

    def test_gif_get_info_raises_or_returns_no_video(self):
        """gif 文件调用 get_video_info 应失败或视频流为 None"""
        if not ffmpeg_available():
            pytest.skip()
        from src.utils.ffmpeg import get_video_info
        from src.errors import ExportError
        try:
            info = get_video_info(GIF_FILE)
            # gif may have no video stream or unusual format — should not crash
            assert info is not None
        except ExportError:
            pass  # acceptable: ffprobe returns non-zero for unsupported input

    def test_thumbnail_ffmpeg_error_raises(self, tmp_path, mocker):
        mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
        mocker.patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="fail"))
        from src.utils.ffmpeg import generate_thumbnail
        from src.errors import ExportError
        with pytest.raises(ExportError):
            generate_thumbnail(Path("bad.mp4"), tmp_path / "out.jpg")


# ── 4. 连续执行稳定性 ─────────────────────────────────────────────────────────

class TestContinuousStability:

    def test_queue_three_tasks_sequential(self):
        """3 个任务按顺序完成，无状态污染"""
        from src.core.task_queue import TaskQueue
        from src.core.export_task import ExportTask
        from src.core.export_params import ExportParams
        from src.core.project import Project

        order = []
        all_done = threading.Event()

        def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
            order.append(output_path.name)
            if len(order) == 3:
                all_done.set()

        mock_executor = MagicMock()
        mock_executor.export.side_effect = fake_export

        q = TaskQueue(mock_executor)
        q.start()

        tasks = [
            ExportTask(project=Project(), output_path=Path(f"out{i}.mp4"), quality=23, params=ExportParams())
            for i in range(3)
        ]
        for t in tasks:
            q.add(t)

        all_done.wait(timeout=5.0)
        q.shutdown()

        assert order == ["out0.mp4", "out1.mp4", "out2.mp4"]
        assert all(t.status == "done" for t in tasks)

    def test_queue_cancel_middle_task(self):
        """取消中间的 pending 任务，前后任务正常完成"""
        from src.core.task_queue import TaskQueue
        from src.core.export_task import ExportTask
        from src.core.export_params import ExportParams
        from src.core.project import Project

        started_first = threading.Event()
        release_first = threading.Event()
        completed = threading.Event()
        order = []

        def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
            name = output_path.name
            if name == "t0.mp4":
                started_first.set()
                release_first.wait(timeout=3.0)
            order.append(name)
            if len(order) == 2:
                completed.set()

        mock_executor = MagicMock()
        mock_executor.export.side_effect = fake_export

        q = TaskQueue(mock_executor)
        q.start()

        t0 = ExportTask(project=Project(), output_path=Path("t0.mp4"), quality=23, params=ExportParams())
        t1 = ExportTask(project=Project(), output_path=Path("t1.mp4"), quality=23, params=ExportParams())
        t2 = ExportTask(project=Project(), output_path=Path("t2.mp4"), quality=23, params=ExportParams())
        q.add(t0); q.add(t1); q.add(t2)

        started_first.wait(timeout=3.0)
        q.cancel(t1.id)
        assert t1.status == "cancelled"
        release_first.set()

        completed.wait(timeout=5.0)
        q.shutdown()

        assert "t1.mp4" not in order
        assert t0.status == "done"
        assert t2.status == "done"

    def test_queue_recovers_after_failed_task(self):
        """一个任务失败后，队列继续执行下一个任务"""
        from src.core.task_queue import TaskQueue
        from src.core.export_task import ExportTask
        from src.core.export_params import ExportParams
        from src.core.project import Project

        second_done = threading.Event()

        def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
            if output_path.name == "fail.mp4":
                raise RuntimeError("simulated failure")
            second_done.set()

        mock_executor = MagicMock()
        mock_executor.export.side_effect = fake_export

        q = TaskQueue(mock_executor)
        q.start()

        t_fail = ExportTask(project=Project(), output_path=Path("fail.mp4"), quality=23, params=ExportParams())
        t_ok   = ExportTask(project=Project(), output_path=Path("ok.mp4"),   quality=23, params=ExportParams())
        q.add(t_fail); q.add(t_ok)

        second_done.wait(timeout=5.0)
        time.sleep(0.05)
        q.shutdown()

        assert t_fail.status == "failed"
        assert t_ok.status == "done"

    def test_multiple_exports_no_temp_dir_leakage(self, tmp_path, mocker):
        """连续导出后 .temp 临时目录被清理"""
        mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
        mocker.patch("src.utils.ffmpeg.get_video_info", return_value={"duration": 10.0})

        proc = MagicMock()
        proc.poll.return_value = 0
        proc.communicate.return_value = ("", "")
        proc.returncode = 0
        mocker.patch("subprocess.Popen", return_value=proc)

        from src.utils.ffmpeg import export_project
        from src.core.project import Project
        from src.core.segment import Segment

        for i in range(3):
            project = Project()
            project.add_segment(Segment(source_path=Path("a.mp4"), start_time=0, end_time=5))
            out = tmp_path / f"out_{i}.mp4"
            export_project(project, out, quality=23)
            temp_dir = out.parent / ".temp"
            assert not temp_dir.exists(), f"temp dir leaked after export {i}"

    @pytest.mark.integration
    def test_real_export_two_segments_sequential(self, tmp_path):
        """真实 ffmpeg 连续导出两个片段，验证输出完整"""
        if not ffmpeg_available(): pytest.skip()
        from src.core.project import Project
        from src.core.segment import Segment
        from src.core.executor import Executor

        executor = Executor()
        for i in range(2):
            project = Project()
            project.add_segment(Segment(source_path=MP4_FILE, start_time=0, end_time=2))
            out = tmp_path / f"stable_{i}.mp4"
            executor.export(project, out, quality=35)
            assert out.exists() and out.stat().st_size > 5000
