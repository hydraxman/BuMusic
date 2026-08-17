# 发布 BuMusic

正式发布使用`.github/workflows/publish.yml`。流水线会验证版本、执行完整测试、构建并
检查wheel/sdist、从干净环境运行wheel、发布TestPyPI、验证索引中的wheel，最后在
`pypi` GitHub Environment审批后发布正式PyPI。

TestPyPI和PyPI下载后的wheel必须与build job artifact的SHA256完全一致；同版本文件
已存在时发布会失败，不会跳过并继续验证旧文件。

## 一次性配置

1. 在仓库Settings > Environments创建`testpypi`和`pypi`；
2. 给`pypi`配置required reviewers；
3. 在TestPyPI创建项目`bumusic`的pending Trusted Publisher：
   - owner：`hydraxman`
   - repository：`BuMusic`
   - workflow：`publish.yml`
   - environment：`testpypi`
4. 在正式PyPI创建相同publisher，environment使用`pypi`。

发布不使用长期API token。workflow只在对应job中授予`id-token: write`。

## 发布步骤

1. 确认`pyproject.toml`中的版本是即将发布的PEP 440版本；
2. 确认main分支CI全部通过；
3. 创建GitHub Release，tag必须严格为`v<project.version>`，例如`v0.2.0`；
4. 发布Release；
5. 等待TestPyPI发布和smoke test通过；
6. 审批`pypi` Environment deployment；
7. 等待正式PyPI发布后smoke test通过。

本地可以预先执行：

```bash
python scripts/dev.py test
python scripts/dev.py build
python scripts/wheel_smoke.py
python scripts/release_version.py v0.2.0
```

同一版本不能覆盖上传。发布错误时应发布下一个patch；严重问题先在PyPI yank，
再发布修复版本。
