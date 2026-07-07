"""
text_preprocessor.py
--------------------
Rule-based pipeline: raw OCR/extracted text → structured Markdown.

Pipeline:
  1. Normalize  — strip \r, collapse whitespace, fix encoding artifacts
  2. Merge      — rejoin broken/continuation lines that were split mid-sentence
  3. Headings   — detect Chương X, Bảng X, numbered sections, ALL-CAPS titles
  4. Lists      — detect ●, –, *, indented bullet items
  5. Tables     — detect two-column Actor/Chức-năng style tables
  6. Emit       — produce clean Markdown text
"""

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Regex helpers
# ─────────────────────────────────────────────────────────────────────────────

# Vietnamese-aware "starts with uppercase" (incl. accented capitals)
_UPPER_START = re.compile(
    r'^[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝ\[\(]'
)

# Heading matchers: (pattern, md_level)
_HEADING_RULES: list[tuple[re.Pattern, int]] = [
    (re.compile(r'^(ASSIGNMENT\s+\d+)', re.IGNORECASE), 1),
    (re.compile(r'^(Chương\s+\d+[\.\:])', re.IGNORECASE), 2),
    (re.compile(r'^(Phần\s+\d+[\.\:])', re.IGNORECASE), 2),
    (re.compile(r'^(Section\s+\d+[\.\:])', re.IGNORECASE), 2),
    (re.compile(r'^(\d+\.\d+\s+\S.{3,})'), 3),                # 2.1 Sub-heading
    (re.compile(r'^(\d+\.\s+[A-ZÁÀẢÃẠ\[\(].{3,})'), 2),       # 1. Major heading
    (re.compile(r'^(Bảng\s+\d+[\.\:])', re.IGNORECASE), 3),   # Bảng 1:
    (re.compile(r'^(Hình\s+\d+[\.\:])', re.IGNORECASE), 3),
    (re.compile(r'^(Mục\s+\d+[\.\:])', re.IGNORECASE), 3),
]

# List item prefixes
_LIST_PREFIX = re.compile(r'^[\●\•\–\—\*]\s*')
_NUMBERED_LIST = re.compile(r'^\d+[\.\)]\s+\S')

# Garbage line: >60% non-alphabetic (OCR diagram noise)
def _is_garbage(line: str) -> bool:
    s = line.strip()
    if len(s) < 4:
        return False
    alpha = sum(1 for c in s if c.isalpha())
    return (alpha / len(s)) < 0.38

# Sentence-ending punctuation (do NOT merge next line onto this)
_SENTENCE_END = re.compile(r'[.!?:)\]»\u201d]\s*$')

# Lines that are clearly standalone (don't merge with previous)
def _is_standalone(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if _LIST_PREFIX.match(s) or _NUMBERED_LIST.match(s):
        return True
    for pattern, _ in _HEADING_RULES:
        if pattern.match(s):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Normalize
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> list[str]:
    """Normalize line endings, strip trailing spaces, remove garbage."""
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    result = []
    for line in lines:
        line = line.rstrip()
        if not _is_garbage(line):
            result.append(line)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Merge broken continuation lines
# ─────────────────────────────────────────────────────────────────────────────

def _merge_lines(lines: list[str]) -> list[str]:
    """
    Rejoin lines that were wrapped mid-sentence by the PDF layout.

    A line is merged onto the previous one when:
    - Previous line does NOT end with sentence-ending punctuation
    - Current line does NOT start a new structural element
    - Neither line is blank
    """
    merged: list[str] = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]

        # Blank line: always a paragraph break
        if not line.strip() or not prev.strip():
            merged.append(line)
            continue

        # Current line starts a new structure → don't merge
        if _is_standalone(line):
            merged.append(line)
            continue

        # Previous line ends a sentence → don't merge
        if _SENTENCE_END.search(prev):
            merged.append(line)
            continue

        # Current line starts lowercase (or continuation of a word) → merge
        if not _UPPER_START.match(line.lstrip()):
            merged[-1] = prev + ' ' + line.lstrip()
        else:
            merged.append(line)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Table detection & formatting
# ─────────────────────────────────────────────────────────────────────────────

_TABLE_HEADER = re.compile(
    r'^(Bảng\s+\d+[\.\:].+)',
    re.IGNORECASE,
)

