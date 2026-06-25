#!/usr/bin/env python3
"""Compare BM25, vector, hybrid, and reranked retrieval on one question set."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_module(script_name: str):
    path = Path(__file__).with_name(script_name)
    spec = importlib.util.spec_from_file_location(script_name.removesuffix(".py"), path)
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


def metrics_for_rows(rows: list[dict], top_k: int) -> dict:
    total = max(len(rows), 1)
    recall_hits = 0
    reciprocal_sum = 0.0
    precision_sum = 0.0
    for row in rows:
        flags = row["relevant_flags"]
        first_rank = next((i + 1 for i, ok in enumerate(flags) if ok), None)
        recall_hits += 1 if first_rank else 0
        reciprocal_sum += 1 / first_rank if first_rank else 0
        precision_sum += sum(flags) / max(len(flags), 1)
        row["first_relevant_rank"] = first_rank
        row.pop("relevant_flags", None)
    return {
        f"recall@{top_k}": recall_hits / total,
        "mrr": reciprocal_sum / total,
        f"precision@{top_k}": precision_sum / total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare retrieval methods")
    parser.add_argument("--bm25-index", default="build/index.json")
    parser.add_argument("--vector-index", default="build/vector_index.json")
    parser.add_argument("--questions", default="eval/questions.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--out", default="eval/retriever_comparison.json")
    args = parser.parse_args()

    bm25_mod = load_module("query_rag.py")
    vector_mod = load_module("query_vector_rag.py")
    hybrid_mod = load_module("query_hybrid_rag.py")
    rerank_mod = load_module("rerank_results.py")

    bm25_index = json.loads(Path(args.bm25_index).read_text(encoding="utf-8"))
    vector_index = json.loads(Path(args.vector_index).read_text(encoding="utf-8"))
    questions = [json.loads(line) for line in Path(args.questions).read_text(encoding="utf-8").splitlines() if line.strip()]

    reports: dict[str, dict] = {}
    for name in ["bm25", "vector", "hybrid", "hybrid_rerank"]:
        rows = []
        for item in questions:
            query = item["query"]
            if name == "bm25":
                hits = [
                    {"rank": rank, "score": round(value, 4), **bm25_index["chunks"][chunk_i]}
                    for rank, (value, chunk_i) in enumerate(bm25_mod.score(query, bm25_index)[:args.top_k], start=1)
                ]
            elif name == "vector":
                hits = vector_mod.hits_for_query(query, vector_index, args.top_k)
            elif name == "hybrid":
                hits = hybrid_mod.retrieve(query, bm25_index, vector_index, args.top_k)
            else:
                candidates = hybrid_mod.retrieve(query, bm25_index, vector_index, args.candidate_k)
                hits = rerank_mod.rerank(query, candidates, args.top_k)
            rows.append({
                "id": item.get("id"),
                "query": query,
                "top_chunks": [hit["chunk_id"] for hit in hits],
                "relevant_flags": [is_relevant(hit, item) for hit in hits],
            })
        metrics = metrics_for_rows(rows, args.top_k)
        reports[name] = {"metrics": metrics, "rows": rows}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = {"questions": len(questions), "top_k": args.top_k, "reports": reports}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
