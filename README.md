# BuMusic

[![CI](https://github.com/hydraxman/BuMusic/actions/workflows/ci.yml/badge.svg)](https://github.com/hydraxman/BuMusic/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

BuMusic是一个离线的单声部人声转谱工具。它从无伴奏哼唱或唱名中提取音高、起止时间和置信度，输出可编辑的JSON、MusicXML、MIDI和SVG五线谱，并能把识别结果按原始时间反向合成为WAV，方便与原声A/B试听。

> 当前版本面向干净、单人、单声部录音。带伴奏歌曲、和声、合唱和复调转录不在0.1.1支持范围内。

## 能做什么

一条命令完成：

```text
WAV/FLAC/OGG（MP3/M4A取决于系统解码后端）
  -> Balanced pYIN音高检测
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
- 保留pYIN平滑后每个事件的中位F0和相对十二平均律的音分偏差；
- 分离“原始秒时间”和“谱面量化时间”；
- original timing反向播放，避免BPM量化改变原始旋律轮廓；
- 完全离线，不上传录音；
- Linux、macOS、Windows上的Python 3.12/3.13自动测试和wheel构建。

## 快速开始

### 环境要求

- macOS、Linux或Windows（GitHub Actions持续验证三种系统）；
- Python 3.12或3.13；
- 建议使用虚拟环境，依赖不会写入仓库。

### 从源码安装

```bash
git clone https://github.com/hydraxman/BuMusic.git
cd BuMusic
./scripts/setup.sh
```

也可以手动安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[dev]'
```

Windows PowerShell对应命令：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -e ".[dev]"
```

`.venv/`、构建目录和所有生成音频均已加入`.gitignore`，不会上传到GitHub。

## 使用方法

### 从人声生成完整结果

```bash
.venv/bin/bumusic transcribe input.ogg --out bumusic-output --bpm 120
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

```bash
.venv/bin/bumusic synthesize \
  bumusic-output/notes.json \
  --output reconstructed.wav
```

### 查看版本

```bash
.venv/bin/bumusic --version
```

## 离线演示

演示脚本会合成`C4 D4 E4 F4 G4 A4 B4 C5`，然后运行完整转谱流程：

```bash
./scripts/demo.sh
```

结果写入`.demo/result/`。`.demo/`不会提交到Git。

## 固化的Balanced配置

默认参数位于`src/bumusic/config.py`，并由`tests/test_config.py`锁定：

| 参数 | 默认值 |
|---|---:|
| 重采样率 | 22050 Hz |
| pYIN hop length | 128 samples |
| voiced threshold | 0.35 |
| 最短音符 | 45 ms |
| 同音合并间隙 | 55 ms |
| 中值滤波 | 3 frames |
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
│   ├── export.py          # JSON/MusicXML/MIDI/SVG
│   └── synthesis.py       # original timing反向合成
├── tests/                 # 参数、识别、导出、合成和CLI测试
├── scripts/
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

运行质量门禁：

```bash
./scripts/test.sh
```

等价命令：

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/python -m pytest
```

构建wheel并重新安装验证：

```bash
./scripts/build.sh
```

产物位于`dist/`：

```text
dist/bumusic-0.1.1-py3-none-any.whl
dist/bumusic-0.1.1.tar.gz
```

常用Make目标：

```bash
make setup
make lint
make test
make demo
make build
make clean
```

GitHub Actions会在Linux、macOS和Windows的Python 3.12/3.13上执行安装、Ruff、pytest、wheel构建，并从干净wheel运行一次真实音阶转录。

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
- 同音重复但没有清晰起音时可能被合并；
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
