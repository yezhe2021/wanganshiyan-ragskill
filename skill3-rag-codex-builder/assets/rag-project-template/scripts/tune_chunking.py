#!/usr/bin/env python3
"""Compare chunk settings using the same corpus and optional eval set."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path


def load_module(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune chunk_size and overlap")
    parser.add_argument("--corpus", default="build/corpus.jsonl")
    parser.add_argument("--questions", default="eval/questions.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--sizes", default="400,700,900")
    parser.add_argument("--overlaps", default="60,120,150")
    args = parser.parse_args()

    build = load_module("build_index")
    query = load_module("query_rag")
    questions_path = Path(args.questions)
    questions = []
    if questions_path.exists():
        questions = [json.loads(line) for line in questions_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    records = build.load_corpus(Path(args.corpus))
    results = []
    for size in [int(x) for x in args.sizes.split(",") if x.strip()]:
        for overlap in [int(x) for x in args.overlaps.split(",") if x.strip()]:
            chunks = []
            for record in records:
                chunks.extend(build.chunk_document(record, size, overlap))
            index = build.build_index(chunks)
            row = {"chunk_size": size, "overlap": overlap, "chunks": len(chunks)}
            if questions:
                recall = 0
                for item in questions:
                    hits = [index["chunks"][i] for _, i in query.score(item["query"], index)[: args.top_k]]
                    expected = item.get("relevant_doc_ids") or []
                    ok = any(any(e in (h["doc_id"] + h["title"] + h["source_path"]) for e in expected) for h in hits)
                    recall += 1 if ok else 0
                row[f"recall@{args.top_k}"] = recall / len(questions)
            results.append(row)

    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
