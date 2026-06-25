# Evaluation Report

Status: ready

## Artifact Completeness

| Artifact | Exists | Ready |
| --- | --- | --- |
| `rag_requirement.md` | True | True |
| `rag_config.yaml` | True | True |
| `prompt_pack.md` | True | True |
| `codex_task.md` | True | True |
| `evaluation_plan.md` | True | True |

Artifact readiness score: **1.0**

## Available Runtime Evidence

- Found `C:\Users\MYS\Desktop\网安大实验\skill项目开题报告(1)\andun-rag-system\eval\retrieval_report.json`.
  Metrics snapshot: `{"recall@5": 1.0, "mrr": 1.0, "precision@5": 0.9}`
- Found `C:\Users\MYS\Desktop\网安大实验\skill项目开题报告(1)\andun-rag-system\eval\retriever_comparison.json`.

## Required Final Metrics

- Retrieval: Recall@k, MRR, NDCG, Hit Rate.
- Generation: Exact Match, F1, ROUGE-L, BLEU, BERTScore, LLM-as-Judge.
- Faithfulness: Faithfulness, Groundedness, Citation Accuracy, Hallucination Rate.
- System: Latency, Token Cost, Throughput, Failure Rate.

## Next Actions

1. Run the Codex implementation task in `shared/codex_task.md`.
2. Prepare `eval/questions.jsonl` with relevant chunk labels.
3. Run retrieval and generation evaluation.
4. Update this report with real metric tables and failure cases.
