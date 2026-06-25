#!/usr/bin/env python3
"""Evaluate top-k retrieval against a JSONL question set."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_query_module():
    path = Path(__file__).with_name("query_rag.py")
    spec = importlib.util.spec_from_file_location("query_rag", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def is_relevant(hit: dict, item: dict) -> bool:
    chunk_ids = item.get("relevant_chunk_ids") or []
    doc_ids = item.get("relevant_doc_ids") or []
    if hit["chunk_id"] in chunk_ids:
        return True
    doc = hit["doc_id"] + " " + hit.get("title", "") + " " + hit.get("source_path", "")
    return any(expected in doc for expected in doc_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local retrieval")
    parser.add_argument("--index", default="build/index.json")
    parser.add_argument("--questions", default="eval/questions.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out", default="eval/retrieval_report.json")
    args = parser.parse_args()

    query_mod = load_query_module()
    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    questions = [json.loads(line) for line in Path(args.questions).read_text(encoding="utf-8").splitlines() if line.strip()]

    rows = []
    recall_hits = 0
    reciprocal_sum = 0.0
    precision_sum = 0.0
    for item in questions:
        scored = query_mod.score(item["query"], index)[: args.top_k]
        hits = [index["chunks"][chunk_i] for _, chunk_i in scored]
        relevant_flags = [is_relevant(hit, item) for hit in hits]
        first_rank = next((i + 1 for i, ok in enumerate(relevant_flags) if ok), None)
        recall_hits += 1 if first_rank else 0
        reciprocal_sum += 1 / first_rank if first_rank else 0
        precision_sum += sum(relevant_flags) / max(len(hits), 1)
        rows.append({
            "id": item.get("id"),
            "query": item["query"],
            "first_relevant_rank": first_rank,
            "top_chunks": [hit["chunk_id"] for hit in hits],
        })

    total = max(len(questions), 1)
    report = {
        "questions": len(questions),
        f"recall@{args.top_k}": recall_hits / total,
        "mrr": reciprocal_sum / total,
        f"precision@{args.top_k}": precision_sum / total,
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
