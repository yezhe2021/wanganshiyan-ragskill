---
name: skill2-rag-prompt-generator
description: Generate a modular RAG Prompt Pack from `rag_requirement.md`, `rag_config.yaml`, and optional corpus analysis, including query rewrite, retrieval planning, evidence selection, answer generation, citation, refusal, and evaluation prompts. Use after requirements are defined and before Codex implementation planning.
---

# RAG Prompt Generator

Convert `shared/rag_requirement.md` and `shared/rag_config.yaml` into reusable prompts.

## Inputs

- `shared/rag_requirement.md`
- `shared/rag_config.yaml`
- Optional `shared/document_analysis.md`

If requirement or config is missing, ask the orchestrator to run `skill1-rag-requirement-designer` first.

## Prompt Pack Sections

Write `shared/prompt_pack.md` with:

1. Query Rewrite Prompt
2. Retrieval Planning Prompt
3. Evidence Selection Prompt
4. Answer Generation Prompt
5. Citation Prompt
6. Refusal Prompt
7. Evaluation Prompt

## Prompt Rules

- Bind prompts to configured data domain, language, citation policy, refusal policy, and retrieval method.
- Require the model to answer only from retrieved evidence.
- Preserve evidence IDs such as `[doc_id/chunk_id]`.
- Make uncertainty explicit when evidence is insufficient.
- Do not ask the model to invent sources, page numbers, or metrics.
- Include input schema, output schema, constraints, and failure behavior.
- Include placeholders such as `{user_query}`, `{retrieved_evidence}`, `{conversation_history}`, `{citation_format}`, and `{evaluation_rubric}` when helpful.

## Deterministic Script

```bash
python skill2-rag-prompt-generator/scripts/generate_prompt_pack.py
```