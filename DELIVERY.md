# 命令行视频剪辑工具 - 交付文档

## 1. 源码与启动命令

### 项目结构
```
exam/
├── run.sh                    # 启动脚本（主入口）
├── run.py                    # Python 应用入口
├── src/
│   ├── cli.py               # 命令行接口定义
│   ├── core/                # 核心业务逻辑
│   │   ├── executor.py      # ffmpeg 执行引擎
│   │   ├── project.py       # 项目与片段管理
│   │   ├── segment.py       # 时间段片段类
│   │   ├── task_queue.py    # 导出任务队列
│   │   ├── export_params.py # 导出预设配置
│   │   └── validator.py     # 时间码验证
│   ├── tui/                 # TUI 交互界面（Textual 框架）
│   │   ├── app.py           # 应用主类
│   │   ├── screens/         # 各个屏幕
│   │   │   ├── media_list.py     # 媒体列表
│   │   │   ├── editor.py         # 片段编辑（入出点）
│   │   │   ├── timeline.py       # 时间线管理
│   │   │   ├── export.py         # 导出设置
│   │   │   └── task_queue.py     # 任务队列显示
│   │   └── style.tcss       # Textual 样式
│   └── utils/               # 工具模块
│       ├── config.py        # 配置管理
│       ├── ffmpeg.py        # ffmpeg 工具类
│       └── logger.py        # 日志系统
├── video_res/               # 视频素材目录
├── output/                  # 导出输出目录
├── requirements.txt         # Python 依赖
└── DELIVERY.md              # 本文件

```

### 依赖安装

**系统依赖：**
- Python 3.8+
- ffmpeg 及 ffprobe（用于视频处理）
- xdg-open（Linux 环境下用于查看缩略图）

**Python 依赖：**
```bash
pip install -r requirements.txt
```

主要包：
- `rich` - 终端美化输出
- `textual` - TUI 框架
- `click` - 命令行参数解析

### 启动方式

#### 启动 TUI 交互界面
```bash
./run.sh
```
首次运行会自动检查并安装依赖。

#### 检查系统依赖
```bash
./run.sh check
```
验证 ffmpeg 和 ffprobe 是否正确安装。

#### 命令行模式

**切分视频：**
```bash
./run.sh split <input_file> --start <time> --end <time> [--output <file>] [--quality <crf>]
```

**拼接视频：**
```bash
./run.sh concat <file1> <file2> ... [--output <file>] [--quality <crf>]
```

---

## 2. 使用说明（关键操作与参数）

### TUI 模式操作流程

#### 屏幕 1: 媒体列表（MediaListScreen）
应用启动后进入媒体列表，显示 `video_res/` 目录中的所有支持格式视频。

**可用操作：**
- **上/下方向键** - 在列表中导航
- **Enter** - 选择文件，进入编辑器
- **T** - 跳转到时间线（管理已添加的片段）
- **E** - 跳转到导出屏幕
- **Q** - 跳转到任务队列查看导出进度
- **Q（全局）** - 退出应用

**支持的格式：** mp4, avi, mov, flv, mkv, webm

#### 屏幕 2: 片段编辑器（EditorScreen）
选择视频文件后进入编辑器，用于设置入点（start）和出点（end）。

**关键参数：**
- **入点（Start）** - 片段开始时间，支持两种格式：
  - 秒数格式：`5`、`10.5`
  - 时间码格式：`00:00:05`、`01:23:45`
- **出点（End）** - 片段结束时间，格式同上
  - 默认为视频总长度（不填则使用全部）

**可用操作：**
- **Enter** - 编辑当前字段
- **Tab/Shift+Tab** - 字段切换
- **Ctrl+C** - 返回上一屏
- **Enter（确认）** - 添加片段到时间线

**示例输入：**
- `Start: 0, End: 5` - 从开始切到第 5 秒
- `Start: 00:00:10, End: 00:00:20` - 从 10 秒切到 20 秒
- `Start: 5, End: (留空)` - 从第 5 秒切到视频末尾

#### 屏幕 3: 时间线（TimelineScreen）
显示已添加的所有片段，可调整顺序和删除。

