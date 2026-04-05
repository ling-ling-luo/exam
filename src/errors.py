"""自定义异常模块"""


class VideoClipError(Exception):
    """基础异常类"""
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class FileNotFoundError(VideoClipError):
    """文件不存在"""
    def __init__(self, path: str):
        super().__init__(f"文件不存在: {path}", "FILE_NOT_FOUND")
        self.path = path


class UnsupportedFormatError(VideoClipError):
    """不支持的格式"""
    def __init__(self, format_name: str):
        super().__init__(f"不支持的格式: {format_name}", "UNSUPPORTED_FORMAT")
        self.format = format_name


class InvalidTimeCodeError(VideoClipError):
    """无效的时间码"""
    def __init__(self, time_code: str):
        super().__init__(f"无效的时间码: {time_code}", "INVALID_TIME_CODE")
        self.time_code = time_code


class ExportError(VideoClipError):
    """导出失败"""
    def __init__(self, reason: str):
        super().__init__(f"导出失败: {reason}", "EXPORT_ERROR")
        self.reason = reason


class ValidationError(VideoClipError):
    """验证失败"""
    def __init__(self, message: str, field: str = ""):
        super().__init__(f"验证失败: {message}", "VALIDATION_ERROR")
        self.field = field


class FFmpegNotFoundError(VideoClipError):
    """ffmpeg 未找到"""
    def __init__(self):
        super().__init__("未找到 ffmpeg，请确保已安装", "FFMPEG_NOT_FOUND")