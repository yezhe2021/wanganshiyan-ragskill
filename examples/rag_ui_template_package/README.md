# RAG UI Template Package

这个包用于给 `wanganshiyan-ragskill` 增加一个可复用的前端模板。它的作用是：以后模型 / Codex / skill5 再生成新的 RAG 系统时，不再生成默认丑界面，而是直接复用这个三栏 RAG Workbench。

## 需要复制到仓库的内容

```text
examples/rag_workbench_ui_template/
tools/inject_rag_ui_template.py
docs/rag_ui_template_integration.md
```

## 当前项目一键替换

在仓库根目录运行：

```bash
python tools/inject_rag_ui_template.py \
  --server generated-rag-system/server.py \
  --template examples/rag_workbench_ui_template/index.inline.html
```

然后启动：

```bash
cd generated-rag-system
python server.py --rebuild --host 127.0.0.1 --port 7870
```

## 未来生成新 RAG 时复用

在 `skill5-rag-ui-designer/SKILL.md` 里追加 `docs/skill5_ui_template_append.md` 的内容。

在 `skill3-rag-codex-builder` 的生成任务里追加 `docs/codex_frontend_task_append.md` 的内容。

这样后续生成新 RAG 系统时，模型会优先使用：

```text
examples/rag_workbench_ui_template/index.html
examples/rag_workbench_ui_template/static/rag-workbench.css
examples/rag_workbench_ui_template/static/rag-workbench.js
```

如果后端还是单文件 Python，则使用：

```text
examples/rag_workbench_ui_template/index.inline.html
```
