---
title: Chat API
diagram_commit: bd5fe88
diagram_files:
  - .dingllm/specs/v3/005_server_chat_sequence.mmd
  - .dingllm/specs/v3/005_test_chat_sequence.mmd
  - .dingllm/specs/v3/007_server_code.mmd
approved_at: 2026-05-15
---

# PRD 002: Chat API

## Current Behavior

Bazinga is a CLI-only chat agent (`main.py`). Conversation history is in-memory, lost on exit. No session persistence, no API, no web interface.

## Desired Behavior

A local server exposes a Chat API that accepts `(project_path, session_id, message)` and returns a text response. The server manages multi-turn conversation with session persistence, LLM calls, and tool execution scoped to the target project.

## Components

### ChatAPI

| Method | Signature | Returns |
| --- | --- | --- |
| `chat` | `(project_path: str, session_id: str, message: str)` | `str` |
| `create_session` | `(project_path: str)` | `str` (session_id) |

- Receives a message, loads session history, calls ModelClient, handles the response, saves updated history, returns text.
- If `session_id` is new, starts with empty history.
- Returns text only. Never returns raw `Response` objects.

### ModelClient

| Method | Signature | Returns |
| --- | --- | --- |
| `generate_content` | `(contents: list[Content], config: GenerateContentConfig, project_path: str)` | `Response` |

- Wraps the LLM provider call.
- Holds `MODEL`, `TOOLS`, and `CONFIG` as private state.
- Uses `google-genai` types: `Content`, `Tool`, `GenerateContentConfig`, `Response`.

### ToolExecutor

| Method | Signature | Returns |
| --- | --- | --- |
| `handle_tool_calls` | `(response: Response, history: list[Content], project_path: str)` | `str` |
| `list_files` | `(path: str)` | `str` |
| `read_file` | `(path: str)` | `str` |
| `search_replace` | `(path: str, old_string: str, new_string: str, create_if_missing: bool)` | `str` |

- Loops until the model returns text (no more tool calls).
- Each iteration: execute tool call(s), append tool call + results to `history: list[Content]`, call `generate_content` again.
- All tool file paths are scoped to `project_path`.
- Holds `TOOL_FUNCTIONS: dict[str, callable]` mapping tool names to implementations.
- When a tool writes a diagram or spec, delegates to ArtifactPersistence.

### ArtifactPersistence

| Method | Signature | Returns |
| --- | --- | --- |
| `save_artifact` | `(project_path: str, rel_path: str, content: str)` | `str` |

- Writes artifact files (diagrams, specs) to the project repo.
- `rel_path` must be within `project_path`.

### StateStore

| Method | Signature | Returns |
| --- | --- | --- |
| `save_session` | `(project_path: str, session_id: str, history: list[Content])` | - |
| `load_session` | `(project_path: str, session_id: str)` | `list[Content]` |

- Persists session history keyed by `(project_path, session_id)`.
- Returns empty list for unknown sessions.
- Uses TinyDB.

## Sequence (happy path)

See `005_server_chat_sequence.mmd`:

1. Web UI calls `chat(project_path, session_id, message)`.
2. ChatAPI loads session history from StateStore.
3. ChatAPI calls `generate_content` on ModelClient with history + new message.
4. If Response is text: save history, return text.
5. If Response has tool calls: ToolExecutor loops -- execute tools, append to history, call LLM again -- until text response. If a tool writes an artifact, ArtifactPersistence saves it. Then save history, return text.

## Test Expectations

See `005_test_chat_sequence.mmd` for full assertion diagram. Key assertions:

### Input validation
- `session_id` is not empty.
- `project_path` exists on filesystem.

### Session lifecycle
- New session returns empty `list[Content]`.
- After one exchange, history has user + model turns (`len == prev + 2`).
- After tool loop, history includes all tool call and tool result turns.

### Model interaction
- `contents` passed to `generate_content` has user message appended.
- `Response` is not None.
- Final `Response.text` is a non-empty string.
- Final Response has no remaining tool calls.

### Tool execution
- Tool name exists in `TOOL_FUNCTIONS`.
- Tool args match expected schema.
- Tool result is `str`.
- History grows by 2 per tool iteration (tool call turn + tool result turn).

### Artifact writes
- `rel_path` is within `project_path`.
- File exists on filesystem after write.
- File content matches the input content.

### Response contract
- `chat()` returns `str`, never a `Response` object.

## Dependencies

- PRD 001 (3-module split) -- already done.
- `google-genai` SDK for `Content`, `Tool`, `GenerateContentConfig`, `Response` types.
- `tinydb` for StateStore.

## Implementation Decisions

- **Framework**: FastAPI.
- **Transport**: WebSocket. Chat requires streaming model responses and bidirectional communication within a session.
