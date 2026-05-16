"""Tests for the Artifact API.

Covers all assertions from 006_test_artifact_browse_sequence.mmd:

List artifacts:
- Missing .dingllm/ returns empty list, not error.
- Nonexistent project_path returns error.
- Response is list[ArtifactEntry] with name, path, type (all non-empty strings).
- Only approved extensions returned: md, mmd, txt.
- Files with other extensions are excluded.
- Entries match actual files in .dingllm/ tree.
- Empty .dingllm/ returns empty list.

Read artifact:
- Path traversal (../../) returns error.
- rel_path must be a file, not a directory.
- Nonexistent rel_path returns error.
- Response is str.

Security:
- rel_path is validated to resolve within project_path before any file read.
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from artifact_api import ArtifactAPI
from artifact_persistence import ArtifactEntry, ArtifactPersistence
from server import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with a .dingllm/ tree."""
    dingllm = tmp_path / ".dingllm"
    dingllm.mkdir()

    # constitution/
    constitution = dingllm / "constitution"
    constitution.mkdir()
    (constitution / "mission.md").write_text("# Mission\nBuild things.")

    # specs/
    specs = dingllm / "specs"
    specs.mkdir()
    (specs / "001_arch.mmd").write_text("graph TD\n  A-->B")

    # specs/v3/
    v3 = specs / "v3"
    v3.mkdir()
    (v3 / "002_detail.mmd").write_text("sequenceDiagram\n  A->>B: msg")

    # prd/
    prd = dingllm / "prd"
    prd.mkdir()
    (prd / "notes.txt").write_text("Some notes")

    # Files that should be excluded
    (dingllm / "image.png").write_bytes(b"\x89PNG")
    (dingllm / "data.json").write_text('{"key": "value"}')
    (dingllm / "script.py").write_text("print('hello')")

    return tmp_path


@pytest.fixture
def tmp_empty_dingllm(tmp_path: Path) -> Path:
    """Create a project with an empty .dingllm/ directory."""
    (tmp_path / ".dingllm").mkdir()
    return tmp_path


@pytest.fixture
def tmp_no_dingllm(tmp_path: Path) -> Path:
    """Create a project directory without .dingllm/."""
    return tmp_path


@pytest.fixture
def persistence() -> ArtifactPersistence:
    return ArtifactPersistence()


@pytest.fixture
def api() -> ArtifactAPI:
    return ArtifactAPI()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ===========================================================================
# ArtifactPersistence tests
# ===========================================================================


class TestArtifactPersistenceList:
    """Tests for ArtifactPersistence.list_artifacts."""

    def test_returns_approved_files(self, persistence: ArtifactPersistence, tmp_project: Path):
        entries = persistence.list_artifacts(str(tmp_project))
        names = {e.name for e in entries}
        assert "mission.md" in names
        assert "001_arch.mmd" in names
        assert "002_detail.mmd" in names
        assert "notes.txt" in names

    def test_excludes_unapproved_extensions(self, persistence: ArtifactPersistence, tmp_project: Path):
        entries = persistence.list_artifacts(str(tmp_project))
        names = {e.name for e in entries}
        assert "image.png" not in names
        assert "data.json" not in names
        assert "script.py" not in names

    def test_only_approved_types(self, persistence: ArtifactPersistence, tmp_project: Path):
        entries = persistence.list_artifacts(str(tmp_project))
        for entry in entries:
            assert entry.type in ("md", "mmd", "txt")

    def test_entries_have_nonempty_fields(self, persistence: ArtifactPersistence, tmp_project: Path):
        entries = persistence.list_artifacts(str(tmp_project))
        assert len(entries) > 0
        for entry in entries:
            assert isinstance(entry.name, str) and entry.name
            assert isinstance(entry.path, str) and entry.path
            assert isinstance(entry.type, str) and entry.type

    def test_entries_match_actual_files(self, persistence: ArtifactPersistence, tmp_project: Path):
        entries = persistence.list_artifacts(str(tmp_project))
        dingllm = tmp_project / ".dingllm"
        for entry in entries:
            full_path = dingllm / entry.path
            assert full_path.exists(), f"Entry {entry.path} does not exist on disk"
            assert full_path.is_file()

    def test_path_is_relative_to_dingllm(self, persistence: ArtifactPersistence, tmp_project: Path):
        entries = persistence.list_artifacts(str(tmp_project))
        paths = {e.path for e in entries}
        assert "constitution/mission.md" in paths
        assert "specs/001_arch.mmd" in paths
        assert "specs/v3/002_detail.mmd" in paths
        assert "prd/notes.txt" in paths

    def test_missing_dingllm_returns_empty_list(self, persistence: ArtifactPersistence, tmp_no_dingllm: Path):
        entries = persistence.list_artifacts(str(tmp_no_dingllm))
        assert entries == []

    def test_empty_dingllm_returns_empty_list(self, persistence: ArtifactPersistence, tmp_empty_dingllm: Path):
        entries = persistence.list_artifacts(str(tmp_empty_dingllm))
        assert entries == []

    def test_nonexistent_project_path_raises(self, persistence: ArtifactPersistence):
        with pytest.raises(FileNotFoundError):
            persistence.list_artifacts("/nonexistent/path/that/does/not/exist")


