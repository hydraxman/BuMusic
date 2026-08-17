# BuMusic PyPI 分发与 CLI 安装调研

调研日期：2026-08-17

## 结论

BuMusic 可以发布到 PyPI，并让用户通过 `pip` 或 `pipx` 安装后直接使用
`bumusic` CLI。当前工程已经具备大部分基础能力：

- 使用 `pyproject.toml` 和 `setuptools.build_meta` 构建；
- 使用 `src` layout；
- 通过 `[project.scripts]` 声明 `bumusic = "bumusic.cli:main"`；
- 能构建标准 wheel 和 sdist；
- 已有跨平台 CI，以及从干净虚拟环境安装 wheel 后执行真实转录的 smoke test。

本地实测已经构建：

- `bumusic-0.2.0-py3-none-any.whl`；
- `bumusic-0.2.0.tar.gz`。

wheel 被安装到全新临时虚拟环境后，`bumusic transcribe` 成功生成：

- `notes.json`；
- `score.musicxml`；
- `original-timing.mid`；
- `score.svg`；
- `reconstructed-original-timing.wav`。

因此，核心打包和 CLI 安装链路已经成立。正式发布前的主要工作不是重构核心算法，
而是补齐可信发布、版本一致性、发布后黑盒验证和支持范围说明。

## “self-contained”的准确边界

本项目建议把 “self-contained pip 安装” 定义为：

1. 在明确支持的操作系统、CPU 架构和 Python 版本中，用户只需执行
   `python -m pip install bumusic` 或 `pipx install bumusic`；
2. 不需要克隆源码；
3. 不需要本地 C、C++ 或 Fortran 编译器；
4. 不需要手动安装 libsndfile、OpenBLAS 或 Verovio；
5. 安装后可以直接运行 CLI，并生成 JSON、MIDI、MusicXML、SVG 和 WAV。

这不意味着 BuMusic 自己的 20 KB 左右 wheel 内嵌了所有 native library。实际模型是：

```text
BuMusic pure-Python wheel
  + pip dependency resolver
  + NumPy/SciPy/Numba/soxr/Verovio/SoundFile 的平台 wheel
  = 用户侧无需编译的完整运行环境
```

wheel 是 Python 的标准安装格式，兼容性由 Python、ABI 和平台标签表达：
[Binary distribution format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)。

不应承诺以下场景：

- 所有 CPU 架构和 Linux 发行版；
- 用户强制从 sdist 编译所有依赖；
- M4A/AAC 等所有音频编码；
- 没有对应依赖 wheel 的 Python 新版本；
- 完全离线安装，除非预先下载并提供完整 wheelhouse。

## 当前支持矩阵

项目声明 Python `>=3.12`，当前目标应明确为 CPython 3.12 和 3.13。

| 平台 | 结论 | 说明 |
|---|---|---|
| Windows x64 | 支持 | CPython 3.12/3.13 的依赖 wheel 可解析 |
| macOS x86_64 | 支持 | CPython 3.12/3.13 的依赖 wheel 可解析 |
| macOS arm64 | 支持 | CPython 3.12/3.13 的依赖 wheel 可解析 |
| glibc Linux x86_64 | 支持 | manylinux wheel 可解析 |
| glibc Linux aarch64 | 支持 | manylinux wheel 可解析 |
| Windows ARM64 | 暂不承诺 | Verovio 6.2.1 没有 win_arm64 wheel |
| Alpine/musl Linux | 暂不承诺 | Verovio 6.2.1 没有 musllinux wheel |

本次使用 `pip install --dry-run --only-binary=:all:` 对上述主流目标的 CPython
3.12/3.13 依赖进行了 wheel-only 解析，主流平台全部通过；Windows ARM64 和
musllinux 因 Verovio 无对应 wheel 而失败。该解析是发布前兼容性审计，仍应以各平台
原生 runner 的安装和端到端测试作为最终门禁。

