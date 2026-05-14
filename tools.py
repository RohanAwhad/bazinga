"""Tool implementations for the Gemini CLI agent."""

from pathlib import Path


def list_files(path: str) -> str:
    p = Path(path).expanduser()
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


def read_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Error: {p} does not exist"
    if not p.is_file():
        return f"Error: {p} is not a file"
    return p.read_text()


def search_replace(path: str, old_string: str, new_string: str, create_if_missing: bool = False) -> str:
    """Search and replace exact string in a file.

    Operations:
    - Create new file:  set create_if_missing=True, old_string="", new_string=<full content>
    - Edit file:        old_string=<exact text to find>, new_string=<replacement>
    - Delete content:   old_string=<text to remove>, new_string=""
    """
    p = Path(path).expanduser()
    if not p.exists():
        if create_if_missing and old_string == "":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new_string)
            return f"Created {p} ({len(new_string)} bytes)"
        return f"Error: {p} does not exist"
    if not p.is_file():
        return f"Error: {p} is not a file"
    content = p.read_text()
    count = content.count(old_string)
    if count == 0:
        return f"Error: old_string not found in {p}"
    if count > 1:
        return f"Error: old_string found {count} times in {p} — provide more context to disambiguate"
    content = content.replace(old_string, new_string, 1)
    p.write_text(content)
    return f"Replaced 1 occurrence in {p}"


TOOL_FUNCTIONS: dict[str, callable] = {
    "list_files": list_files,
    "read_file": read_file,
    "search_replace": search_replace,
}
