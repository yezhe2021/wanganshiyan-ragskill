# RAG UI Design

Status: ready

## 1. UI Goal

Build a demo-ready RAG workbench for `general_knowledge_base`. The UI must expose retrieval choices, model generation choices, evidence, citations, and system trace instead of hiding the RAG pipeline behind a single chat box.

## 2. Corpus-Derived Defaults

- File count: 3
- Estimated chunks: 5
- Retrieval strategy: bm25
- Chunk size: 700
- Overlap: 120
- Top-K: 5
- Candidate-K: 20

## 3. First-Screen Layout

Use a three-column desktop workbench:

- Left panel: corpus profile, file list, index health.
- Center panel: query, method selector, model selector, answer, evidence.
- Right panel: method explanation, trace/debug, evaluation status.

On mobile, stack query, answer, evidence, corpus profile, then trace.

## 4. Required Controls

- Retrieval method segmented control: BM25, Vector, Hybrid, Rerank.
- Model dropdown: qwen-plus, qwen-turbo, qwen-max, qwen-long.
- External generation switch: label it clearly as DashScope generation.
- Top-K slider default `5`.
- Candidate-K slider default `20`.
- Rebuild index button.
- Optional prompt export button.

## 5. Required Panels

### Corpus Profile

Show file count, chunk count, chunk size, overlap, average chunk tokens, build time, and document path.

### Answer

Show whether the answer came from:

- local evidence draft, or
- DashScope model generation.

When model generation is used, show model name, latency, and token usage.

### Evidence

Each evidence row must show rank, score, title, page range, section, chunk ID, and preview.

### Trace

Show method, BM25 candidate count, vector candidate count, candidate-k, top-k, model metadata, and errors.

## 6. Safety Requirements

- If `DASHSCOPE_API_KEY` is missing, show a visible error.
- If external model generation is enabled, make clear that retrieved document snippets are sent to DashScope.
- If no evidence is retrieved, trigger refusal behavior instead of hallucinating.
- Keep evidence visible even when model generation fails.

## 7. Visual Direction

- Quiet technical dashboard.
- White panels on light neutral background.
- Teal for primary retrieval/generation actions.
- Blue for model/provider metadata.
- Red only for errors/refusal.
- Use compact typography and stable panel dimensions.
- Do not use a landing-page hero.
