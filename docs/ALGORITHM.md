# 算法说明

BuMusic 0.2.0面向无伴奏、单人、单声部的人声或哼唱。它不是带伴奏歌曲的复调自动扒谱器。

## 固化的Balanced参数

| 参数 | 数值 | 作用 |
|---|---:|---|
| 重采样率 | 22050 Hz | 控制CPU成本并覆盖人声F0范围 |
| pYIN hop | 128 samples | 约5.8 ms时间分辨率 |
| voiced threshold | 0.35 | 在漏音和假音之间取平衡 |
| 最短音符 | 45 ms | 保留短音，同时抑制大部分抖动碎片 |
| 同音合并间隙 | 55 ms | 修补短暂换气或F0掉线 |
| 中值滤波 | 3 frames | 平滑颤音和瞬时跳频 |
| 静音裁剪 | 35 dB | 去除头尾静音 |
| 音域 | C2–C7 | 覆盖常见人声及哼唱 |

这些参数来自纯音、拟人声和真实短人声的反向试听对比。默认配置作为公开行为锁定在`tests/test_config.py`中；修改参数必须同步更新测试和版本说明。

## 数据流

```text
audio
  -> mono 22050 Hz
  -> silence trim
  -> pYIN F0 / voiced / probability
  -> MIDI-float interpolation + median smoothing
  -> stable semitone runs
  -> short-gap merge
  -> NoteEvent(original seconds, median smoothed F0, cents, confidence)
  -> notes.json
  -> original-timing MIDI and reconstructed WAV
  -> quantized MusicXML
  -> Verovio SVG
```

## 两条时间轴

- `start_seconds/end_seconds`是识别真值，用于默认试听和original-timing MIDI；
- `duration_beats`是根据用户BPM得到的可撤销量化解释，用于MusicXML。

BuMusic不会用量化结果覆盖原始时间。没有可靠BPM时，应先听original timing，再决定如何生成谱面。

## 已知限制

- 颤音、滑音、气声和普通语音可能产生短候选音；
- 同音重复但没有明显起音时可能被合并；
- 当前MusicXML先按4/4和C大调输出，不自动推断拍号、调号或弱起；
- MIDI使用整数音高，`notes.json`和反向WAV保留事件区间内平滑F0的中位数与音分；
- 带伴奏、和声、合唱和多声部不在0.2.0支持范围内。
