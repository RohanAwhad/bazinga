"""Artifact API — business logic for listing and reading .dingllm/ artifacts."""

from artifact_persistence import ArtifactEntry, ArtifactPersistence


class ArtifactAPI:
    """High-level API for browsing project artifacts.

    Delegates to ArtifactPersistence for filesystem access.
    """

    def __init__(self, persistence: ArtifactPersistence | None = None) -> None:
        self._persistence = persistence or ArtifactPersistence()

    def list_artifacts(self, project_path: str) -> list[ArtifactEntry]:
        """List all approved artifacts under .dingllm/ in the given project.

        Returns an empty list if .dingllm/ does not exist.
        Raises FileNotFoundError if project_path does not exist.
        """
        return self._persistence.list_artifacts(project_path)

    def read_artifact(self, project_path: str, rel_path: str) -> str:
        """Read a single artifact's content.

        rel_path is relative to .dingllm/ within project_path.
        Raises ValueError for path traversal.
        Raises FileNotFoundError if artifact does not exist.
        Raises IsADirectoryError if rel_path is a directory.
        """
        return self._persistence.read_artifact(project_path, rel_path)
