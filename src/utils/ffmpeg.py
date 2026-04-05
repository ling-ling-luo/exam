"""FFmpeg 封装模块"""
import json
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
import threading

from ..errors import FFmpegNotFoundError, ExportError
from .config import config
from .logger import logger


def _parse_fps(rate_str: str) -> float:
    """安全解析帧率分数字符串，如 '30000/1001'"""
    try:
        parts = rate_str.split("/")
        if len(parts) == 2:
            num, den = int(parts[0]), int(parts[1])
            return num / den if den else 0.0
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


_ffmpeg_available: Optional[bool] = None


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用（结果缓存，只 fork 一次）"""
    global _ffmpeg_available
    if _ffmpeg_available is not None:
        return _ffmpeg_available
    try:
        result = subprocess.run(
            [config.ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        _ffmpeg_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _ffmpeg_available = False
    return _ffmpeg_available


def get_video_info(path: Path) -> Dict[str, Any]:
    """获取视频信息"""
    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    cmd = [
        config.ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise ExportError(f"获取视频信息失败: {result.stderr}")

        data = json.loads(result.stdout)

        # 提取视频流信息
        video_stream = None
        audio_stream = None

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and not video_stream:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and not audio_stream:
                audio_stream = stream

        format_info = data.get("format", {})

        return {
            "path": str(path),
            "filename": path.name,
            "duration": float(format_info.get("duration", 0)),
            "size": int(format_info.get("size", 0)),
            "format": format_info.get("format_name", ""),
            "bitrate": int(format_info.get("bit_rate", 0)),
            "video": {
                "codec": video_stream.get("codec_name") if video_stream else None,
                "width": video_stream.get("width") if video_stream else None,
                "height": video_stream.get("height") if video_stream else None,
                "fps": _parse_fps(video_stream.get("r_frame_rate", "0/1")) if video_stream else None,
            } if video_stream else None,
            "audio": {
                "codec": audio_stream.get("codec_name") if audio_stream else None,
                "sample_rate": audio_stream.get("sample_rate") if audio_stream else None,
                "channels": audio_stream.get("channels") if audio_stream else None,
            } if audio_stream else None,
        }
    except subprocess.TimeoutExpired:
        raise ExportError("获取视频信息超时")
    except json.JSONDecodeError:
        raise ExportError("解析视频信息失败")


def split_video(
    input_path: Path,
    output_path: Path,
    start_time: float,
    end_time: Optional[float] = None,
    quality: int = 23,
    progress_callback: Optional[Callable[[float], None]] = None,
    params=None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    """切分视频"""
    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    duration = end_time - start_time if end_time else None

    cmd = [
        config.ffmpeg_path,
        "-y",
        "-ss", str(start_time),
    ]

    if duration:
        cmd.extend(["-t", str(duration)])

    cmd.extend(["-i", str(input_path), "-c:v", "libx264", "-preset", "medium"])

    # 码率或 CRF（二选一）
    if params and params.video_bitrate:
        cmd.extend(["-b:v", params.video_bitrate])
    else:
        cmd.extend(["-crf", str(quality)])

    # 分辨率缩放
    if params and params.width and params.height:
        cmd.extend(["-vf", f"scale={params.width}:{params.height}"])

    # 帧率
    if params and params.fps:
        cmd.extend(["-r", str(params.fps)])

    audio_bitrate = params.audio_bitrate if params else "128k"
    cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate, str(output_path)])

    logger.info(f"执行命令: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        universal_newlines=True,
    )

    duration_total = None
    if progress_callback:
        try:
            info = get_video_info(input_path)
            duration_total = info.get("duration", 0)
        except Exception:
            pass

    def monitor_progress():
        while process.poll() is None:
            if cancel_event and cancel_event.is_set():
                process.terminate()
                return
            line = process.stderr.readline()
            if "time=" in line and progress_callback:
                try:
                    time_str = line.split("time=")[1].split()[0]
                    parts = time_str.split(":")
                    current_time = 0.0
                    for p in parts:
                        current_time = current_time * 60 + float(p)
                    if duration_total and duration_total > 0:
                        progress = min(int(current_time / duration_total * 100), 100)
                        progress_callback(progress)
                except Exception:
                    pass

    monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
    monitor_thread.start()

    _, stderr = process.communicate()

    if cancel_event and cancel_event.is_set():
        return   # 已取消，不报错

    if process.returncode != 0:
        logger.error(f"ffmpeg 错误: {stderr}")
        raise ExportError(f"视频切分失败: {stderr[:200]}")

    if progress_callback:
        progress_callback(100)


def concat_videos(
    input_paths: List[Path],
    output_path: Path,
    quality: int = 23,
    progress_callback: Optional[Callable[[float], None]] = None
) -> None:
    """拼接多个视频

    Args:
        input_paths: 输入文件路径列表
        output_path: 输出文件路径
        quality: 质量 (crf 值)
        progress_callback: 进度回调函数 (0-100)
    """
    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    if len(input_paths) == 0:
        raise ExportError("没有输入文件")

    list_file = None

    if len(input_paths) == 1:
        # 只有一个文件，直接复制
        cmd = [
            config.ffmpeg_path,
            "-y",
            "-i", str(input_paths[0]),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(quality),
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path)
        ]
    else:
        # 多个文件，需要使用 concat 滤镜
        # 创建临时文件列表
        list_file = output_path.parent / f"{output_path.stem}_concat_list.txt"
        with open(list_file, "w") as f:
            for path in input_paths:
                f.write(f"file '{path.absolute()}'\n")

        cmd = [
            config.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file.absolute()),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(quality),
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path.absolute())
        ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    _, stderr = process.communicate()

    if process.returncode != 0:
        logger.error(f"ffmpeg 错误: {stderr}")
        raise ExportError(f"视频拼接失败: {stderr[:200]}")

    if progress_callback:
        progress_callback(100)

    # 清理临时文件
    if list_file and list_file.exists():
        list_file.unlink()


def export_project(
    project,
    output_path: Path,
    quality: int = 23,
    progress_callback: Optional[Callable[[float], None]] = None,
    params=None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    """导出项目"""
    if not project.segments:
        raise ExportError("没有片段可导出")

    temp_dir = output_path.parent / ".temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        temp_files = []
        total_segments = len(project.segments)

        for i, segment in enumerate(project.segments):
            if cancel_event and cancel_event.is_set():
                return

            temp_file = temp_dir / f"segment_{i}_{segment.id}.mp4"
            logger.info(f"导出片段 {i+1}/{total_segments}: {segment}")

            split_video(
                segment.source_path,
                temp_file,
                segment.start_time,
                segment.end_time,
                quality,
                progress_callback=lambda p, i=i, total=total_segments: progress_callback(
                    (i * 100 + p) / total
                ) if progress_callback else None,
                params=params,
                cancel_event=cancel_event,
            )
            temp_files.append(temp_file)

        if cancel_event and cancel_event.is_set():
            return

        logger.info("拼接所有片段...")
        if progress_callback:
            progress_callback(95)

        concat_videos(temp_files, output_path, quality)

        if progress_callback:
            progress_callback(100)

        logger.info(f"导出完成: {output_path}")

    finally:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def generate_thumbnail(path: Path, output_path: Path, time: float = 0.0) -> Path:
    """提取视频指定时间点的帧作为缩略图 JPEG。

    若 output_path 已存在则直接返回（缓存）。
    """
    if output_path.exists():
        return output_path

    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        config.ffmpeg_path,
        "-y",
        "-ss", str(time),
        "-i", str(path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise ExportError(f"生成缩略图失败: {result.stderr[:200]}")
        return output_path
    except subprocess.TimeoutExpired:
        raise ExportError("生成缩略图超时")