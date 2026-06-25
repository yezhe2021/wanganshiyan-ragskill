---
name: skill3-rag-codex-builder
description: Convert RAG requirements and a prompt pack into a Codex-executable engineering task, including Python project structure, technology choices, module tasks, runnable scaffold guidance, UI/API mode, README expectations, commands, and evaluation interfaces while reusing existing local RAG scripts.
---

# RAG Codex Builder

Turn the requirement spec and prompt pack into a Codex-ready engineering task.

## Inputs

- `shared/rag_config.yaml`
- `shared/rag_requirement.md`
- `shared/prompt_pack.md`
- Optional `shared/document_analysis.md`
- Optional `shared/ui_design.md`

If any required input is missing, route backward to the missing stage.

## Reusable Assets

Use `assets/rag-project-template/scripts/` as the local implementation base. It contains:

- `scan_corpus.py`: scan DOCX, PDF, Markdown, TXT into `build/corpus.jsonl`.
- `build_index.py`: chunk documents and build BM25 index.
- `query_rag.py`: BM25 retrieval.
- `build_vector_index.py`: hashing TF-IDF or optional transformer vector index.
- `query_vector_rag.py`: vector retrieval.
- `query_hybrid_rag.py`: BM25 + vector reciprocal-rank fusion.
- `rerank_results.py`: lightweight coverage reranking.
- `answer_rag.py`: citation-aware prompt assembly.
- `qwen_answer.py`: OpenAI-compatible Qwen/local LLM call.
- `serve_ui.py`: local web UI baseline.
- `tune_chunking.py`: chunk-size/overlap tuning.

For UI-heavy demos, prefer the integrated pattern in `generated-rag-system/server.py`, which combines corpus profiling, method selection, DashScope model selection, evidence display, and trace metadata.

## Project Structure To Generate

Prefer this structure unless the config requires another stack:

```text
rag_project/
  data/
  scripts/
  build/
  eval/
  prompts/
  README.md
  requirements.txt
```

## Required Implementation Modules

- Loader: ingest configured sources and preserve metadata.
- Splitter: produce stable chunk IDs and page/section metadata.
- Embedder: local no-download baseline plus optional model-based embedding.
- Retriever: BM25, vector, hybrid, and configurable top-k.
- Reranker: optional rerank layer using candidate-k.
- Generator: grounded answer generation using prompt pack.
- Citation: source and chunk citation formatting.
- UI/API: method controls, model controls, answer/evidence/trace panels.
- Evaluator: retrieval, generation, faithfulness, and performance metrics.

## Output

Write `shared/codex_task.md` with:

- Goal and acceptance criteria.
- Selected stack: LLM, embedding, vector store, reranker, UI/API mode.
- Project structure.
- File-by-file implementation tasks.
- Commands to install, scan, index, retrieve, answer, serve UI, and evaluate.
- How `prompt_pack.md` is wired into answer generation.
- Test and evaluation commands.

## Implementation Guidance

- Start with the smallest runnable baseline.
- Add vector/hybrid/rerank when the config requires semantic recall, paper comparison, or source robustness.
- Preserve citations and metadata through the pipeline.
- Keep Qwen/OpenAI-compatible API optional and make external provider use explicit.
- Do not require network downloads for the baseline.

## Deterministic Script

```bash
python skill3-rag-codex-builder/scripts/generate_codex_task.py
```