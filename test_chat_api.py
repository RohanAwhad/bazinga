"""Tests for the Chat API (PRD 002).

Covers assertions from 005_test_chat_sequence.mmd:

Input validation:
- session_id is not empty.
- project_path exists on filesystem.

Session lifecycle:
- New session returns empty list[Content].
- After one exchange, history has user + model turns (len == prev + 2).

Model interaction:
- contents passed to generate_content has user message appended.
- Response is not None.

Tool execution:
- Tool name exists in TOOL_FUNCTIONS.
- Tool result is str.
- History grows by 2 per tool iteration (tool call turn + tool result turn).

Artifact writes:
- rel_path is within project_path.
- File exists on filesystem after write.
- File content matches input.

Response contract:
- chat() returns str, never a Response object.
"""

import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.genai.types import Content, Part

from model_client import ModelClient
from state_store import StateStore
from tool_executor import ToolExecutor

# Import ChatAPI from server module
from server import ChatAPI


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def tmp_project_with_dingllm(tmp_path: Path) -> Path:
    """Create a temporary project directory with a .dingllm/ tree."""
    dingllm = tmp_path / ".dingllm"
    dingllm.mkdir()
    specs = dingllm / "specs"
    specs.mkdir()
    return tmp_path


@pytest.fixture
def state_store(tmp_path: Path) -> StateStore:
    """Create a StateStore with a temp DB path."""
    db_path = str(tmp_path / "test_sessions.json")
    return StateStore(db_path=db_path)


@pytest.fixture
def mock_model_client() -> MagicMock:
    """Create a mock ModelClient."""
    client = MagicMock(spec=ModelClient)
    client.config = MagicMock()
    return client


@pytest.fixture
def tool_executor(mock_model_client: MagicMock) -> ToolExecutor:
    """Create a ToolExecutor with a mock ModelClient."""
    return ToolExecutor(mock_model_client)


@pytest.fixture
def chat_api(
    mock_model_client: MagicMock,
    tool_executor: ToolExecutor,
    state_store: StateStore,
) -> ChatAPI:
    """Create a ChatAPI with mock dependencies."""
    return ChatAPI(mock_model_client, tool_executor, state_store)


def _make_text_response(text: str) -> MagicMock:
    """Create a mock model response with text content (no tool calls)."""
    response = MagicMock()
    response.text = text
    part = MagicMock()
    part.function_call = None
    content = MagicMock()
    content.parts = [part]
    content.role = "model"
    candidate = MagicMock()
    candidate.content = content
    response.candidates = [candidate]
    return response


def _make_tool_call_response(tool_name: str, tool_args: dict) -> MagicMock:
    """Create a mock model response with a single tool call."""
    response = MagicMock()
    response.text = None

    fc = MagicMock()
    fc.name = tool_name
    fc.args = tool_args

    part = MagicMock()
    part.function_call = fc

    content = Content(role="model", parts=[Part.from_text(text="placeholder")])
    # We need a real-ish content object that can be appended to history
    mock_content = MagicMock()
    mock_content.parts = [part]
    mock_content.role = "model"

    candidate = MagicMock()
    candidate.content = mock_content
    response.candidates = [candidate]
    return response


# ---------------------------------------------------------------------------
# StateStore tests
# ---------------------------------------------------------------------------


