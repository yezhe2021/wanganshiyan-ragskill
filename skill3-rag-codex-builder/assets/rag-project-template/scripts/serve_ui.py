#!/usr/bin/env python3
"""Serve a small local web UI for querying a RAG index."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Local RAG Console</title>
  <style>
    :root { color-scheme: light; --line:#d8dee8; --ink:#172033; --muted:#647084; --bg:#f6f7f9; --panel:#ffffff; --accent:#0f766e; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; color: var(--ink); background: var(--bg); }
    header { border-bottom: 1px solid var(--line); background: var(--panel); }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 18px 20px; }
    h1 { margin: 0; font-size: 22px; font-weight: 650; }
    .meta { color: var(--muted); font-size: 13px; margin-top: 4px; }
    main { display: grid; grid-template-columns: 380px 1fr; gap: 18px; max-width: 1180px; margin: 0 auto; padding: 18px 20px; }
    section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }
    .panel { padding: 16px; }
    label { display:block; font-size: 13px; font-weight: 600; margin-bottom: 8px; }
    textarea, input { width:100%; border:1px solid var(--line); border-radius:6px; padding:10px; font: inherit; background:#fff; }
    textarea { min-height: 150px; resize: vertical; }
    .row { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:12px; }
    input[type=number] { max-width: 92px; }
    button { border: 0; border-radius: 6px; padding: 10px 13px; font-weight: 650; color: #fff; background: var(--accent); cursor:pointer; }
    button.secondary { color: var(--ink); background:#e9edf3; }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .tabs { display:flex; border-bottom:1px solid var(--line); }
    .tab { padding: 12px 14px; background: transparent; color: var(--muted); border-radius:0; border-right:1px solid var(--line); }
    .tab.active { color: var(--ink); background:#fff; }
    .result { border-bottom:1px solid var(--line); padding:14px 16px; }
    .result:last-child { border-bottom:0; }
    .rank { font-weight: 700; color: var(--accent); }
    .source { color: var(--muted); font-size: 13px; margin: 5px 0 8px; word-break: break-all; }
    .text { line-height: 1.62; white-space: pre-wrap; }
    pre { margin:0; padding:16px; white-space: pre-wrap; line-height:1.55; font-family: Consolas, "Courier New", monospace; font-size:13px; }
    .hidden { display:none; }
    .empty { padding:30px 16px; color:var(--muted); }
    @media (max-width: 860px) { main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header><div class="wrap"><h1>Local RAG Console</h1><div class="meta" id="meta">索引已加载，可检索本地文档证据</div></div></header>
  <main>
    <section class="panel">
      <label for="query">问题</label>
      <textarea id="query" placeholder="例如：项目的研究内容和创新点是什么？"></textarea>
      <div class="row">
        <label for="topk" style="margin:0;">Top-K</label>
        <input id="topk" type="number" min="1" max="20" value="5" />
        <button id="search">检索</button>
        <button id="prompt" class="secondary">生成 Prompt</button>
        <button id="answer" class="secondary">调用 Qwen</button>
      </div>
      <div class="meta" id="status" style="margin-top:12px;">输入问题后开始。</div>
    </section>
    <section>
      <div class="tabs">
        <button class="tab active" data-tab="hits">检索证据</button>
        <button class="tab" data-tab="ragprompt">RAG Prompt</button>
        <button class="tab" data-tab="finalanswer">Qwen 回答</button>
      </div>
      <div id="hits"><div class="empty">暂无检索结果。</div></div>
      <pre id="ragprompt" class="hidden">暂无 Prompt。</pre>
      <pre id="finalanswer" class="hidden">暂无回答。</pre>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    const status = $("status");
    const hits = $("hits");
    const promptBox = $("ragprompt");
    const answerBox = $("finalanswer");
    function setTab(name) {
      document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
      hits.classList.toggle("hidden", name !== "hits");
      promptBox.classList.toggle("hidden", name !== "ragprompt");
      answerBox.classList.toggle("hidden", name !== "finalanswer");
    }
    document.querySelectorAll(".tab").forEach(t => t.onclick = () => setTab(t.dataset.tab));
    async function post(path) {
      const query = $("query").value.trim();
      const top_k = Number($("topk").value || 5);
      if (!query) { status.textContent = "请先输入问题。"; return null; }
      status.textContent = "处理中...";
      const res = await fetch(path, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({query, top_k}) });
      if (!res.ok) throw new Error(await res.text());
      status.textContent = "完成。";
      return await res.json();
    }
    $("search").onclick = async () => {
      try {
        const data = await post("/api/query");
        if (!data) return;
        hits.innerHTML = data.hits.map(h => `<div class="result"><div><span class="rank">#${h.rank}</span> score=${h.score}</div><div class="source">${h.doc_id} / ${escapeHtml(h.section || "")}<br>${h.chunk_id}</div><div class="text">${escapeHtml(h.text.slice(0, 900))}</div></div>`).join("") || "<div class='empty'>没有命中。</div>";
        setTab("hits");
      } catch (err) { status.textContent = "错误：" + err.message; }
    };
    $("prompt").onclick = async () => {
      try {
        const data = await post("/api/prompt");
        if (!data) return;
        promptBox.textContent = data.prompt;
        setTab("ragprompt");
      } catch (err) { status.textContent = "错误：" + err.message; }
    };
    $("answer").onclick = async () => {
      try {
        const data = await post("/api/answer");
        if (!data) return;
        answerBox.textContent = data.answer;
        promptBox.textContent = data.prompt;
        setTab("finalanswer");
      } catch (err) { status.textContent = "错误：" + err.message; }
    };
    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }
  </script>
</body>
</html>
"""


