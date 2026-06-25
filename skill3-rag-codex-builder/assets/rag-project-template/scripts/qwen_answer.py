#!/usr/bin/env python3
"""Generate a final RAG answer with a local Qwen/OpenAI-compatible API."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_answer_module():
    path = Path(__file__).with_name("answer_rag.py")
    spec = importlib.util.spec_from_file_location("answer_rag", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def build_prompt(args) -> str:
    answer_mod = load_answer_module()
    index = json.loads(Path(args.index).read_text(encoding="utf-8"))
    vector_index = None
    if args.retriever != "bm25":
        vector_index = json.loads(Path(args.vector_index).read_text(encoding="utf-8"))
    citations = answer_mod.collect_citations(
        args.query,
        index,
        args.top_k,
        args.max_chars,
        retriever=args.retriever,
        vector_index=vector_index,
        candidate_k=args.candidate_k,
    )
    return answer_mod.build_prompt(args.query, citations)


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve evidence and ask a local Qwen API")
    parser.add_argument("query")
    parser.add_argument("--index", default="build/index.json")
    parser.add_argument("--vector-index", default="build/vector_index.json")
    parser.add_argument("--retriever", choices=["bm25", "vector", "hybrid", "hybrid_rerank"], default="bm25")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--max-chars", type=int, default=3600)
    parser.add_argument("--api-base", default=os.environ.get("QWEN_API_BASE", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--api-key", default=os.environ.get("QWEN_API_KEY", ""))
    parser.add_argument("--model", default=os.environ.get("QWEN_MODEL", "qwen"))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    prompt = build_prompt(args)
    response = call_chat_api(args.api_base, args.api_key, args.model, prompt, args.temperature, args.timeout)
    answer = extract_answer(response)
    if args.json:
        print(json.dumps({"query": args.query, "retriever": args.retriever, "answer": answer, "prompt": prompt, "raw": response}, ensure_ascii=False, indent=2))
    else:
        print(answer)


if __name__ == "__main__":
    main()
