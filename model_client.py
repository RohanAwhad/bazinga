"""ModelClient — wraps the LLM provider call."""

from google import genai
from google.genai.types import (
    Content,
    FunctionDeclaration,
    GenerateContentConfig,
    GenerateContentResponse,
    Tool,
)


class ModelClient:
    """Wraps Gemini model configuration and content generation."""

    def __init__(self) -> None:
        self._client = genai.Client(
            vertexai=True,
            project="redhat-ai-analysis",
            location="global",
        )
        self._MODEL = "gemini-3.1-pro-preview"
        self._TOOLS = [
            Tool(
                function_declarations=[
                    FunctionDeclaration(
                        name="list_files",
                        description="List files and directories at the given path",
                        parameters={
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Directory path to list",
                                }
                            },
                            "required": ["path"],
                        },
                    ),
                    FunctionDeclaration(
                        name="read_file",
                        description="Read the text contents of a file",
                        parameters={
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "File path to read",
                                }
                            },
                            "required": ["path"],
                        },
                    ),
                    FunctionDeclaration(
                        name="search_replace",
                        description=(
                            "Search and replace an exact string in a file. "
                            "old_string must match file content exactly (including whitespace). "
                            "Fails if old_string matches 0 or >1 times — provide more surrounding context to disambiguate. "
                            "To CREATE a new file: set create_if_missing=true, old_string='', new_string=<full file content>. "
                            "To DELETE content: set old_string=<text to remove>, new_string=''. "
                            "To EDIT: set old_string=<exact text to find>, new_string=<replacement text>. "
                            "Always read_file first before editing to see current content."
                        ),
                        parameters={
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "File path to edit or create",
                                },
                                "old_string": {
                                    "type": "string",
                                    "description": "Exact string to find in the file (empty string for new file creation)",
                                },
                                "new_string": {
                                    "type": "string",
                                    "description": "Replacement string (empty string to delete content)",
                                },
                                "create_if_missing": {
                                    "type": "boolean",
                                    "description": "If true and file does not exist, create it with new_string as content. Parent dirs are created automatically.",
                                },
                            },
                            "required": ["path", "old_string", "new_string"],
                        },
                    ),
                ]
            )
        ]
        self._CONFIG = GenerateContentConfig(tools=self._TOOLS)

    @property
    def config(self) -> GenerateContentConfig:
        """The default model configuration (without system instruction)."""
        return self._CONFIG

    def _build_config(self, project_path: str) -> GenerateContentConfig:
        """Build a config with system instruction scoped to project_path."""
        system_instruction = (
            f"You are Bazinga, a coding assistant. "
            f"You are working on the project at: {project_path}\n"
            f"All file paths in tool calls are relative to the project root. "
            f"Use list_files to explore the project structure, read_file to read files, "
            f"and search_replace to create or edit files. "
            f"Always read a file before editing it."
        )
        return GenerateContentConfig(
            tools=self._TOOLS,
            system_instruction=system_instruction,
        )

    def generate_content(
        self, contents: list[Content], config: GenerateContentConfig, project_path: str,
    ) -> GenerateContentResponse:
        """Generate content from the model.

        Args:
            contents: Conversation history as list of Content objects.
            config: Model configuration including tools.
            project_path: The project path for scoping (injected into system instruction).

        Returns:
            Response from the model.
        """
        scoped_config = self._build_config(project_path)
        return self._client.models.generate_content(
            model=self._MODEL,
            contents=contents,
            config=scoped_config,
        )
