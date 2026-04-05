import pytest
from src.core.export_params import ExportParams, PRESETS


def test_default_params():
    p = ExportParams()
    assert p.preset == "original"
    assert p.width is None
    assert p.height is None
    assert p.video_bitrate is None
    assert p.fps is None
    assert p.audio_bitrate == "128k"


def test_presets_exist():
    assert "original" in PRESETS
    assert "480p" in PRESETS
    assert "720p" in PRESETS
    assert "1080p" in PRESETS


def test_480p_preset():
    p = PRESETS["480p"]
    assert p.width == 854
    assert p.height == 480
    assert p.video_bitrate == "1500k"


def test_720p_preset():
    p = PRESETS["720p"]
    assert p.width == 1280
    assert p.height == 720
    assert p.video_bitrate == "4000k"


def test_1080p_preset():
    p = PRESETS["1080p"]
    assert p.width == 1920
    assert p.height == 1080
    assert p.video_bitrate == "8000k"


def test_original_preset_has_no_constraints():
    p = PRESETS["original"]
    assert p.width is None
    assert p.height is None
    assert p.video_bitrate is None
    assert p.fps is None