**可用操作：**
- **上/下方向键** - 导航列表
- **Up/Down（在选中项时）** - 移动片段顺序
- **D** - 删除当前片段
- **Ctrl+C** - 返回媒体列表

#### 屏幕 4: 导出设置（ExportScreen）
配置导出参数并启动导出任务。

**关键参数：**

1. **预设（Preset）** - 快速选择分辨率和码率
   - `original` - 保留原始分辨率与码率
   - `480p` - 854×480，1500k 码率
   - `720p` - 1280×720，4000k 码率
   - `1080p` - 1920×1080，8000k 码率
   - `custom` - 自定义分辨率和码率

2. **质量（CRF）** - 视频质量控制（仅在预设为 `original` 时有效）
   - 范围：0-51（0 = 无损，23 = 默认，51 = 最低）
   - 推荐值：18-28

3. **输出路径** - 默认为 `output/` 目录

**可用操作：**
- **↑/↓** - 修改预设
- **Enter** - 确认并添加到任务队列
- **Ctrl+C** - 返回媒体列表

#### 屏幕 5: 任务队列（TaskQueueScreen）
显示后台导出任务的进度和状态。

**可用操作：**
- **上/下方向键** - 导航任务列表
- **C** - 取消选中的任务（仅限进行中的任务）
- **Ctrl+C** - 返回媒体列表

**任务状态：**
- `Pending` - 等待中
- `In Progress` - 正在处理（显示进度百分比）
- `Completed` - 已完成
- `Failed` - 失败（点击查看错误信息）
- `Cancelled` - 已取消

---

### CLI 模式命令详解

#### 1. 检查依赖
```bash
./run.sh check
```

**预期输出：**
```
检查系统依赖...
✅ ffmpeg 已安装
视频目录: /home/user/exam/video_res
输出目录: /home/user/exam/output
```

#### 2. 切分单个视频
```bash
./run.sh split <input_file> [options]
```

**必选参数：**
- `<input_file>` - 输入视频路径

**可选参数：**
- `--start, -s <time>` - 入点（秒或 HH:MM:SS），默认 0
- `--end, -e <time>` - 出点（秒或 HH:MM:SS），默认为视频末尾
- `--output, -o <path>` - 输出文件路径，默认 `output_<id>.mp4`
- `--quality, -q <crf>` - 导出质量，默认 23

**时间格式示例：**
- 秒数：`5`、`10.5`、`125`
- 时间码：`00:00:05`、`00:01:30`、`01:23:45`

#### 3. 拼接多个视频
```bash
./run.sh concat <file1> <file2> [<file3> ...] [options]
```

**必选参数：**
- `<file1> <file2> ...` - 至少 2 个输入文件（按列出顺序拼接）

**可选参数：**
- `--output, -o <path>` - 输出文件路径，默认 `output.mp4`
- `--quality, -q <crf>` - 导出质量，默认 23

---

## 3. 示例输入与输出结果

### 可用素材
```
video_res/
├── bun33s.mp4              # 33 秒，MP4 格式
├── bun33s.flv              # 33 秒，FLV 格式
├── Big_Buck_Bunny_360_10s_28MB.mp4  # 10 秒，MP4 格式（低分辨率）
├── sample_1280x720_surfing_with_audio.flv  # 720p 高清，带音频
└── video-to-gif-sample.gif # GIF 格式（不支持）
```

### 示例 1: 切分单个视频（前 5 秒）

**命令：**
```bash
./run.sh split video_res/bun33s.mp4 --start 0 --end 5 --output output/clip_5s.mp4 --quality 23
```

**预期输出：**
```
启动 TUI 交互界面...
视频: bun33s.mp4
时长: 33.00秒
切分: 0.00s -> 5.00s
导出进度: 0%
导出进度: 25%
导出进度: 50%
导出进度: 75%
导出进度: 100%
导出完成: output/clip_5s.mp4
```

