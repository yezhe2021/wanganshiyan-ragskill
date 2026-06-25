---
name: skill1-rag-requirement-designer
description: Clarify and structure RAG system requirements, or analyze an uploaded document directory to infer scenario, data profile, retrieval method, chunking parameters, generation behavior, citations, refusal policy, evaluation plan, and engineering constraints. Use when a user describes a RAG need or points to a corpus directory and needs `rag_requirement.md` plus `rag_config.yaml`.
---

# RAG Requirement Designer

Turn fuzzy RAG ideas or uploaded corpora into an actionable requirement spec and machine-readable config.

## Inputs

- User conversation.
- Existing project files, if any.
- Optional upload directory such as `document/`.
- Optional prior `shared/rag_config.yaml` or `shared/rag_requirement.md`.

## Workflow

1. Inspect local files when a corpus directory exists.
2. Parse the user's request for scenario, data, retrieval, generation, evaluation, and engineering constraints.
3. Fill missing fields with conservative defaults.
4. Prefer `hybrid` retrieval when the user asks for accuracy, source citation, heterogeneous documents, paper QA, or production use.
5. Prefer BM25-only only for small local demos where low cost and no model downloads dominate.
6. Require citation and refusal by default for security, compliance, academic, and knowledge-base use cases.
7. Write:
   - `shared/rag_requirement.md`
   - `shared/rag_config.yaml`

## Corpus-Aware Mode

When the user provides an upload directory, run:

```bash
python skill1-rag-requirement-designer/scripts/analyze_documents.py --document-dir document --requirement "用户需求"
```

The analyzer inspects file types, corpus scale, PDF pages, sampled text, language, and academic/code/table signals. It writes:

- `shared/document_analysis.md`
- `shared/document_analysis.json`
- `shared/rag_requirement.md`
- `shared/rag_config.yaml`

Use these corpus-derived recommendations as the default for Skill2, Skill3, Skill5, and Skill4 unless the user explicitly overrides them.

## Text-Only Requirement Mode

Run:

```bash
python skill1-rag-requirement-designer/scripts/design_requirement.py "用户需求"
```

## Clarify Only What Matters

Cover these dimensions. Infer reasonable defaults from local files when possible.

- Task scenario: enterprise knowledge base, paper QA, report QA, codebase QA, customer support, training assistant.
- Data: formats, language, count, size, update frequency, privacy level.
- Chunking: chunk, section, paragraph, function, table row/column, or hybrid.
- Retrieval: BM25, vector, hybrid, rerank, graph RAG.
- Generation: evidence-only answers, citation style, refusal policy, multi-document synthesis.
- Engineering: local/cloud, CPU/GPU, API/web UI, budget, latency, concurrency.
- Evaluation: gold questions, expected sources, retrieval metrics, answer metrics, faithfulness checks.

## Defaults

- Chinese report or course materials: `chunk_size: 700`, `overlap: 120`.
- English technical documents or papers: `chunk_size: 900`, `overlap: 150`.
- Multi-paper QA: section-aware PDF splitting, Hybrid retrieval, `top_k: 8`, `candidate_k: 30`, rerank enabled.
- Preserve `doc_id`, `title`, `section`, `chunk_id`, `source_path`, and page metadata.
- Require citations for knowledge-base QA unless explicitly unnecessary.
- Prefer local/offline evaluation before LLM-as-judge.

## Completion Check

Before finishing, ensure the config contains enough information for prompt generation, UI design, Codex implementation, and evaluation:

- `project`
- `scenario`
- `data`
- `retrieval`
- `generation`
- `engineering`
- `evaluation`