"""执行器：同一套用例跑多个模型/提示词变体，逐条记录结果与耗时。"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from statistics import median

import requests

from .checks import run_check
from .config import API_BASE, API_KEY, CONCURRENCY, TIMEOUT


def call_model(cfg: dict, prompt: str) -> tuple[str, float, int]:
    """返回 (回答, 耗时秒, 输出 token 数)。"""
    messages = []
    if cfg.get("system"):
        messages.append({"role": "system", "content": cfg["system"]})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg.get("temperature", 0),
        "max_tokens": cfg.get("max_tokens", 512),
    }
    t0 = time.time()
    r = requests.post(f"{API_BASE}/chat/completions", json=payload,
                      headers={"Authorization": f"Bearer {API_KEY}"}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    elapsed = time.time() - t0
    usage = data.get("usage") or {}
    return (data["choices"][0]["message"]["content"].strip(),
            round(elapsed, 2), int(usage.get("completion_tokens", 0)))


def run_one(cfg: dict, case: dict) -> dict:
    row = {"variant": cfg["name"], "case_id": case["id"], "prompt": case["prompt"],
           "checks": [], "passed": False, "answer": "", "latency": 0.0, "tokens": 0}
    try:
        answer, latency, tokens = call_model(cfg, case["prompt"])
        row.update(answer=answer, latency=latency, tokens=tokens)
    except Exception as e:
        row["error"] = str(e)[:200]
        return row

    results = []
    for check in case.get("checks", []):
        ok, reason = run_check(answer, check)
        results.append({"check": check, "ok": ok, "reason": reason})
    row["checks"] = results
    row["passed"] = all(c["ok"] for c in results) if results else True
    return row


def run_all(variants: list[dict], cases: list[dict]) -> tuple[list[dict], dict]:
    tasks = [(v, c) for v in variants for c in cases]
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        rows = list(pool.map(lambda t: run_one(*t), tasks))

    summary = {}
    for v in variants:
        rows_v = [r for r in rows if r["variant"] == v["name"]]
        good = [r for r in rows_v if "error" not in r]
        summary[v["name"]] = {
            "cases": len(rows_v),
            "passed": sum(r["passed"] for r in rows_v),
            "pass_rate": round(sum(r["passed"] for r in rows_v) / (len(rows_v) or 1), 3),
            "errors": len(rows_v) - len(good),
            "avg_latency": round(sum(r["latency"] for r in good) / (len(good) or 1), 2),
            "p50_latency": round(median([r["latency"] for r in good]), 2) if good else 0,
            "avg_tokens": round(sum(r["tokens"] for r in good) / (len(good) or 1), 1) if good else 0,
        }
    return rows, summary


def save_json(rows: list[dict], summary: dict, path) -> None:
    path.write_text(json.dumps({"summary": summary, "rows": rows},
                               ensure_ascii=False, indent=2), encoding="utf-8")
