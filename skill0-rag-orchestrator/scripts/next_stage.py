#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"
ORDER = [
    ("requirement", ["rag_requirement.md", "rag_config.yaml"], "skill1-rag-requirement-designer"),
    ("prompt_pack", ["prompt_pack.md"], "skill2-rag-prompt-generator"),
    ("codex_task", ["codex_task.md"], "skill3-rag-codex-builder"),
    ("evaluation_plan", ["evaluation_plan.md"], "skill4-rag-auto-evaluator"),
    ("evaluation_report", ["evaluation_report.md"], "skill4-rag-auto-evaluator"),
]


def ready(name: str) -> bool:
    path = SHARED / name
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return "Status: ready" in text or "stage: requirement_ready" in text


def main() -> None:
    for stage, files, skill in ORDER:
        missing = [name for name in files if not ready(name)]
        if missing:
            print(f"current_stage={stage}")
            print(f"next_skill={skill}")
            print("missing_or_not_ready=" + ",".join(missing))
            return
    print("current_stage=complete")
    print("next_skill=none")
    print("missing_or_not_ready=")


if __name__ == "__main__":
    main()