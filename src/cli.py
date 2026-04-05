"""命令行入口"""
import sys
from pathlib import Path

import click

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger, logger
from src.utils.config import config
from src.errors import VideoClipError


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
@click.option("--video-dir", type=click.Path(exists=True), help="视频资源目录")
@click.option("--output-dir", type=click.Path(), help="输出目录")
@click.pass_context
def cli(ctx, verbose, video_dir, output_dir):
    """命令行视频剪辑工具"""
    # 配置日志
    import logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logger(level=log_level)

    # 配置
    if video_dir:
        config.video_dir = Path(video_dir)
    if output_dir:
        config.output_dir = Path(output_dir)

    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@cli.command()
def tui():
    """启动 TUI 交互界面"""
    from src.tui.app import run_app

    try:
        run_app(config.video_dir)
    except VideoClipError as e:
        logger.error(f"错误: {e.message}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("已退出")
        sys.exit(0)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--start", "-s", default="0", help="入点时间 (秒或 HH:MM:SS)")
@click.option("--end", "-e", help="出点时间 (秒或 HH:MM:SS)")
@click.option("--output", "-o", help="输出文件路径")
@click.option("--quality", "-q", default=23, type=int, help="导出质量 (CRF, 0-51)")
def split(input_file, start, end, output, quality):
    """切分单个视频"""
    from src.core.executor import Executor
    from src.core.segment import Segment
    from src.core.validator import parse_time_code

    executor = Executor()
    input_path = Path(input_file)

    try:
        # 解析时间
        start_time = parse_time_code(start)
        end_time = parse_time_code(end) if end else None

        # 获取媒体信息
        info = executor.get_media_info(input_path)
        duration = info.get("duration", 0)

        if end_time is None:
            end_time = duration

        logger.info(f"视频: {input_path.name}")
        logger.info(f"时长: {duration:.2f}秒")
        logger.info(f"切分: {start_time:.2f}s -> {end_time:.2f}s")

        # 创建片段
        segment = Segment(
            source_path=input_path,
            start_time=start_time,
            end_time=end_time
        )

        # 创建项目并导出
        from src.core.project import Project
        project = Project()
        project.add_segment(segment)

        if not output:
            output = f"output_{segment.id}.mp4"

        output_path = Path(output)
        config.output_dir.mkdir(exist_ok=True)

        def progress(p):
            print(f"\r导出进度: {p}%", end="", flush=True)

        executor.export(project, output_path, quality, progress)
        print()  # 换行
        logger.info(f"导出完成: {output_path}")

    except VideoClipError as e:
        logger.error(f"错误: {e.message}")
        sys.exit(1)


@cli.command()
@click.argument("input_files", nargs=-1, type=click.Path(exists=True))
@click.option("--output", "-o", default="output.mp4", help="输出文件路径")
@click.option("--quality", "-q", default=23, type=int, help="导出质量 (CRF, 0-51)")
def concat(input_files, output, quality):
    """拼接多个视频"""
    from src.core.executor import Executor
    from src.core.segment import Segment
    from src.core.project import Project

    if not input_files:
        click.echo("错误: 请至少提供一个输入文件")
        sys.exit(1)

    executor = Executor()
    project = Project()

    for i, input_file in enumerate(input_files):
        try:
            info = executor.get_media_info(Path(input_file))
            segment = Segment(
                source_path=Path(input_file),
                start_time=0,
                end_time=info.get("duration"),
                name=Path(input_file).name
            )
            project.add_segment(segment)
            logger.info(f"添加片段 {i+1}: {input_file}")
        except VideoClipError as e:
            logger.error(f"处理 {input_file} 失败: {e.message}")
            continue

    if not project.segments:
        logger.error("没有有效的片段")
        sys.exit(1)

    output_path = Path(output)
    config.output_dir.mkdir(exist_ok=True)

    def progress(p):
        print(f"\r导出进度: {p}%", end="", flush=True)

    executor.export(project, output_path, quality, progress)
    print()
    logger.info(f"导出完成: {output_path}")


@cli.command()
def check():
    """检查系统依赖"""
    from src.utils.ffmpeg import check_ffmpeg

    click.echo("检查系统依赖...")

    if check_ffmpeg():
        click.echo("✅ ffmpeg 已安装")
    else:
        click.echo("❌ ffmpeg 未安装或不在 PATH 中")
        sys.exit(1)

    click.echo(f"视频目录: {config.video_dir}")
    click.echo(f"输出目录: {config.output_dir}")


if __name__ == "__main__":
    cli(obj={})