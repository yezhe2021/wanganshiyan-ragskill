#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"


def read(path: Path, default: str = "") -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else default


def config_value(config: str, key: str, default: str) -> str:
    for line in config.splitlines():
        if line.strip().startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return default


def load_analysis() -> dict:
    path = SHARED / "document_analysis.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def main() -> None:
    config = read(SHARED / "rag_config.yaml")
    analysis = load_analysis()
    scenario = config_value(config, "type", analysis.get("scenario", "paper_qa"))
    strategy = config_value(config, "strategy", analysis.get("recommended", {}).get("retrieval_strategy", "hybrid"))
    top_k = config_value(config, "top_k", str(analysis.get("recommended", {}).get("top_k", 8)))
    candidate_k = config_value(config, "candidate_k", str(analysis.get("recommended", {}).get("candidate_k", 30)))
    chunk_size = config_value(config, "chunk_size", str(analysis.get("recommended", {}).get("chunk_size", 900)))
    overlap = config_value(config, "overlap", str(analysis.get("recommended", {}).get("overlap", 150)))
    file_count = analysis.get("file_count", "unknown")
    chunk_estimate = analysis.get("estimated_chunks", "unknown")

    methods = ["BM25", "Vector", "Hybrid", "Rerank"]
    if "graph" in strategy.lower():
        methods.append("Graph RAG")

    content = f"""# RAG UI Design

Status: ready

## 1. UI Goal

Build a demo-ready RAG workbench for `{scenario}`. The UI must expose retrieval choices, model generation choices, evidence, citations, and system trace instead of hiding the RAG pipeline behind a single chat box.

Default template: `examples/rag_workbench_ui_template/`

- Static backend: use `index.html` with `static/rag-workbench.css` and `static/rag-workbench.js`.
- Single-file Python backend: use `index.inline.html`.
- API contract: `GET /api/profile`, `POST /api/query`, `POST /api/rebuild`.
- Use another template only when the user explicitly requests it.

## 2. Corpus-Derived Defaults

- File count: {file_count}
- Estimated chunks: {chunk_estimate}
- Retrieval strategy: {strategy}
- Chunk size: {chunk_size}
- Overlap: {overlap}
- Top-K: {top_k}
- Candidate-K: {candidate_k}

## 3. First-Screen Layout

Use the default template's three-column desktop workbench:

- Top bar: project identity plus corpus and index status.
- Left panel: retrieval/model controls, parameters, rebuild action, corpus summary.
- Center panel: query, grounded answer, citation tags, trace chips, pipeline timeline.
- Right panel: evidence search, ranked evidence cards, source metadata, score bars, evaluation snapshot.

On mobile, stack query, answer, evidence, corpus profile, then trace.

## 4. Required Controls

- Retrieval method segmented control: {", ".join(methods)}.
- Model dropdown: qwen-plus, qwen-turbo, qwen-max, qwen-long.
- External generation switch: label it clearly as DashScope generation.
- Top-K slider default `{top_k}`.
- Candidate-K slider default `{candidate_k}`.
- Rebuild index button.
- Optional prompt export button.

## 5. Required Panels

### Corpus Profile

Show file count, chunk count, chunk size, overlap, average chunk tokens, build time, and document path.

### Answer

Show whether the answer came from:

- local evidence draft, or
- DashScope model generation.

When model generation is used, show model name, latency, and token usage.

### Evidence

Each evidence row must show rank, score, title, page range, section, chunk ID, and preview.

### Trace

Show method, BM25 candidate count, vector candidate count, candidate-k, top-k, model metadata, and errors.

## 6. Safety Requirements

- If `DASHSCOPE_API_KEY` is missing, show a visible error.
- If external model generation is enabled, make clear that retrieved document snippets are sent to DashScope.
- If no evidence is retrieved, trigger refusal behavior instead of hallucinating.
- Keep evidence visible even when model generation fails.

## 7. Visual Direction

- Quiet technical dashboard.
- White panels on light neutral background.
- Teal for primary retrieval/generation actions.
- Blue for model/provider metadata.
- Red only for errors/refusal.
- Use compact typography and stable panel dimensions.
- Do not use a landing-page hero.
"""
    (SHARED / "ui_design.md").write_text(content, encoding="utf-8")
    print("wrote shared/ui_design.md")


if __name__ == "__main__":
    main()

