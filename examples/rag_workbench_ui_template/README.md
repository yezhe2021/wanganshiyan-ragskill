# RAG Workbench UI Template

这是一个可复用的 RAG 前端模板，设计目标是替换默认的朴素页面，让新生成的 RAG Demo 直接拥有一个更像产品原型的三栏工作台界面。

## 目录

```text
examples/rag_workbench_ui_template/
├── index.html
├── index.inline.html
├── static/
│   ├── rag-workbench.css
│   └── rag-workbench.js
└── assets/
    ├── design-reference.png
    └── design-handoff.png
```

## 后端接口约定

模板默认复用当前 `generated-rag-system/server.py` 的接口：

```text
GET  /api/profile
POST /api/query
POST /api/rebuild
```

`/api/query` 请求体：

```json
{
  "query": "用户问题",
  "method": "bm25 | vector | hybrid | rerank",
  "top_k": 5,
  "candidate_k": 50,
  "use_model": true,
  "model": "qwen-plus"
}
```

`/api/query` 返回体建议包含：

```json
{
  "answer": "带引用的回答 [C12] [C27]",
  "hits": [
    {
      "chunk_id": "C12",
      "title": "文档标题",
      "source_path": "xxx.pdf",
      "section": "method",
      "page_start": 1,
      "page_end": 2,
      "text": "证据片段",
      "score": 0.92
    }
  ],
  "trace": {
    "retrieve_ms": 128,
    "rerank_ms": 72,
    "answer_ms": 412
  }
}
```

## 两种使用方式

### 方式 A：未来新项目推荐使用分离版

把本目录复制到新生成 RAG 项目的 `examples/` 或 `frontend/` 下，然后让后端服务静态文件：

```text
frontend/
├── index.html
└── static/
    ├── rag-workbench.css
    └── rag-workbench.js
```

### 方式 B：当前 `server.py` 快速替换用内联版

当前 `server.py` 是把 HTML 页面写在 `HTML = r'''...'''` 里面的，所以可以直接使用 `index.inline.html` 替换原来的 HTML 字符串内容。

推荐使用仓库根目录下的工具脚本：

```bash
python tools/inject_rag_ui_template.py \
  --server generated-rag-system/server.py \
  --template examples/rag_workbench_ui_template/index.inline.html
```

## 设计原则

- 三栏布局：左侧配置，中间问答，右侧证据。
- 证据优先：回答和证据同时可见。
- 保留评测区域：展示延迟、Recall@5、Citation Accuracy。
- 保留 Debug Trace：方便课程展示和实验解释。
- 样式统一：浅灰背景、白色卡片、蓝色主色、圆角组件。
