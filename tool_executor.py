"""ToolExecutor — executes tool calls scoped to a project path."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from google.genai.types import Content, Part

from artifact_persistence import ArtifactPersistence

if TYPE_CHECKING:
    from model_client import ModelClient

# Patterns that trigger artifact persistence
_ARTIFACT_PATTERNS = [
    ".dingllm/specs/*.mmd",
    ".dingllm/specs/**/*.mmd",
    ".dingllm/*.md",
    ".dingllm/**/*.md",
]

# Maximum tool-call iterations before aborting
_MAX_TOOL_ROUNDS = 25


class ToolExecutor:
    """Executes tool calls with file paths scoped to a project directory."""

    def __init__(self, model_client: ModelClient) -> None:
        self._model_client = model_client
        self._artifact_persistence = ArtifactPersistence()
        self.TOOL_FUNCTIONS: dict[str, Callable[..., str]] = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "search_replace": self.search_replace,
        }

    def _scope_path(self, path: str, project_path: str) -> Path:
        """Resolve a tool path relative to project_path and validate it stays within."""
        project = Path(project_path).resolve()
        # If path is relative, resolve against project_path
        p = Path(path)
        if not p.is_absolute():
            resolved = (project / p).resolve()
        else:
            resolved = p.resolve()
        # Validate scoping
        if not str(resolved).startswith(str(project) + "/") and resolved != project:
            raise ValueError(
                f"Path '{path}' resolves outside project_path '{project_path}'"
            )
        return resolved

    def _is_artifact_path(self, rel_path: str) -> bool:
        """Check if a relative path matches artifact patterns."""
        p = Path(rel_path)
        for pattern in _ARTIFACT_PATTERNS:
            if p.match(pattern):
                return True
        return False

    def list_files(self, path: str, *, project_path: str) -> str:
        """List files and directories at the given path, scoped to project_path."""
        p = self._scope_path(path, project_path)
        if not p.exists():
            return f"Error: {p} does not exist"
        if not p.is_dir():
            return f"Error: {p} is not a directory"
        entries = sorted(p.iterdir())
        lines = []
        for e in entries:
            suffix = "/" if e.is_dir() else ""
            lines.append(f"{e.name}{suffix}")
        return "\n".join(lines) if lines else "(empty directory)"

    def read_file(self, path: str, *, project_path: str) -> str:
        """Read the text contents of a file, scoped to project_path."""
        p = self._scope_path(path, project_path)
        if not p.exists():
            return f"Error: {p} does not exist"
        if not p.is_file():
            return f"Error: {p} is not a file"
        return p.read_text()

    def search_replace(
        self,
        path: str,
        old_string: str,
        new_string: str,
        create_if_missing: bool = False,
        *,
        project_path: str,
    ) -> str:
        """Search and replace exact string in a file, scoped to project_path.

        When the file matches artifact patterns, delegates to ArtifactPersistence.
        """
        p = self._scope_path(path, project_path)
        project = Path(project_path).resolve()

        if not p.exists():
            if create_if_missing and old_string == "":
                # Check if this is an artifact path
                try:
                    rel = str(p.relative_to(project))
                except ValueError:
                    rel = ""
                if rel and self._is_artifact_path(rel):
                    return self._artifact_persistence.save_artifact(
                        project_path, rel, new_string
                    )
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(new_string)
                return f"Created {p} ({len(new_string)} bytes)"
            return f"Error: {p} does not exist"

        if not p.is_file():
            return f"Error: {p} is not a file"

        content = p.read_text()

        # Guard against empty old_string on existing files
        if old_string == "":
            return f"Error: old_string must not be empty for existing file {p}. Read the file first."

        count = content.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {p}"
        if count > 1:
            return f"Error: old_string found {count} times in {p} — provide more context to disambiguate"

        content = content.replace(old_string, new_string, 1)

        # Check if this is an artifact path
        try:
            rel = str(p.relative_to(project))
        except ValueError:
            rel = ""
        if rel and self._is_artifact_path(rel):
            return self._artifact_persistence.save_artifact(
                project_path, rel, content
            )

        p.write_text(content)
        return f"Replaced 1 occurrence in {p}"

    def handle_tool_calls(
        self, response, history: list[Content], project_path: str
    ) -> str:
        """Execute tool calls in a loop until the model produces a text response.

        Each iteration: execute tool call(s), append tool call + results to
        history, call generate_content again. History grows by 2 per iteration
        (model tool-call turn + user tool-result turn).
        """
        for _ in range(_MAX_TOOL_ROUNDS):
            if not response.candidates:
                raise RuntimeError("No candidates in model response (may be safety-filtered)")
            parts = response.candidates[0].content.parts
            function_calls = [p for p in parts if p.function_call]
            if not function_calls:
                text = response.text
                if not text:
                    return "(No response from model)"
                return text

            # Add model's tool-call turn to history
            history.append(response.candidates[0].content)

            # Execute each function call, build response parts
            fc_response_parts: list[Part] = []
            for part in function_calls:
                fc = part.function_call
                if fc.name not in self.TOOL_FUNCTIONS:
                    raise ValueError(f"Unknown tool: {fc.name}")
                fn = self.TOOL_FUNCTIONS[fc.name]
                # Inject project_path into tool kwargs
                kwargs = dict(fc.args) if fc.args else {}
                kwargs["project_path"] = project_path
                result = fn(**kwargs)
                if not isinstance(result, str):
                    raise TypeError(
                        f"Tool {fc.name} must return str, got {type(result)}"
                    )
                fc_response_parts.append(
                    Part.from_function_response(
                        name=fc.name, response={"result": result}
                    )
                )

            # Add function results to history and re-call
            history.append(Content(role="user", parts=fc_response_parts))
            response = self._model_client.generate_content(
                contents=history,
                config=self._model_client.config,
                project_path=project_path,
            )

        raise RuntimeError(
            f"Too many tool call rounds (max {_MAX_TOOL_ROUNDS})"
        )