def load_module(script_name: str):
    path = Path(__file__).with_name(script_name)
    spec = importlib.util.spec_from_file_location(script_name.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def call_chat_api(base_url: str, api_key: str, model: str, prompt: str, temperature: float, timeout: int) -> dict:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个基于检索证据回答问题的中文助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "stream": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Qwen API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot connect to Qwen API at {endpoint}: {exc.reason}") from exc


def extract_answer(response: dict) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except Exception:
        return json.dumps(response, ensure_ascii=False, indent=2)


def make_prompt(query: str, citations: list[dict]) -> str:
    parts = [
        "你是一个严谨的 RAG 问答助手。只能依据给定资料回答；如果资料不足，请明确说明不足。",
        "回答要求：",
        "1. 先直接回答问题。",
        "2. 保留关键依据，不编造资料中没有的信息。",
        "3. 在关键结论句末使用 [1]、[2] 这样的编号引用来源。",
        "4. 回答使用中文，结构清晰，避免空泛套话。",
        "",
        f"用户问题：{query}",
        "",
        "检索资料：",
    ]
    for item in citations:
        parts.append(f"[{item['rank']}] doc={item['doc_id']} section={item.get('section', '')} chunk={item['chunk_id']}\n{item['text']}")
    return "\n\n".join(parts)


def make_handler(index_path: Path, max_chars: int, api_base: str, api_key: str, model: str, temperature: float, timeout: int):
    query_mod = load_module("query_rag.py")
    index = json.loads(index_path.read_text(encoding="utf-8"))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def send_json(self, data: dict, status: int = 200) -> None:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            if urlparse(self.path).path != "/":
                self.send_error(404)
                return
            payload = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                query = str(body.get("query", "")).strip()
                top_k = int(body.get("top_k", 5))
                if not query:
                    self.send_json({"error": "query is required"}, 400)
                    return
                path = urlparse(self.path).path
                if path == "/api/query":
                    scored = query_mod.score(query, index)[:top_k]
                    hits = []
                    for rank, (value, chunk_i) in enumerate(scored, start=1):
                        chunk = index["chunks"][chunk_i]
                        hits.append({"rank": rank, "score": round(value, 4), **chunk})
                    self.send_json({"query": query, "hits": hits})
                    return
                if path in {"/api/prompt", "/api/answer"}:
                    citations = []
                    used = 0
                    for rank, (value, chunk_i) in enumerate(query_mod.score(query, index)[:top_k], start=1):
                        chunk = index["chunks"][chunk_i]
                        text = chunk["text"].strip()
                        if used + len(text) > max_chars:
                            text = text[: max(max_chars - used, 0)]
                        if not text:
                            break
                        used += len(text)
                        citations.append({"rank": rank, "score": round(value, 4), **chunk, "text": text})
                        if used >= max_chars:
                            break
                    prompt = make_prompt(query, citations)
                    if path == "/api/answer":
                        raw = call_chat_api(api_base, api_key, model, prompt, temperature, timeout)
                        self.send_json({"query": query, "answer": extract_answer(raw), "prompt": prompt, "citations": citations})
                    else:
                        self.send_json({"query": query, "prompt": prompt, "citations": citations})
                    return
                self.send_error(404)
            except Exception as exc:
                self.send_json({"error": str(exc)}, 500)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve a local RAG web console")
    parser.add_argument("--index", default="build/index.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--max-chars", type=int, default=3600)
    parser.add_argument("--api-base", default=os.environ.get("QWEN_API_BASE", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--api-key", default=os.environ.get("QWEN_API_KEY", ""))
    parser.add_argument("--model", default=os.environ.get("QWEN_MODEL", "qwen"))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    index_path = Path(args.index).resolve()
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}")
    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_handler(index_path, args.max_chars, args.api_base, args.api_key, args.model, args.temperature, args.timeout),
    )
    print(f"RAG UI running at http://{args.host}:{args.port}")
    print(f"Using index: {index_path}")
    print(f"Qwen API: {args.api_base}/chat/completions model={args.model}")
    server.serve_forever()


if __name__ == "__main__":
    main()
