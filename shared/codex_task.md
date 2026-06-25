# Codex Task

Status: ready

## Goal

Build a runnable, testable RAG system from the shared artifacts in `rag-system-designer/shared`.

The system must implement the loop:

`load data -> split -> index -> retrieve -> rerank -> generate grounded answer -> cite -> evaluate`.

## Technology Choices

- Runtime: Python 3.10+
- LLM: qwen-compatible
- Embedding baseline: "hashing-tfidf baseline; optional multilingual embedding"
- Retrieval strategy: bm25
- Chunk size: 700
- Overlap: 120
- Top-k: 5
- Candidate-k before rerank: 20
- Interface: cli

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
- Fall back to chunk size `700` and overlap `120`.
- Emit stable `chunk_id` values.

### Embedder

- Implement a no-download hashing TF-IDF baseline.
- Leave a model-based extension point for BGE/GTE embeddings.

### Retriever

- Implement BM25 retrieval.
- Implement vector retrieval when strategy is `bm25`.
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
python scripts/build_index.py --corpus build/corpus.jsonl --out build/index.json --chunk-size 700 --overlap 120
python scripts/query_rag.py "你的问题" --index build/index.json --top-k 5

python scripts/answer_rag.py "你的问题" --index build/index.json --top-k 5
python scripts/qwen_answer.py "你的问题" --index build/index.json --top-k 5 --api-base http://127.0.0.1:8000/v1 --model qwen
python scripts/evaluate_rag.py --config rag-system-designer/shared/rag_config.yaml --questions eval/questions.jsonl --out eval/evaluation_report.json

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
