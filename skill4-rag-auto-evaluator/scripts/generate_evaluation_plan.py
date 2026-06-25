#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"


def main() -> None:
    if not (SHARED / "rag_config.yaml").exists():
        raise SystemExit("missing shared/rag_config.yaml; run Skill1 first")

    content = """# Evaluation Plan

Status: ready

## 1. Dataset Preparation

Prepare `eval/questions.jsonl` with fields:

```json
{"id":"q1","question":"...","expected_answer":"...","relevant_chunk_ids":["..."]}
```

For early experiments, use 5-20 representative questions. For final acceptance, include scenario-specific easy, medium, hard, and refusal questions.

## 2. Retrieval Quality

- Recall@k: whether relevant chunks appear in top-k.
- MRR: rank of the first relevant chunk.
- NDCG: ranking quality with graded relevance when labels exist.
- Hit Rate: whether at least one relevant chunk is retrieved.

## 3. Generation Quality

- Exact Match and F1 for short factual answers.
- ROUGE-L and BLEU for summary-style answers.
- BERTScore when semantic similarity evaluation is available.
- LLM-as-Judge for completeness and usefulness, with answer and evidence passed together.

## 4. Faithfulness

- Faithfulness: answer claims are entailed by evidence.
- Groundedness: each important claim maps to a retrieved chunk.
- Citation Accuracy: citations point to actual supporting chunks.
- Hallucination Rate: unsupported claims divided by total claims.

## 5. System Performance

- Latency: p50, p95, max.
- Token Cost: prompt tokens, completion tokens, estimated cost.
- Throughput: queries per second under batch or concurrent load.
- Failure Rate: failed requests divided by total requests.

## 6. Report Format

Write `shared/evaluation_report.md` with:

- Configuration summary.
- Dataset summary.
- Metric table.
- Failure cases.
- Next optimization actions.
"""
    (SHARED / "evaluation_plan.md").write_text(content, encoding="utf-8")
    print("wrote shared/evaluation_plan.md")


if __name__ == "__main__":
    main()