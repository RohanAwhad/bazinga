"""Artifact persistence layer for reading and listing .dingllm/ artifacts."""

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

APPROVED_EXTENSIONS = {"md", "mmd", "txt"}
DINGLLM_DIR = ".dingllm"


@dataclass
class ArtifactEntry:
    """Represents a single artifact file in the .dingllm/ directory."""

    name: str
    path: str
    type: str


def _validate_rel_path(rel_path: str) -> None:
    """Validate that rel_path is non-empty."""
    if not rel_path or not rel_path.strip():
        raise ValueError("rel_path must be a non-empty relative file path")


def _resolve_and_guard(project_path: str, rel_path: str) -> tuple[Path, Path]:
    """Resolve project and target paths, enforce traversal safety.

    Returns (dingllm_resolved, target_resolved).
    Raises ValueError if target is outside .dingllm/.
    """
    root = Path(project_path).resolve()
    dingllm = (root / DINGLLM_DIR).resolve()
    target = (dingllm / rel_path).resolve()

    # Path traversal prevention: target must be strictly inside dingllm
    if not str(target).startswith(str(dingllm) + "/"):
        raise ValueError(
            f"Path traversal detected: {rel_path} resolves outside project"
        )

    return dingllm, target


class ArtifactPersistence:
    """Reads and lists artifacts from a project's .dingllm/ directory.

    All methods enforce that paths stay within project_path.
    """

    def list_artifacts(self, project_path: str) -> list[ArtifactEntry]:
        """Walk the .dingllm/ directory tree and return approved artifact entries.

        Returns an empty list if .dingllm/ does not exist.
        Raises FileNotFoundError if project_path does not exist.
        """
        root = Path(project_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"project_path does not exist: {project_path}")

        dingllm = root / DINGLLM_DIR
        if not dingllm.exists() or not dingllm.is_dir():
            return []

        dingllm_resolved = dingllm.resolve()

        logger.debug("Listing artifacts in {}", project_path)
        entries: list[ArtifactEntry] = []
        for file_path in sorted(dingllm.rglob("*")):
            # Skip symlinks to prevent traversal via symlink
            if file_path.is_symlink():
                continue
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lstrip(".")
            if ext not in APPROVED_EXTENSIONS:
                continue
            # Verify resolved path is still within dingllm
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(dingllm_resolved) + "/"):
                continue
            rel = file_path.relative_to(dingllm)
            entries.append(
                ArtifactEntry(
                    name=file_path.name,
                    path=str(rel),
                    type=ext,
                )
            )
        logger.debug("Found {} artifacts in {}", len(entries), project_path)
        return entries

    def read_artifact(self, project_path: str, rel_path: str) -> str:
        """Read a single artifact file and return its content.

        rel_path is relative to .dingllm/ within project_path.
        Raises ValueError for path traversal attempts or disallowed extensions.
        Raises FileNotFoundError if the file does not exist.
        Raises IsADirectoryError if rel_path points to a directory.
        """
        _validate_rel_path(rel_path)
        logger.debug("Reading artifact {} from {}", rel_path, project_path)
        dingllm, target = _resolve_and_guard(project_path, rel_path)

        # Check symlink on the raw (unresolved) path for consistency with list_artifacts
        raw_path = Path(project_path).resolve() / DINGLLM_DIR / rel_path
        if raw_path.is_symlink():
            raise ValueError(f"Symlinks not allowed: {rel_path}")

        if not target.exists():
            raise FileNotFoundError(f"Artifact not found: {rel_path}")

        if target.is_dir():
            raise IsADirectoryError(f"Path is a directory, not a file: {rel_path}")

        # Enforce approved extensions on reads
        ext = target.suffix.lstrip(".")
        if ext not in APPROVED_EXTENSIONS:
            raise ValueError(f"File type not allowed: {ext}")

        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Cannot read artifact (encoding error): {exc}") from exc

    def save_artifact(self, project_path: str, rel_path: str, content: str) -> str:
        """Write artifact content to a file within .dingllm/.

        Shared with Chat API (PRD 002).
        Raises ValueError for path traversal, empty rel_path, or disallowed extensions.
        """
        _validate_rel_path(rel_path)
        logger.debug("Saving artifact {} to {}", rel_path, project_path)
        _, target = _resolve_and_guard(project_path, rel_path)

        # Enforce approved extensions on writes
        ext = target.suffix.lstrip(".")
        if ext not in APPROVED_EXTENSIONS:
            raise ValueError(f"File type not allowed: {ext}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.debug("Saved artifact to {}", target)
        return str(target)
