#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"


def read_config_text() -> str:
    path = SHARED / "rag_config.yaml"
    if not path.exists():
        raise SystemExit("missing shared/rag_config.yaml; run Skill1 first")
    return path.read_text(encoding="utf-8")


def get_value(config: str, key: str, default: str) -> str:
    for line in config.splitlines():
        if line.strip().startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return default


def main() -> None:
    config = read_config_text()
    requirement = (SHARED / "rag_requirement.md").read_text(encoding="utf-8") if (SHARED / "rag_requirement.md").exists() else ""
    strategy = get_value(config, "strategy", "hybrid")
    top_k = get_value(config, "top_k", "5")

    content = f"""# Prompt Pack

Status: ready

Source artifacts:

- `rag_requirement.md`
- `rag_config.yaml`

## Query Rewrite Prompt

You are a query rewriting module for a RAG system.

Input:
- User question
- Conversation history
- Domain hints from `rag_config.yaml`

Rules:
- Preserve the user's intent.
- Expand ambiguous references using conversation history.
- Produce Chinese output when the configured language is `zh`.
- Do not add facts that are not implied by the user.

Output JSON:

```json
{{"rewritten_query":"...", "keywords":["..."], "filters":{{}}, "needs_multi_doc":false}}
```

## Retrieval Planning Prompt

You are a retrieval planner.

Configured retrieval strategy: `{strategy}`.

Input:
- Rewritten query
- Available retrievers
- Metadata schema

Rules:
- Use top-k `{top_k}` unless the question requires multi-document synthesis.
- Prefer hybrid retrieval for ambiguous, long, or terminology-heavy questions.
- Add metadata filters only when the user explicitly constrains source, time, author, file type, or section.

Output JSON:

```json
{{"retrievers":["bm25","vector"], "top_k":{top_k}, "filters":{{}}, "rerank":true}}
```

## Evidence Selection Prompt

You select evidence chunks for answer generation.

Rules:
- Keep only chunks that directly support the answer.
- Remove duplicate or near-duplicate chunks.
- Preserve `doc_id`, `source_path`, `section`, `chunk_id`, and score.
- Mark conflicting evidence instead of hiding it.

Output JSON:

```json
{{"selected":[{{"chunk_id":"...", "reason":"..."}}], "conflicts":[]}}
```

## Answer Generation Prompt

You answer using only selected evidence.

Rules:
- Answer the user question directly.
- Cite every factual claim with chunk references.
- If evidence is incomplete, state what is missing.
- Do not use outside knowledge.
- Keep uncertainty visible.

Output format:

```markdown
答案正文，关键事实后使用 [chunk-id] 引用。

证据来源：
- [chunk-id] document title / section
```

## Citation Prompt

Normalize citations.

Rules:
- Every citation must reference an existing selected chunk.
- Use stable chunk IDs.
- Include source title and section when available.
- Reject citations that point to non-retrieved evidence.

## Refusal Prompt

Refuse or ask for clarification when:

- No retrieved evidence supports the answer.
- The question is outside the configured corpus.
- The retrieved evidence conflicts and cannot be resolved.
- The user requests unsupported private, sensitive, or fabricated claims.

Refusal format:

```markdown
无法基于当前知识库可靠回答。原因：...
可以补充的材料：...
```

## Evaluation Prompt

Evaluate an answer against evidence.

Score:
- Relevance: 1-5
- Faithfulness: 1-5
- Citation accuracy: 1-5
- Completeness: 1-5

Return JSON:

```json
{{"relevance":0, "faithfulness":0, "citation_accuracy":0, "completeness":0, "unsupported_claims":["..."], "missing_evidence":["..."]}}
```

## Requirement Snapshot

```markdown
{requirement[:3000]}
```
"""
    (SHARED / "prompt_pack.md").write_text(content, encoding="utf-8")
    print("wrote shared/prompt_pack.md")


if __name__ == "__main__":
    main()