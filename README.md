# Golden Lap 简体中文汉化

为 Golden Lap 增加简体中文界面：以简体中文顶替游戏的土耳其语语言选项，并让界面字体能显示中文。所有改动都在玩家本地完成，本仓库不含任何游戏原始资源。

## 开发

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

- 译文数据格式：[docs/translation-format.md](docs/translation-format.md)
- 校验译文：`PYTHONPATH=src .venv/bin/python -m glzh validate`
- 游戏更新后比对差异：`PYTHONPATH=src .venv/bin/python -m glzh diff [--write]`
- 构建到仓库外的目录（不改动游戏）：`PYTHONPATH=src .venv/bin/python -m glzh build <目录>`
- 术语见 [GLOSSARY.md](GLOSSARY.md)，架构决策见 [docs/adr](docs/adr)

## 许可

安装器与脚本：MIT（见 [LICENSE](LICENSE)）。译文：CC BY-NC-SA 4.0（见 [translations/LICENSE](translations/LICENSE)）。
