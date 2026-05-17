---
title: Web UI (Phase 1)
diagram_commit: 4286b4a
diagram_files:
  - .dingllm/specs/v3/009_component_flowchart_web_ui.mmd
  - .dingllm/specs/v3/010_code_class_chat.mmd
  - .dingllm/specs/v3/011_container_flowchart_web_ui_use_cases.mmd
  - .dingllm/specs/v3/012_code_sequence_start_session.mmd
  - .dingllm/specs/v3/012_code_sequence_send_message.mmd
  - .dingllm/specs/v3/012_code_sequence_stream_response.mmd
  - .dingllm/specs/v3/012_test_code_sequence_start_session.mmd
  - .dingllm/specs/v3/012_test_code_sequence_send_message.mmd
  - .dingllm/specs/v3/012_test_code_sequence_stream_response.mmd
  - .dingllm/specs/v3/013_code_sequence_browse_artifacts.mmd
  - .dingllm/specs/v3/013_code_sequence_view_markdown.mmd
  - .dingllm/specs/v3/013_code_sequence_view_mermaid.mmd
  - .dingllm/specs/v3/013_test_code_sequence_browse_artifacts.mmd
  - .dingllm/specs/v3/013_test_code_sequence_view_markdown.mmd
  - .dingllm/specs/v3/013_test_code_sequence_view_mermaid.mmd
approved_at: 2026-05-17
---

# PRD 004: Web UI (Phase 1)

## Current Behavior

Bazinga has a local server with a Chat API (WebSocket, PRD 002) and an Artifact API (HTTP GET, PRD 003). There is no web interface — the APIs can only be exercised via CLI tools or scripts.

## Desired Behavior

A React + TypeScript web app that provides a two-panel layout: a sidebar for chatting with the agent, and a main content panel for viewing project artifacts (markdown and mermaid diagrams). The app connects to the existing Chat API and Artifact API on the local server.

## Components

See `009_component_flowchart_web_ui.mmd` for the full component architecture.

### UI Components

#### App Shell

- Root layout component. Renders the sidebar (Chat Panel) and main panel (Content Panel) side by side.
- No routing in Phase 1 — single page.

#### Chat Panel

- Sidebar component. Shows message history and a text input.
- Displays user messages and assistant messages in distinct styles.
- Assistant messages may contain clickable artifact references.
- Clicking an artifact ref writes the selection to Session Store.

#### Content Panel

- Main panel component. Renders the currently selected artifact.
- Reads `selectedArtifact` from Session Store.
- Fetches artifact content via Artifact Client.
- Delegates rendering to Markdown Renderer (`.md`) or Mermaid Renderer (`.mmd`) based on file extension.
- Shows artifact file path in a header bar.

#### Markdown Renderer

- Receives raw markdown string, renders to HTML.
- Supports headings, lists, code blocks, tables, inline code.

#### Mermaid Renderer

- Receives raw mermaid string, renders to SVG.
- Supports pan and zoom on the rendered diagram.
- Shows parse errors inline if the mermaid syntax is invalid.

### Infrastructure Components

#### WebSocket Client

See `010_code_class_chat.mmd` for type definitions.

| Method | Signature | Description |
| --- | --- | --- |
| `connect` | `(url: string) => void` | Opens WebSocket connection to Chat API |
| `disconnect` | `() => void` | Closes connection |
| `send` | `(payload: WsSendPayload) => void` | Sends chat message |
| `onMessage` | `(handler: (msg: WsReceivePayload) => void) => void` | Registers message handler |
| `onStatusChange` | `(handler: (status: ConnectionStatus) => void) => void` | Registers status handler |

- `ConnectionStatus`: `connecting | connected | disconnected | error`
- `WsSendPayload`: `{ type: "chat", sessionId: string, content: string }`
- `WsReceivePayload`: `{ type: "chunk" | "done" | "error", content?: string, artifactRefs?: ArtifactRef[] }`

#### Artifact Client

| Method | Signature | Description |
| --- | --- | --- |
| `listArtifacts` | `() => Promise<ArtifactEntry[]>` | Calls `GET /artifacts` |
| `fetchArtifact` | `(path: string) => Promise<string>` | Calls `GET /artifacts/{path}` |

