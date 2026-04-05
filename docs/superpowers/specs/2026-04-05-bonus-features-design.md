# 加分项功能设计文档

**日期**: 2026-04-05  
**范围**: 时间线/片段预览、任务队列与取消、可配置导出参数

---

## 1. 背景

README 加分项要求实现三项功能，本文档描述其设计方案（方案 B：TaskQueueScreen 作中心枢纽）。

---

## 2. 数据模型

### 2.1 `ExportParams`（`src/core/export_params.py`）

导出参数，支持预设和手动覆盖。

```python
@dataclass
class ExportParams:
    preset: str = "original"
    video_bitrate: Optional[str] = None   # None = 由 CRF 控制
    audio_bitrate: str = "128k"
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None           # None = 保持源帧率

PRESETS = {
    "original": ExportParams(preset="original"),
    "480p":  ExportParams(preset="480p",  width=854,  height=480,  video_bitrate="1500k"),
    "720p":  ExportParams(preset="720p",  width=1280, height=720,  video_bitrate="4000k"),
    "1080p": ExportParams(preset="1080p", width=1920, height=1080, video_bitrate="8000k"),
}
```

### 2.2 `ExportTask`（`src/core/export_task.py`）

队列中的单个导出任务。

```python
@dataclass
class ExportTask:
    id: str                   # uuid[:8]
    project: Project          # 深拷贝快照，避免后续编辑污染
    output_path: Path
    quality: int
    params: ExportParams
    status: str = "pending"   # pending / running / done / failed / cancelled
    progress: float = 0.0
    error: Optional[str] = None
```

---

## 3. TaskQueue 引擎（`src/core/task_queue.py`）

单后台线程，顺序消费队列。

### 接口

| 方法 | 说明 |
|------|------|
| `add(task)` | 追加到队列末尾 |
| `cancel(task_id)` | pending → cancelled；running → 发送 cancel_event 终止 ffmpeg |
| `get_tasks()` | 返回任务列表快照（线程安全） |
| `start()` | 启动后台线程，app 初始化时调用 |
| `shutdown()` | 等待当前任务完成后退出，app 退出时调用 |

### 执行逻辑

1. 后台线程 `while not shutdown` 循环
2. 取第一个 `pending` 任务 → 置 `running` → 创建 `cancel_event`
3. 调 `executor.export(project, output_path, quality, params, progress_cb, cancel_event)`
4. 完成 → 置 `done`；异常 → 置 `failed`；cancel_event 触发 → 置 `cancelled`
5. 每次状态变更调 `on_task_updated(task)` 回调通知 UI

### 取消机制

- `cancel_event: threading.Event` 注入到 `split_video`
- 进度监控线程检查 `cancel_event.is_set()` → 调 `process.terminate()`
- ffmpeg 进程终止后，临时文件在 `finally` 块清理

---

## 4. ffmpeg.py 改动

### 4.1 `generate_thumbnail(path, output_path, time)`

```python
def generate_thumbnail(path: Path, output_path: Path, time: float = 0.0) -> Path:
    # ffmpeg -ss {time} -i {path} -vframes 1 -q:v 2 {output_path}
```

- 输出 JPEG，保存到 `.thumbnails/<filename>_<time>.jpg`
- 结果缓存：相同文件+时间点存在则直接返回

### 4.2 `split_video` / `concat_videos` 新增参数

```python
def split_video(..., params: ExportParams = None, cancel_event: threading.Event = None)
```

新增 ffmpeg 参数：
- `-vf scale={width}:{height}` — 分辨率（params.width/height 非 None 时）
- `-r {fps}` — 帧率（params.fps 非 None 时）
- `-b:v {video_bitrate}` — 码率（params.video_bitrate 非 None 时，此时不用 CRF）

---

## 5. UI 屏幕变更

### 5.1 `MediaListScreen`

- 每个文件旁加「🖼 预览」按钮
- 点击 → `generate_thumbnail(path, time=duration/2)` → `xdg-open` 打开
- 底部导航新增「📬 任务队列 (J)」按钮

### 5.2 `ExportScreen` → 配置并加入队列

新增字段：
- **预设选择**（original / 480p / 720p / 1080p / custom）
- **手动覆盖**（宽度、高度、视频码率、帧率）— 选 custom 时可编辑，其余预设时只读展示

按钮行为变更：
- 「开始导出」→「加入队列」
- 点击后将任务加入 `TaskQueue`，dismiss 回素材列表
- 不再阻塞 UI，后台自动处理

### 5.3 `TaskQueueScreen`（新文件）

DataTable 列：序号 / 输出文件 / 状态 / 进度 / 操作

- 每 500ms 通过 `set_interval` 刷新
- 「取消」按钮：pending/running 任务可用，done/cancelled/failed 不可用
- 状态颜色：pending=灰 / running=蓝 / done=绿 / failed=红 / cancelled=黄

### 5.4 `app.py`

- 持有 `TaskQueue` 单例
- `on_mount` → `task_queue.start()`
- `action_quit` → `task_queue.shutdown()`（不阻塞，直接退出）
- `_on_media_selected` 增加 `"queue"` 路由

---

## 6. 文件变更清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/core/export_params.py` | 新建 | ExportParams + PRESETS |
| `src/core/export_task.py` | 新建 | ExportTask dataclass |
| `src/core/task_queue.py` | 新建 | TaskQueue 引擎 |
| `src/tui/screens/task_queue.py` | 新建 | TaskQueueScreen |
| `src/utils/ffmpeg.py` | 修改 | generate_thumbnail, params 注入, cancel_event |
| `src/tui/screens/export.py` | 修改 | 预设选择, 加入队列逻辑 |
| `src/tui/screens/media_list.py` | 修改 | 缩略图预览按钮, 队列入口 |
| `src/tui/app.py` | 修改 | TaskQueue 单例, "queue" 路由 |
| `src/core/__init__.py` | 修改 | 导出新模块 |

---

## 7. 测试场景

| 场景 | 方法 |
|------|------|
| 缩略图生成 | 对 `bun33s.mp4` 生成中点缩略图，验证文件存在 |
| 缩略图缓存 | 连续点击两次，第二次不重新调用 ffmpeg |
| .gif 异常输入 | `video-to-gif-sample.gif` 点预览，应提示不支持 |
| 队列顺序执行 | 加入 3 个任务，验证按顺序完成 |
| 取消 pending | 加入 2 任务，取消第 2 个，验证第 1 个正常完成 |
| 取消 running | 取消正在运行的任务，验证 ffmpeg 进程终止、临时文件清理 |
| 预设参数 | 选 720p 导出，验证输出分辨率为 1280x720 |
| 手动覆盖 | custom 模式，指定 30fps，验证输出帧率 |
| 异构输入拼接 | mp4 + flv 加入队列导出，验证成功 |