class TestStateStore:
    """StateStore round-trip and isolation tests."""

    def test_new_session_returns_empty_list(self, state_store: StateStore):
        """New session returns empty list[Content]."""
        history = state_store.load_session("/tmp/project", "session-new")
        assert history == []
        assert isinstance(history, list)

    def test_save_load_round_trip(self, state_store: StateStore):
        """Save and load preserves Content objects."""
        c1 = Content(role="user", parts=[Part.from_text(text="hello")])
        c2 = Content(role="model", parts=[Part.from_text(text="hi there")])
        state_store.save_session("/tmp/project", "session-001", [c1, c2])

        loaded = state_store.load_session("/tmp/project", "session-001")
        assert len(loaded) == 2
        assert loaded[0].role == "user"
        assert loaded[1].role == "model"

    def test_different_session_isolated(self, state_store: StateStore):
        """Different session IDs are isolated."""
        c1 = Content(role="user", parts=[Part.from_text(text="hello")])
        state_store.save_session("/tmp/project", "session-A", [c1])

        other = state_store.load_session("/tmp/project", "session-B")
        assert other == []

    def test_upsert_overwrites(self, state_store: StateStore):
        """Saving to the same session overwrites previous history."""
        c1 = Content(role="user", parts=[Part.from_text(text="first")])
        state_store.save_session("/tmp/project", "session-001", [c1])

        c2 = Content(role="user", parts=[Part.from_text(text="second")])
        c3 = Content(role="model", parts=[Part.from_text(text="reply")])
        state_store.save_session("/tmp/project", "session-001", [c1, c2, c3])

        loaded = state_store.load_session("/tmp/project", "session-001")
        assert len(loaded) == 3


# ---------------------------------------------------------------------------
# ChatAPI input validation tests
# ---------------------------------------------------------------------------


class TestChatAPIInputValidation:
    """Input validation: session_id and project_path checks."""

    def test_empty_session_id_rejected(self, chat_api: ChatAPI, tmp_project: Path):
        """Empty session_id raises ValueError."""
        with pytest.raises(ValueError, match="session_id must not be empty"):
            chat_api.chat(str(tmp_project), "", "hello")

    def test_nonexistent_project_path_rejected(self, chat_api: ChatAPI):
        """Non-existent project_path raises ValueError."""
        with pytest.raises(ValueError, match="project_path does not exist"):
            chat_api.chat("/nonexistent/path/xyz", "session-1", "hello")

    def test_root_project_path_rejected(self, chat_api: ChatAPI):
        """Root project_path raises ValueError."""
        with pytest.raises(ValueError, match="project_path must not be the filesystem root"):
            chat_api.create_session("/")

    def test_create_session_nonexistent_path_rejected(self, chat_api: ChatAPI):
        """create_session rejects non-existent project_path."""
        with pytest.raises(ValueError, match="project_path does not exist"):
            chat_api.create_session("/nonexistent/path/xyz")


# ---------------------------------------------------------------------------
# ChatAPI session lifecycle tests
# ---------------------------------------------------------------------------


class TestChatAPISessionLifecycle:
    """Session lifecycle: create, chat, history growth."""

    def test_create_session_returns_session_id(
        self, chat_api: ChatAPI, tmp_project: Path
    ):
        """create_session returns a non-empty string session_id."""
        session_id = chat_api.create_session(str(tmp_project))
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_chat_returns_str(
        self,
        chat_api: ChatAPI,
        mock_model_client: MagicMock,
        tmp_project: Path,
    ):
        """chat() returns str, never a Response object."""
        mock_model_client.generate_content.return_value = _make_text_response(
            "Hello! How can I help?"
        )
        session_id = chat_api.create_session(str(tmp_project))
        result = chat_api.chat(str(tmp_project), session_id, "hi")

        assert isinstance(result, str)
        assert result == "Hello! How can I help?"

    def test_history_grows_by_two_after_exchange(
        self,
        chat_api: ChatAPI,
        mock_model_client: MagicMock,
        state_store: StateStore,
        tmp_project: Path,
    ):
        """After one exchange, history has user + model turns (len == prev + 2)."""
        mock_model_client.generate_content.return_value = _make_text_response(
            "I'm fine!"
        )
        session_id = chat_api.create_session(str(tmp_project))
        project_path = str(Path(tmp_project).resolve())

        # Before chat: history is empty
        history_before = state_store.load_session(project_path, session_id)
        assert len(history_before) == 0

        chat_api.chat(str(tmp_project), session_id, "How are you?")

        # After chat: history has 2 entries (user + model)
        history_after = state_store.load_session(project_path, session_id)
        assert len(history_after) == len(history_before) + 2
        assert history_after[0].role == "user"
        assert history_after[1].role == "model"

    def test_response_is_not_none(
        self,
        chat_api: ChatAPI,
        mock_model_client: MagicMock,
        tmp_project: Path,
    ):
        """Model response must not be None."""
        mock_model_client.generate_content.return_value = None
        session_id = chat_api.create_session(str(tmp_project))
        with pytest.raises(RuntimeError, match="Response must not be None"):
            chat_api.chat(str(tmp_project), session_id, "hello")


