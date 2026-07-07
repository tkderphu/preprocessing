"""
text_preprocessor.py
--------------------
Rule-based pipeline: raw OCR/extracted text → structured Markdown.

Pipeline:
  1. Normalize  — strip \\r, remove OCR garbage lines
  2. Merge      — rejoin broken mid-sentence continuation lines
  3. Classify   — detect headings, lists, tables
  4. Emit       — output clean Markdown
"""

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Constants & helpers
# ─────────────────────────────────────────────────────────────────────────────

# Redaction placeholder — must NEVER be treated as a heading or list
_REDACTED_TAG = re.compile(r'^\[.+_REDACTED\]$')

# Heading rules: (pattern, md_level)
_HEADING_RULES: list[tuple[re.Pattern, int]] = [
    (re.compile(r'^(ASSIGNMENT\s+\d+)', re.IGNORECASE), 1),
    (re.compile(r'^(Chương\s+\d+\s*[\.\:])', re.IGNORECASE), 2),
    (re.compile(r'^(Phần\s+\d+\s*[\.\:])', re.IGNORECASE), 2),
    (re.compile(r'^(Section\s+\d+\s*[\.\:])', re.IGNORECASE), 2),
    (re.compile(r'^(\d+\.\d+\s+\S.{2,})'), 3),          # 2.1 Sub-heading
    (re.compile(r'^(\d+\.\s+[A-ZÁÀẢÃẠ].{2,})'), 2),    # 1. Major heading
    (re.compile(r'^(Bảng\s+\d+\s*[\.\:])', re.IGNORECASE), 3),
    (re.compile(r'^(Hình\s+\d+\s*[\.\:])', re.IGNORECASE), 3),
    (re.compile(r'^(Mục\s+\d+\s*[\.\:])', re.IGNORECASE), 3),
]

# Explicit list prefixes
_LIST_PREFIX_RE = re.compile(r'^[\●\•\–\—]\s*')
_DASH_LIST_RE   = re.compile(r'^[-\*]\s+\S')
_NUMBERED_LIST  = re.compile(r'^\d+[\.\)]\s+\S')

# Indented bullet: 1–4 spaces then a Vietnamese/Latin word (not a space-only line)
_INDENT_BULLET  = re.compile(r'^ {1,4}(?=[^\s])')

# Sentence-ending punctuation
_SENTENCE_END   = re.compile(r'[.!?:)\]»\u201d]\s*$')

# OCR garbage: <38% alphabetic characters
def _is_garbage(line: str) -> bool:
    s = line.strip()
    if len(s) < 4:
        return False
    alpha = sum(1 for c in s if c.isalpha())
    return (alpha / len(s)) < 0.38


def _is_heading(stripped: str) -> bool:
    if _REDACTED_TAG.match(stripped):
        return False
    for pattern, _ in _HEADING_RULES:
        if pattern.match(stripped):
            return True
    return False


def _is_list_item(stripped: str) -> bool:
    return bool(
        _LIST_PREFIX_RE.match(stripped)
        or _DASH_LIST_RE.match(stripped)
        or _NUMBERED_LIST.match(stripped)
    )


def _is_standalone(line: str) -> bool:
    """Lines that must NOT be merged onto the previous line."""
    s = line.strip()
    if not s:
        return True
    if _is_list_item(s) or _is_heading(s):
        return True
    if _INDENT_BULLET.match(line) and s:   # space-indented bullet
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Normalize
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> list[str]:
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    return [line.rstrip() for line in lines if not _is_garbage(line)]


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Merge broken continuation lines
# ─────────────────────────────────────────────────────────────────────────────

def _merge_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]

        # Blank line → paragraph break, never merge
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

        # Line starts with lowercase → likely a wrapped continuation
        first_char = line.lstrip()[:1]
        if first_char and first_char == first_char.lower() and first_char.isalpha():
            merged[-1] = prev.rstrip() + ' ' + line.lstrip()
        else:
            merged.append(line)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Title deduplication (merge split title lines)
# ─────────────────────────────────────────────────────────────────────────────

def _merge_title_lines(lines: list[str]) -> list[str]:
    """
    If consecutive non-blank lines at the top are both ALL-CAPS short phrases,
    merge them into one title line (handles 'BOOKSTORE\\nMANAGEMENT SYSTEM').
    Only applies to the first group of lines before any other content.
    """
    result: list[str] = []
    i = 0
    # Find leading title block: consecutive short all-caps lines
    title_parts: list[str] = []
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            if title_parts:
                break
            continue
        if _REDACTED_TAG.match(s):
            break
        # Is this a short all-caps or title-case line?
        words = s.split()
        if 1 <= len(words) <= 6 and s.replace(' ', '').replace(':', '').replace('.', '').isupper():
            title_parts.append(s)
            i += 1
        else:
            break

    if len(title_parts) >= 2:
        result.append(' '.join(title_parts))
    elif title_parts:
        result.append(title_parts[0])

    result.extend(lines[i:])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Table detection & formatting
# ─────────────────────────────────────────────────────────────────────────────

