# 译文数据格式

译文按字符串表分三份 JSON 存于 `translations/zh-Hans/`：`Content.json`、`Menus.json`、`Events.json`。

每份是一个对象，键为翻译条目的 `m_Id`（数字，写成字符串），值为：

| 字段 | 含义 |
| --- | --- |
| `en_hash` | 英文原文的哈希：UTF-8 的 sha256 取前 16 位十六进制。仓库不存英文原文本身，原文在构建时从玩家本地游戏文件提取。 |
| `zh` | 简体中文译文。占位符（如 `{otherDriver}`）、富文本标签（如 `<b>`）与换行须原样保留。 |
| `status` | 校对状态：`mt` 机翻、`ok` 已校对、`stale` 英文原文已变、待复核。 |

示例：

```json
{
  "248174071668736": {
    "en_hash": "…",
    "zh": "生涯",
    "status": "ok"
  }
}
```

文件按 `m_Id` 数值升序写出，便于审阅差异。校验：`python -m glzh validate`。