**验证结果：**
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output/clip_5s.mp4
# 输出: 5.024（约 5 秒）
```

### 示例 2: 拼接多格式视频（MP4 + FLV）

**命令：**
```bash
./run.sh concat video_res/bun33s.mp4 video_res/bun33s.flv --output output/concat_mixed.mp4 --quality 23
```

**预期输出：**
```
启动 TUI 交互界面...
添加片段 1: video_res/bun33s.mp4
添加片段 2: video_res/bun33s.flv
导出进度: 0%
导出进度: 33%
导出进度: 66%
导出进度: 100%
导出完成: output/concat_mixed.mp4
```

**验证结果：**
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output/concat_mixed.mp4
# 输出: 66.048（约 33 + 33 秒）
```

### 示例 3: 高清视频 720p 导出

**命令：**
```bash
./run.sh split video_res/sample_1280x720_surfing_with_audio.flv --start 0 --end 10 --output output/sample_720p.mp4 --quality 20
```

**预期输出：**
```
视频: sample_1280x720_surfing_with_audio.flv
时长: (总时长)秒
切分: 0.00s -> 10.00s
导出进度: 100%
导出完成: output/sample_720p.mp4
```

**输出文件验证：**
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_type output/sample_720p.mp4
# codec_type=video
# width=1280
# height=720
```

### 示例 4: 异常情况 - 不支持格式（GIF）

**命令：**
```bash
./run.sh split video_res/video-to-gif-sample.gif --start 0 --end 5
```

**预期输出：**
```
错误: 不支持的格式: gif
请使用支持的格式: mp4, avi, mov, flv, mkv, webm
```

**说明：** GIF 被排除在支持格式列表外，应用会拒绝处理并给出清晰的错误提示。

### 示例 5: 异常情况 - 无效时间码

**命令：**
```bash
./run.sh split video_res/bun33s.mp4 --start 99:99:99
```

**预期输出：**
```
错误: 无效的时间码格式: 99:99:99
请使用格式: 秒数 (如 5, 10.5) 或 HH:MM:SS (如 00:01:30)
```

### 示例 6: 异常情况 - 文件不存在

**命令：**
```bash
./run.sh split video_res/nonexistent.mp4
```

**预期输出：**
```
错误: 输入文件不存在: video_res/nonexistent.mp4
```

---

## 4. 验证说明

### 场景 1: 基础功能正确性

**目标：** 验证切分、拼接、导出的核心功能正常工作。

#### 1.1 单视频切分
```bash
./run.sh split video_res/bun33s.mp4 --start 0 --end 10 --output output/test_split.mp4
```

**预期结果：**
- 文件成功输出到 `output/test_split.mp4`
- 文件时长约为 10 秒
- 文件可在媒体播放器中正常播放

**验证命令：**
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output/test_split.mp4
# 预期输出: ~10.0
```

#### 1.2 多视频拼接
```bash
./run.sh concat video_res/Big_Buck_Bunny_360_10s_28MB.mp4 video_res/Big_Buck_Bunny_360_10s_28MB.mp4 --output output/test_concat.mp4
```

**预期结果：**
- 文件成功输出
- 文件时长约为 20 秒（两个 10 秒视频）
- 无音画不同步现象

