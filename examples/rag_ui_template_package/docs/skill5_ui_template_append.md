# 可追加到 skill5-rag-ui-designer/SKILL.md 的内容

## Reusable UI Template Rule

When producing `shared/ui_design.md` or frontend implementation guidance, prefer the reusable UI template at:

```text
examples/rag_workbench_ui_template/
```

The default generated RAG UI should use a polished three-column workbench layout:

1. Top status bar: project title, corpus status, index status, project/user pill.
2. Left control sidebar: retrieval method, model selector, Top-K, Candidate-K, citations switch, debug trace switch, rebuild index button, corpus summary.
3. Center workspace: query input, Run button, grounded answer card, citation tags, trace chips, pipeline timeline, debug trace details.
4. Right evidence panel: evidence search, ranked evidence cards, source/chunk tags, score bar.
5. Evaluation snapshot: latency, Recall@5, citation accuracy.

The UI should connect to these backend APIs:

```text
GET  /api/profile
POST /api/query
POST /api/rebuild
```

If the target backend serves static files, use:

```text
index.html
static/rag-workbench.css
static/rag-workbench.js
```

If the target backend only serves a single inline HTML string, use:

```text
index.inline.html
```

Do not generate a plain default HTML page unless the template cannot be used.
