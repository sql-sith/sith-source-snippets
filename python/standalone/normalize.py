# /// script
# requires-python = ">=3.10"
# ///
r"""
Normalize a raw GoCaaS Companion session export into a clean Markdown transcript.

Usage (PowerShell):
    uv run normalize.py path\to\companion-session.txt
    uv run normalize.py session.txt -o cleaned.md --title "My Session"

Behavior:
- Splits the input on `### USER` / `### ASSISTANT` headers.
- Replaces each `<details type="tool_calls" ...>...</details>` block with a
  one-line summary collected into a collapsed <details> at the top of the turn.
- Decodes HTML entities so escaped JSON becomes readable.
- Drops user/assistant pairs where the assistant response is empty
  (typical when the user interrupted and re-asked).
- Renumbers the surviving turns sequentially.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path


TOOL_CALL_RE = re.compile(
    r'<details\s+type="tool_calls"[^>]*?\bname="([^"]+)"[^>]*?\barguments="([^"]*)"[^>]*?>'
    r"(.*?)</details>",
    re.DOTALL,
)

TURN_SPLIT_RE = re.compile(r"^###\s+(USER|ASSISTANT)\s*$", re.MULTILINE)

FILENAME_RE = re.compile(r'"filename"\s*:\s*"([^"]+)"')
SOURCE_RE = re.compile(r'"source"\s*:\s*"([^"]+)"')
# After html.unescape, the body's JSON often retains a layer of backslash-escaped
# quotes (it's a JSON string of JSON). Match that form too.
FILENAME_RE_ESC = re.compile(r'\\"filename\\"\s*:\s*\\"([^"\\]+)\\"')
SOURCE_RE_ESC = re.compile(r'\\"source\\"\s*:\s*\\"([^"\\]+)\\"')


def parse_args_attr(raw_attr: str):
    r"""The `arguments` attribute is HTML-encoded, double-JSON-encoded.

    Example: `&quot;{\&quot;query\&quot;:\&quot;hi\&quot;}&quot;`
    becomes `"{\"query\":\"hi\"}"`, which json.loads twice -> {"query":"hi"}.
    """
    decoded = html.unescape(raw_attr)
    try:
        outer = json.loads(decoded)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(outer, str):
        try:
            return json.loads(outer)
        except (json.JSONDecodeError, ValueError):
            return outer
    return outer


def extract_filename_from_body(body: str) -> str | None:
    decoded = html.unescape(body)
    for pat in (FILENAME_RE_ESC, FILENAME_RE, SOURCE_RE_ESC, SOURCE_RE):
        m = pat.search(decoded)
        if m:
            return m.group(1)
    return None


def summarize_tool_call(name: str, args, body: str) -> str:
    if name == "list_knowledge":
        return f"`{name}`"

    if name == "query_knowledge_files":
        q = args.get("query") if isinstance(args, dict) else None
        return f'`{name}` — *"{q}"*' if q else f"`{name}`"

    if name == "view_knowledge_file":
        filename = extract_filename_from_body(body)
        if filename:
            stem = filename.removesuffix(".md")
            return f"`{name}` — `{stem}`"
        fid = args.get("file_id") if isinstance(args, dict) else None
        if fid:
            short = fid.split("-", 1)[0]
            return f"`{name}` — *(file id `{short}…`)*"
        return f"`{name}`"

    if isinstance(args, dict) and args:
        first_val = next(iter(args.values()))
        if isinstance(first_val, str) and len(first_val) < 80:
            return f"`{name}` — *{first_val}*"
    return f"`{name}`"


def split_turns(text: str) -> list[tuple[str, str]]:
    """Return [(role, content), ...] in document order."""
    parts = TURN_SPLIT_RE.split(text)
    # parts: [preamble, role1, content1, role2, content2, ...]
    turns: list[tuple[str, str]] = []
    for i in range(1, len(parts), 2):
        role = parts[i].lower()
        content = parts[i + 1] if i + 1 < len(parts) else ""
        turns.append((role, content.strip("\n")))
    return turns


def normalize_assistant(content: str) -> tuple[list[str], str]:
    """Strip tool-call blocks; return (summaries, remaining prose)."""
    summaries: list[str] = []

    def repl(m: re.Match[str]) -> str:
        name = m.group(1)
        args = parse_args_attr(m.group(2))
        body = m.group(3)
        summaries.append(summarize_tool_call(name, args, body))
        return ""

    cleaned = TOOL_CALL_RE.sub(repl, content)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return summaries, cleaned


def pair_turns(turns: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Pair user→assistant. Skip pairs where assistant is empty."""
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(turns):
        role, content = turns[i]
        if role != "user":
            i += 1
            continue
        user_msg = content
        assistant_msg = ""
        if i + 1 < len(turns) and turns[i + 1][0] == "assistant":
            assistant_msg = turns[i + 1][1]
            i += 2
        else:
            i += 1
        if not assistant_msg.strip():
            continue
        pairs.append((user_msg, assistant_msg))
    return pairs


