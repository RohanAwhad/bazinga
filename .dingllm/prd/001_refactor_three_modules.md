# 001: Refactor play.py into 3-module architecture

**Gaps**: Entire codebase is a single 268-line monolith
**Severity**: medium
**Diagram**: `002_architecture.mmd`, `003_signatures.mmd`

## Current Behavior

All logic lives in `play.py`:
- Tool implementations (list_files, read_file, search_replace) — lines 40-95
- Tool declarations (TOOLS, FunctionDeclaration schemas) — lines 99-166
- GenerateContentConfig — line 168
- Input parsing (parse_input) — lines 171-190
- Tool-call loop (handle_tool_calls) — lines 193-223
- Main chat loop (main) — lines 226-267
- Client initialization and constants — lines 19-35

## Desired Behavior

Split into 3 modules per `002_architecture.mmd`:

### `tools.py` — Tool Implementations
- `list_files(path: str) -> str`
- `read_file(path: str) -> str`
- `search_replace(path: str, old_string: str, new_string: str, create_if_missing: bool = False) -> str`
- `TOOL_FUNCTIONS: dict[str, callable]` mapping

### `llm.py` — Model Zone
- Client initialization (`genai.Client(...)`)
- `MODEL` constant
- `TOOLS` list (FunctionDeclaration schemas)
- `CONFIG` (GenerateContentConfig)
- `generate_content(contents, config) -> response` — thin wrapper around `client.models.generate_content`

### `main.py` — Script Core
- `VIDEO_PREFIX`, `PDF_PREFIX`, `MIME_TYPES` constants
- `parse_input(raw: str) -> list[Part]`
- `handle_tool_calls(response, history: list[Content]) -> str` — imports from both `tools` and `llm`
- `main() -> None` — chat loop, imports from `llm` and uses `handle_tool_calls`

## Dependencies

None — this is the first PRD.

## Files to change

| Action | File |
|--------|------|
| Create | `tools.py` |
| Create | `llm.py` |
| Create | `main.py` |
| Delete | `play.py` (after migration complete and verified) |
