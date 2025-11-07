from typing import TypedDict, Required, NotRequired
from dataclasses import dataclass
from typing import TypeAlias, Union, Iterable, Literal, Self

class Tool(TypedDict, total=False):
    name: Required[str]
    description: str
    input_schema: Required[dict[str, object]]
    cache_control: NotRequired[dict[str, str]]

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

@dataclass
class ThinkingBlock:
    thinking: str

ContentBlock: TypeAlias = Union[
    TextRaw, ToolUse, ToolUseResult, ThinkingBlock, ToolResult
]


def dump_content(content: Iterable[ContentBlock]) -> list[dict]:
    result = []
    for block in content:
        match block:
            case TextRaw(text):
                result.append({"type": "text", "text": text})
            case ToolUse(name, input, id):
                result.append(
                    {"type": "tool_use", "name": name, "input": input, "id": id}
                )
            case ThinkingBlock(thinking):
                result.append({"type": "thinking", "thinking": thinking})
            case ToolUseResult(tool_use, tool_result):
                result.append(
                    {
                        "type": "tool_use_result",
                        "tool_use": {
                            "name": tool_use.name,
                            "input": tool_use.input,
                            "id": tool_use.id,
                        },
                        "tool_result": {
                            "content": tool_result.content,
                            "tool_use_id": tool_result.tool_use_id,
                            "name": tool_result.name,
                            "is_error": tool_result.is_error,
                        },
                    }
                )
            case ToolResult(content, tool_use_id, name, is_error):
                result.append({
                    "type": "tool_result",
                    "content": content,
                    "tool_use_id": tool_use_id,
                    "name": name,
                    "is_error": is_error,
                })
    return result


def load_content(data: list[dict]) -> list[ContentBlock]:
    content = []
    for block in data:
        match block:
            case {"type": "text", "text": text}:
                content.append(TextRaw(text))
            case {"type": "tool_use", "name": name, "input": input, "id": id}:
                content.append(ToolUse(name, input, id))
            case {"type": "thinking", "thinking": thinking}:
                content.append(ThinkingBlock(thinking))
            case {
                "type": "tool_use_result",
                "tool_use": tool_use,
                "tool_result": tool_result,
            }:
                content.append(
                    ToolUseResult(
                        ToolUse(tool_use["name"], tool_use["input"], tool_use["id"]),
                        ToolResult(
                            tool_result["content"],
                            tool_result.get("tool_use_id"),
                            tool_result.get("name"),
                            tool_result.get("is_error"),
                        ),
                    )
                )
            case {"type": "tool_result", "content": content_str, **rest}:
                content.append(ToolResult(
                    content_str,
                    rest.get("tool_use_id"),
                    rest.get("name"),
                    rest.get("is_error"),
                ))
            case _:
                raise ValueError(f"Unknown block type in content: {block}")
    return content

@dataclass
class InternalMessage:
    role: Literal["user", "assistant"]
    content: Iterable[ContentBlock]

    def to_dict(self) -> dict:
        return {"role": self.role, "content": dump_content(self.content)}

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(data["role"], load_content(data["content"]))
