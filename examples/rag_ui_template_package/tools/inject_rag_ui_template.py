#!/usr/bin/env python3
"""Replace the inline HTML block in generated-rag-system/server.py.

Usage:
    python tools/inject_rag_ui_template.py \
      --server generated-rag-system/server.py \
      --template examples/rag_workbench_ui_template/index.inline.html
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject reusable RAG Workbench UI into server.py")
    parser.add_argument("--server", required=True, help="Path to generated-rag-system/server.py")
    parser.add_argument("--template", required=True, help="Path to index.inline.html")
    parser.add_argument("--no-backup", action="store_true", help="Do not create .bak backup")
    args = parser.parse_args()

    server_path = Path(args.server)
    template_path = Path(args.template)

    if not server_path.exists():
        raise FileNotFoundError(f"server file not found: {server_path}")
    if not template_path.exists():
        raise FileNotFoundError(f"template file not found: {template_path}")

    source = server_path.read_text(encoding="utf-8")
    template = template_path.read_text(encoding="utf-8")

    pattern = re.compile(r"HTML\s*=\s*r?'''(.*?)'''", re.DOTALL)
    if not pattern.search(source):
        raise RuntimeError("Could not find HTML = r'''...''' block in server.py")

    replacement = "HTML = r'''\n" + template.rstrip() + "\n'''"
    updated = pattern.sub(replacement, source, count=1)

    if not args.no_backup:
        backup_path = server_path.with_suffix(server_path.suffix + ".bak")
        backup_path.write_text(source, encoding="utf-8")
        print(f"Backup written: {backup_path}")

    server_path.write_text(updated, encoding="utf-8")
    print(f"Injected UI template into: {server_path}")


if __name__ == "__main__":
    main()
