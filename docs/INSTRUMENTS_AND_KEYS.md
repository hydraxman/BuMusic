# 音色与转调

BuMusic 0.2.0在不改变original timing的前提下，支持内置合成音色、整体半音转调、中央C对齐和多目标大调批量试听。

## 内置音色

| 参数 | 合成特征 | 适用场景 |
|---|---|---|
| `basic` | 基频与二、三次谐波，短起音和释放 | 最中性的音高核对 |
| `piano` | 轻微非整数泛音、琴槌瞬态和指数衰减 | 离散旋律和音高确认 |
| `violin` | 丰富线性泛音和柔和弓弦包络 | 连续旋律试听 |
| `electric-guitar` | 拨弦瞬态、明亮谐波和指数衰减 | 节奏鲜明的旋律试听 |

这些音色是确定性的程序合成近似，不包含第三方采样，不等同于专业SoundFont、SFZ或商业采样库。它们的目标是离线、跨平台和零额外资产的快速A/B试听。

## 三种音高模式

### 手动半音转调

```bash
bumusic synthesize notes.json --transpose 12 --instrument piano
```

`12`表示升高一个八度，`-12`表示降低一个八度。所有音符使用相同的半音偏移，所以旋律音程保持不变。

### 对齐中央C

```bash
bumusic synthesize notes.json \
  --align-middle-c \
  --instrument piano
```

该选项将第一个NoteEvent移动到C4（MIDI 60），其他音符使用相同偏移量。它适合把低音或高音录音统一到便于比较的中央音区。

这里的“第一个音”指按`notes.json`顺序出现的第一个事件，不代表自动识别出来的主音。

### 源调到目标大调

```bash
bumusic synthesize notes.json \
  --source-key A \
  --target-key C \
  --target-key D \
  --target-octave 4 \
  --instrument violin
```

算法寻找事件中第一个音级为源主音的NoteEvent，并把它移动到目标主音和目标八度。例如A2到C4是升高15个半音；其他音符也升高15个半音。

`--target-key`可以重复，因此一次命令可以生成多个目标大调的WAV。支持升号、降号和Unicode符号，例如`C#`、`Db`、`F♯`、`B♭`。

“目标大调”表示整体移调，不表示重新作曲：

- 音程关系保持不变；
- original timing保持不变；
- 输入若原本是大调，移调后仍保持同样的大调结构；
- 不会自动把小调旋律改造成大调；
- 不会生成或重写和弦。

## 原唱音分与标准十二平均律

默认转调保留`pitch_hz`中的原唱音分偏差。例如原音比A4高20音分，升高一个八度后仍比A5高20音分。

加上：

```bash
--snap-to-equal-temperament
```

会把每个音吸附到整数MIDI对应的十二平均律频率，并将`cents_offset`设为0。该模式适合比较标准音高和使用钢琴音色。

## 参数互斥

为避免含糊结果：

- `--align-middle-c`不能与`--transpose`同时使用；
- `--target-key`必须同时提供`--source-key`；
- 目标大调模式不能与`--align-middle-c`或`--transpose`同时使用；
- 重复的等价目标调会返回错误，例如同时指定`C#`和`Db`。

## 数据保持原则

转调会生成新的不可变NoteEvent，不覆盖原始`notes.json`。以下字段保持不变：

```text
start_seconds
end_seconds
duration_beats
confidence
```

以下字段根据转调模式更新：

```text
midi
name
pitch_hz
cents_offset（仅吸附十二平均律时归零）
```

因此可以随时使用同一份原始识别结果，生成不同音色、不同音区和不同目标调的试听版本。

## 音高一致性与防混叠

读取`notes.json`时，BuMusic会验证`pitch_hz`是否与`midi + cents_offset`在0.5音分内一致。互相矛盾的数据会直接报错，不会出现“JSON显示C4、实际播放其他音高”的静默错误。

渲染时还会执行Nyquist保护：

- 事件基频必须低于采样率的一半；
- 超出Nyquist频率的高次泛音和拨弦/琴槌瞬态会被裁掉；
- 小提琴仅使用显式、可裁剪的线性泛音，不施加会产生无限边带的音高调制；
- 弦乐与吉他不使用会重新生成无限高次谐波的非线性失真；
- 多目标调会先验证全部目标，任一目标越界时不会留下部分输出文件。

提高音高或降低`--sample-rate`可能触发明确错误。常规试听建议保留默认44,100 Hz。
