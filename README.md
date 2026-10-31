# LLM Eval Kit · 提示词/模型对比评测

用一套固定用例，把多个提示词或模型跑一遍，输出**通过率、耗时、输出 token** 的对比报告。

> 解决一个很具体的问题：「我觉得这个 prompt 更好」通常靠不住。把判断变成可复现的数字，才能说清楚改动的收益。

## 它怎么工作

```
data/cases.jsonl          每行：id / prompt / checks[]
configs/models.json       每个变体：name / model / system / temperature
        │
        └─► 逐条调用 ─► 跑断言 ─► 汇总 ─► reports/report.md
                                              + report.json（逐条明细）
```

## 关键设计决策

### 1. 优先用确定性断言，而不是让模型当裁判

支持 6 种检查：

| 类型 | 用途 |
|---|---|
| `contains` / `not_contains` | 关键词必须/不得出现 |
| `regex` | 结构化格式、数字结果 |
| `json_keys` | 能解析成 JSON 且含指定字段 |
| `max_chars` / `min_chars` | 指令遵循里的长度约束 |

理由：模型评审本身不稳定——同一份答案两次打分可能不同，评测结果就失去了可比性。
机械检查虽然覆盖面窄，但**同一输入永远给同一结论**，才配当回归测试。

### 2. 所有文本检查忽略大小写

第一版没做，结果「把机器学习翻译成英文」这条被判失败：
模型答的是 `Machine learning`，而断言写的是 `machine learning`。

**评测脚本自己也会出 bug**，而且这种 bug 的方向通常是「把对的判错」。
所以文本类断言统一转小写，正则统一加 `IGNORECASE`。

### 3. 同时记录 token 和耗时

通过率相同不代表没有取舍。两个变体都是 100%，但输出 token 差 3 倍——
这正是评测要回答的问题：**准确性之外还有什么代价**。

### 4. 逐题矩阵而不是只给总分

报告里有「用例 × 变体」的 ✓/✗ 矩阵和失败明细。
总分相同但失败项不同的情况很常见，只看总分会把两种不同的缺陷混为一谈。

## 实测结果

同一模型（`deepseek-chat`）的两个提示词变体，8 条指令遵循用例：

| 变体 | 通过率 | 平均耗时 | 平均输出 tokens |
|---|---|---|---|
| baseline（「你是一个乐于助人的助手」） | 8/8 = 100% | 0.93 s | **32.4** |
| strict（强约束指令执行器） | 8/8 = 100% | 0.63 s | **11.2** |

**结论：准确率相同，但 strict 变体输出 token 少 65%、耗时低 32%。**
在按 token 计费的场景里，这是一个可以直接换算成成本的改进。

> 这个结果也说明：DeepSeek 对基础指令的遵循已经很好，
> 想靠 system prompt 拉开通过率差距，得设计更难的用例（长上下文、多步推理、格式嵌套）。

## 快速开始

```bash
pip install -r requirements.txt
copy .env.example .env          # 填入 DEEPSEEK_API_KEY

python -m src.cli run
# 输出 reports/report.md 与 reports/report.json
```

加一个变体：往 `configs/models.json` 里追加一个对象。
加一条用例：往 `data/cases.jsonl` 里追加一行。

## 目录结构

```
src/
  checks.py   # 6 种断言
  runner.py   # 并发调用、汇总指标
  cli.py      # 命令行与报告生成
configs/      # 变体定义
data/         # 用例
reports/      # 生成的报告
```

## 已知限制

- 断言是机械的，覆盖不了「答案是否合理」这类开放式判断；接入 LLM 评审是下一步
- 用例只有 8 条，统计意义有限，扩到上百条才有区分度
- 只支持 OpenAI 兼容接口，本地模型需要先套一层兼容服务（如 Ollama 的 `/v1`）
- 没有做多次采样（同一输入跑 N 次看稳定性）
