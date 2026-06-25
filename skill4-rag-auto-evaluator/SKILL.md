---
name: skill4-rag-auto-evaluator
description: Design and run automated RAG evaluation across retrieval quality, generation quality, factual consistency, citation accuracy, hallucination rate, latency, throughput, token cost, and failure rate. Use when a RAG implementation or artifacts must be assessed and `evaluation_plan.md` or `evaluation_report.md` is needed.
---

# RAG Auto Evaluator

Evaluate a RAG system with deterministic retrieval checks first, then generation and faithfulness checks.

## Inputs

- `shared/rag_config.yaml`
- `shared/codex_task.md`
- Optional `shared/evaluation_plan.md`
- Optional eval set such as `eval/questions.jsonl`
- Optional implementation outputs such as retrieval reports, answer logs, latency logs, or benchmark JSON.

## Reusable Scripts

Use:

- `scripts/evaluate_retrieval.py` for recall@k, MRR, precision@k.
- `scripts/compare_retrievers.py` for BM25/vector/hybrid/hybrid+rerank comparison.
- `scripts/evaluate_artifacts.py` for shared artifact completeness and available runtime evidence.

When evaluating a generated project, copy or reference these scripts in its `scripts/` directory.

## Metrics

Retrieval:

- Recall@k
- MRR
- NDCG when graded relevance is available
- Hit Rate

Generation:

- Exact Match and F1 for extractive QA
- ROUGE-L or BLEU for summarization-style QA
- BERTScore when the dependency is available
- LLM-as-Judge only after deterministic checks

Faithfulness:

- Groundedness
- Citation Accuracy
- Unsupported Claim Rate
- Hallucination Rate

System:

- Latency
- Token cost
- Throughput
- Failure rate

## Evaluation Order

1. Confirm corpus scan and index files exist.
2. Run retrieval evaluation.
3. Compare retrievers when vector/hybrid exists.
4. Sample evidence manually for source correctness.
5. Run answer generation checks.
6. Check UI/API failure cases: no API key, provider error, no evidence, rebuild index.
7. Write the report with concrete next actions.

## Outputs

- `shared/evaluation_plan.md`
- `shared/evaluation_report.md`

The report must include dataset description, commands run, metric table, failure cases, and recommendations in priority order.

## Deterministic Scripts

```bash
python skill4-rag-auto-evaluator/scripts/generate_evaluation_plan.py
python skill4-rag-auto-evaluator/scripts/evaluate_artifacts.py
```