def _is_table_section(lines: list[str], start: int) -> Optional[int]:
    """
    Detect a simple 2-column table starting at `start`.
    Returns the end index (exclusive) if detected, else None.

    Pattern recognised:
        [Column header 1]       ← one short line
        [Column header 2]       ← one short line
        [Row header (actor)]
        - item
        - item
        [Row header]
        - item
        ...
    """
    # We need at least 2 header lines + some rows
    n = len(lines)
    if start + 4 >= n:
        return None

    col1 = lines[start].strip()
    col2 = lines[start + 1].strip() if start + 1 < n else ""

    # Both must be short single-word/phrase lines (not list items, not headings)
    if not col1 or not col2:
        return None
    if _LIST_PREFIX.match(col1) or _is_standalone(col1):
        return None
    if len(col1.split()) > 5 or len(col2.split()) > 5:
        return None

    # Look ahead for rows that alternate between: header-line and list-items
    i = start + 2
    rows_found = 0
    while i < n:
        row_line = lines[i].strip()
        if not row_line:
            break
        # Row header: not a list item, not a heading
        if _LIST_PREFIX.match(row_line) or not row_line:
            break
        row_header = row_line
        i += 1
        # Collect list items for this row
        items: list[str] = []
        while i < n and lines[i].strip() and _LIST_PREFIX.match(lines[i].strip()):
            items.append(_LIST_PREFIX.sub('', lines[i].strip()).strip())
            i += 1
        if items:
            rows_found += 1

    if rows_found >= 2:
        return i  # table ends at i
    return None


def _build_table(lines: list[str], start: int, end: int) -> list[str]:
    """Format detected table region as Markdown table."""
    col1 = lines[start].strip()
    col2 = lines[start + 1].strip()

    md = [f"| {col1} | {col2} |", "|---|---|"]

    i = start + 2
    while i < end:
        row_line = lines[i].strip()
        if not row_line or _LIST_PREFIX.match(row_line):
            i += 1
            continue
        row_header = row_line
        i += 1
        items: list[str] = []
        while i < end and lines[i].strip() and _LIST_PREFIX.match(lines[i].strip()):
            items.append(_LIST_PREFIX.sub('', lines[i].strip()).strip())
            i += 1
        cell = '<br>'.join(items) if items else ''
        md.append(f"| {row_header} | {cell} |")

    return md


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Classify and emit lines
# ─────────────────────────────────────────────────────────────────────────────

def _classify_and_emit(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            # Avoid double blank lines
            if out and out[-1] != '':
                out.append('')
            i += 1
            continue

        # Heading detection
        heading_found = False
        for pattern, level in _HEADING_RULES:
            if pattern.match(stripped):
                out.append('')
                out.append('#' * level + ' ' + stripped)
                out.append('')
                heading_found = True
                break
        if heading_found:
            i += 1
            continue

        # ALL-CAPS short line → h1
        if stripped.isupper() and 3 <= len(stripped) <= 80 and len(stripped.split()) <= 8:
            out.append('')
            out.append('# ' + stripped)
            out.append('')
            i += 1
            continue

        # Table detection: look for 2-col header right after a "Bảng" heading
        if out and out[-1].startswith('### Bảng'):
            end = _is_table_section(lines, i)
            if end:
                out.extend(_build_table(lines, i, end))
                out.append('')
                i = end
                continue

        # List item: ●, –, *, –
        if _LIST_PREFIX.match(stripped):
            item_text = _LIST_PREFIX.sub('', stripped).strip()
            out.append(f'- {item_text}')
            i += 1
            continue

        # Numbered list
        if _NUMBERED_LIST.match(stripped):
            # Convert "1." or "1)" → keep as-is (Markdown renders it)
            out.append(stripped)
            i += 1
            continue

        # Regular paragraph line
        out.append(stripped)
        i += 1

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def text_to_markdown(raw_text: str) -> str:
    """
    Full pipeline: raw OCR/extracted text → clean Markdown.

    Steps:
        1. Normalize (strip garbage, normalize newlines)
        2. Merge broken continuation lines
        3. Classify & emit (headings, lists, tables, paragraphs)
        4. Collapse excess blank lines
    """
    lines   = _normalize(raw_text)
    lines   = _merge_lines(lines)
    lines   = _classify_and_emit(lines)

    # Final pass: collapse >2 consecutive blank lines
    result: list[str] = []
    blanks = 0
    for ln in lines:
        if ln == '':
            blanks += 1
            if blanks <= 1:
                result.append(ln)
        else:
            blanks = 0
            result.append(ln)

    return '\n'.join(result).strip()
