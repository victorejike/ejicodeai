"""File renderers for the ATS CV: plain text, .docx and PDF - all stdlib.

An ATS parses the *text layer* of whatever you upload. Anything that makes text
hard to extract in the right order (tables, text boxes, multiple columns, images,
headers/footers, unusual glyphs) is what actually gets CVs rejected. So instead of
pulling in a document library that can express all of those, these renderers can
only produce a single stream of left-aligned paragraphs - the safe shape is the
only shape available.

* ``render_docx`` writes a minimal WordprocessingML package with ``zipfile``:
  paragraphs and runs only, no tables, no sections beyond the single body.
* ``render_pdf`` writes a single-column PDF with one text-showing operator per
  line using the standard Helvetica font, so ``pdftotext`` recovers the lines in
  reading order.
"""
from __future__ import annotations

import zipfile
from io import BytesIO
from typing import List, Tuple

#: Rendering geometry, in PDF points (1/72 inch) on US Letter.
PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 54
BODY_SIZE = 10.5
HEADING_SIZE = 11.5
NAME_SIZE = 16
LINE_HEIGHT = 14.5

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _xml_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _classify(line: str, headings: Tuple[str, ...]) -> str:
    """``"name"``, ``"heading"`` or ``"body"`` for one rendered line."""
    stripped = line.strip()
    if not stripped:
        return "blank"
    if stripped in headings or stripped.upper() in {h.upper() for h in headings}:
        return "heading"
    return "body"


def render_docx(text: str, headings: Tuple[str, ...] = ()) -> bytes:
    """Minimal single-column .docx. Paragraphs only - no tables, no columns."""
    lines = text.splitlines()
    paragraphs: List[str] = []

    for index, line in enumerate(lines):
        kind = _classify(line, headings)
        if kind == "blank":
            paragraphs.append(f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>')
            continue

        bold = kind == "heading" or index == 0
        size = NAME_SIZE if index == 0 else (HEADING_SIZE if kind == "heading" else BODY_SIZE)
        half_points = int(size * 2)
        run_props = f'<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="{half_points}"/>'
        if bold:
            run_props += "<w:b/>"
        run_props += "</w:rPr>"
        paragraphs.append(
            "<w:p>"
            '<w:pPr><w:jc w:val="left"/><w:spacing w:after="0"/></w:pPr>'
            f"<w:r>{run_props}<w:t xml:space=\"preserve\">{_xml_escape(line)}</w:t></w:r>"
            "</w:p>"
        )

    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}"><w:body>'
        + "".join(paragraphs)
        + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" '
        'w:header="0" w:footer="0" w:gutter="0"/>'
        "</w:sectPr></w:body></w:document>"
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def _pdf_escape(text: str) -> str:
    return str(text).replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(line: str, size: float, width: float) -> List[str]:
    """Greedy wrap using an average Helvetica advance width."""
    limit = max(int(width / (size * 0.5)), 20)
    if len(line) <= limit:
        return [line]
    words = line.split(" ")
    wrapped: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                wrapped.append(current)
            current = word
    if current:
        wrapped.append(current)
    return wrapped or [""]


def render_pdf(text: str, headings: Tuple[str, ...] = ()) -> bytes:
    """Single-column PDF whose text layer extracts in reading order."""
    usable_width = PAGE_WIDTH - 2 * MARGIN
    pages: List[List[Tuple[str, float, bool]]] = [[]]
    y = PAGE_HEIGHT - MARGIN

    for index, raw_line in enumerate(text.splitlines()):
        kind = _classify(raw_line, headings)
        size = NAME_SIZE if index == 0 else (HEADING_SIZE if kind == "heading" else BODY_SIZE)
        bold = kind == "heading" or index == 0

        segments = [""] if kind == "blank" else _wrap(raw_line, size, usable_width)
        for segment in segments:
            if y - LINE_HEIGHT < MARGIN:
                pages.append([])
                y = PAGE_HEIGHT - MARGIN
            pages[-1].append((segment, size, bold))
            y -= LINE_HEIGHT

    objects: List[str] = []
    page_count = len(pages)
    # 1: catalog, 2: pages, 3..: [page, content] pairs, then the two fonts.
    font_regular = 3 + 2 * page_count
    font_bold = font_regular + 1

    page_ids = [3 + 2 * i for i in range(page_count)]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>")

    for page_index, page_lines in enumerate(pages):
        content_id = page_ids[page_index] + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )

        stream_lines = ["BT"]
        cursor = PAGE_HEIGHT - MARGIN
        for segment, size, bold in page_lines:
            if segment:
                font = "/F2" if bold else "/F1"
                stream_lines.append(f"{font} {size:.1f} Tf")
                stream_lines.append("1 0 0 1 %d %.1f Tm" % (MARGIN, cursor))
                stream_lines.append(f"({_pdf_escape(segment)}) Tj")
            cursor -= LINE_HEIGHT
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        objects.append(f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\nstream\n{stream}\nendstream")

    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets: List[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1", "replace")

    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)
