"""Renders an executed plan into a .docx document using python-docx."""

from __future__ import annotations

import datetime as _dt
import re
import uuid

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from .config import settings
from .models import ExecutedSection, ExecutionPlan

# Brand palette
_PRIMARY = RGBColor(0x1F, 0x3A, 0x5F)   # deep navy
_ACCENT = RGBColor(0x2E, 0x86, 0xC1)    # blue
_GREY = RGBColor(0x60, 0x60, 0x60)
_HEADER_FILL = "1F3A5F"
_BAND_FILL = "EAF2F8"


def build_document(
    plan: ExecutionPlan,
    sections: list[ExecutedSection],
    original_request: str,
) -> str:
    """Write the .docx to the output dir and return its filename."""
    doc = Document()
    _configure_base_styles(doc)
    _add_cover(doc, plan)
    _add_meta_and_assumptions(doc, plan, original_request)

    for section in sections:
        _add_heading(doc, section.heading)
        for block in section.blocks:
            if block.type == "paragraph":
                _add_paragraph(doc, block.text)
            elif block.type == "bullets":
                _add_bullets(doc, block.items)
            elif block.type == "table":
                _add_table(doc, block.headers, block.rows)

    _add_footer(doc, plan)

    filename = f"{_slugify(plan.title)}-{uuid.uuid4().hex[:8]}.docx"
    doc.save(settings.output_dir / filename)
    return filename




def _configure_base_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)


def _add_cover(doc: Document, plan: ExecutionPlan) -> None:
    label = doc.add_paragraph()
    label.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = label.add_run(plan.document_type.upper())
    run.font.size = Pt(12)
    run.font.color.rgb = _ACCENT
    run.font.bold = True

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    trun = title.add_run(plan.title)
    trun.font.size = Pt(26)
    trun.font.bold = True
    trun.font.color.rgb = _PRIMARY

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    srun = sub.add_run(plan.objective)
    srun.font.size = Pt(12)
    srun.font.italic = True
    srun.font.color.rgb = _GREY

    doc.add_paragraph()  # spacer


def _add_meta_and_assumptions(
    doc: Document, plan: ExecutionPlan, original_request: str
) -> None:
    today = _dt.date.today().strftime("%B %d, %Y")
    meta = doc.add_table(rows=0, cols=2)
    meta.style = "Light List Accent 1"
    for key, value in (
        ("Date", today),
        ("Audience", plan.audience),
        ("Document Type", plan.document_type),
        ("Original Request", original_request),
    ):
        row = meta.add_row().cells
        row[0].text = key
        row[1].text = value
        row[0].paragraphs[0].runs[0].font.bold = True

    if plan.assumptions:
        _add_heading(doc, "Assumptions Made")
        intro = doc.add_paragraph()
        intro.add_run(
            "Where the request was ambiguous or incomplete, the agent made the "
            "following reasonable assumptions:"
        ).italic = True
        _add_bullets(doc, plan.assumptions)

    doc.add_paragraph()


def _add_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = _PRIMARY
    _add_bottom_border(p)


def _add_paragraph(doc: Document, text: str) -> None:
    if text and text.strip():
        doc.add_paragraph(text.strip())


def _add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        if item and item.strip():
            doc.add_paragraph(item.strip(), style="List Bullet")


def _add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        return
    ncols = len(headers) if headers else max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    if headers:
        hcells = table.add_row().cells
        for i, h in enumerate(headers[:ncols]):
            hcells[i].text = str(h)
            _shade_cell(hcells[i], _HEADER_FILL)
            para = hcells[i].paragraphs[0]
            run = para.runs[0] if para.runs else para.add_run("")
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i in range(ncols):
            cells[i].text = str(row[i]) if i < len(row) else ""
            if idx % 2 == 1:
                _shade_cell(cells[i], _BAND_FILL)
    doc.add_paragraph()


def _add_footer(doc: Document, plan: ExecutionPlan) -> None:
    section = doc.sections[0]
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run(
        f"{plan.title}  ·  Generated by Autonomous Agent  ·  "
        f"{_dt.date.today().strftime('%Y-%m-%d')}"
    )
    run.font.size = Pt(8)
    run.font.color.rgb = _GREY




def _shade_cell(cell, hex_fill: str) -> None:
    shd = cell._tc.get_or_add_tcPr()
    el = shd.makeelement(qn("w:shd"), {qn("w:fill"): hex_fill})
    shd.append(el)


def _add_bottom_border(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.makeelement(qn("w:pBdr"), {})
    bottom = p_bdr.makeelement(
        qn("w:bottom"),
        {
            qn("w:val"): "single",
            qn("w:sz"): "6",
            qn("w:space"): "2",
            qn("w:color"): "2E86C1",
        },
    )
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:50] or "document"
