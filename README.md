# BuMusic

[![CI](https://github.com/hydraxman/BuMusic/actions/workflows/ci.yml/badge.svg)](https://github.com/hydraxman/BuMusic/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

BuMusic是一个离线的单声部人声转谱工具。它从无伴奏哼唱或唱名中提取音高、起止时间和置信度，输出可编辑的JSON、MusicXML、MIDI和SVG五线谱，并能把识别结果按原始时间反向合成为WAV，方便与原声A/B试听。

> 当前版本面向干净、单人、单声部录音。带伴奏歌曲、和声、合唱和复调转录不在0.2.0支持范围内。

## 能做什么

一条命令完成：

```text
WAV/FLAC/OGG（MP3/M4A取决于系统解码后端）
  -> Balanced pYIN音高检测 + 谱通量/RMS起音检测
  -> 平滑后的事件中位F0、音分、秒级起止时间
  -> notes.json
  -> original-timing MIDI
  -> reconstructed-original-timing.wav
  -> MusicXML
  -> SVG五线谱
```

核心特性：

- 默认使用经过真实试听对比的Balanced参数；
- 约5.8毫秒的音高时间分辨率；
- 在稳定同音run内部用强起音证据恢复重复音符；
- 保留pYIN平滑后每个事件的中位F0和相对十二平均律的音分偏差；
- 分离“原始秒时间”和“谱面量化时间”；
- original timing反向播放，避免BPM量化改变原始旋律轮廓；
- 完全离线，不上传录音；
- Linux/Python 3.12及macOS、Windows/Python 3.13自动测试和wheel构建。

## 快速开始

### 环境要求

- macOS、Linux或Windows（GitHub Actions持续验证三种系统）；
- Python 3.12或3.13；
- 建议使用虚拟环境，依赖不会写入仓库。

### 从源码安装

BuMusic提供不依赖Bash、Make或PowerShell脚本的统一Python任务入口。Windows PowerShell或CMD：

```powershell
git clone https://github.com/hydraxman/BuMusic.git
cd BuMusic
py -3.12 scripts/dev.py setup
```

macOS或Linux：

```bash
git clone https://github.com/hydraxman/BuMusic.git
cd BuMusic
python3 scripts/dev.py setup
```

也可以手动安装。macOS或Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[dev]'
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -e ".[dev]"
```

`.venv/`、构建目录和所有生成音频均已加入`.gitignore`，不会上传到GitHub。

## 使用方法

### 从人声生成完整结果

macOS或Linux：

```bash
.venv/bin/bumusic transcribe input.ogg --out bumusic-output --bpm 120
```

Windows PowerShell或CMD：

```powershell
.venv\Scripts\python -m bumusic.cli transcribe input.ogg --out bumusic-output --bpm 120
```

输出目录：

```text
bumusic-output/
├── notes.json                         # 识别事件、中位F0、音分和置信度
├── original-timing.mid                # 保留原始秒时间的MIDI
├── reconstructed-original-timing.wav  # 事件中位F0反向合成试听
├── score.musicxml                     # 按BPM量化的交换乐谱
└── score.svg                          # 五线谱预览
```

建议先听`reconstructed-original-timing.wav`，确认音高轮廓，再判断BPM和谱面量化是否合理。

### 单独反向播放notes.json

默认`basic`音色。macOS或Linux：

```bash
.venv/bin/bumusic synthesize \
  bumusic-output/notes.json \
  --output reconstructed.wav
```

Windows PowerShell：

```powershell
.venv\Scripts\python -m bumusic.cli synthesize `
  bumusic-output\notes.json `
  --output reconstructed.wav
```

### 选择钢琴、小提琴或电吉他音色

内置音色均为确定性的离线程序合成，不需要下载采样库：

```bash
.venv/bin/bumusic transcribe input.wav \
  --out result \
  --instrument electric-guitar

.venv/bin/bumusic synthesize result/notes.json \
  --output piano.wav \
  --instrument piano
```

可选音色：

```text
basic
piano
violin
electric-guitar
```

这些音色用于快速试听和A/B验证，是轻量合成近似，不等同于专业SoundFont或商业采样库。

### 升降音高和对齐中央C

整体升高一个八度，同时保留原唱音分偏差：

```bash
.venv/bin/bumusic synthesize result/notes.json \
  --output octave-up.wav \
  --instrument piano \
  --transpose 12
```

将第一个音移到中央C（C4/MIDI 60），并吸附到十二平均律：

```bash
.venv/bin/bumusic synthesize result/notes.json \
  --output middle-c.wav \
  --instrument piano \
  --align-middle-c \
  --snap-to-equal-temperament
```

### 批量切换目标大调

下面把A大调旋律的第一个A音作为源主音，分别移动到C4、D4和G4；音程、节奏和original timing保持不变：

```bash
.venv/bin/bumusic synthesize result/notes.json \
  --output violin.wav \
  --instrument violin \
  --source-key A \
  --target-key C \
  --target-key D \
  --target-key G \
  --target-octave 4 \
  --snap-to-equal-temperament
```

输出：

```text
violin-c-major.wav
violin-d-major.wav
violin-g-major.wav
```

这里的“切换大调”是整体移调：如果输入旋律原本是大调，音程关系会保持为大调；BuMusic不会自动重写和声，也不会把任意小调旋律强制改造成大调。完整语义见[音色与转调说明](docs/INSTRUMENTS_AND_KEYS.md)。

### 查看版本

```bash
.venv/bin/bumusic --version
```

Windows：

```powershell
.venv\Scripts\python -m bumusic.cli --version
```

## 离线演示

演示脚本会合成`C4 D4 E4 F4 G4 A4 B4 C5`，然后运行完整转谱流程：

```bash
python3 scripts/dev.py demo
```

Windows使用`py -3.12 scripts/dev.py demo`。

结果写入`.demo/result/`。`.demo/`不会提交到Git。

## 固化的Balanced配置

默认参数位于`src/bumusic/config.py`，并由`tests/test_config.py`锁定：

| 参数 | 默认值 |
|---|---:|
| 重采样率 | 22050 Hz |
| pYIN hop length | 128 samples |
| voiced threshold | 0.35 |
| 基础run最短时长 | 约45 ms（沿用原帧网格） |
| 同音合并间隙 | 55 ms |
| 中值滤波 | 3 frames |
| 归一化起音局部增量 | 0.10 |
| 起音最小切分间隔 | 100 ms |
| 起音切分片段最短时长 | 至少45 ms（向上取整） |
| 起音RMS谷比例 | 50% |
| 静音裁剪 | 35 dB |
| 检测音域 | C2–C7 |

完整算法说明见[docs/ALGORITHM.md](docs/ALGORITHM.md)。

## 为什么保留original timing

人声录音没有可靠节拍、拍号和首个强拍时，无法唯一推导四分音符、八分音符和小节线。BuMusic同时保存：

1. `start_seconds/end_seconds`：模型实际听到的时间；
2. `duration_beats`：按用户BPM得到的谱面解释。

original timing是默认试听真值。MusicXML量化不会覆盖它。

## 项目结构

```text
BuMusic/
├── src/bumusic/
│   ├── cli.py             # 命令行入口
│   ├── config.py          # 固化的Balanced参数
│   ├── transcription.py   # pYIN与音符切分
│   ├── models.py          # NoteEvent数据模型
│   ├── pitch.py           # 半音转调、中央C和目标大调
│   ├── export.py          # JSON/MusicXML/MIDI/SVG
│   └── synthesis.py       # 多音色original timing反向合成
├── tests/                 # 参数、识别、导出、合成和CLI测试
├── scripts/
│   ├── dev.py             # Windows/macOS/Linux统一任务入口
│   ├── wheel_smoke.py     # 干净wheel安装与真实转录冒烟
│   ├── setup.sh           # 创建环境和安装依赖
│   ├── test.sh            # lint + tests
│   ├── build.sh           # 构建wheel并验证安装
│   ├── demo.sh            # 完整离线演示
│   └── generate_demo.py   # 合成测试音阶
├── docs/ALGORITHM.md
├── .github/workflows/ci.yml
├── pyproject.toml
├── MANIFEST.in
├── Makefile
└── LICENSE
```

## 测试与构建

统一任务入口支持Windows PowerShell、CMD、macOS和Linux：

| 任务 | Windows | macOS / Linux |
|---|---|---|
| 安装开发环境 | `py -3.12 scripts/dev.py setup` | `python3 scripts/dev.py setup` |
| lint + 测试 | `py -3.12 scripts/dev.py test` | `python3 scripts/dev.py test` |
| 构建wheel | `py -3.12 scripts/dev.py build` | `python3 scripts/dev.py build` |
| 离线演示 | `py -3.12 scripts/dev.py demo` | `python3 scripts/dev.py demo` |
| 清理产物 | `py -3.12 scripts/dev.py clean` | `python3 scripts/dev.py clean` |

`scripts/*.sh`只是macOS/Linux和Git Bash的便捷包装，不是Windows前置条件；它们内部也调用同一个`scripts/dev.py`。Windows不需要安装WSL、Git Bash或GNU Make。

在macOS或Linux上仍可运行原有质量门禁：

```bash
./scripts/test.sh
```

底层等价命令：

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/python -m pytest
```

构建wheel并重新安装验证：

```bash
python3 scripts/dev.py build
```

产物位于`dist/`：

```text
dist/bumusic-0.2.0-py3-none-any.whl
dist/bumusic-0.2.0.tar.gz
```

macOS/Linux或已安装GNU Make的环境仍可使用Make目标：

```bash
make setup
make lint
make test
make demo
make build
make clean
```

GitHub Actions会在Linux/Python 3.12及macOS、Windows/Python 3.13上执行安装、Ruff、pytest、wheel构建，并在各系统的原生默认shell中调用跨平台Python脚本，从干净wheel运行一次真实音阶转录。Windows任务不再借用Bash。

### 真人哼唱黄金回归集

`tests/fixtures/golden/`包含两段经录音者明确选择的原始哼唱及其静态Note JSON回归基线。测试会重新执行Balanced转录，并严格比较音符数量、MIDI/音名序列和谱面时值；Hz、音分、置信度及相对时间使用小范围容差。回归基线用于保护用户选定的产品行为，不声称是逐音人工标注的音乐学绝对真值。

本地单独运行：

```bash
.venv/bin/python -m pytest -m golden
```

GitHub Actions在每个操作系统/Python矩阵中将其显示为独立的`Golden humming regression`步骤；任一录音不匹配都会阻止PR通过。

回归基线不会在测试期间自动生成或更新。算法变化导致失败时，必须先试听和审查；只有录音者明确认可新输出后，才能更新基线。完整规则见[`tests/fixtures/golden/README.md`](tests/fixtures/golden/README.md)。

## Python API

```python
from bumusic.export import export_all
from bumusic.synthesis import synthesize_original_timing
from bumusic.transcription import transcribe_audio

notes = transcribe_audio("voice.ogg", bpm=120)
export_all(notes, "result", bpm=120)
synthesize_original_timing(notes, "result/reconstructed.wav")
```

`NoteEvent`包含：

```text
midi, name, pitch_hz, cents_offset,
start_seconds, end_seconds,
duration_beats, confidence
```

## 已知限制

- 普通说话、辅音、明显滑音和强颤音可能产生短碎音；
- 同音重复可在谱通量起音足够清晰、局部RMS至少回落50%、且两侧都至少持续100毫秒时切开；更弱或更短的同音重复仍可能被合并；
- 当前五线谱固定使用高音谱号、4/4拍和C大调；
- 当前不自动推断BPM、拍号、调号或弱起；
- MIDI使用整数半音，JSON和反向WAV保留pYIN平滑后的事件中位F0；
- WAV、FLAC和OGG是推荐输入；MP3/M4A能否读取取决于平台上的libsndfile或其他解码后端；
- 录音过短、过轻、混响严重或含伴奏时准确率会下降。

## 路线图

- Basic Pitch音符候选与pYIN连续F0双通道；
- speech-vs-melody输入质量判断；
- 钢琴卷帘、F0曲线和五线谱联动编辑；
- BPM、拍号、首拍和量化网格确认；
- 音符合并、拆分、拖动和低置信度高亮；
- MuseScore高质量PDF导出。

## 隐私

BuMusic默认完全离线运行。CLI不会上传音频，也不包含遥测、账号或网络请求。请勿把包含隐私的人声样本提交到公共仓库。

## 许可证

[MIT License](LICENSE)
