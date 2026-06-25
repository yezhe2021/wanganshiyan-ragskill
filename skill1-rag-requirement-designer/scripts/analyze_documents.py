#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"


SUPPORTED_TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".csv", ".json", ".jsonl", ".yaml", ".yml", ".py", ".java", ".js", ".ts"}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | {".pdf"}


def is_corpus_file(path: Path) -> bool:
    if any(part.startswith(".") for part in path.parts):
        return False
    if any(part in {"__pycache__", "node_modules"} for part in path.parts):
        return False
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


ACADEMIC_MARKERS = [
    "abstract", "introduction", "related work", "method", "evaluation",
    "experiment", "conclusion", "references", "arxiv", "attention",
    "transformer", "token", "cache", "retrieval", "benchmark",
]


def read_pdf_sample(path: Path, max_pages: int = 3) -> tuple[int, str]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        return 0, f"[pypdf unavailable: {exc}]"

    try:
        reader = PdfReader(str(path))
        pages = len(reader.pages)
        parts = []
        for page in reader.pages[:max_pages]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return pages, "\n".join(parts)
    except Exception as exc:
        return 0, f"[pdf read failed: {exc}]"


def safe_text_sample(path: Path, limit: int = 8000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    letters = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", text))
    return cjk / max(letters, 1)


def tokenish_count(text: str) -> int:
    english_words = re.findall(r"[A-Za-z][A-Za-z0-9_\-]+", text)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return len(english_words) + len(cjk_chars)


def infer_profile(document_dir: Path) -> dict:
    files = [p for p in document_dir.rglob("*") if p.is_file() and is_corpus_file(p)]
    ext_counts = Counter(p.suffix.lower().lstrip(".") or "no_ext" for p in files)
    total_bytes = sum(p.stat().st_size for p in files)

    samples: list[str] = []
    pdf_pages = 0
    file_rows = []
    read_errors = []

    for path in files:
        ext = path.suffix.lower()
        sample = ""
        pages = None
        if ext == ".pdf":
            pages, sample = read_pdf_sample(path)
            pdf_pages += pages
        elif ext in SUPPORTED_TEXT_EXTENSIONS:
            sample = safe_text_sample(path)
        else:
            sample = ""

        if sample.startswith("[") and "failed" in sample:
            read_errors.append({"file": str(path), "error": sample})
        samples.append(sample[:4000])
        file_rows.append({
            "name": path.name,
            "extension": ext.lstrip(".") or "no_ext",
            "bytes": path.stat().st_size,
            "pages": pages,
        })

    combined = "\n".join(samples)
    lowered = combined.lower()
    language = "zh" if cjk_ratio(combined) > 0.2 else "en"

    academic_score = sum(1 for marker in ACADEMIC_MARKERS if marker in lowered)
    code_score = sum(1 for marker in ["def ", "class ", "import ", "function ", "public static", "package "] if marker in lowered)
    table_score = sum(1 for marker in [",", "\t", "| ---", "table "] if marker in lowered)

    if ext_counts.get("pdf", 0) >= max(1, len(files) * 0.6) and academic_score >= 4:
        scenario = "paper_qa"
    elif code_score >= 3:
        scenario = "codebase_qa"
    elif table_score >= 4 and any(ext in ext_counts for ext in ["csv", "xlsx"]):
        scenario = "structured_data_qa"
    else:
        scenario = "general_knowledge_base"

    approx_tokens = tokenish_count(combined)
    # Extrapolate from sampled pages for PDFs. Keep this rough and explainable.
    sampled_pdf_pages = min(ext_counts.get("pdf", 0) * 3, max(pdf_pages, 1))
    if pdf_pages and sampled_pdf_pages:
        approx_tokens = int(approx_tokens * (pdf_pages / sampled_pdf_pages))
    approx_tokens = max(approx_tokens, len(files) * 500)

    if len(files) <= 20 and approx_tokens < 500_000:
        scale = "small"
    elif len(files) <= 300 and approx_tokens < 5_000_000:
        scale = "medium"
    else:
        scale = "large"

    mostly_pdf = ext_counts.get("pdf", 0) >= max(1, len(files) * 0.8)
    if scenario == "paper_qa" and language == "en":
        chunk_size = 900
        overlap = 150
        granularity = "section_chunk"
    elif language == "zh":
        chunk_size = 700
        overlap = 120
        granularity = "chunk"
    else:
        chunk_size = 800
        overlap = 140
        granularity = "chunk"

    multi_doc = len(files) >= 5
    semantic_needed = scenario in {"paper_qa", "codebase_qa"} or multi_doc
    strategy = "hybrid" if semantic_needed else "bm25"
    top_k = 8 if multi_doc else 5
    candidate_k = 30 if multi_doc else 20
    estimated_chunks = math.ceil(approx_tokens / max(1, chunk_size - overlap))

    if scenario == "paper_qa":
        embedding = "BAAI/bge-m3 or intfloat/e5-base-v2; hashing-tfidf fallback"
        reranker = "BAAI/bge-reranker-base optional; lightweight coverage reranker fallback"
        splitter = "PDF section-aware splitter, preserve title/page/section"
    elif scenario == "codebase_qa":
        embedding = "code-aware embedding optional; hashing-tfidf fallback"
        reranker = "symbol/query coverage reranker"
        splitter = "function/class-aware splitter"
    else:
        embedding = "hashing-tfidf baseline; optional multilingual embedding"
        reranker = "lightweight coverage reranker"
        splitter = "heading/paragraph-aware splitter"

    return {
        "document_dir": str(document_dir),
        "file_count": len(files),
        "extension_counts": dict(ext_counts),
        "total_bytes": total_bytes,
        "pdf_pages": pdf_pages,
        "language": language,
        "scenario": scenario,
        "scale": scale,
        "approx_tokens": approx_tokens,
        "estimated_chunks": estimated_chunks,
        "recommended": {
            "document_types": sorted(dict(ext_counts).keys()),
            "granularity": granularity,
            "retrieval_strategy": strategy,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "top_k": top_k,
            "candidate_k": candidate_k,
            "use_reranker": True,
            "embedding": embedding,
            "reranker": reranker,
            "splitter": splitter,
            "citation": "cite paper title, page, section, and chunk_id",
            "refusal_policy": "strict",
        },
        "files": file_rows,
        "read_errors": read_errors,
    }


def yaml_list(items: list[str], indent: int = 4) -> str:
    prefix = " " * indent
    return "\n".join(f"{prefix}- {item}" for item in items)


def write_outputs(profile: dict, requirement: str) -> None:
    SHARED.mkdir(parents=True, exist_ok=True)
    rec = profile["recommended"]
    doc_types = rec["document_types"]

    analysis_md = [
        "# Document Analysis",
        "",
        "Status: ready",
        "",
        f"- Document directory: `{profile['document_dir']}`",
        f"- File count: {profile['file_count']}",
        f"- Extension counts: `{json.dumps(profile['extension_counts'], ensure_ascii=False)}`",
        f"- Total size: {profile['total_bytes']} bytes",
        f"- PDF pages: {profile['pdf_pages']}",
        f"- Language: {profile['language']}",
        f"- Scenario: {profile['scenario']}",
        f"- Scale: {profile['scale']}",
        f"- Approx tokens: {profile['approx_tokens']}",
        f"- Estimated chunks: {profile['estimated_chunks']}",
        "",
        "## Recommended RAG Design",
        "",
        f"- Document types: {', '.join(doc_types)}",
        f"- Granularity: {rec['granularity']}",
        f"- Retrieval strategy: {rec['retrieval_strategy']}",
        f"- Chunk size: {rec['chunk_size']}",
        f"- Overlap: {rec['overlap']}",
        f"- Top-k: {rec['top_k']}",
        f"- Candidate-k before rerank: {rec['candidate_k']}",
        f"- Reranker: {rec['reranker']}",
        f"- Embedding: {rec['embedding']}",
        f"- Splitter: {rec['splitter']}",
        f"- Citation: {rec['citation']}",
        f"- Refusal policy: {rec['refusal_policy']}",
        "",
        "## Files",
        "",
        "| File | Type | Size | Pages |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in profile["files"]:
        analysis_md.append(f"| {row['name']} | {row['extension']} | {row['bytes']} | {row['pages'] or ''} |")
    if profile["read_errors"]:
        analysis_md.extend(["", "## Read Errors", ""])
        for err in profile["read_errors"]:
            analysis_md.append(f"- `{err['file']}`: {err['error']}")

    (SHARED / "document_analysis.md").write_text("\n".join(analysis_md) + "\n", encoding="utf-8")
    (SHARED / "document_analysis.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    config = f"""project:
  name: rag-system-designer
  stage: requirement_ready
scenario:
  type: {profile['scenario']}
  language: {profile['language']}
data:
  document_dir: "{profile['document_dir']}"
  document_types:
{yaml_list(doc_types)}
  estimated_scale: {profile['scale']}
  estimated_tokens: {profile['approx_tokens']}
  estimated_chunks: {profile['estimated_chunks']}
  granularity: {rec['granularity']}
retrieval:
  strategy: {rec['retrieval_strategy']}
  chunk_size: {rec['chunk_size']}
  overlap: {rec['overlap']}
  top_k: {rec['top_k']}
  candidate_k: {rec['candidate_k']}
  use_reranker: {str(rec['use_reranker']).lower()}
  embedding: "{rec['embedding']}"
  reranker: "{rec['reranker']}"
generation:
  answer_mode: grounded
  require_citation: true
  citation_policy: "{rec['citation']}"
  refusal_policy: {rec['refusal_policy']}
engineering:
  deployment: local
  runtime: python
  interface: cli
  llm: qwen-compatible
  splitter: "{rec['splitter']}"
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
    (SHARED / "rag_config.yaml").write_text(config, encoding="utf-8")

    req = f"""# RAG Requirement

Status: ready

## 1. User Need

{requirement}

## 2. Corpus-Derived Scenario

- Document directory: `{profile['document_dir']}`
- File count: {profile['file_count']}
- Document types: {', '.join(doc_types)}
- Language: {profile['language']}
- Scenario: {profile['scenario']}
- Scale: {profile['scale']}
- PDF pages: {profile['pdf_pages']}
- Estimated chunks: {profile['estimated_chunks']}

## 3. Recommended Retrieval Design

- Granularity: {rec['granularity']}
- Strategy: {rec['retrieval_strategy']}
- Chunk size: {rec['chunk_size']}
- Overlap: {rec['overlap']}
- Top-k: {rec['top_k']}
- Candidate-k before rerank: {rec['candidate_k']}
- Rerank: enabled
- Embedding: {rec['embedding']}

Reason: the uploaded corpus is dominated by research PDFs. Multi-paper QA needs exact term matching for paper-specific names and semantic matching for paraphrased concepts, so Hybrid retrieval with reranking is a better default than BM25-only.

## 4. Generation Design

- Answer only from retrieved evidence.
- Cite paper title, page, section, and chunk ID.
- Refuse when evidence is insufficient or contradictory.
- For multi-paper questions, compare agreements, differences, and unresolved uncertainty.

## 5. Engineering Constraints

- Deployment: local first.
- Runtime: Python.
- Parser: PDF extraction with page metadata.
- Splitter: {rec['splitter']}

## 6. Acceptance Criteria

- Can ingest all files in `document/`.
- Can build BM25 and vector indexes.
- Can run hybrid retrieval and rerank candidates.
- Can return evidence with paper/page/chunk citations.
- Can evaluate retrieval, answer quality, citation accuracy, and latency.
"""
    (SHARED / "rag_requirement.md").write_text(req, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze uploaded documents and recommend RAG methods/parameters.")
    parser.add_argument("--document-dir", default=str(ROOT / "document"), help="Directory containing uploaded files")
    parser.add_argument("--requirement", default="根据上传目录自动构建适合该语料的 RAG 系统", help="User need to record in the requirement artifact")
    parser.add_argument("--json", action="store_true", help="Print JSON profile")
    args = parser.parse_args()

    document_dir = Path(args.document_dir)
    if not document_dir.exists():
        raise SystemExit(f"document directory does not exist: {document_dir}")
    profile = infer_profile(document_dir)
    write_outputs(profile, args.requirement)
    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        rec = profile["recommended"]
        print(f"scenario={profile['scenario']}")
        print(f"language={profile['language']}")
        print(f"files={profile['file_count']} pdf_pages={profile['pdf_pages']} scale={profile['scale']}")
        print(f"strategy={rec['retrieval_strategy']} chunk_size={rec['chunk_size']} overlap={rec['overlap']} top_k={rec['top_k']} candidate_k={rec['candidate_k']}")
        print("wrote shared/document_analysis.md")
        print("wrote shared/rag_requirement.md")
        print("wrote shared/rag_config.yaml")


if __name__ == "__main__":
    main()