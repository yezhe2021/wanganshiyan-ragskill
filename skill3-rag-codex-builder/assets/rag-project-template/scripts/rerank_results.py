#!/usr/bin/env python3
"""Rerank retrieved chunks with lightweight query-coverage features."""

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


def query_terms(query: str) -> set[str]:
    bm25_mod = load_module("query_rag.py")
    return set(bm25_mod.tokenize(query))


def coverage_score(terms: set[str], text: str) -> float:
    if not terms:
        return 0.0
    bm25_mod = load_module("query_rag.py")
    chunk_terms = set(bm25_mod.tokenize(text))
    return len(terms & chunk_terms) / len(terms)


def rerank(query: str, hits: list[dict], top_k: int) -> list[dict]:
    terms = query_terms(query)
    if not hits:
        return []
    max_original = max(float(hit.get("score", 0.0)) for hit in hits) or 1.0
    reranked = []
    for hit in hits:
        evidence_text = " ".join([
            str(hit.get("title", "")),
            str(hit.get("section", "")),
            str(hit.get("text", "")),
        ])
        original = float(hit.get("score", 0.0)) / max_original
        coverage = coverage_score(terms, evidence_text)
        section_bonus = 0.15 if coverage_score(terms, f"{hit.get('title', '')} {hit.get('section', '')}") > 0 else 0.0
        length = len(str(hit.get("text", "")))
        length_bonus = 0.1 if 180 <= length <= 1200 else 0.0
        rerank_score = 0.55 * original + 0.30 * coverage + section_bonus + length_bonus
        reranked.append({**hit, "rerank_score": round(rerank_score, 6), "coverage": round(coverage, 4)})
    reranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    for rank, item in enumerate(reranked[:top_k], start=1):
        item["rank"] = rank
        item["score"] = item["rerank_score"]
    return reranked[:top_k]


def load_base_hits(args) -> list[dict]:
    if args.hits:
        data = json.loads(Path(args.hits).read_text(encoding="utf-8"))
        return data["hits"] if isinstance(data, dict) and "hits" in data else data

    if args.retriever == "bm25":
        bm25_mod = load_module("query_rag.py")
        index = json.loads(Path(args.bm25_index).read_text(encoding="utf-8"))
        return [
            {"rank": rank, "score": round(value, 4), **index["chunks"][chunk_i]}
            for rank, (value, chunk_i) in enumerate(bm25_mod.score(args.query, index)[:args.candidate_k], start=1)
        ]
    if args.retriever == "vector":
        vector_mod = load_module("query_vector_rag.py")
        index = json.loads(Path(args.vector_index).read_text(encoding="utf-8"))
        return vector_mod.hits_for_query(args.query, index, args.candidate_k)

    hybrid_mod = load_module("query_hybrid_rag.py")
    bm25_index = json.loads(Path(args.bm25_index).read_text(encoding="utf-8"))
    vector_index = json.loads(Path(args.vector_index).read_text(encoding="utf-8"))
    return hybrid_mod.retrieve(args.query, bm25_index, vector_index, args.candidate_k)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rerank retrieved RAG chunks")
    parser.add_argument("query")
    parser.add_argument("--retriever", choices=["bm25", "vector", "hybrid"], default="hybrid")
    parser.add_argument("--bm25-index", default="build/index.json")
    parser.add_argument("--vector-index", default="build/vector_index.json")
    parser.add_argument("--hits", help="Optional JSON file containing hits to rerank")
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    hits = rerank(args.query, load_base_hits(args), args.top_k)
    if args.json:
        print(json.dumps({"query": args.query, "hits": hits}, ensure_ascii=False, indent=2))
        return

    print(f"Query: {args.query}\n")
    for hit in hits:
        preview = hit["text"].replace("\n", " ")[:360]
        print(f"[{hit['rank']}] score={hit['score']} coverage={hit['coverage']} doc={hit['doc_id']}")
        print(f"    section={hit['section']} chunk={hit['chunk_id']}")
        print(f"    {preview}\n")


if __name__ == "__main__":
    main()
