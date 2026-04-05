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