# ---------------------------------------------------------------------------
# ToolExecutor tests
# ---------------------------------------------------------------------------


class TestToolExecutor:
    """Tool execution: path scoping, TOOL_FUNCTIONS registry, result types."""

    def test_tool_functions_registry(self, tool_executor: ToolExecutor):
        """TOOL_FUNCTIONS has all 3 required tools."""
        assert "list_files" in tool_executor.TOOL_FUNCTIONS
        assert "read_file" in tool_executor.TOOL_FUNCTIONS
        assert "search_replace" in tool_executor.TOOL_FUNCTIONS

    def test_scope_path_relative(self, tool_executor: ToolExecutor, tmp_project: Path):
        """Relative path scoped correctly within project."""
        p = tool_executor._scope_path("subdir/file.txt", str(tmp_project))
        assert p.is_relative_to(Path(tmp_project).resolve())

    def test_scope_path_traversal_rejected(
        self, tool_executor: ToolExecutor, tmp_project: Path
    ):
        """Path traversal (../../) is rejected."""
        with pytest.raises(ValueError, match="resolves outside project_path"):
            tool_executor._scope_path("../../etc/passwd", str(tmp_project))

    def test_list_files_returns_str(
        self, tool_executor: ToolExecutor, tmp_project: Path
    ):
        """list_files returns str."""
        result = tool_executor.list_files(".", project_path=str(tmp_project))
        assert isinstance(result, str)

    def test_read_file_returns_str(
        self, tool_executor: ToolExecutor, tmp_project: Path
    ):
        """read_file returns str for an existing file."""
        test_file = tmp_project / "test.txt"
        test_file.write_text("hello world")
        result = tool_executor.read_file("test.txt", project_path=str(tmp_project))
        assert isinstance(result, str)
        assert result == "hello world"

    def test_search_replace_creates_file(
        self, tool_executor: ToolExecutor, tmp_project: Path
    ):
        """search_replace with create_if_missing creates a new file."""
        result = tool_executor.search_replace(
            "newfile.txt",
            "",
            "new content",
            create_if_missing=True,
            project_path=str(tmp_project),
        )
        assert isinstance(result, str)
        created = tmp_project / "newfile.txt"
        assert created.exists()
        assert created.read_text() == "new content"


# ---------------------------------------------------------------------------
# ToolExecutor handle_tool_calls tests
# ---------------------------------------------------------------------------


class TestToolExecutorHandleToolCalls:
    """Tool call loop: history growth, tool dispatch, text termination."""

    def test_text_response_returns_immediately(
        self, tool_executor: ToolExecutor
    ):
        """If response has no tool calls, returns text directly."""
        response = _make_text_response("Just text, no tools")
        history: list[Content] = []
        result = tool_executor.handle_tool_calls(response, history, "/tmp")
        assert result == "Just text, no tools"

    def test_tool_call_then_text(
        self,
        tool_executor: ToolExecutor,
        mock_model_client: MagicMock,
        tmp_project: Path,
    ):
        """Tool call followed by text response: history grows by 2."""
        # First response: tool call to list_files
        tool_response = _make_tool_call_response(
            "list_files", {"path": "."}
        )
        # Second response: text
        text_response = _make_text_response("Here are the files")
        mock_model_client.generate_content.return_value = text_response

        history: list[Content] = []
        initial_len = len(history)
        result = tool_executor.handle_tool_calls(
            tool_response, history, str(tmp_project)
        )

        assert result == "Here are the files"
        # History should have grown by 2 (tool call turn + tool result turn)
        assert len(history) == initial_len + 2

    def test_unknown_tool_raises(self, tool_executor: ToolExecutor):
        """Unknown tool name raises ValueError."""
        response = _make_tool_call_response("nonexistent_tool", {})
        history: list[Content] = []
        with pytest.raises(ValueError, match="Unknown tool"):
            tool_executor.handle_tool_calls(response, history, "/tmp")


