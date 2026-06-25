# Document Analysis

Status: ready

- Document directory: `document`
- File count: 3
- Extension counts: `{"json": 2, "md": 1}`
- Total size: 907390055 bytes
- PDF pages: 0
- Language: zh
- Scenario: general_knowledge_base
- Scale: small
- Approx tokens: 2447
- Estimated chunks: 5

## Recommended RAG Design

- Document types: json, md
- Granularity: chunk
- Retrieval strategy: bm25
- Chunk size: 700
- Overlap: 120
- Top-k: 5
- Candidate-k before rerank: 20
- Reranker: lightweight coverage reranker
- Embedding: hashing-tfidf baseline; optional multilingual embedding
- Splitter: heading/paragraph-aware splitter
- Citation: cite paper title, page, section, and chunk_id
- Refusal policy: strict

## Files

| File | Type | Size | Pages |
| --- | --- | ---: | ---: |
| dataset_infos.json | json | 188 |  |
| README.md | md | 9182 |  |
| SoulChatCorpus-sft-multi-Turn.json | json | 907380685 |  |
