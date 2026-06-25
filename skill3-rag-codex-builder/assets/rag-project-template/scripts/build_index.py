#!/usr/bin/env python3
"""Build a portable BM25 retrieval index from corpus.jsonl."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


HEADING_RE = re.compile(r"^(#{1,6}\s+.+|第[一二三四五六七八九十0-9]+[章节].+|[一二三四五六七八九十]+、.+|（[一二三四五六七八九十0-9]+）.+|\d+(?:\.\d+)*[、.]\s*.+)$")


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for part in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part)
            tokens.extend(part[i:i + 2] for i in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？；!?;])\s*|\n{2,}", text)
    return [p.strip() for p in pieces if p.strip()]


def chunk_document(record: dict, chunk_size: int, overlap: int) -> list[dict]:
    title = record["title"]
    doc_id = record["doc_id"]
    paragraphs = [p.strip() for p in re.split(r"\n+", record["text"]) if p.strip()]
    chunks: list[dict] = []
    section = title
    current = ""
    current_section = section

    def emit(text: str, section_name: str) -> None:
        clean = text.strip()
        if not clean:
            return
        chunk_id = f"{doc_id}::chunk-{len(chunks):04d}"
        chunks.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "title": title,
            "section": section_name,
            "source_path": record.get("source_path", ""),
            "text": clean,
        })

    for para in paragraphs:
        if HEADING_RE.match(para[:80]):
            if current:
                emit(f"{title}\n{current_section}\n{current}", current_section)
                current = ""
            section = para[:120]
            current_section = section
            continue
        units = split_sentences(para) if len(para) > chunk_size else [para]
        for unit in units:
            prefix = f"{title}\n{section}\n"
            candidate = (current + "\n" + unit).strip() if current else unit
            if len(prefix + candidate) <= chunk_size:
                current = candidate
                current_section = section
                continue
            emit(f"{title}\n{current_section}\n{current}", current_section)
            tail = current[-overlap:] if overlap and current else ""
            current = (tail + "\n" + unit).strip()
            current_section = section
    if current:
        emit(f"{title}\n{current_section}\n{current}", current_section)
    return chunks


def load_corpus(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_index(chunks: list[dict]) -> dict:
    term_freqs = []
    doc_freq = Counter()
    lengths = []
    for chunk in chunks:
        tokens = tokenize(chunk["text"])
        counts = Counter(tokens)
        term_freqs.append(counts)
        lengths.append(len(tokens))
        doc_freq.update(counts.keys())
    n = max(len(chunks), 1)
    avg_len = sum(lengths) / n if lengths else 0
    idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in doc_freq.items()}
    serial_tf = [dict(counts) for counts in term_freqs]
    return {"version": 1, "retriever": "bm25", "avg_len": avg_len, "idf": idf, "term_freqs": serial_tf, "chunks": chunks}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local retrieval index")
    parser.add_argument("--corpus", default="build/corpus.jsonl")
    parser.add_argument("--out", default="build/index.json")
    parser.add_argument("--chunk-size", type=int, default=700)
    parser.add_argument("--overlap", type=int, default=120)
    args = parser.parse_args()

    records = load_corpus(Path(args.corpus))
    chunks = []
    for record in records:
        chunks.extend(chunk_document(record, args.chunk_size, args.overlap))
    index = build_index(chunks)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(out), "documents": len(records), "chunks": len(chunks), "chunk_size": args.chunk_size, "overlap": args.overlap}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
