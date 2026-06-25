# 如何把 RAG Workbench UI 模板放进项目

## 推荐新增目录

在仓库中增加：

```text
examples/
└── rag_workbench_ui_template/
    ├── index.html
    ├── index.inline.html
    ├── static/
    │   ├── rag-workbench.css
    │   └── rag-workbench.js
    └── assets/
        ├── design-reference.png
        └── design-handoff.png
```

同时增加：

```text
tools/
└── inject_rag_ui_template.py
```

## 当前项目替换方式

当前 `generated-rag-system/server.py` 的前端页面是一个内联 HTML 字符串，根路径 `/` 返回这个字符串；后端接口已有 `/api/profile`、`/api/query`、`/api/rebuild`。因此最稳妥的替换方式是：

```bash
python tools/inject_rag_ui_template.py \
  --server generated-rag-system/server.py \
  --template examples/rag_workbench_ui_template/index.inline.html
```

然后运行：

```bash
cd generated-rag-system
python server.py --rebuild --host 127.0.0.1 --port 7870
```

浏览器打开：

```text
http://127.0.0.1:7870
```

## 给 skill5 的补充要求

把下面内容加入 `skill5-rag-ui-designer/SKILL.md` 或生成 UI 规范时使用：

```text
When generating a new RAG UI, prefer the reusable template located at:
examples/rag_workbench_ui_template/

The generated UI should keep the following layout:
1. Top status bar: project title, corpus status, index status, project/user pill.
2. Left control sidebar: retrieval method, model selector, Top-K, Candidate-K, citations switch, debug trace switch, rebuild index button, corpus summary.
3. Center workspace: query input, Run button, grounded answer card, citation tags, trace chips, pipeline timeline, debug trace details.
4. Right evidence panel: evidence search, ranked evidence cards, source/chunk tags, score bar.
5. Bottom/right evaluation snapshot: latency, Recall@5, citation accuracy.

The UI must connect to these backend APIs:
GET /api/profile
POST /api/query
POST /api/rebuild

Use the template unless the user explicitly asks for another style.
```

## 给 skill3 / Codex 的补充要求

把下面内容加入 `skill3-rag-codex-builder` 生成的 Codex task：

```text
Frontend requirement:
Reuse examples/rag_workbench_ui_template as the default frontend template.
If the backend serves a single inline HTML string, use index.inline.html.
If the backend supports static file serving, use index.html plus static/rag-workbench.css and static/rag-workbench.js.
Do not generate a plain default HTML page unless the template cannot be used.
```
