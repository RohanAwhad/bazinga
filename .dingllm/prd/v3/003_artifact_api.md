---
title: Artifact API
diagram_commit: f19ffbd
diagram_files:
  - .dingllm/specs/v3/006_artifact_browse_sequence.mmd
  - .dingllm/specs/v3/006_test_artifact_browse_sequence.mmd
  - .dingllm/specs/v3/008_artifact_api_code.mmd
approved_at: 2026-05-15
---

# PRD 003: Artifact API

## Current Behavior

There is no way to browse or read `.dingllm/` artifacts from the Bazinga web UI. Artifacts (diagrams, PRDs, constitution, roadmap) are only accessible via the filesystem or the standalone `serve.py` doc server.

## Desired Behavior

The Bazinga Local Server exposes an Artifact API over HTTP that lets the Web UI list and read artifacts from a project's `.dingllm/` directory. The developer sees a file list in a sidebar and clicks a filename to render it in the diagram canvas.

## Components

### ArtifactAPI

| Method | Signature | Returns |
| --- | --- | --- |
| `list_artifacts` | `(project_path: str)` | `list[ArtifactEntry]` |
| `read_artifact` | `(project_path: str, rel_path: str)` | `str` |

- `list_artifacts` walks the `.dingllm/` directory tree under `project_path`.
- Only returns files with approved extensions: `md`, `mmd`, `txt`.
- Files with other extensions are excluded.
- If `.dingllm/` does not exist, returns an empty list (not an error).
- If `project_path` does not exist, returns an error.

- `read_artifact` reads a single file and returns its content as a string.
- `rel_path` must resolve to a location within `project_path` (path traversal prevention).
- `rel_path` must be a file, not a directory.
- Nonexistent `rel_path` returns an error.

### ArtifactEntry

| Field | Type |
| --- | --- |
| `name` | `str` |
| `path` | `str` |
| `type` | `str` |

- `name`: filename (e.g., `003_container_architecture.mmd`)
- `path`: relative path from `.dingllm/` (e.g., `specs/v3/003_container_architecture.mmd`)
- `type`: file extension (e.g., `mmd`)

### ArtifactPersistence

| Method | Signature | Returns |
| --- | --- | --- |
| `save_artifact` | `(project_path: str, rel_path: str, content: str)` | `str` |
| `read_artifact` | `(project_path: str, rel_path: str)` | `str` |
| `list_artifacts` | `(project_path: str)` | `list[ArtifactEntry]` |

- Shared with the Chat API (PRD 002) -- `save_artifact` is already defined there.
- This PRD adds `read_artifact` and `list_artifacts` to ArtifactPersistence.
- All methods enforce that paths stay within `project_path`.

## HTTP Endpoints

| Method | Path | Query Params | Returns |
| --- | --- | --- | --- |
| `GET` | `/artifacts` | `project_path` | `list[ArtifactEntry]` as JSON |
| `GET` | `/artifacts/{path}` | `project_path` | `str` (file content) |

## Sequence (happy path)

See `006_artifact_browse_sequence.mmd`:

1. Developer opens artifact sidebar in Web UI.
2. Web UI calls `GET /artifacts?project_path=...`.
3. Artifact API reads `.dingllm/` directory tree, filters to approved types.
4. Returns `[{name, path, type}]`.
5. Web UI shows file list in sidebar.
6. Developer clicks a diagram filename.
7. Web UI calls `GET /artifacts/{path}?project_path=...`.
8. Artifact API reads the file, returns content.
9. Web UI renders the Mermaid diagram in the canvas.

## Test Expectations

See `006_test_artifact_browse_sequence.mmd` for full assertion diagram. Key assertions:

### List artifacts
- Missing `.dingllm/` returns empty list, not error.
- Nonexistent `project_path` returns error.
- Response is `list[ArtifactEntry]` with `name`, `path`, `type` (all non-empty strings).
- Only approved extensions returned: `md`, `mmd`, `txt`.
- Files with other extensions are excluded.
- Entries match actual files in `.dingllm/` tree.
- Empty `.dingllm/` returns empty list.

### Read artifact
- Path traversal (`../../`) returns error.
- `rel_path` must be a file, not a directory.
- Nonexistent `rel_path` returns error.
- Response is `str`.

### Security
- `rel_path` is validated to resolve within `project_path` before any file read.

## Dependencies

- PRD 002 (Chat API) -- shares `ArtifactPersistence`. This PRD extends it with `read_artifact` and `list_artifacts`.
- FastAPI for HTTP endpoints.

## Implementation Decisions

- **Framework**: FastAPI (same server as Chat API).
- **Transport**: HTTP GET (read-only, no streaming needed).
