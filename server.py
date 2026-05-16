"""Bazinga Local Server — FastAPI application.

Exposes the Artifact API over HTTP and the Chat API over WebSocket.

Run:
    uv run uvicorn server:app --reload --port 8080
"""

import asyncio
import threading
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from google.genai.types import Content, Part
from loguru import logger

from artifact_api import ArtifactAPI
from model_client import ModelClient
from state_store import StateStore
from tool_executor import ToolExecutor

app = FastAPI(title="Bazinga Local Server")

# --- Artifact API ---

_artifact_api = ArtifactAPI()


@app.get("/artifacts")
def list_artifacts(project_path: str = Query(..., description="Absolute path to the project root")):
    """List all approved artifacts under .dingllm/ in the given project.

    Returns a JSON array of ArtifactEntry objects.
    """
    logger.info("GET /artifacts project_path={}", project_path)
    try:
        entries = _artifact_api.list_artifacts(project_path)
    except FileNotFoundError as exc:
        logger.warning("list_artifacts failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    return [asdict(entry) for entry in entries]


@app.get("/artifacts/{path:path}")
def read_artifact(
    path: str,
    project_path: str = Query(..., description="Absolute path to the project root"),
):
    """Read a single artifact file from .dingllm/.

    Returns the file content as plain text.
    """
    logger.info("GET /artifacts/{} project_path={}", path, project_path)
    try:
        content = _artifact_api.read_artifact(project_path, path)
    except FileNotFoundError as exc:
        logger.warning("read_artifact failed: {}", exc)
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        logger.warning("read_artifact failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except IsADirectoryError as exc:
        logger.warning("read_artifact failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    return PlainTextResponse(content)


# --- Chat API ---

_model_client = ModelClient()
_tool_executor = ToolExecutor(_model_client)
_state_store = StateStore()

# Per-session locks to serialize concurrent access to the same session
_session_locks: dict[str, threading.Lock] = {}
_session_locks_guard = threading.Lock()


def _get_session_lock(session_id: str) -> threading.Lock:
    """Get or create a lock for the given session_id."""
    with _session_locks_guard:
        if session_id not in _session_locks:
            _session_locks[session_id] = threading.Lock()
        return _session_locks[session_id]


class ChatAPI:
    """Chat API that manages sessions, LLM calls, and tool execution."""

    def __init__(
        self,
        model_client: ModelClient,
        tool_executor: ToolExecutor,
        state_store: StateStore,
    ) -> None:
        self._model_client = model_client
        self._tool_executor = tool_executor
        self._state_store = state_store

    def create_session(self, project_path: str) -> str:
        """Create a new session for the given project. Returns session_id."""
        project_path = str(Path(project_path).resolve())
        if project_path == "/":
            raise ValueError("project_path must not be the filesystem root")
        if not Path(project_path).exists():
            raise ValueError(f"project_path does not exist: {project_path}")
        session_id = uuid.uuid4().hex
        # Initialize with empty history
        self._state_store.save_session(project_path, session_id, [])
        return session_id

    def chat(self, project_path: str, session_id: str, message: str) -> str:
        """Process a chat message and return a text response.

        Loads session history, appends the user message, calls the model,
        handles any tool calls, saves updated history, and returns text.
        Always returns str, never a raw Response object.
        """
        if not session_id:
            raise ValueError("session_id must not be empty")
        project_path = str(Path(project_path).resolve())
        if not Path(project_path).exists():
            raise ValueError(f"project_path does not exist: {project_path}")

        lock = _get_session_lock(session_id)
        with lock:
            # Load session history
            history = self._state_store.load_session(project_path, session_id)

            # Append user message
            user_content = Content(
                role="user", parts=[Part.from_text(text=message)]
            )
            history.append(user_content)

            # Call model
            response = self._model_client.generate_content(
                contents=history,
                config=self._model_client.config,
                project_path=project_path,
            )
            if response is None:
                raise RuntimeError("Response must not be None")

            # Handle tool calls if present, otherwise get text directly
            text = self._tool_executor.handle_tool_calls(
                response, history, project_path
            )
            if not isinstance(text, str) or not text:
                raise RuntimeError("Response text must be a non-empty string")

            # Append model's final text response to history
            model_content = Content(
                role="model", parts=[Part.from_text(text=text)]
            )
            history.append(model_content)

            # Save updated history
            self._state_store.save_session(project_path, session_id, history)

            return text


# Shared ChatAPI instance
_chat_api = ChatAPI(_model_client, _tool_executor, _state_store)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for the Chat API.

    Accepts JSON messages:
      - Chat: {"project_path": "...", "session_id": "...", "message": "..."}
        Returns: {"response": "..."}
      - Create session: {"action": "create_session", "project_path": "..."}
        Returns: {"session_id": "..."}
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "create_session":
                project_path = data.get("project_path")
                if not project_path:
                    await websocket.send_json(
                        {"error": "missing 'project_path'"}
                    )
                    continue
                session_id = await asyncio.to_thread(
                    _chat_api.create_session, project_path
                )
                await websocket.send_json({"session_id": session_id})
            else:
                project_path = data.get("project_path")
                session_id = data.get("session_id")
                message = data.get("message")
                if not project_path or not session_id or not message:
                    missing = [
                        f for f in ("project_path", "session_id", "message")
                        if not data.get(f)
                    ]
                    await websocket.send_json(
                        {"error": f"missing fields: {', '.join(missing)}"}
                    )
                    continue
                response_text = await asyncio.to_thread(
                    _chat_api.chat, project_path, session_id, message
                )
                await websocket.send_json({"response": response_text})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close(code=1011)
        except Exception:
            pass
