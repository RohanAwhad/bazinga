"""Multi-turn CLI chat with Gemini 3.1 Pro via Vertex AI.

Supports video input with: <|VIDEO|>/path/to/video.mov
Supports PDF input with: <|PDF|>/path/to/document.pdf
Model has tools: list_files, read_file, search_replace
"""

from pathlib import Path

from google import genai
from google.genai.types import (
    Content,
    FunctionDeclaration,
    GenerateContentConfig,
    Part,
    Tool,
)

client = genai.Client(
    vertexai=True,
    project="redhat-ai-analysis",
    location="global",
)

MODEL = "gemini-3.1-pro-preview"
VIDEO_PREFIX = "<|VIDEO|>"
PDF_PREFIX = "<|PDF|>"

MIME_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}

# --- Tool implementations ---


def list_files(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Error: {p} does not exist"
    if not p.is_dir():
        return f"Error: {p} is not a directory"
    entries = sorted(p.iterdir())
    lines = []
    for e in entries:
        suffix = "/" if e.is_dir() else ""
        lines.append(f"{e.name}{suffix}")
    return "\n".join(lines) if lines else "(empty directory)"


def read_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Error: {p} does not exist"
    if not p.is_file():
        return f"Error: {p} is not a file"
    return p.read_text()


def search_replace(path: str, old_string: str, new_string: str, create_if_missing: bool = False) -> str:
    """Search and replace exact string in a file.

    Operations:
    - Create new file:  set create_if_missing=True, old_string="", new_string=<full content>
    - Edit file:        old_string=<exact text to find>, new_string=<replacement>
    - Delete content:   old_string=<text to remove>, new_string=""
    """
    p = Path(path).expanduser()
    if not p.exists():
        if create_if_missing and old_string == "":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new_string)
            return f"Created {p} ({len(new_string)} bytes)"
        return f"Error: {p} does not exist"
    if not p.is_file():
        return f"Error: {p} is not a file"
    content = p.read_text()
    count = content.count(old_string)
    if count == 0:
        return f"Error: old_string not found in {p}"
    if count > 1:
        return f"Error: old_string found {count} times in {p} — provide more context to disambiguate"
    content = content.replace(old_string, new_string, 1)
    p.write_text(content)
    return f"Replaced 1 occurrence in {p}"


TOOL_FUNCTIONS: dict[str, callable] = {
    "list_files": list_files,
    "read_file": read_file,
    "search_replace": search_replace,
}

# --- Tool declarations ---

TOOLS = [
    Tool(
        function_declarations=[
            FunctionDeclaration(
                name="list_files",
                description="List files and directories at the given path",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path to list",
                        }
                    },
                    "required": ["path"],
                },
            ),
            FunctionDeclaration(
                name="read_file",
                description="Read the text contents of a file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to read",
                        }
                    },
                    "required": ["path"],
                },
            ),
            FunctionDeclaration(
                name="search_replace",
                description=(
                    "Search and replace an exact string in a file. "
                    "old_string must match file content exactly (including whitespace). "
                    "Fails if old_string matches 0 or >1 times — provide more surrounding context to disambiguate. "
                    "To CREATE a new file: set create_if_missing=true, old_string='', new_string=<full file content>. "
                    "To DELETE content: set old_string=<text to remove>, new_string=''. "
                    "To EDIT: set old_string=<exact text to find>, new_string=<replacement text>. "
                    "Always read_file first before editing to see current content."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to edit or create",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "Exact string to find in the file (empty string for new file creation)",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "Replacement string (empty string to delete content)",
                        },
                        "create_if_missing": {
                            "type": "boolean",
                            "description": "If true and file does not exist, create it with new_string as content. Parent dirs are created automatically.",
                        },
                    },
                    "required": ["path", "old_string", "new_string"],
                },
            ),
        ]
    )
]

CONFIG = GenerateContentConfig(tools=TOOLS)


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
        response = client.models.generate_content(
            model=MODEL,
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

        response = client.models.generate_content(
            model=MODEL,
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
