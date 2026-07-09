# groq_markdown.py
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
import groq
import PyPDF2
from io import BytesIO

# Load environment variables
load_dotenv()

# System prompt for markdown formatting
SYSTEM_PROMPT = """You are a document reconstruction assistant.

Your task is to convert noisy plaintext extracted from PDF/OCR into clean Markdown.

Rules:
- Preserve ALL information.
- Never summarize.
- Never omit text.
- Reconstruct tables using Markdown tables.
- Merge broken lines into complete paragraphs.
- Preserve heading hierarchy (#, ##, ###).
- Preserve ordered and unordered lists.
- Remove OCR artifacts.
- Remove processing metadata such as timestamps unless explicitly part of the document.
- Output ONLY valid Markdown."""

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return None

def read_text_file(file_path):
    """Read text file with encoding fallback"""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue
    
    print(f"Error: Could not read file with any encoding")
    return None

def convert_to_markdown(text, custom_prompt=None, model="mixtral-8x7b-32768"):
    """Convert text to markdown using Groq API"""
    try:
        client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        if not client.api_key:
            print("Error: GROQ_API_KEY not found in environment variables")
            print("Please set it with: export GROQ_API_KEY='your-api-key'")
            return None
        
        prompt = custom_prompt or f"""
        Convert the following text to clean Markdown:
        
        {text}
        """
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model=model,
            temperature=0.1,
            max_tokens=4096,
        )
        
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return None

def save_markdown(content, input_path, output_path=None):
    """Save markdown content to file"""
    if output_path:
        output_file = output_path
    else:
        # Create output filename with .md extension
        input_path = Path(input_path)
        output_file = input_path.parent / f"{input_path.stem}_formatted.md"
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"Markdown saved to: {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(
        description="Convert file content to clean Markdown using Groq AI"
    )
    parser.add_argument(
        "file_path",
        help="Path to the text or PDF file to convert"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: input_name_formatted.md)"
    )
    parser.add_argument(
    "-m", "--model",
    default="llama-3.3-70b-versatile",  # Changed from mixtral-8x7b-32768
    choices=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"],
    help="Groq model to use (default: llama-3.3-70b-versatile)"
)
    parser.add_argument(
        "-p", "--prompt",
        help="Custom prompt to override the default"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the markdown output to console"
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)
    
    # Read file based on extension
    print(f"Reading file: {file_path}")
    
    if file_path.suffix.lower() == '.pdf':
        text = extract_text_from_pdf(file_path)
    else:
        text = read_text_file(file_path)

    print("text: ", text)
    
    if text is None:
        print("Error: Failed to read file")
        sys.exit(1)
    
    if not text.strip():
        print("Error: File is empty")
        sys.exit(1)
    
    print(f"Extracted {len(text)} characters from file")
    
    # Convert to markdown
    print("Converting to markdown using Groq AI...")
    print(f"Using model: {args.model}")
    
    markdown = convert_to_markdown(text, args.prompt, args.model)
    
    if markdown is None:
        print("Error: Conversion failed")
        sys.exit(1)
    
    # Save output
    output_file = save_markdown(markdown, file_path, args.output)
    
    # Print if requested
    if args.print:
        print("\n" + "="*50)
        print("MARKDOWN OUTPUT:")
        print("="*50)
        print(markdown)
    
    print(f"\n✅ Successfully converted '{file_path}' to markdown")

if __name__ == "__main__":
    main()