# Application

# 1. Features

Using python and fastapi to create an application that can extract data from audio/docs/pdf files.

1. Upload files
2. send event to queue(rabbit mq)
3. create worker to handle data 
4. extract data based audio/docs/pdf
5. redact pii
6. formatting data to markdown: source, meeting date, participants
7. send mail and auto push to gitlab

For audio files, use whisper + diarization
For docs/pdf files, use apache tika and tesseract ocr
For formatting data to markdown using qwen3.5


# Setup

- create project structure
- write features
- create docker compose