**验证命令：**
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output/test_concat.mp4
# 预期输出: ~20.0
```

### 场景 2: 异构输入兼容性

**目标：** 验证 MP4、FLV 等多格式视频的支持情况。

#### 2.1 MP4 格式处理
```bash
./run.sh split video_res/bun33s.mp4 --start 0 --end 5 --output output/test_mp4.mp4
```

**预期结果：** 导出成功，文件正常

#### 2.2 FLV 格式处理
```bash
./run.sh split video_res/bun33s.flv --start 0 --end 5 --output output/test_flv.mp4
```

**预期结果：** 导出成功，FLV 自动转换为 MP4

#### 2.3 混合格式拼接
```bash
./run.sh concat video_res/bun33s.mp4 video_res/bun33s.flv video_res/Big_Buck_Bunny_360_10s_28MB.mp4 --output output/test_mixed.mp4
```

**预期结果：**
- 成功添加所有 3 个片段
- 输出单一 MP4 文件
- 音视频同步正常

**验证命令：**
```bash
ffprobe -v error -select_streams v:0,a:0 -show_entries stream=codec_type,codec_name output/test_mixed.mp4
# 验证音视频流存在
```

### 场景 3: 异常输入鲁棒性

**目标：** 验证异常输入的处理和错误提示的清晰度。

#### 3.1 不支持的格式（GIF）
```bash
./run.sh split video_res/video-to-gif-sample.gif --start 0 --end 5
```

**预期结果：**
- 应用拒绝处理
- 输出清晰的错误消息（不是 ffmpeg 原始错误）
- 应用正常退出（不崩溃）

#### 3.2 无效的时间码
```bash
./run.sh split video_res/bun33s.mp4 --start 99:99:99 --end 100:00:00
```

**预期结果：**
- 验证失败，给出格式提示
- 应用正常退出

#### 3.3 不存在的输入文件
```bash
./run.sh split video_res/no_such_file.mp4
```

**预期结果：**
- 输出清晰的"文件不存在"错误
- 应用正常退出

#### 3.4 入点大于出点
```bash
./run.sh split video_res/bun33s.mp4 --start 10 --end 5
```

**预期结果：**
- 验证失败，提示入点不能大于出点
- 应用正常退出

### 场景 4: 连续执行稳定性

**目标：** 验证连续多个任务执行时的队列稳定性和资源管理。

#### 4.1 连续导出 3 个任务（CLI 模式）
```bash
# 任务 1
./run.sh split video_res/bun33s.mp4 --start 0 --end 5 --output output/task1.mp4 &

# 任务 2（等任务 1 完成）
sleep 10
./run.sh split video_res/bun33s.mp4 --start 10 --end 15 --output output/task2.mp4 &

# 任务 3（等任务 2 完成）
sleep 10
./run.sh concat output/task1.mp4 output/task2.mp4 --output output/task3_final.mp4

# 等待所有任务完成
wait
```

**预期结果：**
- 所有 3 个文件都成功生成
- 无内存泄漏（进程正常退出）
- 最终拼接结果时长约 10 秒（5 + 5）

**验证命令：**
```bash
ls -lh output/task*.mp4
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output/task3_final.mp4
```

#### 4.2 TUI 模式任务队列测试
```bash
./run.sh
```

**操作流程：**
1. 进入媒体列表，选择 `bun33s.mp4`
2. 在编辑器中设置 `Start: 0, End: 5`，添加片段
3. 返回媒体列表，再次选择 `bun33s.mp4`
4. 设置 `Start: 10, End: 15`，添加第二个片段
5. 进入时间线，验证 2 个片段已添加
6. 进入导出屏幕，选择预设 `720p`，导出
7. 打开任务队列查看导出进度

**预期结果：**
- 任务队列正确显示导出进度
- 导出完成后，输出文件出现在 `output/` 目录
- 可取消进行中的任务
- 应用响应流畅，无卡顿

---

## 5. 已知限制与优化方向

### 已知限制

#### 1. 预览功能
- **限制：** 仅支持生成缩略图预览，不支持实时视频播放
- **原因：** 集成播放器会增加依赖复杂度，目前采用轻量级方案
- **影响：** 无法在编辑时听音频、看视频内容，只能通过时间码参考

#### 2. 平台依赖
- **限制：** 缩略图查看依赖 `xdg-open`（Linux 专有）
- **原因：** 跨平台播放器集成复杂
- **影响：** macOS 和 Windows 上缩略图功能不可用

#### 3. 导出效率
- **限制：** 拼接时有双重编码，导致处理速度较慢
- **原因：** 
  - 第一步：切分时重新编码（split 命令）
  - 第二步：拼接时再次编码（concat 命令）
- **影响：** 处理大文件或多个片段时耗时较长，CPU 占用高

**具体场景：** 
```bash
# 这个流程会导致双重编码
./run.sh split input.mp4 --start 0 --end 10 --output temp.mp4
./run.sh concat temp.mp4 other.mp4 --output final.mp4
# temp.mp4 在 concat 时会被再次编码
```

#### 4. 音频支持
- **限制：** 仅支持有视频流的媒体，不支持纯音频格式
- **原因：** 工具定位为视频编辑，音频处理需要独立UI设计
- **影响：** MP3、WAV 等纯音频格式无法导入

#### 5. 格式限制
- **限制：** GIF 等非标准视频格式不支持
- **原因：** ffmpeg 对这些格式的处理有特殊要求
- **影响：** 需要用户预先将 GIF 转换为 MP4 或 FLV

#### 6. 任务队列持久化
- **限制：** 队列内容仅保存在内存中，应用关闭后丢失
- **原因：** 当前采用简单的内存队列实现
- **影响：** 无法在崩溃后恢复未完成的导出任务

---

### 优化方向

#### 优化 1: 避免双重编码（推荐优先级：高）
**方案：** 在 concat 阶段使用 `-c copy` 流复制模式

**实现：**
```bash
# 修改 src/core/executor.py 中的 concat 逻辑
# 从：
ffmpeg -i input1.mp4 -i input2.mp4 -c:v libx264 output.mp4
# 改为：
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
```

**优势：**
- 拼接速度快 10-20 倍（无需重新编码）
- CPU 占用大幅降低
- 质量无损（完全复制流）

**劣势：**
- 要求所有输入文件具有完全相同的编码参数（分辨率、编码器、码率等）
- 实现复杂度略高

#### 优化 2: 集成本地视频播放（推荐优先级：中）
**方案：** 集成 mpv 或 ffplay 进行实时预览

**实现：**
```python
# 在 EditorScreen 中添加"播放"按钮
import subprocess
subprocess.Popen(['mpv', str(video_path)])  # 使用 mpv
# 或
subprocess.Popen(['ffplay', str(video_path)])  # 使用 ffmpeg 内置播放器
```

**优势：**
- 用户可实时验证切分点
- 支持音频预听
- 提升用户体验

**劣势：**
- 新增依赖（mpv 或 ffplay）
- TUI 应用需要处理外部窗口的生命周期管理
- 可能影响应用响应性

#### 优化 3: 任务队列持久化（推荐优先级：低）
**方案：** 将任务队列定期保存至本地 JSON 或 SQLite 数据库

**实现：**
```python
# 在 src/core/task_queue.py 中添加
import json
from pathlib import Path

