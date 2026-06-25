#!/usr/bin/env python3
"""Query a local BM25 RAG index and print cited contexts."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for part in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part)
            tokens.extend(part[i:i + 2] for i in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


def score(query: str, index: dict, k1: float = 1.5, b: float = 0.75) -> list[tuple[float, int]]:
    q = Counter(tokenize(query))
    avg_len = index.get("avg_len") or 1
    idf = index["idf"]
    scored = []
    for i, tf in enumerate(index["term_freqs"]):
        length = sum(tf.values()) or 1
        total = 0.0
        for term, q_count in q.items():
            if term not in tf:
                continue
            freq = tf[term]
            denom = freq + k1 * (1 - b + b * length / avg_len)
            total += idf.get(term, 0.0) * (freq * (k1 + 1) / denom) * math.sqrt(q_count)
        if total > 0:
            scored.append((total, i))
    return sorted(scored, reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve chunks for a query")
    parser.add_argument("query")
    parser.add_argument("--index", default="build/index.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Output JSON instead of readable text")
    args = parser.parse_args()

    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    hits = []
    for rank, (value, chunk_i) in enumerate(score(args.query, index)[: args.top_k], start=1):
        chunk = index["chunks"][chunk_i]
        hits.append({"rank": rank, "score": round(value, 4), **chunk})

    if args.json:
        print(json.dumps({"query": args.query, "hits": hits}, ensure_ascii=False, indent=2))
        return

    print(f"Query: {args.query}\n")
    for hit in hits:
        text = hit["text"].replace("\n", " ")
        preview = text[:360] + ("..." if len(text) > 360 else "")
        print(f"[{hit['rank']}] score={hit['score']} doc={hit['doc_id']} section={hit['section']}")
        print(f"    chunk={hit['chunk_id']}")
        print(f"    {preview}\n")


if __name__ == "__main__":
    main()
