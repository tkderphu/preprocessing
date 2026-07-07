import re
from typing import List, Dict
from gliner import GLiNER


class VietnameseRedactor:

    def __init__(self):
        print("Loading GLiNER model...")

        self.model = GLiNER.from_pretrained(
            "urchade/gliner_multi-v2.1"
        )

        self.labels = [
            "person",
            "location",
            "organization"
        ]

    # ---------------------------------------------------
    # Regex Detection
    # ---------------------------------------------------

    EMAIL_PATTERN = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )

    PHONE_PATTERN = re.compile(
        r"(?:\+84|0)[35789]\d{8}"
    )

    CCCD_PATTERN = re.compile(
        r"\b\d{12}\b"
    )

    CMND_PATTERN = re.compile(
        r"\b\d{9}\b"
    )

    # ---------------------------------------------------
    # Regex PII
    # ---------------------------------------------------

    def detect_regex(self, text: str):

        entities = []

        for match in self.EMAIL_PATTERN.finditer(text):
            entities.append({
                "start": match.start(),
                "end": match.end(),
                "label": "EMAIL"
            })

        for match in self.PHONE_PATTERN.finditer(text):
            entities.append({
                "start": match.start(),
                "end": match.end(),
                "label": "PHONE"
            })

        for match in self.CCCD_PATTERN.finditer(text):
            entities.append({
                "start": match.start(),
                "end": match.end(),
                "label": "CCCD"
            })

        for match in self.CMND_PATTERN.finditer(text):
            entities.append({
                "start": match.start(),
                "end": match.end(),
                "label": "CMND"
            })

        return entities

    # ---------------------------------------------------
    # AI Detection
    # ---------------------------------------------------

    def detect_ai(self, text: str):

        results = self.model.predict_entities(
            text,
            self.labels
        )

        entities = []

        for item in results:

            label = item["label"].lower()

            if label == "person":
                entity = "PERSON"

            elif label == "location":
                entity = "ADDRESS"

            elif label == "organization":
                entity = "ORGANIZATION"

            else:
                continue

            entities.append({
                "start": item["start"],
                "end": item["end"],
                "label": entity
            })

        return entities

    # ---------------------------------------------------
    # Merge
    # ---------------------------------------------------

    def merge_entities(self, entities):

        entities.sort(
            key=lambda x: (
                x["start"],
                -(x["end"] - x["start"])
            )
        )

        merged = []

        current_end = -1

        for entity in entities:

            if entity["start"] >= current_end:
                merged.append(entity)
                current_end = entity["end"]

        return merged

    # ---------------------------------------------------
    # Redaction
    # ---------------------------------------------------

    def redact(self, text: str):

        regex_entities = self.detect_regex(text)

        ai_entities = self.detect_ai(text)

        entities = self.merge_entities(
            regex_entities + ai_entities
        )

        entities.sort(
            key=lambda x: x["start"],
            reverse=True
        )

        redacted = text

        for entity in entities:

            replacement = f"[{entity['label']}_REDACTED]"

            redacted = (
                redacted[:entity["start"]]
                + replacement
                + redacted[entity["end"]:]
            )

        return redacted, entities


if __name__ == "__main__":

    sample = """
    Chào anh,

    Tôi là Nguyễn Văn Hùng.

    Tôi đang sống tại
    12 Trần Hưng Đạo,
    Quận 1,
    TP Hồ Chí Minh.

    CCCD:
    012345678901

    Điện thoại:
    0912345678

    Email:
    hung.nguyen@company.com.vn

    Tôi làm việc tại FPT Software.
    """

    redactor = VietnameseRedactor()

    redacted_text, entities = redactor.redact(sample)

    print("=" * 80)
    print("Detected entities")
    print("=" * 80)

    for e in entities:
        print(e)

    print()
    print("=" * 80)
    print("Redacted text")
    print("=" * 80)
    print(redacted_text)