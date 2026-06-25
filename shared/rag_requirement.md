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
