#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"


def has_any(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def detect(requirement: str) -> dict:
    text = requirement.lower()
    zh = bool(re.search(r"[\u4e00-\u9fff]", requirement)) or has_any(text, ["qwen", "通义"])

    if has_any(requirement, ["企业", "公司", "内部", "制度", "客服", "知识库"]):
        scenario = "enterprise_knowledge_base"
    elif has_any(requirement, ["论文", "文献", "paper", "academic"]):
        scenario = "paper_qa"
    elif has_any(requirement, ["代码", "仓库", "函数", "接口", "repo"]):
        scenario = "codebase_qa"
    elif has_any(requirement, ["数据库", "表格", "sql", "excel", "csv"]):
        scenario = "structured_data_qa"
    else:
        scenario = "general_knowledge_base"

    doc_types = []
    for name, markers in {
        "pdf": ["pdf", "论文"],
        "docx": ["word", "docx", "报告", "文档"],
        "markdown": ["markdown", "md"],
        "txt": ["txt", "文本"],
        "csv": ["csv", "表格"],
        "database": ["数据库", "sql", "mysql", "postgres"],
        "code": ["代码", "仓库", "python", "java", "js"],
    }.items():
        if has_any(requirement, markers):
            doc_types.append(name)
    if not doc_types:
        doc_types = ["pdf", "docx", "markdown", "txt"]

    large = has_any(requirement, ["海量", "百万", "千万", "上万", "大量"])
    medium = has_any(requirement, ["千", "中等", "部门"])
    scale = "large" if large else ("medium" if medium else "small")

    local = has_any(requirement, ["本地", "离线", "内网", "私有化", "不能联网"])
    cloud = has_any(requirement, ["云", "api", "在线"])
    deployment = "local" if local else ("cloud" if cloud else "local")

    gpu = has_any(requirement, ["gpu", "显卡", "cuda"])
    interface = "web" if has_any(requirement, ["网页", "ui", "界面", "演示"]) else "cli"

    code_like = scenario == "codebase_qa"
    table_like = scenario == "structured_data_qa"
    granularity = "function" if code_like else ("table_row" if table_like else "chunk")

    accuracy = has_any(requirement, ["准确", "召回", "语义", "质量", "复杂", "多文档"])
    graph = has_any(requirement, ["图谱", "graph", "关系"])
    strategy = "graph_rag" if graph else ("hybrid" if accuracy or len(doc_types) > 1 else "bm25")

    return {
        "requirement": requirement,
        "language": "zh" if zh else "mixed",
        "scenario": scenario,
        "doc_types": doc_types,
        "scale": scale,
        "granularity": granularity,
        "strategy": strategy,
        "chunk_size": 900 if code_like else 700,
        "overlap": 150 if code_like else 120,
        "top_k": 8 if large else 5,
        "use_reranker": strategy in {"hybrid", "graph_rag"},
        "require_citation": not has_any(requirement, ["不需要引用", "无需引用"]),
        "refusal_policy": "strict",
        "deployment": deployment,
        "runtime": "python",
        "interface": interface,
        "llm": "qwen-compatible",
        "embedding": "bge-m3" if accuracy and gpu else "hashing-tfidf-baseline",
    }


def yaml_list(items: list[str], indent: int = 4) -> str:
    prefix = " " * indent
    return "\n".join(f"{prefix}- {item}" for item in items)


def write_config(data: dict) -> None:
    content = f"""project:
  name: rag-system-designer
  stage: requirement_ready
scenario:
  type: {data['scenario']}
  language: {data['language']}
data:
  document_types:
{yaml_list(data['doc_types'])}
  estimated_scale: {data['scale']}
  granularity: {data['granularity']}
retrieval:
  strategy: {data['strategy']}
  chunk_size: {data['chunk_size']}
  overlap: {data['overlap']}
  top_k: {data['top_k']}
  use_reranker: {str(data['use_reranker']).lower()}
generation:
  answer_mode: grounded
  require_citation: {str(data['require_citation']).lower()}
  refusal_policy: {data['refusal_policy']}
engineering:
  deployment: {data['deployment']}
  runtime: {data['runtime']}
  interface: {data['interface']}
  llm: {data['llm']}
  embedding: {data['embedding']}
evaluation:
  retrieval_metrics:
    - recall@k
    - mrr
    - ndcg
    - hit_rate
  generation_metrics:
    - exact_match
    - f1
    - rouge_l
    - bleu
    - bertscore
    - llm_as_judge
  faithfulness_metrics:
    - faithfulness
    - groundedness
    - citation_accuracy
    - hallucination_rate
  performance_metrics:
    - latency
    - token_cost
    - throughput
    - failure_rate
"""
    (SHARED / "rag_config.yaml").write_text(content, encoding="utf-8")


def write_requirement(data: dict) -> None:
    content = f"""# RAG Requirement

Status: ready

## 1. User Need

{data['requirement']}

## 2. Scenario

- Type: {data['scenario']}
- Language: {data['language']}
- Main task: grounded knowledge-base question answering

## 3. Data

- Document types: {', '.join(data['doc_types'])}
- Scale: {data['scale']}
- Retrieval granularity: {data['granularity']}
- Metadata requirement: preserve source path, document title, section, chunk ID, and updated time.

## 4. Retrieval Design

- Strategy: {data['strategy']}
- Chunk size: {data['chunk_size']}
- Overlap: {data['overlap']}
- Top-k: {data['top_k']}
- Rerank: {'enabled' if data['use_reranker'] else 'disabled'}

## 5. Generation Design

- Answer mode: grounded answer from retrieved evidence only.
- Citation: {'required' if data['require_citation'] else 'optional'}.
- Refusal: use strict refusal when evidence is missing, conflicting, or out of scope.
- Multi-document synthesis: summarize agreements, conflicts, and source differences.

## 6. Engineering Constraints

- Deployment: {data['deployment']}
- Runtime: {data['runtime']}
- Interface: {data['interface']}
- LLM: {data['llm']}
- Embedding: {data['embedding']}

## 7. Acceptance Criteria

- The system can ingest configured document types.
- The system can build retrieval indexes reproducibly.
- The system can retrieve evidence with stable chunk IDs.
- The system can generate answers with citations and refusal behavior.
- The system can run retrieval, generation, faithfulness, and performance evaluation.
"""
    (SHARED / "rag_requirement.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RAG requirement and config artifacts.")
    parser.add_argument("requirement", help="Natural-language RAG need")
    args = parser.parse_args()

    SHARED.mkdir(parents=True, exist_ok=True)
    data = detect(args.requirement)
    write_requirement(data)
    write_config(data)
    print("wrote shared/rag_requirement.md")
    print("wrote shared/rag_config.yaml")


if __name__ == "__main__":
    main()