# Devlogs

## 2026-05-14

- Reframed constitution around Bazinga as a visual, multimodal engineering control plane for agentic software development.
- Added `.dingllm/constitution/features.md` as the product capability map and phased plan.
- Updated roadmap and tech stack to reflect the current CLI prototype and future web/IDE-like target.
- Started v3 specs with context-level MVP diagrams in `.dingllm/specs/v3/`.
- Validated v3 Mermaid diagrams with Playwright against `.dingllm/serve.py`; flowchart titles must use Mermaid frontmatter instead of the `title` keyword.
- Corrected v3 context diagrams so diagram rendering is a Bazinga system capability, not an external system.
- Added v3 container architecture diagram for Web UI, Local Server, Agent Runtime, Bazinga State Store, and project workspace/artifact boundaries.
- Drilled into Agent Runtime with component architecture and component-level use case diagrams, both validated with Playwright.
- Merged chat/design agent into Bazinga Local Server (not a separate process boundary). Added Implementation Agent as the async worker container for approved PRDs.
- Rewrote 003 (container), 004 (server components), 005 (server use cases) to reflect this. All validated with Playwright.

## 2026-05-15

- Simplified 004 server components to match existing code structure: ChatAPI, ModelClient, ToolExecutor, ArtifactPersistence + added ArtifactAPI.
- Created chat and artifact browse sequence diagrams (005, 006) with typed signatures and project_path scoping.
- Created code-level diagrams: 007 (chat), 008 (artifact API) with `<<google-genai>>` and `<<bazinga>>` stereotypes for external vs owned types.
- Created test assertion diagram (005_test) for chat sequence.
- Approved 005, 005_test, 007. Created PRD 002 (Chat API) under `.dingllm/prd/v3/` with artifact provenance chain (diagram_commit: bd5fe88).
- Decided: FastAPI framework, WebSocket transport for chat.
- Replaced worktree-based implementation with container-based: ephemeral Implementation Workers, Redis job queue, SLURM-like job scheduling.
- Folded Implementation Agent into Local Server as a job scheduler component.
- Built and tested `Dockerfile.worker` (Alpine 3.21 + Python 3.12 + uv + git + gh + OpenCode 1.15.0). All tools verified inside container.
- Created `compose.yaml` with volume mounts for gcloud and gh auth (no baked credentials).
