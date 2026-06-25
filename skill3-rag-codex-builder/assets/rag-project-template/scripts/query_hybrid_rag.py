#!/usr/bin/env python3
"""Query BM25 and vector indexes with reciprocal-rank fusion."""

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


def retrieve(query: str, bm25_index: dict, vector_index: dict, top_k: int, rank_window: int = 40, rrf_k: int = 60) -> list[dict]:
    bm25_mod = load_module("query_rag.py")
    vector_mod = load_module("query_vector_rag.py")

    bm25_scores = bm25_mod.score(query, bm25_index)[:rank_window]
    vector_scores = vector_mod.score(query, vector_index)[:rank_window]

    fused: dict[str, dict] = {}

    def add_hits(scored: list[tuple[float, int]], source: str, chunks: list[dict]) -> None:
        for rank, (value, chunk_i) in enumerate(scored, start=1):
            chunk = chunks[chunk_i]
            chunk_id = chunk["chunk_id"]
            item = fused.setdefault(chunk_id, {
                **chunk,
                "score": 0.0,
                "bm25_rank": None,
                "vector_rank": None,
                "bm25_score": 0.0,
                "vector_score": 0.0,
            })
            item["score"] += 1.0 / (rrf_k + rank)
            item[f"{source}_rank"] = rank
            item[f"{source}_score"] = round(value, 4)

    add_hits(bm25_scores, "bm25", bm25_index["chunks"])
    add_hits(vector_scores, "vector", vector_index["chunks"])

    ranked = sorted(fused.values(), key=lambda item: item["score"], reverse=True)[:top_k]
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
        item["score"] = round(item["score"], 6)
    return ranked


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid BM25 + vector retrieval")
    parser.add_argument("query")
    parser.add_argument("--bm25-index", default="build/index.json")
    parser.add_argument("--vector-index", default="build/vector_index.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rank-window", type=int, default=40)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    bm25_index = json.loads(Path(args.bm25_index).read_text(encoding="utf-8"))
    vector_index = json.loads(Path(args.vector_index).read_text(encoding="utf-8"))
    hits = retrieve(args.query, bm25_index, vector_index, args.top_k, args.rank_window, args.rrf_k)

    if args.json:
        print(json.dumps({"query": args.query, "hits": hits}, ensure_ascii=False, indent=2))
        return

    print(f"Query: {args.query}\n")
    for hit in hits:
        preview = hit["text"].replace("\n", " ")[:360]
        print(f"[{hit['rank']}] score={hit['score']} bm25_rank={hit['bm25_rank']} vector_rank={hit['vector_rank']}")
        print(f"    doc={hit['doc_id']} section={hit['section']}")
        print(f"    chunk={hit['chunk_id']}")
        print(f"    {preview}\n")


if __name__ == "__main__":
    main()
