# Tech Stack

## Runtime

| Component | Value |
|-----------|-------|
| Language | Python 3.12 |
| Package manager | uv |
| Current runtime | Local CLI |
| Target runtime | Web/IDE-like UI plus local agent orchestration |

## Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Vertex AI / Gemini SDK (`google.genai`) |
| `tinydb` | State store for sessions, approvals, artifact links |
| stdlib `pathlib` | File system operations for tools |

## Services

| Service | Details |
|---------|---------|
| Google Vertex AI | Model backend, project: `redhat-ai-analysis`, location: `global` |
| Model | `gemini-3.1-pro-preview` |

## Local Development

| Component | Value |
|-----------|-------|
| Container runtime | Podman |
| Orchestration | Podman Compose |
| Service mapping | Each container from 003 runs as a separate Compose service (Web UI, Local Server, Implementation Agent, State Store) |
| Target project | Mounted as a volume from the host filesystem |

## Target Stack

Future UI and orchestration stack is intentionally TBD. Do not treat the current CLI architecture as the final product architecture.

## Repo Layout

| Path | Purpose |
|------|---------|
| `main.py` | Current CLI loop, input parsing, and tool-call execution loop |
| `llm.py` | Gemini client init, model config, tool declarations, API wrapper |
| `tools.py` | Tool implementations and `TOOL_FUNCTIONS` registry |
| `gemini_vertex.py` | Standalone Vertex AI tool-calling example |
| `.dingllm/specs/` | Mermaid sequence/architecture/class diagrams |
| `.dingllm/constitution/` | Project constitution (this directory) |
| `.dingllm/prd/` | Product requirement documents |
| `.dingllm/serve.py` | Local doc server for .dingllm/ files |