- `ArtifactEntry`: `{ name: string, path: string, type: string }`

#### Session Store

| Method | Signature | Description |
| --- | --- | --- |
| `addMessage` | `(msg: ChatMessage) => void` | Appends message to history |
| `appendChunk` | `(id: string, chunk: string) => void` | Appends streaming chunk to in-progress message |
| `setSelectedArtifact` | `(ref: ArtifactRef) => void` | Sets currently viewed artifact |

- `ChatMessage`: `{ id: string, role: "user" | "assistant", content: string, artifactRefs?: ArtifactRef[] }`
- `ArtifactRef`: `{ path: string, label: string }`
- State: `{ sessionId: string, messages: ChatMessage[], selectedArtifact: ArtifactRef | null }`
- Client-side only in Phase 1. No persistence across page reloads.

## Sequences

### Chat Use Cases

See `012_code_sequence_*.mmd` for detailed flows.

#### Start / Resume Session (`012_code_sequence_start_session.mmd`)

1. Developer opens app or selects a session.
2. Chat Panel reads existing sessions from Session Store.
3. For new session: create session with new ID. For existing: load message history.
4. Chat Panel calls `WebSocketClient.connect(sessionId)`.
5. WebSocket connection established with Chat API.

#### Send Chat Message (`012_code_sequence_send_message.mmd`)

1. Developer types message and clicks Send.
2. Chat Panel adds user message to Session Store.
3. Chat Panel renders user message bubble.
4. Chat Panel sends `WsSendPayload` via WebSocket Client.
5. WebSocket Client transmits frame to Chat API.

#### View Streaming Response (`012_code_sequence_stream_response.mmd`)

1. Chat API sends `WsReceivePayload` chunks.
2. WebSocket Client forwards each chunk to Chat Panel.
3. Chat Panel appends each chunk to Session Store.
4. Chat Panel renders streaming text progressively.
5. Chat API sends `done` payload with artifact refs.
6. Chat Panel finalizes message and stores artifact refs.
7. Chat Panel renders complete message with clickable artifact refs.
8. Developer clicks artifact ref — Chat Panel writes selection to Session Store.

### Artifact Use Cases

See `013_code_sequence_*.mmd` for detailed flows.

#### Browse Artifact List (`013_code_sequence_browse_artifacts.mmd`)

1. Developer opens content panel.
2. Content Panel calls `ArtifactClient.listArtifacts()`.
3. Artifact Client sends `GET /artifacts`.
4. Artifact API returns `ArtifactEntry[]`.
5. Content Panel renders artifact list grouped by directory.

#### View Markdown Artifact (`013_code_sequence_view_markdown.mmd`)

1. Developer clicks `.md` artifact.
2. Content Panel reads `selectedArtifact` from Session Store.
3. Content Panel calls `ArtifactClient.fetchArtifact(path)`.
4. Artifact API returns raw markdown content.
5. Content Panel delegates to Markdown Renderer.
6. Markdown Renderer returns HTML.
7. Content Panel displays rendered markdown.

#### View Mermaid Diagram (`013_code_sequence_view_mermaid.mmd`)

1. Developer clicks `.mmd` artifact.
2. Content Panel reads `selectedArtifact` from Session Store.
3. Content Panel calls `ArtifactClient.fetchArtifact(path)`.
4. Artifact API returns raw mermaid content.
5. Content Panel delegates to Mermaid Renderer.
6. Mermaid Renderer returns SVG.
7. Content Panel displays rendered diagram with pan/zoom.

## Test Expectations

See `012_test_*.mmd` and `013_test_*.mmd` for full assertion diagrams.

### Start / Resume Session

- Session list returns array (empty OK for first use).
- New session ID is non-empty and unique.
- Resumed session renders messages in chronological order.
- Message count matches store.
- WebSocket status transitions: `connecting` → `connected`.
- Send button enabled only after connected.

### Send Chat Message

