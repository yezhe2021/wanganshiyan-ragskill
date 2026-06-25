#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"


REQUIRED = [
    "rag_requirement.md",
    "rag_config.yaml",
    "prompt_pack.md",
    "codex_task.md",
    "evaluation_plan.md",
]


def status(path: Path) -> tuple[bool, bool]:
    if not path.exists():
        return False, False
    text = path.read_text(encoding="utf-8", errors="replace")
    return True, "Status: ready" in text or "stage: requirement_ready" in text


def main() -> None:
    rows = []
    ready_count = 0
    for name in REQUIRED:
        exists, ready = status(SHARED / name)
        ready_count += int(ready)
        rows.append((name, exists, ready))

    score = round(ready_count / len(REQUIRED), 3)
    existing_reports = []
    root_parent = ROOT.parent
    for candidate in [
        root_parent / "andun-rag-system" / "eval" / "retrieval_report.json",
        root_parent / "andun-rag-system" / "eval" / "retriever_comparison.json",
    ]:
        if candidate.exists():
            try:
                existing_reports.append((candidate, json.loads(candidate.read_text(encoding="utf-8", errors="replace"))))
            except Exception:
                existing_reports.append((candidate, None))

    report_lines = [
        "# Evaluation Report",
        "",
        "Status: ready",
        "",
        "## Artifact Completeness",
        "",
        "| Artifact | Exists | Ready |",
        "| --- | --- | --- |",
    ]
    for name, exists, ready in rows:
        report_lines.append(f"| `{name}` | {exists} | {ready} |")
    report_lines.extend([
        "",
        f"Artifact readiness score: **{score}**",
        "",
        "## Available Runtime Evidence",
        "",
    ])

    if existing_reports:
        for path, payload in existing_reports:
            report_lines.append(f"- Found `{path}`.")
            if isinstance(payload, dict):
                metrics = payload.get("metrics") or {k: payload.get(k) for k in ["recall@5", "mrr", "precision@5"] if k in payload}
                if metrics:
                    report_lines.append(f"  Metrics snapshot: `{json.dumps(metrics, ensure_ascii=False)}`")
    else:
        report_lines.append("- No implementation evaluation JSON was found. Run the generated Codex task before final system scoring.")

    report_lines.extend([
        "",
        "## Required Final Metrics",
        "",
        "- Retrieval: Recall@k, MRR, NDCG, Hit Rate.",
        "- Generation: Exact Match, F1, ROUGE-L, BLEU, BERTScore, LLM-as-Judge.",
        "- Faithfulness: Faithfulness, Groundedness, Citation Accuracy, Hallucination Rate.",
        "- System: Latency, Token Cost, Throughput, Failure Rate.",
        "",
        "## Next Actions",
        "",
        "1. Run the Codex implementation task in `shared/codex_task.md`.",
        "2. Prepare `eval/questions.jsonl` with relevant chunk labels.",
        "3. Run retrieval and generation evaluation.",
        "4. Update this report with real metric tables and failure cases.",
    ])

    (SHARED / "evaluation_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print("wrote shared/evaluation_report.md")


if __name__ == "__main__":
    main()