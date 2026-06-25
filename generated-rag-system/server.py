#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import urllib.error
import urllib.request


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_DOCUMENT_DIR = APP_ROOT.parent / "document"
BUILD_DIR = APP_ROOT / "build"
INDEX_PATH = BUILD_DIR / "rag_index.json"
DASHSCOPE_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = os.environ.get("DASHSCOPE_MODEL", "qwen-plus")


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{1,}|[\u4e00-\u9fff]")
SECTION_RE = re.compile(r"^(abstract|introduction|related work|background|method|methods|approach|design|implementation|evaluation|experiment|experiments|results|discussion|conclusion|references)\b", re.I)
SUPPORTED_TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".csv", ".json", ".jsonl", ".yaml", ".yml", ".py", ".java", ".js", ".ts"}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | {".pdf"}
MAX_JSON_RECORDS = int(os.environ.get("RAG_MAX_JSON_RECORDS", "2000"))
LARGE_FILE_BYTES = 50 * 1024 * 1024


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    source_path: str
    page_start: int
    page_end: int
    section: str
    text: str


def tokenize(text: str) -> list[str]:
    tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_\\-]{1,}", text)]
    cjk_spans = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    for span in cjk_spans:
        tokens.append(span)
        tokens.extend(span[i:i + 2] for i in range(max(0, len(span) - 1)))
        tokens.extend(span[i:i + 3] for i in range(max(0, len(span) - 2)))
    # Keep single CJK chars only as a weak fallback; bigrams/trigrams carry most ranking signal.
    tokens.extend(re.findall(r"[\u4e00-\u9fff]", text))
    return tokens


def stable_id(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:n]


def clean_text(text: str) -> str:
    return text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def is_corpus_file(path: Path) -> bool:
    if any(part.startswith(".") for part in path.parts):
        return False
    if any(part in {"__pycache__", "node_modules"} for part in path.parts):
        return False
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def list_documents(document_dir: Path) -> list[Path]:
    return sorted(p for p in document_dir.rglob("*") if p.is_file() and is_corpus_file(p))


