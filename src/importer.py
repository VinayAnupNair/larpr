import json
from pathlib import Path

import anthropic
import pdfplumber

from . import print_usage
from .schema import TOOL_DEFINITION


def extract_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def structure_resume(text: str, client: anthropic.Anthropic, model: str) -> dict:
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=(
            "You are a resume parser. Extract every detail from the resume text "
            "into the structure_resume tool. Preserve all facts, metrics, dates, "
            "and wording exactly as they appear. Do not invent or omit anything. "
            "Do not use em dashes."
        ),
        tools=[TOOL_DEFINITION],
        messages=[
            {
                "role": "user",
                "content": f"Parse this resume into structured JSON:\n\n{text}",
            }
        ],
    )

    print_usage(response, "import")

    for block in response.content:
        if block.type == "tool_use" and block.name == "structure_resume":
            return block.input

    raise RuntimeError("Claude did not return a tool_use block for structure_resume")


def run(pdf_path: str, output_path: str, client: anthropic.Anthropic, model: str):
    print(f"Extracting text from {pdf_path}...")
    text = extract_text(pdf_path)
    print(f"Extracted {len(text)} characters.")

    print("Sending to Claude for structuring...")
    data = structure_resume(text, client, model)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"Saved structured resume to {output_path}")
