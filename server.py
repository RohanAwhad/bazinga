"""Bazinga Local Server — FastAPI application.

Exposes the Artifact API over HTTP. Designed to be extended with the
Chat API (PRD 002) on the same server instance.

Run:
    uv run uvicorn server:app --reload --port 8080
"""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from artifact_api import ArtifactAPI

app = FastAPI(title="Bazinga Local Server")

_artifact_api = ArtifactAPI()


@app.get("/artifacts")
def list_artifacts(project_path: str = Query(..., description="Absolute path to the project root")):
    """List all approved artifacts under .dingllm/ in the given project.

    Returns a JSON array of ArtifactEntry objects.
    """
    try:
        entries = _artifact_api.list_artifacts(project_path)
    except FileNotFoundError as exc:
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
    try:
        content = _artifact_api.read_artifact(project_path, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IsADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return PlainTextResponse(content)