def extract_pdf(path: Path) -> tuple[int, list[tuple[int, str]]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    rows = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            rows.append((i, clean_text(page.extract_text() or "")))
        except Exception:
            rows.append((i, ""))
    return len(reader.pages), rows





def iter_json_array_objects(path: Path, limit: int = MAX_JSON_RECORDS):
    decoder = json.JSONDecoder()
    buffer = ""
    yielded = 0
    started = False
    with path.open("r", encoding="utf-8", errors="replace") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            buffer += chunk
            while True:
                buffer = buffer.lstrip()
                if not started:
                    if buffer.startswith("["):
                        buffer = buffer[1:]
                        started = True
                    else:
                        break
                buffer = buffer.lstrip()
                if buffer.startswith("]"):
                    return
                if buffer.startswith(","):
                    buffer = buffer[1:].lstrip()
                try:
                    obj, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    if len(buffer) > 8 * 1024 * 1024:
                        buffer = buffer[-4 * 1024 * 1024:]
                    break
                yield obj
                yielded += 1
                buffer = buffer[end:]
                if yielded >= limit:
                    return


def conversation_to_text(obj: dict) -> str:
    parts = [f"id: {obj.get('id', '')}", f"topic: {obj.get('topic', '')}"]
    messages = obj.get("messages") or []
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = clean_text(str(msg.get("content", "")))
                if content:
                    parts.append(f"{role}: {content}")
    return "\n".join(parts)


def split_json_dataset(path: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    title = path.stem
    doc_id = f"{stable_id(str(path))}-{stable_id(title)}"
    chunks: list[Chunk] = []
    for obj in iter_json_array_objects(path, MAX_JSON_RECORDS):
        if not isinstance(obj, dict):
            continue
        text = conversation_to_text(obj)
        if len(text) < 20:
            continue
        chunk_no = len(chunks)
        topic = str(obj.get("topic") or "conversation")
        chunks.append(Chunk(
            chunk_id=f"{doc_id}::conv-{chunk_no:05d}",
            doc_id=doc_id,
            title=title,
            source_path=str(path),
            page_start=int(obj.get("id", chunk_no)) if str(obj.get("id", "")).isdigit() else chunk_no,
            page_end=int(obj.get("id", chunk_no)) if str(obj.get("id", "")).isdigit() else chunk_no,
            section=topic,
            text=text,
        ))
    return chunks


def extract_text_file(path: Path) -> tuple[int, list[tuple[int, str]]]:
    text = clean_text(path.read_text(encoding="utf-8", errors="replace"))
    return 1, [(1, text)]
def section_from_text(text: str, previous: str) -> str:
    for raw in text.splitlines()[:12]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            return line.lstrip("#").strip()[:80] or "heading"
        if line.startswith("#"):
            return line.lstrip("#").strip()[:80] or "heading"
        if SECTION_RE.search(line):
            return line[:80]
    return previous or "body"


def split_pages(path: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    title = path.stem
    doc_id = f"{stable_id(str(path))}-{stable_id(title)}"
    if path.suffix.lower() == ".pdf":
        _, pages = extract_pdf(path)
    else:
        _, pages = extract_text_file(path)
    chunks: list[Chunk] = []
    current_section = "body"
    carry: list[tuple[int, str]] = []
    carry_tokens = 0
    step = max(100, chunk_size - overlap)

    def flush(force: bool = False) -> None:
        nonlocal carry, carry_tokens, current_section
        while carry_tokens >= chunk_size or (force and carry):
            take: list[tuple[int, str]] = []
            count = 0
            for page_no, sentence in carry:
                take.append((page_no, sentence))
                count += max(1, len(tokenize(sentence)))
                if count >= chunk_size:
                    break
            text = " ".join(s for _, s in take).strip()
            if text:
                chunk_no = len(chunks)
                pages_in = [p for p, _ in take]
                chunks.append(Chunk(
                    chunk_id=f"{doc_id}::chunk-{chunk_no:04d}",
                    doc_id=doc_id,
                    title=title,
                    source_path=str(path),
                    page_start=min(pages_in),
                    page_end=max(pages_in),
                    section=current_section,
                    text=text,
                ))
            if force:
                carry = []
                carry_tokens = 0
                return
            drop_count = 0
            drop_tokens = 0
            for _, sentence in carry:
                drop_count += 1
                drop_tokens += max(1, len(tokenize(sentence)))
                if drop_tokens >= step:
                    break
            carry = carry[max(1, drop_count):]
            carry_tokens = sum(max(1, len(tokenize(s))) for _, s in carry)

    for page_no, text in pages:
        current_section = section_from_text(text, current_section)
        sentences = re.split(r"(?<=[.!?。！？])\s+|\n{2,}", text)
        for sentence in sentences:
            sentence = clean_text(re.sub(r"\s+", " ", sentence)).strip()
            if len(sentence) < 20:
                continue
            carry.append((page_no, sentence))
            carry_tokens += max(1, len(tokenize(sentence)))
            flush(False)
    flush(True)
    return chunks


def build_index(document_dir: Path, chunk_size: int, overlap: int) -> dict:
    started = time.time()
    files = list_documents(document_dir)
    chunks: list[Chunk] = []
    errors = []
    for path in files:
        try:
            if path.suffix.lower() == ".json" and path.stat().st_size > LARGE_FILE_BYTES:
                chunks.extend(split_json_dataset(path, chunk_size, overlap))
            else:
                chunks.extend(split_pages(path, chunk_size, overlap))
        except Exception as exc:
            errors.append({"file": str(path), "error": str(exc)})

    tokenized = [tokenize(c.text) for c in chunks]
    doc_freq: Counter[str] = Counter()
    for toks in tokenized:
        doc_freq.update(set(toks))
    avg_len = sum(len(toks) for toks in tokenized) / max(1, len(tokenized))

    index = {
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "document_dir": str(document_dir),
        "chunk_size": chunk_size,
        "overlap": overlap,
        "file_count": len(files),
        "chunk_count": len(chunks),
        "json_record_limit": MAX_JSON_RECORDS,
        "avg_chunk_tokens": round(avg_len, 2),
        "build_seconds": round(time.time() - started, 3),
        "errors": errors,
        "chunks": [asdict(c) for c in chunks],
        "doc_freq": dict(doc_freq),
        "tokenized": tokenized,
    }
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return index


def load_index() -> dict | None:
    if not INDEX_PATH.exists():
        return None
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def bm25_scores(query: str, index: dict) -> list[tuple[float, int]]:
    q = tokenize(query)
    tokenized = index["tokenized"]
    df = index["doc_freq"]
    n_docs = max(1, len(tokenized))
    avg_len = index.get("avg_chunk_tokens") or 1
    k1 = 1.5
    b = 0.75
    scores = []
    for i, toks in enumerate(tokenized):
        tf = Counter(toks)
        dl = max(1, len(toks))
        score = 0.0
        for term in q:
            if term not in tf:
                continue
            idf = math.log(1 + (n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
            score += idf * (tf[term] * (k1 + 1)) / (tf[term] + k1 * (1 - b + b * dl / avg_len))
        if score > 0:
            scores.append((score, i))
    return sorted(scores, reverse=True)


def hash_vector(tokens: list[str], dims: int = 512) -> dict[int, float]:
    vec: defaultdict[int, float] = defaultdict(float)
    for tok, count in Counter(tokens).items():
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        sign = 1 if h % 2 == 0 else -1
        vec[h % dims] += sign * (1 + math.log(count))
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1
    return {k: v / norm for k, v in vec.items()}


def cosine_sparse(a: dict[int, float], b: dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def vector_scores(query: str, index: dict) -> list[tuple[float, int]]:
    qv = hash_vector(tokenize(query))
    scores = []
    for i, toks in enumerate(index["tokenized"]):
        score = cosine_sparse(qv, hash_vector(toks))
        if score > 0:
            scores.append((score, i))
    return sorted(scores, reverse=True)


def rrf(lists: list[list[tuple[float, int]]], k: int = 60) -> list[tuple[float, int]]:
    fused: defaultdict[int, float] = defaultdict(float)
    for ranked in lists:
        for rank, (_, idx) in enumerate(ranked, start=1):
            fused[idx] += 1 / (k + rank)
    return sorted(((score, idx) for idx, score in fused.items() if score > 0), reverse=True)


def rerank(query: str, scored: list[tuple[float, int]], index: dict) -> list[tuple[float, int]]:
    q_terms = set(tokenize(query))
    adjusted = []
    for score, idx in scored:
        chunk_terms = set(index["tokenized"][idx])
        coverage = len(q_terms & chunk_terms) / max(1, len(q_terms))
        title_bonus = 0.08 if any(t in index["chunks"][idx]["title"].lower() for t in q_terms) else 0
        adjusted.append((score + coverage * 0.35 + title_bonus, idx))
    return sorted(adjusted, reverse=True)


def search(query: str, method: str, top_k: int, candidate_k: int, index: dict) -> tuple[list[dict], dict]:
    bm25 = bm25_scores(query, index)
    vector = vector_scores(query, index)
    method = method.lower()
    if method == "bm25":
        base = bm25
    elif method == "vector":
        base = vector
    elif method in {"hybrid", "rerank"}:
        base = rrf([bm25, vector])
    else:
        base = rrf([bm25, vector])
    if method == "rerank":
        base = rerank(query, base[:candidate_k], index)

    hits = []
    for rank, (score, idx) in enumerate(base[:top_k], start=1):
        c = index["chunks"][idx]
        hits.append({
            "rank": rank,
            "score": round(score, 5),
            **c,
            "preview": c["text"][:900],
        })
    trace = {
        "method": method,
        "bm25_candidates": len(bm25),
        "vector_candidates": len(vector),
        "candidate_k": candidate_k,
        "top_k": top_k,
    }
    return hits, trace



def make_prompt(query: str, hits: list[dict]) -> str:
    if not hits:
        return f"用户问题：{query}\n\n当前没有检索到证据。请拒答，并说明需要补充哪些论文或材料。"
    evidence_lines = []
    for h in hits[:8]:
        page = f"p.{h['page_start']}" if h["page_start"] == h["page_end"] else f"pp.{h['page_start']}-{h['page_end']}"
        text = re.sub(r"\s+", " ", h["text"]).strip()[:1800]
        evidence_lines.append(
            f"[{h['chunk_id']}]\n"
            f"Title: {h['title']}\n"
            f"Section: {h['section']}\n"
            f"Page: {page}\n"
            f"Evidence: {text}"
        )
    return "\n\n".join([
        "你是一个严谨的知识库 RAG 问答助手。",
        "只能使用给定证据回答，不允许使用外部知识。你正在基于检索到的本地语料片段回答用户问题。",
        "每个关键事实后必须引用 chunk_id，例如 [abc::chunk-0001]。",
        "如果证据不足、互相矛盾或不能回答，要明确拒答并说明缺少什么证据。",
        "用户问题：",
        query,
        "检索证据：",
        "\n\n---\n\n".join(evidence_lines),
        "请用中文回答，必要时保留英文术语。",
    ])


def call_dashscope(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 60) -> tuple[str, dict]:
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set in this process environment")
    endpoint = f"{DASHSCOPE_API_BASE}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a citation-grounded RAG assistant for local knowledge bases."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DashScope HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot connect to DashScope: {exc.reason}") from exc
    data = json.loads(raw)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    meta = {
        "model": model,
        "latency_seconds": round(time.time() - started, 3),
        "usage": usage,
    }
    return content or "[模型未返回内容]", meta


def answer_with_model(query: str, hits: list[dict], model: str = DEFAULT_MODEL) -> dict:
    prompt = make_prompt(query, hits)
    answer, meta = call_dashscope(prompt, model=model)
    return {"answer": answer, "prompt": prompt, "model_meta": meta}
def evidence_locator(hit: dict) -> str:
    if "::conv-" in hit.get("chunk_id", ""):
        return f"record {hit['page_start']}"
    if hit["page_start"] == hit["page_end"]:
        return f"p.{hit['page_start']}"
    return f"pp.{hit['page_start']}-{hit['page_end']}"


def parse_dialogue(text: str) -> dict:
    topic = ""
    m = re.search(r"topic:\s*([^\n]+)", text)
    if m:
        topic = m.group(1).strip()
    turns = []
    for role, content in re.findall(r"\b(user|assistant):\s*(.*?)(?=\n(?:user|assistant):|\Z)", text, flags=re.S):
        clean = re.sub(r"\s+", " ", content).strip()
        if clean:
            turns.append((role, clean))
    user_turns = [content for role, content in turns if role == "user"]
    assistant_turns = [content for role, content in turns if role == "assistant"]
    pairs = []
    for i, (role, content) in enumerate(turns):
        if role != "user":
            continue
        answer = ""
        for next_role, next_content in turns[i + 1:]:
            if next_role == "assistant":
                answer = next_content
                break
            if next_role == "user":
                break
        pairs.append((content, answer))
    return {
        "topic": topic or "未明确",
        "user": user_turns,
        "assistant": assistant_turns,
        "pairs": pairs,
    }


def short_clause(text: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。；,. ") + "..."


def overlap_score(query: str, text: str) -> float:
    q = set(tokenize(query))
    if not q:
        return 0.0
    t = set(tokenize(text))
    return len(q & t) / max(1, len(q))


def best_dialogue_pair(query: str, parsed: dict) -> tuple[str, str, float]:
    best_user = parsed["user"][0] if parsed["user"] else ""
    best_answer = parsed["assistant"][0] if parsed["assistant"] else ""
    best_score = overlap_score(query, best_user + " " + best_answer)
    for user_text, assistant_text in parsed.get("pairs", []):
        score = overlap_score(query, user_text + " " + assistant_text)
        if score > best_score:
            best_user, best_answer, best_score = user_text, assistant_text, score
    return best_user, best_answer, best_score


def infer_strategy_label(answer: str) -> str:
    labels = []
    rules = [
        ("共情确认", ["理解", "明白", "感受", "支持", "不容易"]),
        ("压力来源澄清", ["压力", "原因", "事情", "困扰", "发生"]),
        ("情绪调节建议", ["放松", "呼吸", "运动", "休息", "睡眠", "规划", "倾诉"]),
        ("专业帮助提醒", ["专业", "心理医生", "咨询师", "医生", "帮助"]),
        ("积极鼓励", ["相信", "可以", "勇敢", "努力", "希望"]),
    ]
    for label, markers in rules:
        if any(marker in answer for marker in markers):
            labels.append(label)
    return "、".join(labels[:3]) if labels else "共情回应与一般性支持"


def make_conversation_answer(query: str, hits: list[dict]) -> str:
    candidates = []
    for h in hits[: min(12, len(hits))]:
        parsed = parse_dialogue(h["text"])
        user_need, advice, pair_score = best_dialogue_pair(query, parsed)
        # Blend retriever rank score and question-pair overlap. This removes obvious off-topic dialogue rows.
        combined = pair_score + min(float(h.get("score", 0.0)), 1.0) * 0.08
        candidates.append((combined, pair_score, h, parsed, user_need, advice))
    candidates.sort(key=lambda row: row[0], reverse=True)

    selected = []
    seen_topics = Counter()
    for combined, pair_score, h, parsed, user_need, advice in candidates:
        if pair_score <= 0 and len(selected) >= 3:
            continue
        if seen_topics[parsed["topic"]] >= 2 and len(selected) >= 3:
            continue
        selected.append((h, parsed, user_need, advice, pair_score))
        seen_topics[parsed["topic"]] += 1
        if len(selected) >= 5:
            break

    if not selected:
        return "无法基于当前 SoulChatCorpus 样本可靠回答。没有检索到足够相关的对话证据。"

    topic_counts = Counter(parsed["topic"] for _, parsed, _, _, _ in selected)
    common = "、".join(f"{k}({v})" for k, v in topic_counts.most_common())
    lines = [
        "基于当前检索到的 SoulChat 多轮对话样本，可以做如下归纳回答：",
        "",
        f"与问题最相关的样本主题集中在：{common}。",
        "",
        "综合这些样本，SoulChat 风格的回应通常不是直接给出诊断，而是先承认用户处境，再询问或承接压力来源，最后给出低风险、可执行的调节建议。",
        "",
        "证据要点：",
    ]
    for h, parsed, user_need, advice, pair_score in selected:
        strategy = infer_strategy_label(advice)
        lines.append(
            f"- `{parsed['topic']}` 样本中，相关用户诉求是“{short_clause(user_need, 90)}”；"
            f"助手回应策略偏向“{strategy}”，代表性回应为“{short_clause(advice, 130)}”。"
            f" [{h['chunk_id']}]"
        )
    lines.extend([
        "",
        "使用边界：这些内容来自数据集样本，适合分析共情对话和支持型回复模式；如果用户问题涉及真实心理诊断、治疗或危机干预，应提示寻求专业人士帮助。",
        "",
        "证据来源：",
    ])
    for h, parsed, _, _, _ in selected:
        lines.append(f"- [{h['chunk_id']}] {h['title']} / {parsed['topic']} / {evidence_locator(h)}")
    return "\n".join(lines)


def make_answer(query: str, hits: list[dict]) -> str:
    if not hits:
        return "无法基于当前知识库可靠回答。没有检索到足够相关的证据。"

    if any("::conv-" in h.get("chunk_id", "") for h in hits):
        return make_conversation_answer(query, hits)

    selected = hits[: min(4, len(hits))]
    lines = [
        "基于当前检索证据，可以给出以下回答草稿：",
        "",
    ]
    for h in selected:
        text = re.sub(r"\s+", " ", h["text"]).strip()
        sentences = [x.strip() for x in re.split(r"(?<=[.!?。！？])\s+", text) if x.strip()]
        snippet = " ".join(sentences[:2])[:360] if sentences else text[:360]
        lines.append(f"- {snippet} [{h['chunk_id']}]")
    lines.extend([
        "",
        "证据来源：",
    ])
    for h in selected:
        lines.append(f"- [{h['chunk_id']}] {h['title']} / {h['section']} / {evidence_locator(h)}")
    return "\n".join(lines)

HTML = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RAG System Designer</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #20242c;
      --muted: #657083;
      --line: #dfe4ec;
      --accent: #0f766e;
      --accent-2: #1d4ed8;
      --danger: #b91c1c;
      --shadow: 0 10px 28px rgba(20, 30, 45, .08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font: 14px/1.5 "Inter", "Segoe UI", Arial, sans-serif; color: var(--ink); background: var(--bg); }
    header { height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; border-bottom: 1px solid var(--line); background: rgba(255,255,255,.9); position: sticky; top: 0; z-index: 5; }
    .brand { display:flex; align-items:center; gap: 12px; font-weight: 700; }
    .mark { width: 34px; height: 34px; border-radius: 8px; background: linear-gradient(135deg, var(--accent), var(--accent-2)); display:grid; place-items:center; color:white; }
    .layout { display: grid; grid-template-columns: 320px 1fr 380px; gap: 16px; padding: 16px; max-width: 1600px; margin: 0 auto; }
    aside, main, .right { min-width: 0; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); }
    .panel h2 { font-size: 15px; margin: 0; padding: 14px 16px; border-bottom: 1px solid var(--line); }
    .body { padding: 14px 16px; }
    .stats { display:grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .stat { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: #fbfcfe; }
    .stat b { display:block; font-size: 18px; }
    .muted { color: var(--muted); }
    textarea { width: 100%; min-height: 132px; resize: vertical; border: 1px solid var(--line); border-radius: 8px; padding: 12px; font: inherit; }
    button { border: 1px solid var(--line); background: #fff; color: var(--ink); border-radius: 8px; height: 36px; padding: 0 12px; cursor: pointer; font-weight: 600; }
    button.primary { background: var(--accent); color: white; border-color: var(--accent); }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .methods { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
    .method { height: 42px; }
    .method.active { background: #e6f4f1; border-color: var(--accent); color: #0b5f59; }
    .row { display:flex; gap: 10px; align-items:center; margin-top: 12px; }
    .row label { min-width: 88px; color: var(--muted); }
    input[type=range] { width: 100%; }
    .value { width: 34px; text-align:right; font-variant-numeric: tabular-nums; }
    .actions { display:flex; gap: 10px; margin-top: 14px; }
    .trace { display:flex; flex-wrap:wrap; gap: 8px; margin-top: 12px; }
    .chip { border:1px solid var(--line); background:#f8fafc; border-radius: 999px; padding: 4px 9px; color: var(--muted); }
    .answer { white-space: pre-wrap; background: #fbfcfe; border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-height: 140px; }
    .hit { border-top: 1px solid var(--line); padding: 14px 16px; }
    .hit:first-child { border-top: 0; }
    .hit-head { display:flex; justify-content:space-between; gap: 12px; }
    .rank { font-weight: 800; color: var(--accent); }
    .source { color: var(--muted); font-size: 12px; margin: 6px 0; }
    .preview { color:#303845; }
    .status { color: var(--muted); }
    .files { max-height: 360px; overflow:auto; }
    .file { padding: 9px 0; border-bottom:1px solid var(--line); }
    .file:last-child { border-bottom:0; }
    @media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } header { position: static; } }
  </style>
</head>
<body>
  <header>
    <div class="brand"><div class="mark">R</div><div>RAG System Designer <span class="muted">/ paper QA workbench</span></div></div>
    <div class="status" id="status">初始化中</div>
  </header>
  <div class="layout">
    <aside class="panel">
      <h2>语料画像</h2>
      <div class="body">
        <div class="stats">
          <div class="stat"><span class="muted">Files</span><b id="fileCount">-</b></div>
          <div class="stat"><span class="muted">Chunks</span><b id="chunkCount">-</b></div>
          <div class="stat"><span class="muted">Chunk</span><b id="chunkSize">-</b></div>
          <div class="stat"><span class="muted">Overlap</span><b id="overlap">-</b></div>
        </div>
        <div class="trace" id="profileChips"></div>
      </div>
      <h2>文件</h2>
      <div class="body files" id="files"></div>
    </aside>
    <main class="panel">
      <h2 class="toolbar-title"><span>查询与方法选择</span><span class="badge">BM25 / Vector / Hybrid / Rerank</span></h2>
      <div class="body">
        <textarea id="query" placeholder="例如：Which papers optimize KV cache memory, and how do their methods differ?"></textarea>
        <div class="row"><label>方法</label><div class="methods" id="methods"></div></div>
        <div class="row"><label>Top-K</label><input id="topK" type="range" min="3" max="12" value="8"><span class="value" id="topKVal">8</span></div>
        <div class="row"><label>Candidate-K</label><input id="candidateK" type="range" min="10" max="60" value="30"><span class="value" id="candidateKVal">30</span></div>
        <div class="model-box">
          <div class="model-head">
            <div class="model-title">DashScope 模型生成</div>
            <label class="switch"><input id="useModel" type="checkbox" checked> 启用模型</label>
          </div>
          <div class="row" style="margin-top:0;"><label>模型</label>
            <select id="model">
              <option value="qwen-plus" selected>qwen-plus</option>
              <option value="qwen-turbo">qwen-turbo</option>
              <option value="qwen-max">qwen-max</option>
              <option value="qwen-long">qwen-long</option>
            </select>
          </div>
          <div class="hint">使用环境变量 DASHSCOPE_API_KEY；关闭后只返回本地证据草稿。</div>
        </div>
        <div class="actions">
          <button class="primary" id="run">检索并生成回答</button>
          <button id="rebuild">重建索引</button>
        </div>
        <div class="trace" id="trace"></div>
      </div>
      <h2>回答草稿</h2>
      <div class="body"><div class="answer" id="answer">等待查询。</div></div>
      <h2>证据</h2>
      <div id="hits"></div>
    </main>
    <section class="right panel">
      <h2>方法说明</h2>
      <div class="body">
        <p><b>BM25</b>：适合论文名词、方法名、缩写等精确匹配。</p>
        <p><b>Vector</b>：使用 hashing 向量近似语义召回，无需下载模型。</p>
        <p><b>Hybrid</b>：BM25 + Vector，使用 RRF 融合，适合多论文问答默认方案。</p>
        <p><b>Rerank</b>：先 Hybrid 召回 Candidate-K，再按查询覆盖率和标题命中重排。</p>
      </div>
      <h2>推荐配置</h2>
      <div class="body">
        <div class="trace">
          <span class="chip">paper_qa</span>
          <span class="chip">section_chunk</span>
          <span class="chip">hybrid + rerank</span>
          <span class="chip">citation required</span>
        </div>
      </div>
    </section>
  </div>
  <script>
    const methods = ["BM25", "Vector", "Hybrid", "Rerank"];
    let activeMethod = "Rerank";
    const $ = id => document.getElementById(id);
    function esc(s){ return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
    function renderMethods(){
      $("methods").innerHTML = methods.map(m => `<button class="method ${m===activeMethod?'active':''}" data-m="${m}">${m}</button>`).join("");
      document.querySelectorAll(".method").forEach(b => b.onclick = () => { activeMethod = b.dataset.m; renderMethods(); });
    }
    function bindRange(id, out){ $(id).oninput = () => $(out).textContent = $(id).value; }
    async function api(path, body){
      const res = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body || {})});
      if(!res.ok) throw new Error(await res.text());
      return res.json();
    }
    async function loadProfile(){
      const res = await fetch("/api/profile");
      const data = await res.json();
      $("fileCount").textContent = data.file_count ?? 0;
      $("chunkCount").textContent = data.chunk_count ?? 0;
      $("chunkSize").textContent = data.chunk_size ?? "-";
      $("overlap").textContent = data.overlap ?? "-";
      $("profileChips").innerHTML = [`${data.document_dir}`, `${data.build_seconds ?? 0}s build`, `${data.avg_chunk_tokens ?? 0} avg tokens`].map(x=>`<span class="chip">${esc(x)}</span>`).join("");
      $("files").innerHTML = (data.files || []).map(f => `<div class="file"><b>${esc(f.name)}</b><br><span class="muted">${esc(f.size)} bytes</span></div>`).join("");
      $("status").textContent = data.chunk_count ? "索引就绪" : "需要重建索引";
    }
    async function runQuery(){
      const query = $("query").value.trim();
      if(!query){ $("answer").textContent = "请先输入问题。"; return; }
      $("status").textContent = "检索中";
      $("run").disabled = true;
      try {
        const data = await api("/api/query", { query, method: activeMethod.toLowerCase(), top_k: Number($("topK").value), candidate_k: Number($("candidateK").value), use_model: $("useModel").checked, model: $("model").value || "qwen-plus" });
        $("answer").textContent = data.answer;
        const modelChips = data.model_meta ? Object.entries({model:data.model_meta.model, latency:data.model_meta.latency_seconds + "s", tokens: JSON.stringify(data.model_meta.usage || {})}) : [];
        $("trace").innerHTML = Object.entries(data.trace).concat(modelChips).map(([k,v]) => `<span class="chip">${esc(k)}=${esc(v)}</span>`).join("");
        $("hits").innerHTML = data.hits.map(h => `<div class="hit"><div class="hit-head"><div><span class="rank">#${h.rank}</span> ${esc(h.title)}</div><b>${h.score}</b></div><div class="source">${esc(h.section)} / p.${h.page_start}${h.page_end!==h.page_start?'-'+h.page_end:''}<br>${esc(h.chunk_id)}</div><div class="preview">${esc(h.preview)}</div></div>`).join("") || `<div class="hit muted">没有命中。</div>`;
        $("status").textContent = "完成";
      } catch(e) {
        $("answer").textContent = "请求失败：" + e.message;
        $("status").textContent = "失败";
      } finally {
        $("run").disabled = false;
      }
    }
    async function rebuild(){
      $("status").textContent = "重建索引中";
      $("rebuild").disabled = true;
      try {
        await api("/api/rebuild", { chunk_size: 900, overlap: 150 });
        await loadProfile();
      } catch(e) {
        $("status").textContent = "重建失败";
        alert(e.message);
      } finally {
        $("rebuild").disabled = false;
      }
    }
    renderMethods();
    bindRange("topK", "topKVal"); bindRange("candidateK", "candidateKVal");
    $("run").onclick = runQuery; $("rebuild").onclick = rebuild;
    loadProfile();
  </script>
</body>
</html>'''


class Handler(BaseHTTPRequestHandler):
    document_dir: Path = DEFAULT_DOCUMENT_DIR

    def log_message(self, fmt: str, *args) -> None:
        return

    def send_json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            payload = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == "/api/profile":
            index = load_index()
            files = [{"name": p.name, "size": p.stat().st_size, "type": p.suffix.lower().lstrip(".")} for p in list_documents(self.document_dir)]
            if not index:
                self.send_json({"document_dir": str(self.document_dir), "files": files, "file_count": len(files), "chunk_count": 0})
                return
            self.send_json({
                "document_dir": index["document_dir"],
                "file_count": index["file_count"],
                "chunk_count": index["chunk_count"],
                "chunk_size": index["chunk_size"],
                "overlap": index["overlap"],
                "avg_chunk_tokens": index["avg_chunk_tokens"],
                "build_seconds": index["build_seconds"],
                "files": files,
                "errors": index["errors"],
            })
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        try:
            if path == "/api/rebuild":
                index = build_index(self.document_dir, int(body.get("chunk_size", 900)), int(body.get("overlap", 150)))
                self.send_json({"ok": True, "chunk_count": index["chunk_count"]})
                return
            if path == "/api/query":
                index = load_index()
                if not index:
                    index = build_index(self.document_dir, 900, 150)
                query = str(body.get("query", "")).strip()
                if not query:
                    self.send_json({"error": "query is required"}, 400)
                    return
                hits, trace = search(query, str(body.get("method", "rerank")), int(body.get("top_k", 8)), int(body.get("candidate_k", 30)), index)
                use_model = bool(body.get("use_model", True))
                if use_model:
                    model_result = answer_with_model(query, hits, model=str(body.get("model") or DEFAULT_MODEL))
                    self.send_json({"query": query, "hits": hits, "trace": trace, **model_result})
                else:
                    self.send_json({"query": query, "hits": hits, "trace": trace, "answer": make_answer(query, hits), "answer_mode": "local_draft"})
                return
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)
            return
        self.send_error(404)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the generated RAG workbench UI.")
    parser.add_argument("--document-dir", default=str(DEFAULT_DOCUMENT_DIR))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7870)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    Handler.document_dir = Path(args.document_dir)
    if args.rebuild or not INDEX_PATH.exists():
        print("Building index...")
        index = build_index(Handler.document_dir, 900, 150)
        print(f"Indexed {index['chunk_count']} chunks from {index['file_count']} files.")
        if args.build_only:
            return
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"RAG UI: http://{args.host}:{args.port}")
    print(f"Document dir: {Handler.document_dir}")
    server.serve_forever()


if __name__ == "__main__":
    main()
