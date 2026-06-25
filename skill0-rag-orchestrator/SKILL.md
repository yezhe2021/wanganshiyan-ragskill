---
name: skill0-rag-orchestrator
description: Coordinate a multi-stage RAG system design workflow from vague requirements or uploaded documents to requirement spec, prompt pack, Codex build task, polished UI workbench, runnable system, and evaluation report. Use when the user asks to build, redesign, continue, improve UI, or evaluate a RAG workflow and the current stage must be identified.
---

# RAG Orchestrator

Coordinate the RAG System Designer suite. Inspect artifacts, route to the right skill, and keep outputs flowing in order.

## Stage Contract

The shared artifacts are the source of truth:

1. `shared/rag_requirement.md` and `shared/rag_config.yaml`
2. `shared/document_analysis.md` and `shared/document_analysis.json` when a corpus directory exists
3. `shared/prompt_pack.md`
4. `shared/codex_task.md`
5. `shared/ui_design.md`
6. `shared/evaluation_plan.md`
7. `shared/evaluation_report.md`

Do not skip a stage if its required input artifact is missing or still marked as `draft`, unless the user explicitly asks for a partial artifact.

## Stage Routing

| User state | Next skill | Required output |
|---|---|---|
| Vague idea such as "make a knowledge-base QA system" | `skill1-rag-requirement-designer` | `shared/rag_requirement.md`, `shared/rag_config.yaml` |
| User provides an upload/document directory | `skill1-rag-requirement-designer` corpus-aware mode | `shared/document_analysis.*`, `shared/rag_requirement.md`, `shared/rag_config.yaml` |
| Has requirements/config and wants prompts | `skill2-rag-prompt-generator` | `shared/prompt_pack.md` |
| Has requirement/config/prompt pack and wants implementation | `skill3-rag-codex-builder` | `shared/codex_task.md`, project scaffold guidance |
| User asks for better UI, method buttons, model controls, or demo workbench | `skill5-rag-ui-designer` | `shared/ui_design.md` |
| Has a running or partially running RAG system | `skill4-rag-auto-evaluator` | `shared/evaluation_plan.md`, `shared/evaluation_report.md` |
| User asks for full closed loop | Run Skill1 -> Skill2 -> Skill3 -> Skill5 -> Skill4 | All shared artifacts |

## Workflow

1. Inspect existing artifacts before asking questions.
2. If `shared/rag_config.yaml` exists, treat it as the source of truth unless the user asks to revise it.
3. If a stage input is missing, route backward to the earliest missing stage.
4. Preserve domain constraints: data security, local/cloud deployment, model choice, language, scale, latency, UI mode, and citation policy.
5. Reuse local runnable assets when available instead of giving generic RAG advice.
6. After each stage, state the next concrete action and the artifact just produced.

## Existing Project Reuse

When a project already contains runnable RAG scripts or UI code, reuse them as implementation assets. Prefer:

- `skill3-rag-codex-builder/assets/rag-project-template/scripts/` for baseline RAG scripts.
- `examples/rag_workbench_ui_template/` as the default frontend for newly generated Web RAG systems.
- `skill5-rag-ui-designer/references/rag_ui_patterns.md` for UI rules.
- Existing `generated-rag-system/` implementations only as references; do not modify them unless explicitly requested.

## Output

Always state:

- Current stage
- Missing artifacts
- Next skill to run
- Exact script command if a deterministic script exists
