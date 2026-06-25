# RAG Project Template

This template reuses the runnable local RAG scripts from the previous `rag-builder` project.

## Baseline

```bash
python scripts/scan_corpus.py data --out build/corpus.jsonl
python scripts/build_index.py --corpus build/corpus.jsonl --out build/index.json --chunk-size 700 --overlap 120
python scripts/query_rag.py "your question" --index build/index.json --top-k 5
python scripts/answer_rag.py "your question" --index build/index.json --top-k 5
```

## Hybrid And Evaluation

```bash
python scripts/build_vector_index.py --index build/index.json --out build/vector_index.json --method hashing --dimensions 512
python scripts/query_hybrid_rag.py "your question" --bm25-index build/index.json --vector-index build/vector_index.json --top-k 5
python scripts/compare_retrievers.py --bm25-index build/index.json --vector-index build/vector_index.json --questions eval/questions.jsonl --top-k 5 --out eval/retriever_comparison.json
```
