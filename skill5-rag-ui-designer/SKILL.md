---
name: skill5-rag-ui-designer
description: Design and generate UI requirements for runnable RAG systems, especially paper QA and knowledge-base QA workbenches. Use when a RAG project needs a polished Web UI with corpus profiling, retrieval method selection, model selection, parameter controls, evidence display, citation-aware answers, trace/debug panels, index rebuild controls, and evaluation visibility.
---

# RAG UI Designer

Use this skill to turn the RAG workflow into an inspectable, demo-ready Web UI.

## Inputs

- `shared/rag_config.yaml`
- `shared/document_analysis.md` or `shared/document_analysis.json`
- `shared/prompt_pack.md`
- Default reusable frontend: `examples/rag_workbench_ui_template/`
- Optional existing UI implementation. Preserve it unless the user explicitly requests migration.

## Output

- `shared/ui_design.md`
- Optional frontend implementation tasks appended to `shared/codex_task.md`

## Default Template

Use `examples/rag_workbench_ui_template/` by default unless the user explicitly requests another visual system.

- Use `index.html` with `static/rag-workbench.css` and `static/rag-workbench.js` when the generated backend serves static files.
- Use `index.inline.html` when the generated backend embeds one HTML string.
- Connect the template to `GET /api/profile`, `POST /api/query`, and `POST /api/rebuild`.
- Preserve the template's three-column workbench, evidence cards, citation controls, trace timeline, and evaluation snapshot.
- Adapt labels, defaults, methods, models, and corpus metadata from `shared/rag_config.yaml` and `shared/document_analysis.*`.
- Do not generate a plain fallback page when this template is available.
- Do not modify an already generated RAG system unless the user explicitly asks to apply the template to it.

## Required UI Zones

Design the first screen as a working RAG console, not a landing page.

1. Corpus profile: file count, document types, chunk count, chunk size, overlap, build time.
2. Query panel: large question input and clear run button.
3. Retrieval method selector: BM25, Vector, Hybrid, Rerank, and Graph RAG if configured.
4. Model selector: provider, model dropdown, API-key status, and local/external generation toggle.
5. Parameter controls: Top-K, Candidate-K, chunk size, overlap, rerank toggle.
6. Answer panel: model answer, refusal state, citation status, token/latency metadata.
7. Evidence panel: ranked chunks with score, paper/title, page, section, chunk ID, and preview.
8. Trace/debug panel: retrieval method, candidate counts, fusion/rerank steps, prompt preview.
9. Operations: rebuild index, refresh corpus, export prompt, export evaluation report.

## Design Rules

- Prefer dense, work-focused dashboard layout over decorative marketing layout.
- Keep method and model selection visually prominent.
- Make external model use explicit because retrieved local document text may be sent to a provider.
- Show the no-model fallback clearly: local evidence draft.
- Every evidence card must expose `chunk_id`, source, page/section, score, and preview.
- Do not hide retrieval trace; it is part of the RAG system's explainability.
- Use restrained colors with at least two functional accent colors, not a one-hue palette.
- Avoid nested cards. Use panels for major zones and list rows for evidence.
- Keep responsive behavior: desktop three-column workbench, mobile stacked panels.

## Deterministic Script

Run:

```bash
python skill5-rag-ui-designer/scripts/generate_ui_spec.py
```

The script reads shared artifacts and writes `shared/ui_design.md`.

