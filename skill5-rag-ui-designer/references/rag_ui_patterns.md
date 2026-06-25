# RAG UI Patterns

## Workbench Layout

Use a three-zone desktop layout:

- Left: corpus profile, file list, index health.
- Center: question input, method controls, answer, evidence list.
- Right: method explanation, model settings, trace/debug, evaluation status.

On mobile, stack in this order:

1. Query and method controls
2. Answer
3. Evidence
4. Corpus profile
5. Trace and operations

## Controls

- Retrieval method: segmented buttons for BM25, Vector, Hybrid, Rerank, Graph.
- Model: dropdown for `qwen-plus`, `qwen-turbo`, `qwen-max`, `qwen-long`, plus optional custom text field.
- External generation: explicit checkbox or switch.
- Top-K and Candidate-K: sliders with numeric readouts.
- Rebuild index: secondary action button with loading state.

## States

- No index: show rebuild action and corpus path.
- Indexing: show progress or busy state.
- Retrieval success: show trace chips and evidence rows.
- No evidence: show refusal-ready state.
- Missing API key: show `DASHSCOPE_API_KEY` missing, do not fail silently.
- External API error: show provider HTTP error summary and keep evidence visible.

## Evidence Row

Required fields:

- rank
- score
- title
- page range
- section
- chunk ID
- preview text

## Answer Requirements

- Show whether answer came from local draft or model.
- Show model name, latency, and usage when available.
- Preserve citations in answer text.
- Keep evidence visible below the answer for auditability.