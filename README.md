# RAG System Designer

`rag-system-designer` is a multi-skill workflow for turning vague RAG needs into a runnable, UI-ready, and evaluable RAG system.

It combines two design directions:

- A formal staged Skill suite: requirement -> prompt pack -> Codex task -> evaluation.
- A corpus-aware implementation path: inspect uploaded documents, infer RAG methods/parameters, generate a runnable Web workbench, and evaluate it.

## Workflow

1. `skill0-rag-orchestrator`: choose the current stage and enforce artifact order.
2. `skill1-rag-requirement-designer`: clarify requirements or analyze uploaded documents, then produce `shared/rag_requirement.md` and `shared/rag_config.yaml`.
3. `skill2-rag-prompt-generator`: convert requirement/config into `shared/prompt_pack.md`.
4. `skill3-rag-codex-builder`: produce `shared/codex_task.md` and implementation guidance.
5. `skill4-rag-auto-evaluator`: produce `shared/evaluation_plan.md` and `shared/evaluation_report.md`.
6. `skill5-rag-ui-designer`: produce `shared/ui_design.md` and UI workbench requirements, defaulting to `examples/rag_workbench_ui_template/`.

New Web RAG systems use `examples/rag_workbench_ui_template/` by default. Static backends use `index.html` plus `static/`; single-file Python backends use `index.inline.html`. Existing generated systems are not migrated automatically.

The `shared/` directory is the contract between skills. Each stage reads previous artifacts and writes the next artifact, so the project forms a closed loop:

`需求澄清 -> 语料分析 -> 提示词生成 -> Codex 实现 -> UI 工作台 -> 自动化评测`

## Quick Demo From Uploaded Documents

```powershell
cd "C:\Users\MYS\Desktop\网安大实验\skill项目开题报告(1)\rag-system-designer"
python skill1-rag-requirement-designer/scripts/analyze_documents.py --document-dir document --requirement "根据上传论文目录自动构建适合该语料的 RAG 系统，要求引用来源和自动评测"
python skill2-rag-prompt-generator/scripts/generate_prompt_pack.py
python skill3-rag-codex-builder/scripts/generate_codex_task.py
python skill5-rag-ui-designer/scripts/generate_ui_spec.py
python skill4-rag-auto-evaluator/scripts/generate_evaluation_plan.py
python skill4-rag-auto-evaluator/scripts/evaluate_artifacts.py
```

## Run The Generated UI

```powershell
cd "C:\Users\MYS\Desktop\网安大实验\skill项目开题报告(1)\rag-system-designer\generated-rag-system"
python server.py --rebuild --host 127.0.0.1 --port 7870
```

Open:

```text
http://127.0.0.1:7870
```

The UI supports BM25, Vector, Hybrid, Rerank, Top-K/Candidate-K controls, DashScope model selection, evidence display, trace chips, citation-aware answers, and index rebuild.

