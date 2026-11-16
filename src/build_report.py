"""docs/REPORT.md -> docs/report.html -> docs/report.pdf (A4), styled after the Apart sprint template.

  uv run python src/build_report.py

Figures are referenced from the Markdown as ../figs/*.png|svg and embedded by path; Chromium (Playwright)
prints the PDF, so what you see in docs/report.html is what is submitted.
"""
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC, HTML, PDF = ROOT / "docs/REPORT.md", ROOT / "docs/report.html", ROOT / "docs/report.pdf"

CSS = """
@page { size: A4; margin: 18mm 17mm 18mm 17mm; }
body { font-family: "Georgia", "Times New Roman", serif; font-size: 10.4pt; line-height: 1.42; color: #111; }
h1 { font-family: Helvetica, Arial, sans-serif; font-size: 17pt; line-height: 1.2; margin: 0 0 6pt; }
h2 { font-family: Helvetica, Arial, sans-serif; font-size: 12pt; margin: 14pt 0 4pt; }
h3 { font-family: Helvetica, Arial, sans-serif; font-size: 10.6pt; margin: 10pt 0 3pt; }
p, li { text-align: justify; hyphens: auto; }
p { margin: 0 0 6pt; }
ul, ol { margin: 0 0 6pt 16pt; padding: 0; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 4pt 0 8pt; font-family: Helvetica, Arial, sans-serif; }
th, td { border-bottom: 0.6pt solid #c3c2b7; padding: 2.2pt 4pt; text-align: left; vertical-align: top; }
th { border-bottom: 1pt solid #52514e; }
img { max-width: 100%; display: block; margin: 4pt auto 2pt; }
code { font-size: 8.8pt; }
.authors { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; margin-bottom: 8pt; }
.abstract { border-left: 3pt solid #2a78d6; padding: 4pt 10pt; background: #f4f8fd; margin: 6pt 0 10pt; }
.caption, em.caption { font-size: 8.8pt; color: #333; display: block; margin: 0 0 8pt; }
.pagebreak { page-break-before: always; }
"""


def loosen_lists(md):
    """Python-Markdown needs a blank line before a list; GitHub doesn't. Insert one so both render the same."""
    out, prev = [], ""
    for line in md.splitlines():
        line = re.sub(r"^ {2,3}(?=(?:[-*]|\d+\.)\s)", "    ", line)  # nested items need 4 spaces here
        is_item = bool(re.match(r"\s*(?:[-*]|\d+\.)\s", line))
        prev_item = bool(re.match(r"\s*(?:[-*]|\d+\.)\s", prev))
        if is_item and prev.strip() and not prev_item and not prev.lstrip().startswith("|"):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def main():
    body = markdown.markdown(loosen_lists(SRC.read_text(encoding="utf-8")), extensions=["tables", "md_in_html", "attr_list"])
    HTML.write_text(f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>BPS claims report</title>"
                    f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page()
        page.goto(HTML.resolve().as_uri(), wait_until="load")
        page.pdf(path=str(PDF), format="A4", print_background=True,
                 margin={"top": "18mm", "bottom": "18mm", "left": "17mm", "right": "17mm"},
                 display_header_footer=True, header_template="<span></span>",
                 footer_template="<div style='font-size:8px;width:100%;text-align:center;color:#666'>"
                                 "<span class='pageNumber'></span> / <span class='totalPages'></span></div>")
        b.close()
    print(f"-> {HTML.relative_to(ROOT)}, {PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