class TestArtifactPersistenceRead:
    """Tests for ArtifactPersistence.read_artifact."""

    def test_reads_file_content(self, persistence: ArtifactPersistence, tmp_project: Path):
        content = persistence.read_artifact(str(tmp_project), "constitution/mission.md")
        assert isinstance(content, str)
        assert "# Mission" in content

    def test_reads_nested_file(self, persistence: ArtifactPersistence, tmp_project: Path):
        content = persistence.read_artifact(str(tmp_project), "specs/v3/002_detail.mmd")
        assert "sequenceDiagram" in content

    def test_nonexistent_rel_path_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(FileNotFoundError):
            persistence.read_artifact(str(tmp_project), "nonexistent/file.md")

    def test_directory_rel_path_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(IsADirectoryError):
            persistence.read_artifact(str(tmp_project), "specs")

    def test_path_traversal_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(ValueError, match="traversal"):
            persistence.read_artifact(str(tmp_project), "../../etc/passwd")

    def test_path_traversal_dotdot_in_middle_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(ValueError, match="traversal"):
            persistence.read_artifact(str(tmp_project), "specs/../../etc/passwd")

    def test_response_is_str(self, persistence: ArtifactPersistence, tmp_project: Path):
        result = persistence.read_artifact(str(tmp_project), "prd/notes.txt")
        assert isinstance(result, str)

    def test_empty_rel_path_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(ValueError):
            persistence.read_artifact(str(tmp_project), "")

    def test_whitespace_rel_path_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(ValueError):
            persistence.read_artifact(str(tmp_project), "   ")

    def test_read_unapproved_extension_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(ValueError, match="File type not allowed"):
            persistence.read_artifact(str(tmp_project), "script.py")

    def test_read_unapproved_json_raises(self, persistence: ArtifactPersistence, tmp_project: Path):
        with pytest.raises(ValueError, match="File type not allowed"):
            persistence.read_artifact(str(tmp_project), "data.json")

    def test_read_binary_file_raises_encoding_error(self, persistence: ArtifactPersistence, tmp_path: Path):
        """Binary files with approved extensions should raise ValueError with encoding error."""
        dingllm = tmp_path / ".dingllm"
        dingllm.mkdir()
        (dingllm / "binary.md").write_bytes(b'\xff\xfe\x00\x01')
        with pytest.raises(ValueError, match="encoding error"):
            persistence.read_artifact(str(tmp_path), "binary.md")

    def test_symlink_excluded_from_listing(self, persistence: ArtifactPersistence, tmp_path: Path):
        """Symlinks inside .dingllm/ should be skipped during listing."""
        dingllm = tmp_path / ".dingllm"
        dingllm.mkdir()
        real_file = tmp_path / "outside.md"
        real_file.write_text("secret")
        symlink = dingllm / "link.md"
        symlink.symlink_to(real_file)
        # Also add a normal file so we know listing works
        (dingllm / "normal.md").write_text("normal content")

        entries = persistence.list_artifacts(str(tmp_path))
        names = {e.name for e in entries}
        assert "link.md" not in names
        assert "normal.md" in names

    def test_read_symlink_raises(self, persistence: ArtifactPersistence, tmp_path: Path):
        """Reading a symlink inside .dingllm/ should raise ValueError."""
        dingllm = tmp_path / ".dingllm"
        dingllm.mkdir()
        real_file = dingllm / "real.md"
        real_file.write_text("real content")
        symlink = dingllm / "link.md"
        symlink.symlink_to(real_file)
        with pytest.raises(ValueError, match="Symlinks not allowed"):
            persistence.read_artifact(str(tmp_path), "link.md")