QUEUE_FILE = Path("output/.task_queue.json")

def save_queue(self):
    """持久化队列到文件"""
    tasks = [asdict(t) for t in self.tasks]
    QUEUE_FILE.write_text(json.dumps(tasks, indent=2))

def load_queue(self):
    """从文件恢复队列"""
    if QUEUE_FILE.exists():
        tasks_data = json.loads(QUEUE_FILE.read_text())
        self.tasks = [ExportTask(**t) for t in tasks_data]
```

**优势：**
- 应用崩溃后可恢复任务
- 支持长时间后台处理
- 便于调试和日志记录

**劣势：**
- 需要处理任务状态的持久化更新
- 依赖性增加（JSON 或数据库）

#### 优化 4: 跨平台缩略图支持（推荐优先级：低）
**方案：** 根据操作系统使用不同的查看器

**实现：**
```python
# 在 src/utils/ffmpeg.py 中修改
import platform

def show_thumbnail(thumb_path: Path):
    if platform.system() == "Linux":
        subprocess.Popen(['xdg-open', str(thumb_path)])
    elif platform.system() == "Darwin":  # macOS
        subprocess.Popen(['open', str(thumb_path)])
    elif platform.system() == "Windows":
        import os
        os.startfile(str(thumb_path))
```

**优势：**
- 所有平台用户都能查看缩略图
- 实现简单

**劣势：**
- 依赖系统命令，可能在某些环境不可用

---

## 总结

本工具实现了一个功能完整的命令行视频编辑解决方案，支持：
- ✅ 交互友好的 TUI 界面
- ✅ 强大的 CLI 命令行工具
- ✅ 多格式视频支持（MP4、FLV 等）
- ✅ 灵活的导出预设和自定义参数
- ✅ 后台任务队列管理
- ✅ 清晰的错误提示和异常处理

**建议的使用场景：**
1. **快速转码和转格式** - 使用 split/concat 命令快速处理
2. **批量视频处理** - 利用 CLI 和任务队列进行自动化
3. **交互式编辑** - 使用 TUI 进行实时预览和调整（需改进预览功能）

