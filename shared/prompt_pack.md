# Prompt Pack

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
{"rewritten_query":"...", "keywords":["..."], "filters":{}, "needs_multi_doc":false}
```

## Retrieval Planning Prompt

You are a retrieval planner.

Configured retrieval strategy: `bm25`.

Input:
- Rewritten query
- Available retrievers
- Metadata schema

Rules:
- Use top-k `5` unless the question requires multi-document synthesis.
- Prefer hybrid retrieval for ambiguous, long, or terminology-heavy questions.
- Add metadata filters only when the user explicitly constrains source, time, author, file type, or section.

Output JSON:

```json
{"retrievers":["bm25","vector"], "top_k":5, "filters":{}, "rerank":true}
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
{"selected":[{"chunk_id":"...", "reason":"..."}], "conflicts":[]}
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
{"relevance":0, "faithfulness":0, "citation_accuracy":0, "completeness":0, "unsupported_claims":["..."], "missing_evidence":["..."]}
```

## Requirement Snapshot

```markdown
# RAG Requirement

Status: ready

## 1. User Need

根据新的 SoulChatCorpus 文档自动创建适合该语料的 RAG 系统，要求引用来源、方法可选、支持 DashScope 模型回答和自动评测

## 2. Corpus-Derived Scenario

- Document directory: `document`
- File count: 3
- Document types: json, md
- Language: zh
- Scenario: general_knowledge_base
- Scale: small
- PDF pages: 0
- Estimated chunks: 5

## 3. Recommended Retrieval Design

- Granularity: chunk
- Strategy: bm25
- Chunk size: 700
- Overlap: 120
- Top-k: 5
- Candidate-k before rerank: 20
- Rerank: enabled
- Embedding: hashing-tfidf baseline; optional multilingual embedding

Reason: the uploaded corpus is dominated by research PDFs. Multi-paper QA needs exact term matching for paper-specific names and semantic matching for paraphrased concepts, so Hybrid retrieval with reranking is a better default than BM25-only.

## 4. Generation Design

- Answer only from retrieved evidence.
- Cite paper title, page, section, and chunk ID.
- Refuse when evidence is insufficient or contradictory.
- For multi-paper questions, compare agreements, differences, and unresolved uncertainty.

## 5. Engineering Constraints

- Deployment: local first.
- Runtime: Python.
- Parser: PDF extraction with page metadata.
- Splitter: heading/paragraph-aware splitter

## 6. Acceptance Criteria

- Can ingest all files in `document/`.
- Can build BM25 and vector indexes.
- Can run hybrid retrieval and rerank candidates.
- Can return evidence with paper/page/chunk citations.
- Can evaluate retrieval, answer quality, citation accuracy, and latency.

```
