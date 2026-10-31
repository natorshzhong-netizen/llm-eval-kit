"""断言检查：把「答得对不对」拆成可复现的机械判断。

刻意不用「让另一个模型打分」作为主要手段——模型评审本身不稳定，
同一份答案两次打分可能不同。这里优先用确定性检查：

  contains       答案必须包含某段文本
  not_contains   答案不得包含某段文本（防泄漏、防编造）
  regex          正则匹配
  json_keys      答案能解析成 JSON 且包含指定字段
  max_chars      长度上限（考「简洁回答」这类指令遵循）
  min_chars      长度下限
"""
from __future__ import annotations

import json
import re
from typing import Any


def _as_text(answer: str) -> str:
    return (answer or "").strip()


def run_check(answer: str, check: dict[str, Any]) -> tuple[bool, str]:
    kind = check.get("type")
    value = check.get("value")
    text = _as_text(answer)

    # 文本检查统一忽略大小写：答 "Machine learning" 和 "machine learning"
    # 在语义上没有区别，不该被判错。
    if kind == "contains":
        ok = str(value).lower() in text.lower()
        return ok, "" if ok else f"缺少「{value}」"

    if kind == "not_contains":
        ok = str(value).lower() not in text.lower()
        return ok, "" if ok else f"不应出现「{value}」"

    if kind == "regex":
        ok = re.search(str(value), text, re.IGNORECASE) is not None
        return ok, "" if ok else f"未匹配正则 {value}"

    if kind == "json_keys":
        try:
            body = text
            if body.startswith("```"):
                body = body.split("```")[1]
                body = body[4:] if body.lower().startswith("json") else body
            data = json.loads(body)
        except Exception:
            return False, "不是合法 JSON"
        missing = [k for k in value if k not in data]
        return (not missing), (f"缺字段 {missing}" if missing else "")

    if kind == "max_chars":
        ok = len(text) <= int(value)
        return ok, "" if ok else f"长度 {len(text)} 超过 {value}"

    if kind == "min_chars":
        ok = len(text) >= int(value)
        return ok, "" if ok else f"长度 {len(text)} 少于 {value}"

    return False, f"未知检查类型 {kind}"