- Input is non-empty before send.
- Input cleared after send.
- User message appears in list, styled as user bubble.
- `WsSendPayload.type` is `"chat"`.
- `WsSendPayload.sessionId` matches current session.
- `WsSendPayload.content` matches input text.
- Connection status is `connected` before send.
- Store message count increments by 1.

### View Streaming Response

- Each chunk payload has non-empty content.
- Store message content grows by chunk length.
- Partial text visible during streaming, styled as assistant bubble.
- Final content equals concatenation of all chunks.
- Done payload finalizes message.
- Artifact refs stored on message (may be empty array).
- Each artifact ref has `path` and `label`.
- Artifact refs rendered as clickable elements.
- Streaming indicator removed after done.
- Clicking artifact ref sets `selectedArtifact` in store.

### Browse Artifact List

- Response is array (empty OK if no `.dingllm/`).
- Each entry has `path`, `type`, `name` (non-empty strings, see note below about `size`).
- Type is one of: `md`, `mmd`, `txt`.
- List item count matches response length.
- Entries grouped by parent directory.
- Each item is clickable.

### View Markdown Artifact

- `selectedArtifact` is not null, path ends with `.md`.
- Response status 200, body is non-empty string.
- Output is rendered HTML, not raw markdown.
- Headings, lists, code blocks rendered correctly.
- File path shown in content header.

### View Mermaid Diagram

- `selectedArtifact` is not null, path ends with `.mmd`.
- Response status 200, body is non-empty string.
- Output contains SVG element, not raw mermaid text.
- No mermaid parse errors.
- File path shown in content header.
- Diagram is pannable and zoomable.

### Integration Tests (Playwright)

Prerequisites: local server running (Chat API + Artifact API), Web UI dev server running, a target project with `.dingllm/` containing at least one `.md` and one `.mmd` file.

#### Chat round-trip

1. Open the app in a real browser.
2. Assert WebSocket connection established (send button enabled).
3. Type a message in the chat input, click Send.
4. Assert user message bubble appears.
5. Assert assistant response streams in (text appears progressively).
6. Assert assistant message bubble is complete after streaming finishes.

#### Artifact ref → content panel

1. Send a message that triggers artifact refs in the response (e.g., ask about architecture).
2. Assert at least one clickable artifact ref appears in the assistant message.
3. Click an artifact ref.
4. Assert content panel header shows the artifact file path.
5. If `.md`: assert rendered HTML is visible (not raw markdown).
6. If `.mmd`: assert SVG element is present (not raw mermaid text).

#### Browse artifacts

1. Open the content panel.
2. Assert artifact list is populated (at least one entry).
3. Assert entries are grouped by directory.
4. Click a `.md` artifact in the list.
5. Assert content panel renders markdown as HTML.
6. Click a `.mmd` artifact in the list.
7. Assert content panel renders mermaid as SVG.

#### Error handling

1. Disconnect the local server while the UI is open.
2. Assert WebSocket status reflects disconnected state.
3. Assert send button is disabled.
4. Request a nonexistent artifact path.
5. Assert content panel shows an error state, not a blank screen.

## Dependencies

- PRD 002 (Chat API) — WebSocket server endpoint.
- PRD 003 (Artifact API) — HTTP GET endpoints for listing and reading artifacts.

## Implementation Decisions

- **Framework**: React + TypeScript.
- **Build tool**: Vite.
- **State management**: React Context or Zustand (implementer's choice, must satisfy Session Store interface).
- **Markdown rendering**: `react-markdown` or `marked` (implementer's choice).
- **Mermaid rendering**: `mermaid` library, client-side rendering.
- **No routing**: Single page app, no React Router in Phase 1.
- **No server-side rendering**: Client-side only.
- **No persistence**: Session state is in-memory, lost on page reload in Phase 1.
- **Layout**: See `.dingllm/wireframes/phase1_web_ui.html` for reference wireframe.

## Notes

- The `ArtifactEntry` type in PRD 003 has `name`, `path`, `type`. The 013 test diagram mentions `size` — this is aspirational. If the Artifact API doesn't return `size`, omit it. Do not break the API contract from PRD 003.
- The Web UI assumes the local server is running on the same host. The base URL for API connections should be configurable (environment variable or config file).
