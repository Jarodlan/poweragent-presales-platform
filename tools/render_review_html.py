from __future__ import annotations

import html
import re
import sys
from pathlib import Path


TITLE_RE = re.compile(r"^\s*#\s+(.+?)\s*$")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
UL_RE = re.compile(r"^\s*-\s+(.+)$")
TABLE_RE = re.compile(r"^\|.*\|\s*$")


def extract_section(text: str, start: str, end: str | None = None) -> str:
    start_idx = text.find(start)
    if start_idx == -1:
        return ""
    start_idx += len(start)
    if end:
        end_idx = text.find(end, start_idx)
        if end_idx != -1:
            return text[start_idx:end_idx].strip()
    return text[start_idx:].strip()


def strip_first_h1(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    stripped = []
    skipped = False
    for line in lines:
        if not skipped and TITLE_RE.match(line):
            skipped = True
            continue
        stripped.append(line)
    return "\n".join(stripped).strip()


def derive_summary(markdown_text: str, limit: int = 3) -> str:
    lines = markdown_text.splitlines()
    paragraphs: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        paragraph = " ".join(line.strip() for line in current).strip()
        current = []
        if not paragraph:
            return
        if paragraph.startswith("#"):
            return
        if paragraph.startswith("- "):
            return
        if paragraph.startswith("|"):
            return
        paragraphs.append(paragraph)

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            flush()
            continue
        if HEADING_RE.match(line) or UL_RE.match(line) or TABLE_RE.match(line):
            flush()
            continue
        current.append(line)

    flush()
    return "\n\n".join(paragraphs[:limit]).strip()


def format_inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    return escaped


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            merged = " ".join(line.strip() for line in paragraph).strip()
            if merged:
                blocks.append(f"<p>{format_inline(merged)}</p>")
        paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            items = "".join(f"<li>{format_inline(item)}</li>" for item in list_items)
            blocks.append(f"<ul>{items}</ul>")
        list_items = []

    def flush_table() -> None:
        nonlocal table_lines
        if not table_lines:
            return
        rows = []
        for line in table_lines:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)
        if len(rows) >= 2 and all(set(cell) <= {"-", ":"} for cell in rows[1]):
            header = rows[0]
            body = rows[2:]
        else:
            header = rows[0]
            body = rows[1:]
        thead = "<tr>" + "".join(f"<th>{format_inline(cell)}</th>" for cell in header) + "</tr>"
        tbody = "".join(
            "<tr>" + "".join(f"<td>{format_inline(cell)}</td>" for cell in row) + "</tr>"
            for row in body
        )
        blocks.append(f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>")
        table_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if line.strip() == "---":
            flush_paragraph()
            flush_list()
            flush_table()
            blocks.append("<hr>")
            continue
        if TABLE_RE.match(line):
            flush_paragraph()
            flush_list()
            table_lines.append(line)
            continue
        flush_table()
        heading = HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)) + 1, 4)
            blocks.append(f"<h{level}>{format_inline(heading.group(2))}</h{level}>")
            continue
        list_match = UL_RE.match(line)
        if list_match:
            flush_paragraph()
            list_items.append(list_match.group(1))
            continue
        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    flush_table()
    return "\n".join(blocks)


