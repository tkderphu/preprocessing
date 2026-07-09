import sys
from app.services.extractor.audio import AudioExtractor

try:
    print(AudioExtractor().extract('audio2.mp3').raw_transcript)
except Exception as e:
    import traceback
    traceback.print_exc()