class TestArtifactPersistenceSave:
    """Tests for ArtifactPersistence.save_artifact."""

    def test_save_creates_file(self, persistence: ArtifactPersistence, tmp_path: Path):
        (tmp_path / ".dingllm").mkdir()
        result = persistence.save_artifact(str(tmp_path), "new_file.md", "# New")
        assert Path(result).exists()
        assert Path(result).read_text() == "# New"

    def test_save_creates_nested_dirs(self, persistence: ArtifactPersistence, tmp_path: Path):
        (tmp_path / ".dingllm").mkdir()
        persistence.save_artifact(str(tmp_path), "deep/nested/file.mmd", "graph TD")
        assert (tmp_path / ".dingllm" / "deep" / "nested" / "file.mmd").exists()

    def test_save_traversal_raises(self, persistence: ArtifactPersistence, tmp_path: Path):
        (tmp_path / ".dingllm").mkdir()
        with pytest.raises(ValueError, match="traversal"):
            persistence.save_artifact(str(tmp_path), "../../evil.md", "pwned")

    def test_save_empty_rel_path_raises(self, persistence: ArtifactPersistence, tmp_path: Path):
        (tmp_path / ".dingllm").mkdir()
        with pytest.raises(ValueError):
            persistence.save_artifact(str(tmp_path), "", "content")

    def test_save_unapproved_extension_raises(self, persistence: ArtifactPersistence, tmp_path: Path):
        (tmp_path / ".dingllm").mkdir()
        with pytest.raises(ValueError, match="File type not allowed"):
            persistence.save_artifact(str(tmp_path), "evil.py", "import os")


# ===========================================================================
# ArtifactAPI tests
# ===========================================================================


class TestArtifactAPI:
    """Tests for the ArtifactAPI business logic layer."""

    def test_list_delegates_to_persistence(self, api: ArtifactAPI, tmp_project: Path):
        entries = api.list_artifacts(str(tmp_project))
        assert len(entries) == 4  # mission.md, 001_arch.mmd, 002_detail.mmd, notes.txt

    def test_read_delegates_to_persistence(self, api: ArtifactAPI, tmp_project: Path):
        content = api.read_artifact(str(tmp_project), "constitution/mission.md")
        assert "# Mission" in content

    def test_list_missing_dingllm(self, api: ArtifactAPI, tmp_no_dingllm: Path):
        assert api.list_artifacts(str(tmp_no_dingllm)) == []

    def test_read_traversal_raises(self, api: ArtifactAPI, tmp_project: Path):
        with pytest.raises(ValueError):
            api.read_artifact(str(tmp_project), "../../etc/passwd")


# ===========================================================================
# HTTP endpoint tests (FastAPI TestClient)
# ===========================================================================


