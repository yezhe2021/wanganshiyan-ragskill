#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"


def require(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing {path.relative_to(ROOT)}; run previous skills first")
    return path.read_text(encoding="utf-8")


def find_value(config: str, key: str, default: str) -> str:
    for line in config.splitlines():
        if line.strip().startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return default


def main() -> None:
    config = require(SHARED / "rag_config.yaml")
    require(SHARED / "rag_requirement.md")
    require(SHARED / "prompt_pack.md")

    strategy = find_value(config, "strategy", "hybrid")
    chunk_size = find_value(config, "chunk_size", "700")
    overlap = find_value(config, "overlap", "120")
    top_k = find_value(config, "top_k", "5")
    candidate_k = find_value(config, "candidate_k", "20")
    interface = find_value(config, "interface", "cli")
    embedding = find_value(config, "embedding", "hashing-tfidf-baseline")
    llm = find_value(config, "llm", "qwen-compatible")

    vector_commands = ""
    if strategy in {"hybrid", "graph_rag"}:
        vector_commands = """
python scripts/build_vector_index.py --index build/index.json --out build/vector_index.json --method hashing --dimensions 512
python scripts/query_hybrid_rag.py "你的问题" --bm25-index build/index.json --vector-index build/vector_index.json --top-k {top_k}
python scripts/rerank_results.py "你的问题" --retriever hybrid --bm25-index build/index.json --vector-index build/vector_index.json --candidate-k {candidate_k} --top-k {top_k}
""".format(top_k=top_k, candidate_k=candidate_k).strip()

    ui_command = ""
    if interface == "web":
        ui_command = """
python scripts/serve_ui.py --index build/index.json --host 127.0.0.1 --port 7860 --api-base http://127.0.0.1:8000/v1 --model qwen
""".strip()

    content = f"""# Codex Task

Status: ready

## Goal

Build a runnable, testable RAG system from the shared artifacts in `rag-system-designer/shared`.

The system must implement the loop:

`load data -> split -> index -> retrieve -> rerank -> generate grounded answer -> cite -> evaluate`.

## Technology Choices

- Runtime: Python 3.10+
- LLM: {llm}
- Embedding baseline: {embedding}
- Retrieval strategy: {strategy}
- Chunk size: {chunk_size}
- Overlap: {overlap}
- Top-k: {top_k}
- Candidate-k before rerank: {candidate_k}
- Interface: {interface}

## Frontend Template Requirement

Use `examples/rag_workbench_ui_template/` as the default frontend for a Web interface.

- Use `index.inline.html` when the backend embeds HTML in a Python string.
- Use `index.html` with `static/rag-workbench.css` and `static/rag-workbench.js` when static files are supported.
- Connect the UI to `GET /api/profile`, `POST /api/query`, and `POST /api/rebuild`.
- Preserve evidence cards, citation controls, trace chips, pipeline timeline, and evaluation snapshot.
- Do not generate a plain HTML UI while the reusable template is available.
- Do not modify an existing `generated-rag-system/` unless the user explicitly requests migration.

## Project Structure

```text
rag_app/
├── README.md
├── requirements.txt
├── data/
├── build/
├── eval/
├── prompts/
│   └── prompt_pack.md
├── scripts/
│   ├── scan_corpus.py
│   ├── build_index.py
│   ├── build_vector_index.py
│   ├── query_rag.py
│   ├── query_hybrid_rag.py
│   ├── rerank_results.py
│   ├── answer_rag.py
│   ├── qwen_answer.py
│   └── evaluate_rag.py
└── rag_app/
    ├── loader.py
    ├── splitter.py
    ├── embedder.py
    ├── retriever.py
    ├── reranker.py
    ├── generator.py
    ├── citation.py
    └── evaluator.py
```

## Module Tasks

### Loader

- Load configured document types.
- Normalize text to UTF-8.
- Preserve `source_path`, `doc_id`, title, section, page, and modified time.

### Splitter

- Split by semantic boundaries when possible.
- Fall back to chunk size `{chunk_size}` and overlap `{overlap}`.
- Emit stable `chunk_id` values.

### Embedder

- Implement a no-download hashing TF-IDF baseline.
- Leave a model-based extension point for BGE/GTE embeddings.

### Retriever

- Implement BM25 retrieval.
- Implement vector retrieval when strategy is `{strategy}`.
- Implement hybrid fusion with Reciprocal Rank Fusion.

### Reranker

- Add a lightweight coverage reranker.
- Keep scores and reasons inspectable.

### Generator

- Use `prompt_pack.md`.
- Answer only from selected evidence.
- Apply strict refusal when evidence is insufficient.

### Citation

- Cite every factual claim with retrieved chunk IDs.
- Reject citations not present in selected evidence.

### Evaluator

- Retrieval: Recall@k, MRR, NDCG, Hit Rate.
- Generation: Exact Match, F1, ROUGE-L, BLEU, optional BERTScore.
- Faithfulness: groundedness, citation accuracy, hallucination rate.
- System: latency, throughput, token cost estimate, failure rate.

## Required Commands

```bash
python scripts/scan_corpus.py data --out build/corpus.jsonl
python scripts/build_index.py --corpus build/corpus.jsonl --out build/index.json --chunk-size {chunk_size} --overlap {overlap}
python scripts/query_rag.py "你的问题" --index build/index.json --top-k {top_k}
{vector_commands}
python scripts/answer_rag.py "你的问题" --index build/index.json --top-k {top_k}
python scripts/qwen_answer.py "你的问题" --index build/index.json --top-k {top_k} --api-base http://127.0.0.1:8000/v1 --model qwen
python scripts/evaluate_rag.py --config rag-system-designer/shared/rag_config.yaml --questions eval/questions.jsonl --out eval/evaluation_report.json
{ui_command}
```

## README Requirements

The README must include:

- What the system does.
- Installation.
- Data placement.
- Index build commands.
- Query commands.
- Qwen API configuration.
- Evaluation commands.
- Known limitations.

## Acceptance Criteria

- The full command sequence runs on a small local corpus.
- Retrieval returns ranked chunks with source metadata.
- Generation cites chunk IDs.
- Refusal triggers when no evidence is retrieved.
- Evaluation writes a machine-readable report and a Markdown summary.
"""
    (SHARED / "codex_task.md").write_text(content, encoding="utf-8")
    print("wrote shared/codex_task.md")


if __name__ == "__main__":
    main()
