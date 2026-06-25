#!/usr/bin/env python3
"""Build a portable vector retrieval index from an existing chunk index."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_bm25_module():
    path = Path(__file__).with_name("build_index.py")
    spec = importlib.util.spec_from_file_location("build_index", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def tokenize(text: str) -> list[str]:
    module = load_bm25_module()
    return module.tokenize(text)


def stable_bucket(token: str, dimensions: int) -> tuple[int, int]:
    digest = hashlib.sha1(token.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % dimensions
    sign = 1 if digest[4] % 2 == 0 else -1
    return bucket, sign


def sparse_hash_vector(tokens: list[str], idf: dict[str, float], dimensions: int) -> dict[str, float]:
    counts = Counter(tokens)
    values: dict[int, float] = {}
    for token, count in counts.items():
        bucket, sign = stable_bucket(token, dimensions)
        tf = 1.0 + math.log(count)
        values[bucket] = values.get(bucket, 0.0) + sign * tf * idf.get(token, 1.0)
    norm = math.sqrt(sum(value * value for value in values.values())) or 1.0
    return {str(bucket): round(value / norm, 8) for bucket, value in values.items() if value}


def build_hashing_index(chunks: list[dict], dimensions: int) -> dict:
    tokenized = [tokenize(chunk["text"]) for chunk in chunks]
    doc_freq: Counter[str] = Counter()
    for tokens in tokenized:
        doc_freq.update(set(tokens))
    total = max(len(chunks), 1)
    idf = {token: math.log(1 + (total + 1) / (freq + 1)) for token, freq in doc_freq.items()}
    vectors = [sparse_hash_vector(tokens, idf, dimensions) for tokens in tokenized]
    return {
        "version": 1,
        "retriever": "vector",
        "method": "hashing_tfidf",
        "dimensions": dimensions,
        "idf": idf,
        "vectors": vectors,
        "chunks": chunks,
    }


def build_transformer_index(chunks: list[dict], model_name: str) -> dict:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Install sentence-transformers to use --method transformer") from exc
    model = SentenceTransformer(model_name)
    texts = [chunk["text"] for chunk in chunks]
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return {
        "version": 1,
        "retriever": "vector",
        "method": "sentence_transformer",
        "model": model_name,
        "vectors": [[round(float(value), 8) for value in vector] for vector in vectors],
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local vector retrieval index")
    parser.add_argument("--index", default="build/index.json", help="Existing BM25/chunk index")
    parser.add_argument("--out", default="build/vector_index.json")
    parser.add_argument("--method", choices=["hashing", "transformer"], default="hashing")
    parser.add_argument("--dimensions", type=int, default=512)
    parser.add_argument("--model", default="BAAI/bge-small-zh-v1.5")
    args = parser.parse_args()

    source = json.loads(Path(args.index).read_text(encoding="utf-8"))
    chunks = source["chunks"]
    if args.method == "transformer":
        index = build_transformer_index(chunks, args.model)
    else:
        index = build_hashing_index(chunks, args.dimensions)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "output": str(out),
        "chunks": len(chunks),
        "method": index["method"],
        "dimensions": index.get("dimensions", len(index["vectors"][0]) if index["vectors"] else 0),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