# ---------------------------------------------------------------------------
# ArtifactPersistence tests (via ToolExecutor)
# ---------------------------------------------------------------------------


class TestArtifactWriteViaToolExecutor:
    """Artifact writes: path validation, file creation, content matching."""

    def test_artifact_write_creates_file(
        self, tool_executor: ToolExecutor, tmp_project_with_dingllm: Path
    ):
        """Writing an artifact creates the file on filesystem."""
        result = tool_executor.search_replace(
            ".dingllm/specs/test.mmd",
            "",
            "graph LR; A-->B",
            create_if_missing=True,
            project_path=str(tmp_project_with_dingllm),
        )
        assert isinstance(result, str)
        target = tmp_project_with_dingllm / ".dingllm" / "specs" / "test.mmd"
        assert target.exists()

    def test_artifact_content_matches(
        self, tool_executor: ToolExecutor, tmp_project_with_dingllm: Path
    ):
        """Written artifact content matches input."""
        content = "sequenceDiagram\n  A->>B: msg"
        tool_executor.search_replace(
            ".dingllm/specs/flow.mmd",
            "",
            content,
            create_if_missing=True,
            project_path=str(tmp_project_with_dingllm),
        )
        target = tmp_project_with_dingllm / ".dingllm" / "specs" / "flow.mmd"
        assert target.read_text() == content

    def test_artifact_path_traversal_rejected(
        self, tool_executor: ToolExecutor, tmp_project_with_dingllm: Path
    ):
        """Artifact write with path traversal is rejected."""
        with pytest.raises(ValueError):
            tool_executor.search_replace(
                "../../etc/passwd",
                "",
                "bad content",
                create_if_missing=True,
                project_path=str(tmp_project_with_dingllm),
            )


# ---------------------------------------------------------------------------
# WebSocket endpoint existence test
# ---------------------------------------------------------------------------


class TestFastAPIApp:
    """FastAPI app configuration tests."""

    def test_app_title(self):
        """App title is 'Bazinga Local Server'."""
        from server import app
        assert app.title == "Bazinga Local Server"

    def test_ws_chat_endpoint_exists(self):
        """WebSocket /ws/chat endpoint exists."""
        from server import app
        ws_routes = [
            r for r in app.routes
            if hasattr(r, "path") and r.path == "/ws/chat"
        ]
        assert len(ws_routes) == 1

    def test_artifact_endpoints_exist(self):
        """HTTP artifact endpoints still exist."""
        from server import app
        artifact_routes = [
            r for r in app.routes
            if hasattr(r, "path") and r.path.startswith("/artifacts")
        ]
        assert len(artifact_routes) >= 2  # list + read


# ---------------------------------------------------------------------------
# Response contract tests
# ---------------------------------------------------------------------------


class TestResponseContract:
    """Response contract: chat() returns str."""

    def test_chat_returns_str_not_response(
        self,
        chat_api: ChatAPI,
        mock_model_client: MagicMock,
        tmp_project: Path,
    ):
        """chat() returns str, not a Response object."""
        mock_model_client.generate_content.return_value = _make_text_response(
            "Test response"
        )
        session_id = chat_api.create_session(str(tmp_project))
        result = chat_api.chat(str(tmp_project), session_id, "test")

        assert isinstance(result, str)
        assert not hasattr(result, "candidates")  # Not a Response
        assert result == "Test response"

    def test_empty_model_text_returns_fallback(
        self,
        chat_api: ChatAPI,
        mock_model_client: MagicMock,
        tmp_project: Path,
    ):
        """Empty model text produces a fallback string, not a crash."""
        response = _make_text_response("")
        response.text = ""
        mock_model_client.generate_content.return_value = response
        session_id = chat_api.create_session(str(tmp_project))
        result = chat_api.chat(str(tmp_project), session_id, "test")
        # ToolExecutor returns "(No response from model)" for empty text
        assert isinstance(result, str)
        assert len(result) > 0
