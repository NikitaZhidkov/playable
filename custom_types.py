from typing import TypedDict, Required, NotRequired
from dataclasses import dataclass

class Tool(TypedDict, total=False):
    name: Required[str]
    description: str
    input_schema: Required[dict[str, object]]

@dataclass
class ToolResult:
    content: str
    tool_use_id: str | None = None
    name: str | None = None
    is_error: bool | None = None

@dataclass
class ToolUse:
    name: str
    input: object
    id: str

@dataclass
class ToolUseResult:
    tool_use: ToolUse
    tool_result: ToolResult

    @classmethod
    def from_tool_use(
        cls, tool_use: ToolUse, content: str, is_error: bool | None = None
    ) -> "ToolUseResult":
        return cls(tool_use, ToolResult(content, tool_use.id, tool_use.name, is_error))

@dataclass
class TextRaw:
    text: str