当前 GitHub Actions 已在 Ubuntu/Python 3.12、macOS/Python 3.13 和
Windows/Python 3.13 上完成安装、测试、构建和 clean-wheel smoke：
[CI run 31930645549](https://github.com/hydraxman/BuMusic/actions/runs/31930645549)。
建议把矩阵扩展为三个系统均测试 Python 3.12 和 3.13。

## 依赖和 native runtime

| 依赖 | 打包结论 | 官方依据 |
|---|---|---|
| librosa 1.0.0 | pure-Python wheel，但会引入 NumPy、SciPy、Numba、scikit-learn、SoundFile、soxr 等 | [PyPI JSON](https://pypi.org/pypi/librosa/1.0.0/json) |
| NumPy | 主流 Windows、macOS、manylinux 的 CPython 3.12/3.13 wheel | [PyPI JSON](https://pypi.org/pypi/numpy/2.5.2/json) |
| SciPy | 主流 Windows、macOS、manylinux 的 CPython 3.12/3.13 wheel；二进制包可携带 OpenBLAS 等 runtime | [PyPI JSON](https://pypi.org/pypi/scipy/1.18.0/json) |
| SoundFile | 平台 wheel 可携带 libsndfile；源码安装或非常规平台可能要求系统 libsndfile | [SoundFile 安装说明](https://python-soundfile.readthedocs.io/en/latest/#installation)、[PyPI JSON](https://pypi.org/pypi/soundfile/0.14.0/json) |
| Verovio | 提供 Windows x64、macOS x86_64/arm64、manylinux x86_64/aarch64 的 CPython 3.12/3.13 wheel | [PyPI JSON](https://pypi.org/pypi/verovio/6.2.1/json) |

Verovio 自身说明其若干解析和压缩库为 embedded libraries：
[Verovio PyPI metadata](https://pypi.org/project/verovio/)。

### 音频格式边界

BuMusic 通过 `librosa.load()` 读取输入，而 librosa 的格式支持最终取决于
SoundFile/libsndfile：
[librosa audio I/O](https://librosa.org/doc/latest/ioformats.html)。

建议正式承诺：

- WAV；
- FLAC；
- OGG/Vorbis。

MP3 可以作为“依赖当前 libsndfile 能力的支持格式”，但应保留兼容性说明。
M4A/AAC 不应纳入 self-contained 承诺。libsndfile 的格式列表见
[Supported formats](https://libsndfile.github.io/libsndfile/formats.html)。

## 已具备的发布能力

### 标准项目元数据

`pyproject.toml` 已包含构建后端、项目名、版本、Python 约束、运行依赖和项目 URL。
`src` layout 可以避免开发时意外从源码目录导入未安装代码：
[src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)。

### CLI 入口

```toml
[project.scripts]
bumusic = "bumusic.cli:main"
```

安装器会根据 console-script entry point 生成平台对应的命令包装器：
[Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/)。

用户安装后可运行：

```bash
bumusic --version
bumusic transcribe input.wav --out bumusic-output --bpm 120
bumusic synthesize bumusic-output/notes.json --output reconstructed.wav
```

### wheel 内容

当前 wheel 只包含：

- `bumusic/*.py`；
- `LICENSE`；
- dist-info 元数据；
- `entry_points.txt`。

运行时不依赖仓库中的 `docs/`、`scripts/` 或 `tests/`，说明 wheel 的运行边界清晰。
当前 sdist 会额外包含 docs、scripts、tests 和 golden audio。它不影响 wheel 用户，
但发布前可以决定是否精简；如果保留，应继续确保真人音频具有明确公开授权。

## 发布前差距与风险

| 项目 | 等级 | 建议 |
|---|---:|---|
| 没有 TestPyPI/PyPI 发布 workflow | 高 | 新增基于 Trusted Publishing 的独立 workflow |
| 没有从 TestPyPI/PyPI 安装后的黑盒 smoke | 高 | 发布后从索引安装精确版本，再运行真实 CLI |
| 版本存在两个来源 | 高 | 消除 `pyproject.toml` 与 `__version__` 的漂移风险 |
| GitHub 最新 Release 是 v0.1.1，而包版本是 0.2.0 | 高 | 发布时校验 tag、项目元数据和 CLI 版本完全一致 |
| 当前 smoke 使用 checkout 中的 `generate_demo.py` | 中 | 发布后 smoke 应在临时目录独立生成 WAV |
| CI 矩阵未覆盖每个平台的 3.12/3.13 | 中 | 扩展为 3 OS × 2 Python |
| 音频格式承诺不够严格 | 中 | 明确 guaranteed 与 best-effort 格式 |
| Windows ARM64、Alpine 缺少依赖 wheel | 中 | 文档明确暂不支持，并持续监控 Verovio |
| sdist 包含 tests 和真人 golden audio | 低 | 根据分发需要决定是否精简 |

`bumusic` 在本次调研时访问正式 PyPI 和 TestPyPI JSON API 均返回 404，说明当时没有
可查询的同名项目，但名称只有在首次上传成功后才真正由发布者控制：

- `https://pypi.org/pypi/bumusic/json`
- `https://test.pypi.org/pypi/bumusic/json`

## 推荐发布架构

不要让三个操作系统各自构建并上传同名 `py3-none-any` wheel。推荐只构建一次，
测试矩阵下载并验证同一份 artifact，最终发布的也必须是这份已验证 artifact。

```text
tag vX.Y.Z
  |
  +-- validate-version
  |     tag == pyproject version == bumusic --version
  |
  +-- test-source
  |     lint + unit + golden tests
  |
  +-- build-once
  |     python -m build
  |     twine check --strict dist/*
  |     upload immutable artifact
  |
  +-- wheel-smoke matrix
  |     Windows/macOS/Linux × Python 3.12/3.13
  |     pip install --only-binary=:all: artifact
  |     real CLI transcription
  |
  +-- publish-testpypi
  |     OIDC Trusted Publishing
  |
  +-- smoke-testpypi
  |     install exact version from TestPyPI
  |
  +-- approve GitHub environment "pypi"
  |
  +-- publish-pypi
  |     publish the same artifact
  |
  +-- smoke-pypi
        install exact version from PyPI
        attach artifacts/hashes to GitHub Release
```

PyPI Trusted Publishing 使用 GitHub OIDC 换取短时令牌，不需要保存长期 API token：
[PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)。

官方发布指南要求发布 job 配置 `id-token: write`，并建议使用 GitHub Environment：
[Publishing package distribution releases using GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)。

`pypa/gh-action-pypi-publish` 还可以生成 PyPI digital attestations。GitHub Environment
应至少设置：

- `testpypi`；
- `pypi`；
- `pypi` required reviewers；
- tag-only 发布规则。

GitHub Environment 的保护规则见
[Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)。

## TestPyPI 到 PyPI

1. 在 TestPyPI 创建 pending Trusted Publisher；
2. 在 PyPI 创建 pending Trusted Publisher；
3. 两边都绑定仓库、workflow 文件和对应 GitHub Environment；
4. 构建并对 `dist/*` 执行 `twine check --strict`；
5. 上传到 TestPyPI；
6. 从 TestPyPI 下载 BuMusic 自身 artifact；
7. 让依赖只从正式 PyPI 安装；
8. 运行完整 CLI smoke；
9. 审批 `pypi` environment；
10. 上传同一份已验证 artifact 到正式 PyPI；
11. 从正式 PyPI 安装精确版本并再次 smoke。

TestPyPI 和正式 PyPI 是两个独立索引，TestPyPI 不一定拥有全部第三方依赖：
[Using TestPyPI](https://packaging.python.org/en/latest/guides/using-testpypi/)。

为了避免多索引解析带来的歧义，建议先从 TestPyPI 只下载 BuMusic、禁用依赖解析，
再从本地 wheel 安装并让依赖来自正式 PyPI，而不是长期依赖
`--extra-index-url`：

```bash
python -m pip download \
  --index-url https://test.pypi.org/simple/ \
  --no-deps "bumusic==0.2.0"
python -m pip install --only-binary=:all: ./bumusic-0.2.0-py3-none-any.whl
```

## 发布后端到端验证

发布后测试必须满足：

- 当前目录不在源码 checkout 中；
- 不设置 `PYTHONPATH`；
- 使用全新虚拟环境；
- 通过索引安装精确版本；
- 使用 `--only-binary=:all:`，确保支持矩阵不退化成本地编译；
- 使用 Python 标准库在临时目录生成短 WAV；
- 调用安装后生成的 `bumusic` 命令，而不是 `python src/...`；
- 验证 5 个输出文件存在且非空；
- 验证 JSON 音符序列和 MIDI/SVG/MusicXML 文件签名；
- Windows 使用 `.exe` launcher，POSIX 使用 shell command；
- 对索引同步采用有限次数、明确失败的重试，不静默跳过。

推荐矩阵：

| OS | Python | 架构 |
|---|---|---|
| Ubuntu latest | 3.12、3.13 | x86_64 |
| macOS latest | 3.12、3.13 | arm64 |
| Windows latest | 3.12、3.13 | x64 |

如果正式声明 macOS Intel 或 Linux aarch64，也应增加对应原生 runner，而不只依赖
跨平台 wheel 解析。

## 用户安装方式

### pip + venv

Windows：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install bumusic
.\.venv\Scripts\bumusic.exe --version
.\.venv\Scripts\bumusic.exe transcribe input.wav --out bumusic-output
```

macOS/Linux：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install bumusic
.venv/bin/bumusic --version
.venv/bin/bumusic transcribe input.wav --out bumusic-output
```

### pipx

CLI 用户优先推荐：

```bash
pipx install bumusic
bumusic --version
bumusic transcribe input.wav --out bumusic-output
```

pipx 会为 CLI 应用创建隔离虚拟环境，同时把命令暴露到 PATH：
[Installing stand-alone command line tools](https://packaging.python.org/en/latest/guides/installing-stand-alone-command-line-tools/)。

## 版本和回滚

- 版本必须符合 [PEP 440](https://packaging.python.org/en/latest/specifications/version-specifiers/)；
- tag `vX.Y.Z`、package metadata 和 `bumusic --version` 必须完全一致；
- PyPI 已上传的同名同版本文件不能覆盖；
- 普通修复发布下一个 patch，例如 `0.2.1`；
- 严重问题先 yank，再发布修复版；
- 不通过删除和重传模拟回滚。

PyPI yanked release 默认不会被一般依赖解析选中，但精确 pin 仍可能安装：
[Yanking](https://docs.pypi.org/project-management/yanking/)。

建议把版本改为单一来源。可选方案：

1. 以 `pyproject.toml` 为发布真值，运行时通过
   `importlib.metadata.version("bumusic")` 获取；
2. 或使用 setuptools dynamic version 从一个 Python 属性读取。

无论选择哪种，都应由 CI 校验 tag 和最终 wheel metadata。

## 建议实施顺序

1. 消除版本双写，并增加 tag/version 校验；
2. 扩展 CI 至三个系统的 Python 3.12/3.13；
3. 把 wheel smoke 改为完全独立于源码运行；
4. 增加 `twine check --strict` 和 artifact 内容检查；
5. 新增 TestPyPI/PyPI Trusted Publishing workflow；
6. 配置 `testpypi`、`pypi` GitHub Environments；
7. 配置两个 PyPI 索引的 pending Trusted Publisher；
8. 在 README 增加 pip、pipx 安装说明和明确支持矩阵；
9. 先发布 TestPyPI 并完成索引安装后的 E2E；
10. 打 `v0.2.0` tag，审批并发布正式 PyPI；
11. 从正式 PyPI 再次安装和验证；
12. 将相同 dist artifact、SHA256 和 release notes 附加到 GitHub Release。

完成前 8 项后，BuMusic 就具备可重复、可审计、对最终用户友好的 PyPI CLI 发布链路。
