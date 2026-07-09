from pathlib import Path
import requests
import time
import json
import re

def clean_text(text: str) -> str:
    """
    Clean OCR/plaintext before splitting.

    - Normalize line endings
    - Remove trailing spaces
    - Merge wrapped lines
    - Preserve blank lines (paragraphs)
    """

    # Normalize newline
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove trailing spaces
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    # Remove spaces before newline
    text = re.sub(r"[ \t]+\n", "\n", text)

    # Collapse too many blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = text.split("\n")

    merged = []

    for line in lines:

        line = line.strip()

        # Keep paragraph break
        if line == "":
            merged.append("")
            continue

        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]

        # Previous line is blank -> new paragraph
        if prev == "":
            merged.append(line)
            continue

        # New heading
        if line.startswith("#"):
            merged.append(line)
            continue

        # Markdown list
        if re.match(r"^[-*+] ", line):
            merged.append(line)
            continue

        # Numbered list
        if re.match(r"^\d+[.)]\s", line):
            merged.append(line)
            continue

        # Code fence
        if line.startswith("```") or prev.startswith("```"):
            merged.append(line)
            continue

        # Merge wrapped OCR line
        merged[-1] += " " + line

    return "\n".join(merged)

# ==========================================================
# CONFIG
# ==========================================================

MODEL = "qwen3:4b-instruct"
OLLAMA_URL = "http://103.82.22.43:11434/api/chat"

INPUT_FILE = "input.txt"
OUTPUT_FILE = "output.md"

# Phải <= OLLAMA_CONTEXT_LENGTH
NUM_CTX = 16384

# Chia theo ký tự
CHUNK_SIZE = 9000

# Giữ lại một phần nội dung để tránh mất ngữ cảnh
OVERLAP = 500

TEMPERATURE = 0

# ==========================================================

SYSTEM_PROMPT = """
You are an expert Markdown formatter.

Your ONLY task is converting plaintext into clean Markdown.

Rules:

- Preserve ALL content exactly.
- Never summarize.
- Never omit any text.
- Never rewrite sentences.
- Merge wrapped lines into proper paragraphs.
- Detect Markdown headings.
- Detect unordered lists.
- Detect ordered lists.
- Preserve code blocks.
- Preserve URLs.
- Preserve tables whenever possible.
- Remove OCR line breaks.
- Output ONLY Markdown.
"""


def split_text(text, chunk_size=9000, overlap=500):
    """
    Split text into chunks.
    Prefer splitting on blank lines or line breaks.
    """

    chunks = []

    start = 0
    length = len(text)

    while start < length:

        end = min(start + chunk_size, length)

        if end < length:

            # ưu tiên xuống dòng đôi
            pos = text.rfind("\n\n", start, end)

            # nếu không có thì xuống dòng đơn
            if pos == -1:
                pos = text.rfind("\n", start, end)

            # nếu không có thì khoảng trắng
            if pos == -1:
                pos = text.rfind(" ", start, end)

            # chỉ dùng điểm cắt nếu không quá gần đầu chunk
            if pos != -1 and pos > start + chunk_size * 0.7:
                end = pos

        chunks.append(text[start:end])

        if end >= length:
            break

        start = max(0, end - overlap)

    return chunks


def format_chunk(chunk):

    payload = {
        "model": MODEL,
        "stream": True,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": chunk
            }
        ],
        "options": {
            "num_ctx": NUM_CTX,
            "temperature": TEMPERATURE
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        stream=True
    )

    response.raise_for_status()

    output = ""

    for line in response.iter_lines():

        if not line:
            continue

        data = json.loads(line.decode("utf-8"))

        if "message" in data:
            text = data["message"].get("content", "")

            print(text, end="", flush=True)

            output += text

        if data.get("done", False):
            break

    print()

    return output

def main():

    text = Path(INPUT_FILE).read_text(
        encoding="utf-8",
        errors="ignore"
    )

    print("Cleaning text...")

    text = clean_text(text)

    chunks = split_text(
        text,
        CHUNK_SIZE,
        OVERLAP
    )

    print(f"Total chunks: {len(chunks)}")

    outputs = []

    for index, chunk in enumerate(chunks):

        print(f"\n========== Chunk {index + 1}/{len(chunks)} ==========\n")

        markdown = format_chunk(chunk)

        outputs.append(markdown)

    Path(OUTPUT_FILE).write_text(
        "\n\n".join(outputs),
        encoding="utf-8"
    )

    print()
    print("===================================")
    print("Finished!")
    print(f"Output saved to: {OUTPUT_FILE}")
    print("===================================")


if __name__ == "__main__":
    main()