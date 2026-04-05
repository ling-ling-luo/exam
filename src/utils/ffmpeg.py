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


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用"""
    try:
        result = subprocess.run(
            [config.ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


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
                "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else None,
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
    progress_callback: Optional[Callable[[float], None]] = None
) -> None:
    """切分视频

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒），None 表示到视频末尾
        quality: 质量 (crf 值)
        progress_callback: 进度回调函数 (0-100)
    """
    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    duration = end_time - start_time if end_time else None

    cmd = [
        config.ffmpeg_path,
        "-y",  # 覆盖输出文件
        "-ss", str(start_time),
    ]

    if duration:
        cmd.extend(["-t", str(duration)])

    cmd.extend([
        "-i", str(input_path),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", str(quality),
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path)
    ])

    logger.info(f"执行命令: {' '.join(cmd)}")

    # 使用管道处理进度
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        universal_newlines=True
    )

    # 解析进度
    duration_total = None
    if progress_callback:
        # 从 ffprobe 获取总时长
        try:
            info = get_video_info(input_path)
            duration_total = info.get("duration", 0)
        except:
            pass

        # 启动进度监控线程
        def monitor_progress():
            while process.poll() is None:
                line = process.stderr.readline()
                if "time=" in line:
                    try:
                        # 解析时间
                        time_str = line.split("time=")[1].split()[0]
                        parts = time_str.split(":")
                        current_time = 0
                        for p in parts:
                            current_time = current_time * 60 + float(p)

                        # 计算进度
                        if duration_total and duration_total > 0:
                            progress = min(int(current_time / duration_total * 100), 100)
                            progress_callback(progress)
                    except:
                        pass

        monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
        monitor_thread.start()

    _, stderr = process.communicate()

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
    if list_file.exists():
        list_file.unlink()


def export_project(
    project,
    output_path: Path,
    quality: int = 23,
    progress_callback: Optional[Callable[[float], None]] = None
) -> None:
    """导出项目

    Args:
        project: Project 对象
        output_path: 输出文件路径
        quality: 质量 (crf 值)
        progress_callback: 进度回调函数 (0-100)
    """
    if not project.segments:
        raise ExportError("没有片段可导出")

    # 创建临时文件目录
    temp_dir = output_path.parent / ".temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        # 导出每个片段
        temp_files = []
        total_segments = len(project.segments)

        for i, segment in enumerate(project.segments):
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
                ) if progress_callback else None
            )

            temp_files.append(temp_file)

        # 拼接所有片段
        logger.info("拼接所有片段...")

        if progress_callback:
            progress_callback(95)

        concat_videos(temp_files, output_path, quality)

        if progress_callback:
            progress_callback(100)

        logger.info(f"导出完成: {output_path}")

    finally:
        # 清理临时文件
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)