#!/usr/bin/env python3
"""Assemble a citation-aware RAG prompt from retrieved chunks."""

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


def build_prompt(query: str, citations: list[dict]) -> str:
    prompt_parts = [
        "你是一个严谨的 RAG 问答助手。只能依据给定资料回答；如果资料不足，请明确说明不足。",
        "回答要求：",
        "1. 先直接回答问题。",
        "2. 保留关键依据，不编造资料中没有的信息。",
        "3. 在关键结论句末使用 [1]、[2] 这样的编号引用来源。",
        "4. 回答使用中文，结构清晰，避免空泛套话。",
        "",
        f"用户问题：{query}",
        "",
        "检索资料：",
    ]
    for item in citations:
        prompt_parts.append(
            f"[{item['rank']}] doc={item['doc_id']} section={item['section']} chunk={item['chunk_id']}\n{item['text']}"
        )
    return "\n\n".join(prompt_parts)


def trim_hits(hits: list[dict], max_chars: int) -> list[dict]:
    citations = []
    used = 0
    for rank, hit in enumerate(hits, start=1):
        text = hit["text"].strip()
        if used + len(text) > max_chars:
            text = text[: max(max_chars - used, 0)]
        if not text:
            break
        used += len(text)
        citations.append({
            "rank": rank,
            "score": round(float(hit.get("score", 0.0)), 4),
            "chunk_id": hit["chunk_id"],
            "doc_id": hit["doc_id"],
            "section": hit.get("section", ""),
            "source_path": hit.get("source_path", ""),
            "text": text,
        })
        if used >= max_chars:
            break
    return citations


def collect_citations(
    query: str,
    index: dict,
    top_k: int,
    max_chars: int,
    retriever: str = "bm25",
    vector_index: dict | None = None,
    candidate_k: int = 20,
) -> list[dict]:
    if retriever == "bm25":
        query_mod = load_module("query_rag.py")
        hits = [
            {"rank": rank, "score": round(value, 4), **index["chunks"][chunk_i]}
            for rank, (value, chunk_i) in enumerate(query_mod.score(query, index)[:top_k], start=1)
        ]
        return trim_hits(hits, max_chars)

    if vector_index is None:
        raise ValueError(f"{retriever} retrieval requires --vector-index")

    if retriever == "vector":
        vector_mod = load_module("query_vector_rag.py")
        return trim_hits(vector_mod.hits_for_query(query, vector_index, top_k), max_chars)

    hybrid_mod = load_module("query_hybrid_rag.py")
    if retriever == "hybrid":
        return trim_hits(hybrid_mod.retrieve(query, index, vector_index, top_k), max_chars)

    if retriever == "hybrid_rerank":
        rerank_mod = load_module("rerank_results.py")
        candidates = hybrid_mod.retrieve(query, index, vector_index, candidate_k)
        return trim_hits(rerank_mod.rerank(query, candidates, top_k), max_chars)

    raise ValueError(f"Unsupported retriever: {retriever}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a grounded RAG answer prompt")
    parser.add_argument("query")
    parser.add_argument("--index", default="build/index.json", help="BM25 index path")
    parser.add_argument("--vector-index", default="build/vector_index.json")
    parser.add_argument("--retriever", choices=["bm25", "vector", "hybrid", "hybrid_rerank"], default="bm25")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--max-chars", type=int, default=3600)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    vector_index = None
    if args.retriever != "bm25":
        vector_index = json.loads(Path(args.vector_index).read_text(encoding="utf-8"))
    citations = collect_citations(
        args.query,
        index,
        args.top_k,
        args.max_chars,
        retriever=args.retriever,
        vector_index=vector_index,
        candidate_k=args.candidate_k,
    )
    prompt = build_prompt(args.query, citations)

    if args.json:
        print(json.dumps({"query": args.query, "retriever": args.retriever, "prompt": prompt, "citations": citations}, ensure_ascii=False, indent=2))
    else:
        print(prompt)


if __name__ == "__main__":
    main()
