#!/usr/bin/env python3
"""Query a local vector RAG index and print cited contexts."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_vector_builder():
    path = Path(__file__).with_name("build_vector_index.py")
    spec = importlib.util.spec_from_file_location("build_vector_index", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def dot_sparse(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def dot_dense(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def encode_query(query: str, index: dict):
    if index["method"] == "sentence_transformer":
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Install sentence-transformers to query a transformer vector index") from exc
        model = SentenceTransformer(index["model"])
        vector = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        return [float(value) for value in vector]

    builder = load_vector_builder()
    tokens = builder.tokenize(query)
    return builder.sparse_hash_vector(tokens, index.get("idf", {}), int(index.get("dimensions", 512)))


def score(query: str, index: dict) -> list[tuple[float, int]]:
    query_vector = encode_query(query, index)
    scored = []
    for i, vector in enumerate(index["vectors"]):
        value = dot_dense(query_vector, vector) if isinstance(vector, list) else dot_sparse(query_vector, vector)
        if value > 0:
            scored.append((value, i))
    return sorted(scored, reverse=True)


def hits_for_query(query: str, index: dict, top_k: int) -> list[dict]:
    hits = []
    for rank, (value, chunk_i) in enumerate(score(query, index)[:top_k], start=1):
        chunk = index["chunks"][chunk_i]
        hits.append({"rank": rank, "score": round(value, 4), **chunk})
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve chunks from a vector index")
    parser.add_argument("query")
    parser.add_argument("--index", default="build/vector_index.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    hits = hits_for_query(args.query, index, args.top_k)

    if args.json:
        print(json.dumps({"query": args.query, "hits": hits}, ensure_ascii=False, indent=2))
        return

    print(f"Query: {args.query}\n")
    for hit in hits:
        preview = hit["text"].replace("\n", " ")[:360]
        print(f"[{hit['rank']}] score={hit['score']} doc={hit['doc_id']} section={hit['section']}")
        print(f"    chunk={hit['chunk_id']}")
        print(f"    {preview}\n")


if __name__ == "__main__":
    main()
