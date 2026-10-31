"""命令行入口：

    python -m src.cli run                                  # 跑默认用例与配置
    python -m src.cli run --cases data/cases.jsonl --variants configs/models.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import run_all, save_json

ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def build_report(rows: list[dict], summary: dict, cases: list[dict]) -> str:
    names = list(summary)
    lines = ["# 评测报告", ""]

    lines += ["## 汇总", "",
              "| 变体 | 通过 | 通过率 | 平均耗时(s) | P50(s) | 平均输出 tokens | 错误 |",
              "|---|---|---|---|---|---|---|"]
    for name, s in summary.items():
        lines.append(f"| {name} | {s['passed']}/{s['cases']} | {s['pass_rate']:.1%} | "
                     f"{s['avg_latency']} | {s['p50_latency']} | {s['avg_tokens']} | {s['errors']} |")

    lines += ["", "## 逐题结果", "",
              "| 用例 | " + " | ".join(names) + " |",
              "|---" * (len(names) + 1) + "|"]
    for case in cases:
        cells = []
        for name in names:
            row = next((r for r in rows if r["variant"] == name and r["case_id"] == case["id"]), None)
            if row is None:
                cells.append("—")
            elif row.get("error"):
                cells.append("error")
            else:
                cells.append("✓" if row["passed"] else "✗")
        lines.append(f"| {case['id']} | " + " | ".join(cells) + " |")

    failures = [r for r in rows if not r["passed"] and not r.get("error")]
    if failures:
        lines += ["", "## 失败明细", ""]
        for r in failures:
            reasons = "；".join(f"{c['check']['type']}: {c['reason']}" for c in r["checks"] if not c["ok"])
            lines.append(f"- **{r['variant']} / {r['case_id']}** — {reasons}")
            lines.append(f"  - 问题：{r['prompt'][:60]}")
            lines.append(f"  - 回答：{r['answer'][:120]}")

    return "\n".join(lines) + "\n"


def cmd_run(args) -> None:
    cases = load_jsonl(Path(args.cases))
    variants = json.loads(Path(args.variants).read_text(encoding="utf-8"))
    if isinstance(variants, dict):
        variants = variants.get("variants", [])

    print(f"用例 {len(cases)} 条 × 变体 {len(variants)} 个 = {len(cases) * len(variants)} 次调用")
    rows, summary = run_all(variants, cases)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report(rows, summary, cases), encoding="utf-8")
    save_json(rows, summary, out.with_suffix(".json"))

    print("\n| 变体 | 通过率 | 平均耗时 |")
    print("|---|---|---|")
    for name, s in summary.items():
        print(f"| {name} | {s['pass_rate']:.1%} | {s['avg_latency']}s |")
    print(f"\n报告已写入 {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="LLM 评测小平台")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("run", help="跑评测")
    pr.add_argument("--cases", default=str(ROOT / "data" / "cases.jsonl"))
    pr.add_argument("--variants", default=str(ROOT / "configs" / "models.json"))
    pr.add_argument("--out", default=str(ROOT / "reports" / "report.md"))
    pr.set_defaults(func=cmd_run)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
