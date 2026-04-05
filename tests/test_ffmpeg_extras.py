from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_generate_thumbnail_calls_ffmpeg(tmp_path):
    with patch("src.utils.ffmpeg.check_ffmpeg", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            from src.utils.ffmpeg import generate_thumbnail
            out = tmp_path / "thumb.jpg"
            result = generate_thumbnail(Path("input.mp4"), out, time=5.0)

            assert result == out
            cmd = mock_run.call_args[0][0]
            assert len(cmd) > 0
            assert "-ss" in cmd
            assert "5.0" in cmd
            assert str(out) in cmd


def test_generate_thumbnail_raises_on_ffmpeg_error(tmp_path):
    with patch("src.utils.ffmpeg.check_ffmpeg", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error msg")

            from src.utils.ffmpeg import generate_thumbnail
            from src.errors import ExportError

            with pytest.raises(ExportError):
                generate_thumbnail(Path("input.mp4"), tmp_path / "thumb.jpg", time=0)


def test_generate_thumbnail_cached(tmp_path):
    """已存在的缩略图不重复调用 ffmpeg"""
    with patch("src.utils.ffmpeg.check_ffmpeg", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            from src.utils.ffmpeg import generate_thumbnail
            out = tmp_path / "thumb.jpg"
            out.touch()  # simulate existing file

            generate_thumbnail(Path("input.mp4"), out, time=5.0)
            mock_run.assert_not_called()


def test_split_video_720p_params(tmp_path, mocker):
    mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
    mocker.patch("src.utils.ffmpeg.get_video_info", return_value={"duration": 30.0})
    mock_popen = mocker.patch("subprocess.Popen")
    proc = MagicMock()
    proc.poll.return_value = 0
    proc.communicate.return_value = ("", "")
    proc.returncode = 0
    mock_popen.return_value = proc

    from src.utils.ffmpeg import split_video
    from src.core.export_params import ExportParams

    params = ExportParams(preset="720p", width=1280, height=720, video_bitrate="4000k")
    split_video(Path("in.mp4"), tmp_path / "out.mp4", 0, 10, params=params)

    cmd = mock_popen.call_args[0][0]
    assert "-vf" in cmd
    assert "scale=1280:720" in cmd
    assert "-b:v" in cmd
    assert "4000k" in cmd
    assert "-crf" not in cmd   # 固定码率时不用 CRF


def test_split_video_cancel(tmp_path, mocker):
    import threading
    mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
    mocker.patch("src.utils.ffmpeg.get_video_info", return_value={"duration": 30.0})
    mock_popen = mocker.patch("subprocess.Popen")
    proc = MagicMock()
    proc.poll.return_value = None   # always running
    proc.stderr.readline.return_value = ""
    proc.communicate.return_value = ("", "")
    proc.returncode = 0
    mock_popen.return_value = proc

    cancel = threading.Event()
    cancel.set()   # cancel immediately

    from src.utils.ffmpeg import split_video
    split_video(Path("in.mp4"), tmp_path / "out.mp4", 0, 10, cancel_event=cancel)

    proc.terminate.assert_called()
