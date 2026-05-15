# AGENTS.md

## What this is

CLI chat agent powered by Gemini 3.1 Pro via Vertex AI (`google-genai` SDK). Supports multi-turn conversation with tool calling (file ops), video input, and PDF input.

## Run

```bash
uv run python main.py
```

## Auth

Requires Google Cloud credentials for Vertex AI. Project: `redhat-ai-analysis`, location: `global`.

```bash
gcloud auth application-default login
```

## Architecture

Three files, all at root:

- `main.py` — CLI loop, input parsing (video/PDF prefixes), tool-call execution loop
- `llm.py` — Gemini client init, model config, tool declarations, `generate_content()` wrapper
- `tools.py` — Tool implementations (`list_files`, `read_file`, `search_replace`) and `TOOL_FUNCTIONS` registry

Flow: `main.py:main()` → `llm.generate_content()` → if tool calls, `main.py:handle_tool_calls()` loops calling `tools.TOOL_FUNCTIONS[name]` until text response.

## Other files

- `gemini_vertex.py` — standalone experiment script (not part of main app)
- `.dingllm/` — specs, PRD, constitution docs (planning artifacts)
- `docs/` — research notes

## Conventions

- Python 3.12, `uv` for package management
- Single dependency: `google-genai>=2.2.0`
- No tests, no CI, no linter config currently
- Model is hardcoded in `llm.py:MODEL`
