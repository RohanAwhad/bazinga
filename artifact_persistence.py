"""ArtifactPersistence — writes artifact files (diagrams, specs) to the project repo."""

from pathlib import Path


class ArtifactPersistence:
    """Persists artifact files scoped to a project directory."""

    def save_artifact(self, project_path: str, rel_path: str, content: str) -> str:
        """Write an artifact file to project_path/rel_path.

        Validates that rel_path resolves within project_path.
        Creates parent directories as needed.
        Returns a confirmation string.
        """
        project = Path(project_path).resolve()
        target = (project / rel_path).resolve()

        # Validate rel_path is within project_path
        if not str(target).startswith(str(project) + "/") and target != project:
            raise ValueError(
                f"rel_path '{rel_path}' resolves outside project_path '{project_path}'"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Artifact saved: {target} ({len(content)} bytes)"