class TestHTTPListArtifacts:
    """Tests for GET /artifacts."""

    def test_list_returns_json_array(self, client: TestClient, tmp_project: Path):
        resp = client.get("/artifacts", params={"project_path": str(tmp_project)})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 4

    def test_list_entry_structure(self, client: TestClient, tmp_project: Path):
        resp = client.get("/artifacts", params={"project_path": str(tmp_project)})
        data = resp.json()
        for entry in data:
            assert "name" in entry
            assert "path" in entry
            assert "type" in entry
            assert isinstance(entry["name"], str) and entry["name"]
            assert isinstance(entry["path"], str) and entry["path"]
            assert isinstance(entry["type"], str) and entry["type"]

    def test_list_only_approved_types(self, client: TestClient, tmp_project: Path):
        resp = client.get("/artifacts", params={"project_path": str(tmp_project)})
        data = resp.json()
        for entry in data:
            assert entry["type"] in ("md", "mmd", "txt")

    def test_list_excludes_unapproved(self, client: TestClient, tmp_project: Path):
        resp = client.get("/artifacts", params={"project_path": str(tmp_project)})
        data = resp.json()
        names = {e["name"] for e in data}
        assert "image.png" not in names
        assert "data.json" not in names
        assert "script.py" not in names

    def test_list_missing_dingllm_returns_empty(self, client: TestClient, tmp_no_dingllm: Path):
        resp = client.get("/artifacts", params={"project_path": str(tmp_no_dingllm)})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_empty_dingllm_returns_empty(self, client: TestClient, tmp_empty_dingllm: Path):
        resp = client.get("/artifacts", params={"project_path": str(tmp_empty_dingllm)})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_nonexistent_project_path_returns_error(self, client: TestClient):
        resp = client.get("/artifacts", params={"project_path": "/nonexistent/path"})
        assert resp.status_code == 400

    def test_list_missing_project_path_param(self, client: TestClient):
        resp = client.get("/artifacts")
        assert resp.status_code == 422  # FastAPI validation error


class TestHTTPReadArtifact:
    """Tests for GET /artifacts/{path}."""

    def test_read_returns_content(self, client: TestClient, tmp_project: Path):
        resp = client.get(
            "/artifacts/constitution/mission.md",
            params={"project_path": str(tmp_project)},
        )
        assert resp.status_code == 200
        assert "# Mission" in resp.text

    def test_read_nested_file(self, client: TestClient, tmp_project: Path):
        resp = client.get(
            "/artifacts/specs/v3/002_detail.mmd",
            params={"project_path": str(tmp_project)},
        )
        assert resp.status_code == 200
        assert "sequenceDiagram" in resp.text

    def test_read_response_is_plain_text(self, client: TestClient, tmp_project: Path):
        resp = client.get(
            "/artifacts/prd/notes.txt",
            params={"project_path": str(tmp_project)},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")

    def test_read_nonexistent_returns_404(self, client: TestClient, tmp_project: Path):
        resp = client.get(
            "/artifacts/nonexistent/file.md",
            params={"project_path": str(tmp_project)},
        )
        assert resp.status_code == 404

    def test_read_path_traversal_returns_error(self, client: TestClient, tmp_project: Path):
        # Starlette normalizes ../../ in URL paths, so the request may resolve
        # to a nonexistent file (404) instead of hitting our validation (400).
        # The critical security property is that traversal never succeeds (200).
        resp = client.get(
            "/artifacts/../../etc/passwd",
            params={"project_path": str(tmp_project)},
        )
        assert resp.status_code in (400, 404)
        assert resp.status_code != 200

    def test_read_path_traversal_dotdot_returns_error(self, client: TestClient, tmp_project: Path):
        # Use a traversal that starts within a valid subdir to avoid URL normalization
        resp = client.get(
            "/artifacts/specs/../../etc/passwd",
            params={"project_path": str(tmp_project)},
        )
        assert resp.status_code in (400, 404)
        assert resp.status_code != 200

    def test_read_directory_returns_error(self, client: TestClient, tmp_project: Path):
        resp = client.get(
            "/artifacts/specs",
            params={"project_path": str(tmp_project)},
        )
        assert resp.status_code == 400

    def test_read_missing_project_path_param(self, client: TestClient):
        resp = client.get("/artifacts/some/file.md")
        assert resp.status_code == 422
