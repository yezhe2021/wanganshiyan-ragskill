# Generated RAG System

This is the runnable RAG workbench generated from `rag-system-designer`.

It reads PDFs from:

```text
../document
```

It provides a local Web UI with method selection:

- BM25
- Vector
- Hybrid
- Rerank

## Run

```powershell
cd "C:\Users\MYS\Desktop\网安大实验\skill项目开题报告(1)\rag-system-designer\generated-rag-system"
python server.py --rebuild --host 127.0.0.1 --port 7870
```

Open:

```text
http://127.0.0.1:7870
```

## Notes

- The vector mode uses hashing vectors, so it does not require downloading embedding models.
- Rerank mode uses hybrid candidates plus lightweight query coverage reranking.
- The answer is an evidence-grounded extractive draft. It is intentionally conservative and cites chunk IDs.
