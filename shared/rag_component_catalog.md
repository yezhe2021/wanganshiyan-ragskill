# RAG Component Catalog

## Loader

| Component | Script | Use case |
|---|---|---|
| Batch file scanner | `scan_corpus.py` | Scan DOCX, PDF, Markdown, TXT into JSONL corpus |
| Metadata extractor | `scan_corpus.py` | Preserve source path, title, doc ID, modified time |

## Splitter

| Component | Script | Use case |
|---|---|---|
| Heading-aware chunker | `build_index.py` | Chinese reports, course documents, manuals |
| Chunk tuner | `tune_chunking.py` | Compare chunk size and overlap by retrieval score |

## Index

| Component | Script | Use case |
|---|---|---|
| BM25 index | `build_index.py` | Local, offline, low-cost baseline |
| Hashing TF-IDF vector index | `build_vector_index.py` | No model download, lightweight vector baseline |
| Transformer vector index | `build_vector_index.py --method transformer` | Higher semantic recall when model dependencies are available |

## Retrieval

| Component | Script | Use case |
|---|---|---|
| BM25 retriever | `query_rag.py` | Keyword-heavy questions and reliable baseline |
| Vector retriever | `query_vector_rag.py` | Semantic matching and paraphrased questions |
| Hybrid retriever | `query_hybrid_rag.py` | Combine BM25 precision with vector recall |

## Rerank

| Component | Script | Use case |
|---|---|---|
| Lightweight coverage reranker | `rerank_results.py` | Improve top results without model downloads |
| BGE reranker | optional future model | High-accuracy reranking when latency budget allows |

## Generation

| Component | Script | Use case |
|---|---|---|
| Citation prompt builder | `answer_rag.py` | Evidence-grounded answers with chunk citations |
| Qwen/OpenAI-compatible answer call | `qwen_answer.py` | Local or cloud LLM answer generation |
| Local web UI | `serve_ui.py` | Demonstration, manual review, acceptance testing |

## Evaluation

| Component | Script | Use case |
|---|---|---|
| Retrieval evaluator | `evaluate_retrieval.py` | Recall@k, MRR, precision@k |
| Retriever comparator | `compare_retrievers.py` | Compare BM25, vector, hybrid, hybrid + rerank |

## Selection Rules

| Requirement | Recommended architecture |
|---|---|
| Local, offline, low cost, small Chinese corpus | BM25 + citation prompt |
| Need semantic recall without model downloads | BM25 + hashing vector + hybrid |
| Need high semantic quality and can install models | BM25 + transformer vector + hybrid + rerank |
| Need citation and traceability | Preserve metadata + citation prompt builder |
| Need proof of quality | Retrieval evaluator + retriever comparator + faithfulness checks |
| Enterprise scale | Replace JSON index with Qdrant, pgvector, or another production vector store |
