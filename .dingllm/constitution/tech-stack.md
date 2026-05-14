# Tech Stack

## Runtime

| Component | Value |
|-----------|-------|
| Language | Python 3.x |
| Package manager | uv (assumed) |
| Runtime | Local CLI |

## Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Vertex AI / Gemini SDK (`google.genai`) |
| stdlib `pathlib` | File system operations for tools |

## Services

| Service | Details |
|---------|---------|
| Google Vertex AI | Model backend, project: `redhat-ai-analysis`, location: `global` |
| Model | `gemini-3.1-pro-preview` |

## Repo Layout

| Path | Purpose |
|------|---------|
| `play.py` | Current monolith (CLI agent) |
| `gemini_vertex.py` | Standalone Vertex AI tool-calling example |
| `.dingllm/specs/` | Mermaid sequence/architecture/class diagrams |
| `.dingllm/constitution/` | Project constitution (this directory) |
| `.dingllm/prd/` | Product requirement documents |
| `.dingllm/serve.py` | Local doc server for .dingllm/ files |