def render_markdown(pairs: list[tuple[str, str]], title: str | None) -> str:
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
        lines.append("")
    lines.append(
        "> Cleaned transcript of a GoCaaS Companion session. Tool-call payloads"
    )
    lines.append(
        "> have been collapsed to short summaries; assistant prose is preserved verbatim."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    for n, (user_msg, assistant_msg) in enumerate(pairs, start=1):
        lines.append(f"## Turn {n} — User")
        lines.append("")
        lines.append(user_msg.strip())
        lines.append("")
        lines.append(f"## Turn {n} — Assistant")
        lines.append("")

        summaries, prose = normalize_assistant(assistant_msg)
        if summaries:
            lines.append("<details>")
            lines.append(f"<summary>Tools used ({len(summaries)} calls)</summary>")
            lines.append("")
            for idx, s in enumerate(summaries, start=1):
                lines.append(f"{idx}. {s}")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        if prose:
            lines.append(prose)
            lines.append("")
        lines.append("---")
        lines.append("")

    while lines and lines[-1].strip() in ("", "---"):
        lines.pop()
    lines.append("")
    return "\n".join(lines)


def derive_title(input_path: Path) -> str:
    stem = input_path.stem.replace("_", " ").replace("-", " ").strip()
    return stem.title() if stem else "Companion Session"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Normalize a GoCaaS Companion session export to clean Markdown."
    )
    p.add_argument("input", help="Path to the raw companion session file")
    p.add_argument(
        "-o", "--output",
        help="Output Markdown path (default: <input-stem>.md alongside input)",
    )
    p.add_argument("--title", help="Document title (default: derived from filename)")
    p.add_argument(
        "--no-title", action="store_true",
        help="Omit the H1 title from the output",
    )
    ns = p.parse_args(argv)

    src = Path(ns.input)
    if not src.is_file():
        print(f"error: input file not found: {src}", file=sys.stderr)
        return 2

    text = src.read_text(encoding="utf-8")
    turns = split_turns(text)
    if not turns:
        print("error: no `### USER` / `### ASSISTANT` headers found", file=sys.stderr)
        return 1

    pairs = pair_turns(turns)
    title = None if ns.no_title else (ns.title or derive_title(src))
    md = render_markdown(pairs, title=title)

    if ns.output:
        out_path = Path(ns.output)
    else:
        out_path = src.with_suffix(".md")
        if out_path.resolve() == src.resolve():
            out_path = src.with_name(src.stem + ".cleaned.md")

    out_path.write_text(md, encoding="utf-8")
    skipped = sum(1 for r, c in turns if r == "user") - len(pairs)
    note = f" (skipped {skipped} empty assistant turn{'s' if skipped != 1 else ''})" if skipped else ""
    print(f"Wrote {out_path} — {len(pairs)} turn pair{'s' if len(pairs) != 1 else ''}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
