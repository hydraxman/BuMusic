# 算法说明

BuMusic 0.1.1面向无伴奏、单人、单声部的人声或哼唱。它不是带伴奏歌曲的复调自动扒谱器。

## 固化的Balanced参数

| 参数 | 数值 | 作用 |
|---|---:|---|
| 重采样率 | 22050 Hz | 控制CPU成本并覆盖人声F0范围 |
| pYIN hop | 128 samples | 约5.8 ms时间分辨率 |
| voiced threshold | 0.35 | 在漏音和假音之间取平衡 |
| 基础run最短时长 | 约45 ms | 沿用原Balanced帧网格，保持既有短音召回 |
| 同音合并间隙 | 55 ms | 修补短暂换气或F0掉线 |
| 中值滤波 | 3 frames | 平滑颤音和瞬时跳频 |
| 归一化起音局部增量 | 0.10 | 峰值相对局部均值的增量门槛 |
| 起音最小切分间隔 | 100 ms | 防止持续音、颤音和run边缘被过切 |
| 起音切分片段最短时长 | 至少45 ms | 使用向上取整，不让新片段低于配置下限 |
| 起音RMS谷比例 | 50% | 要求能量明显回落并在谷后恢复 |
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
  -> spectral-flux onset + local RMS-dip split inside stable same-pitch runs
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

## 同音重复切分

pYIN只描述连续F0，无法单独区分“一个持续A4”和“重新发声的两个A4”。BuMusic先完成原有stable-run与短gap合并，再在合并后的run内部检测谱通量起音峰。这样不会让新切出的同音片段被55毫秒gap规则重新合并。

谱通量候选阶段不做全局最小间隔抑制；所有局部峰先经过RMS谷验证，再由各自同音run按已接受边界执行100毫秒保护。这样，其他音高run的峰或随后被RMS拒绝的峰不会压掉合法重起音。

候选起音只有同时满足以下条件才成为边界：

1. 位于同一稳定半音run内部；
2. 与run边缘及上一个已接受边界至少相隔100毫秒；
3. 切分后两侧都不短于Balanced最短音符约束；
4. 归一化谱通量峰相对局部均值的增量达到0.10；
5. 候选附近的短窗RMS谷不高于谷前、谷后稳定能量较低值的50%。

run起点附近的初始发声峰、尾部释放峰、持续颤音造成的频谱移动和弱编码波动会被边界/RMS保护过滤。算法不改变pYIN音高、原始秒时间、事件中位F0、音分或置信度计算。

## 已知限制

- 颤音、滑音、气声和普通语音可能产生短候选音；
- 同音重复若没有足够强的谱通量起音和能量谷、或任一侧短于100毫秒，仍可能被合并；
- 当前MusicXML先按4/4和C大调输出，不自动推断拍号、调号或弱起；
- MIDI使用整数音高，`notes.json`和反向WAV保留事件区间内平滑F0的中位数与音分；
- 带伴奏、和声、合唱和多声部不在0.1.1支持范围内。
