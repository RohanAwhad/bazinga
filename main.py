"""Multi-turn CLI chat with Gemini 3.1 Pro via Vertex AI.

Supports video input with: <|VIDEO|>/path/to/video.mov
Supports PDF input with: <|PDF|>/path/to/document.pdf
Model has tools: list_files, read_file, search_replace
"""

from pathlib import Path

from google.genai.types import Content, Part

from llm import CONFIG, generate_content
from tools import TOOL_FUNCTIONS

VIDEO_PREFIX = "<|VIDEO|>"
PDF_PREFIX = "<|PDF|>"

MIME_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}


def parse_input(raw: str) -> list[Part]:
    """Parse user input, returning a list of Parts for the API."""
    raw = raw.strip()
    if raw.startswith(VIDEO_PREFIX):
        video_path = Path(raw[len(VIDEO_PREFIX) :].strip()).expanduser()
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        suffix = video_path.suffix.lower()
        mime = MIME_TYPES.get(suffix)
        if mime is None:
            raise ValueError(f"Unsupported video extension: {suffix}")
        video_bytes = video_path.read_bytes()
        return [Part.from_bytes(data=video_bytes, mime_type=mime)]
    elif raw.startswith(PDF_PREFIX):
        pdf_path = Path(raw[len(PDF_PREFIX) :].strip()).expanduser()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        pdf_bytes = pdf_path.read_bytes()
        return [Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")]
    return [Part.from_text(text=raw)]


def handle_tool_calls(response, history: list[Content]) -> str:
    """Execute tool calls in a loop until the model produces a text response."""
    while True:
        parts = response.candidates[0].content.parts
        function_calls = [p for p in parts if p.function_call]
        if not function_calls:
            return response.text

        # Add model's tool-call turn to history
        history.append(response.candidates[0].content)

        # Execute each function call, build response parts
        fc_response_parts: list[Part] = []
        for part in function_calls:
            fc = part.function_call
            fn = TOOL_FUNCTIONS[fc.name]
            print(f"  [tool] {fc.name}({fc.args})")
            result = fn(**fc.args)
            fc_response_parts.append(
                Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Add function results to history and re-call
        history.append(Content(role="user", parts=fc_response_parts))
        response = generate_content(
            contents=history,
            config=CONFIG,
        )


def main() -> None:
    history: list[Content] = []
    print("Gemini 3.1 Pro — multi-turn chat")
    print("  Video input:  <|VIDEO|>/path/to/video.mov")
    print("  PDF input:    <|PDF|>/path/to/document.pdf")
    print("  Tools:        list_files, read_file, search_replace")
    print("  Exit:         quit / exit / ctrl-c")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Bye.")
            break

        parts = parse_input(user_input)
        user_content = Content(role="user", parts=parts)
        history.append(user_content)

        response = generate_content(
            contents=history,
            config=CONFIG,
        )

        assistant_text = handle_tool_calls(response, history)
        assistant_content = Content(
            role="model", parts=[Part.from_text(text=assistant_text)]
        )
        history.append(assistant_content)

        print(f"\nGemini: {assistant_text}\n")


if __name__ == "__main__":
    main()
