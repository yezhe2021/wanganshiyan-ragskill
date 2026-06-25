# 可追加到 skill3-rag-codex-builder 生成任务中的内容

## Frontend Template Requirement

Reuse the provided RAG Workbench UI template as the default frontend.

Template path:

```text
examples/rag_workbench_ui_template/
```

Implementation rules:

1. Preserve the backend retrieval and generation logic.
2. Replace only the frontend page unless API shape must be normalized.
3. Connect the UI to:
   - `GET /api/profile`
   - `POST /api/query`
   - `POST /api/rebuild`
4. Use `index.inline.html` when the backend stores HTML in a Python string.
5. Use `index.html` + `static/` when the backend can serve static frontend files.
6. Keep evidence cards, citation tags, trace chips, and evaluation snapshot visible.
7. Do not remove debug trace, because it is useful for course demonstration and RAG evaluation.