def _try_build_actor_table(lines: list[str], start: int) -> tuple[list[str], int] | None:
    """
    Detect and format an Actor/Function style 2-column table.

    Expected structure after a '### Bảng' heading:
        ColHeader1          (e.g. "Actor")
        ColHeader2          (e.g. "Chức năng")
        RowHeader
        - item
        - item
        RowHeader
        - item
        ...
    """
    n = len(lines)
    if start + 3 >= n:
        return None

    col1 = lines[start].strip()
    col2 = lines[start + 1].strip() if start + 1 < n else ""

    # Column headers must be short, non-list, non-heading, non-redacted
    for col in (col1, col2):
        if not col or len(col.split()) > 5:
            return None
        if _is_list_item(col) or _is_heading(col) or _REDACTED_TAG.match(col):
            return None

    i = start + 2
    rows: list[tuple[str, list[str]]] = []

    while i < n:
        row_header = lines[i].strip()

        # Stop on blank line after at least 1 row found
        if not row_header:
            if rows:
                i += 1
                break
            i += 1
            continue

        # Stop on new heading or new table
        if _is_heading(row_header) or _LIST_PREFIX_RE.match(row_header):
            break

        # Skip lone page numbers (e.g. "1", "2", "3")
        if row_header.isdigit():
            i += 1
            continue

        i += 1

        # Collect list items for this row
        items: list[str] = []
        while i < n:
            s = lines[i].strip()
            if not s:
                break
            if _LIST_PREFIX_RE.match(s) or _DASH_LIST_RE.match(s):
                items.append(_LIST_PREFIX_RE.sub('', s).strip().lstrip('- ').strip())
                i += 1
            elif _INDENT_BULLET.match(lines[i]) and s:
                items.append(s.lstrip('- ').strip())
                i += 1
            else:
                break

        rows.append((row_header, items))

    if len(rows) < 2:
        return None

    # Build Markdown table
    md = [f"| {col1} | {col2} |", "|---|---|"]
    for header, items in rows:
        cell = ' / '.join(items) if items else '—'
        md.append(f"| **{header}** | {cell} |")

    return md, i


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Classify and emit
# ─────────────────────────────────────────────────────────────────────────────

def _classify_and_emit(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    last_heading_level: int = 0

    def _add_blank():
        if out and out[-1] != '':
            out.append('')

    while i < len(lines):
        line  = lines[i]
        s     = line.strip()

        # ── Blank line ────────────────────────────────────────────────────────
        if not s:
            _add_blank()
            i += 1
            continue

        # ── Redaction tag: treat as bold inline, never as heading ─────────────
        if _REDACTED_TAG.match(s):
            out.append(f'**{s}**')
            i += 1
            continue

        # ── Heading detection ─────────────────────────────────────────────────
        heading_matched = False
        for pattern, level in _HEADING_RULES:
            if pattern.match(s):
                _add_blank()
                out.append('#' * level + ' ' + s)
                _add_blank()
                last_heading_level = level
                heading_matched = True
                break

        if heading_matched:
            i += 1
            # If next line(s) are the 2-col table header, try table
            # (look ahead for "Bảng" tables)
            if last_heading_level == 3 and 'Bảng' in s:
                # Skip blank lines
                j = i
                while j < len(lines) and not lines[j].strip():
                    j += 1
                result = _try_build_actor_table(lines, j)
                if result:
                    table_md, end = result
                    out.extend(table_md)
                    _add_blank()
                    i = end
            continue

        # ── ALL-CAPS short line → h1 (but NOT redaction tags) ─────────────────
        words = s.split()
        is_caps = (
            not _REDACTED_TAG.match(s)
            and s.replace(' ', '').replace(':', '').replace('.', '').isupper()
            and 2 <= len(s) <= 80
            and 1 <= len(words) <= 8
        )
        if is_caps:
            _add_blank()
            out.append('# ' + s)
            _add_blank()
            i += 1
            continue

        # ── Explicit list item (●, –, -) ──────────────────────────────────────
        if _LIST_PREFIX_RE.match(s):
            out.append('- ' + _LIST_PREFIX_RE.sub('', s).strip())
            i += 1
            continue

        if _DASH_LIST_RE.match(s):
            out.append(s)
            i += 1
            continue

        # ── Space-indented bullet (OCR of indented lists without ● prefix) ────
        if _INDENT_BULLET.match(line) and s:
            out.append('- ' + s)
            i += 1
            continue

        # ── Numbered list ─────────────────────────────────────────────────────
        if _NUMBERED_LIST.match(s):
            out.append(s)
            i += 1
            continue

        # ── Regular paragraph ─────────────────────────────────────────────────
        out.append(s)
        i += 1

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def text_to_markdown(raw_text: str) -> str:
    """
    Full rule-based pipeline: raw OCR text → clean Markdown.

    Steps:
      1. Normalize  (strip garbage, normalize newlines)
      2. Merge      (rejoin broken continuation lines)
      3. Merge titles (collapse split ALL-CAPS title lines)
      4. Classify & emit (headings, lists, tables, paragraphs)
      5. Collapse excess blank lines
    """
    lines = _normalize(raw_text)
    lines = _merge_lines(lines)
    lines = _merge_title_lines(lines)
    lines = _classify_and_emit(lines)

    # Collapse >1 consecutive blank line
    result: list[str] = []
    prev_blank = False
    for ln in lines:
        if ln == '':
            if not prev_blank:
                result.append(ln)
            prev_blank = True
        else:
            prev_blank = False
            result.append(ln)

    return '\n'.join(result).strip()