def build_html(document_title: str, summary_html: str, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(document_title)}</title>
  <style>
    :root {{
      --bg: #eef3f7;
      --page: #ffffff;
      --ink: #1e2a36;
      --muted: #5e6b78;
      --line: #d8e2ea;
      --accent: #0f5d8c;
      --soft: #f4f8fb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
      background: linear-gradient(180deg, #edf4f9 0%, #f5f8fb 100%);
      color: var(--ink);
    }}
    .wrap {{
      padding: 28px 16px 48px;
    }}
    .page {{
      width: min(210mm, 100%);
      margin: 0 auto;
      background: var(--page);
      box-shadow: 0 18px 48px rgba(15, 38, 56, 0.12);
      border: 1px solid rgba(15, 93, 140, 0.08);
      min-height: 297mm;
      padding: 24mm 20mm 22mm;
    }}
    .cover {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 22px;
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 10px;
      font-weight: 700;
    }}
    h1 {{
      margin: 0;
      font-size: 30px;
      line-height: 1.25;
      color: #12354e;
    }}
    .subtitle {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.75;
    }}
    .summary-box {{
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 16px;
      margin: 20px 0 28px;
    }}
    .summary-box h2 {{
      margin-top: 0;
      margin-bottom: 12px;
      color: #154c74;
      font-size: 18px;
    }}
    h2 {{
      margin: 26px 0 12px;
      font-size: 22px;
      color: #12354e;
      break-after: avoid;
    }}
    h3 {{
      margin: 20px 0 8px;
      font-size: 18px;
      color: #184f78;
      break-after: avoid;
    }}
    h4 {{
      margin: 16px 0 8px;
      font-size: 16px;
      color: #184f78;
      break-after: avoid;
    }}
    p {{
      margin: 0 0 12px;
      font-size: 15px;
      line-height: 1.9;
      text-align: justify;
    }}
    ul {{
      margin: 0 0 14px 1.2em;
      padding: 0;
    }}
    li {{
      margin: 0 0 8px;
      line-height: 1.8;
      font-size: 15px;
    }}
    strong {{
      color: #163c59;
    }}
    code {{
      padding: 1px 6px;
      border-radius: 6px;
      background: #edf3f7;
      font-size: 0.92em;
      color: #22516f;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 18px;
      font-size: 14px;
      table-layout: fixed;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 10px 12px;
      vertical-align: top;
      line-height: 1.65;
    }}
    th {{
      background: #edf5fb;
      color: #174e77;
      font-weight: 700;
    }}
    hr {{
      border: none;
      border-top: 1px solid var(--line);
      margin: 20px 0;
    }}
    .footer-note {{
      margin-top: 28px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.8;
    }}
    @media print {{
      body {{
        background: #fff;
      }}
      .wrap {{
        padding: 0;
      }}
      .page {{
        width: auto;
        min-height: auto;
        margin: 0;
        border: none;
        box-shadow: none;
        padding: 16mm;
      }}
      a {{
        color: inherit;
        text-decoration: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <main class="page">
      <section class="cover">
        <div class="eyebrow">External Review Draft</div>
        <h1>{html.escape(document_title)}</h1>
        <div class="subtitle">评审版 HTML 页面。适合直接浏览、打印或导出 PDF，用于向非项目组成员确认方案内容是否合适。</div>
      </section>
      <section class="summary-box">
        <h2>方案摘要</h2>
        {summary_html}
      </section>
      <section class="content">
        {body_html}
      </section>
      <section class="footer-note">
        本页面由项目内测试结果自动整理生成，仅保留适合外部评审的摘要与正文内容，已去除内部调试和知识库校核细节。
      </section>
    </main>
  </div>
</body>
</html>
"""


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: render_review_html.py <source_md> <target_html>")
        return 1

    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    text = source.read_text(encoding="utf-8")

    summary_md = extract_section(text, "## 摘要", "## 解决方案正文")
    body_md = extract_section(text, "## 解决方案正文", "## 校核备注")
    if not body_md:
        body_md = extract_section(text, "## 解决方案正文")
    if not body_md:
        body_md = text.strip()
    if not summary_md:
        summary_md = derive_summary(body_md) or derive_summary(text)
    first_body_line = next((line.strip() for line in body_md.splitlines() if line.strip()), "")
    if first_body_line.startswith("# "):
        document_title = first_body_line[2:].strip()
    else:
        title_match = TITLE_RE.search(body_md) or TITLE_RE.search(text)
        document_title = title_match.group(1) if title_match else source.stem
    body_md = strip_first_h1(body_md)

    summary_html = markdown_to_html(summary_md)
    body_html = markdown_to_html(body_md)
    html_text = build_html(document_title, summary_html, body_html)
    target.write_text(html_text, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
