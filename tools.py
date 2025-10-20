from custom_types import Tool, ToolUse, ToolUseResult, TextRaw
from workspace import Workspace
import logging

logger = logging.getLogger(__name__)

class FileOperations():
    """Class that perform file operations with common tools."""

    def __init__(
        self,
        workspace: Workspace,
    ):
        self.workspace = workspace
        logger.info(
            f"Initialized {self.__class__.__name__}"
        )

    @property
    def base_tools(self) -> list[Tool]:
        """Common file operation tools."""
        return [
            {
                "name": "read_file",
                "description": "Read file content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "edit_file",
                "description": "Edit a file by searching and replacing text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "search": {"type": "string"},
                        "replace": {"type": "string"},
                        "replace_all": {"type": "boolean", "default": False},
                    },
                    "required": ["path", "search", "replace"],
                },
            },
            {
                "name": "delete_file",
                "description": "Delete a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "complete",
                "description": "Mark the task as complete. This will run tests and type checks to ensure the changes are correct.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    @property
    def tools(self) -> list[Tool]:
        """All tools available to this actor."""
        return self.base_tools 

    def _short_dict_repr(self, d: dict) -> str:
        """Helper function to create short dictionary representations for logging."""
        return ", ".join(
            f"{k}: {v if len(v) < 100 else v[:50] + '...'}"
            for k, v in d.items()
            if isinstance(v, str)
        )


    def _unpack_exception_group(self, exc: BaseException) -> list[BaseException]:
        """Recursively unpack ExceptionGroup to get all individual exceptions."""
        if isinstance(exc, BaseExceptionGroup):
            exceptions = []
            for e in exc.exceptions:
                exceptions.extend(self._unpack_exception_group(e))
            return exceptions
        else:
            # base case: regular exception
            return [exc]

    async def run_tools(
        self, content
    ) -> tuple[list[ToolUseResult], bool]:
        """Execute tools for a given node."""
        logger.info(f"Running tools")
        result, is_completed = [], False

        for block in content:
            if not isinstance(block, ToolUse):
                match block:
                    case TextRaw(text=text):
                        logger.info(f"LLM output: {text}")
                    case _:
                        pass
                continue

            try:
                logger.info(
                    f"Running tool {block.name} with input {self._short_dict_repr(block.input) if isinstance(block.input, dict) else str(block.input)}"
                )

                match block.name:
                    case "read_file":
                        tool_content = await self.workspace.read_file(
                            block.input["path"]  # pyright: ignore[reportIndexIssue]
                        )
                        result.append(ToolUseResult.from_tool_use(block, tool_content))

                    case "write_file":
                        path = block.input["path"]  # pyright: ignore[reportIndexIssue]
                        content = block.input["content"]  # pyright: ignore[reportIndexIssue]
                        try:
                            logger.info(f"Writing file: {path} (content length: {len(content)})")
                            self.workspace = self.workspace.write_file(path, content)
                            result.append(ToolUseResult.from_tool_use(block, "success"))
                            logger.info(f"✅ Successfully written file: {path}")
                        except FileNotFoundError as e:
                            error_msg = (
                                f"Directory not found for file '{path}': {str(e)}"
                            )
                            logger.info(
                                f"File not found error writing file {path}: {str(e)}"
                            )
                            result.append(
                                ToolUseResult.from_tool_use(
                                    block, error_msg, is_error=True
                                )
                            )
                        except PermissionError as e:
                            error_msg = f"Permission denied writing file '{path}': {str(e)}. Probably this file is out of scope for this particular task."
                            logger.info(
                                f"Permission error writing file {path}: {str(e)}"
                            )
                            result.append(
                                ToolUseResult.from_tool_use(
                                    block, error_msg, is_error=True
                                )
                            )
                        except ValueError as e:
                            error_msg = str(e)
                            logger.info(f"Value error writing file {path}: {error_msg}")
                            result.append(
                                ToolUseResult.from_tool_use(
                                    block, error_msg, is_error=True
                                )
                            )

                    case "edit_file":
                        path = block.input["path"]  # pyright: ignore[reportIndexIssue]
                        search = block.input["search"]  # pyright: ignore[reportIndexIssue]
                        replace = block.input["replace"]  # pyright: ignore[reportIndexIssue]
                        replace_all = block.input.get("replace_all", False)  # pyright: ignore[reportAttributeAccessIssue]

                        try:
                            original = await self.workspace.read_file(path)
                            search_count = original.count(search)
                            match search_count:
                                case 0:
                                    raise ValueError(
                                        f"Search text not found in file '{path}'. Search:\n{search}"
                                    )
                                case 1:
                                    new_content = original.replace(search, replace)
                                    self.workspace = self.workspace.write_file(path, new_content)
                                    result.append(
                                        ToolUseResult.from_tool_use(block, "success")
                                    )
                                    logger.debug(f"Applied edit to file: {path}")
                                case num_hits:
                                    if replace_all:
                                        new_content = original.replace(search, replace)
                                        self.workspace = self.workspace.write_file(
                                            path, new_content
                                        )
                                        result.append(
                                            ToolUseResult.from_tool_use(
                                                block,
                                                f"success - replaced {num_hits} occurrences",
                                            )
                                        )
                                        logger.debug(
                                            f"Applied bulk edit to file: {path} ({num_hits} occurrences)"
                                        )
                                    else:
                                        raise ValueError(
                                            f"Search text found {num_hits} times in file '{path}' (expected exactly 1). Use replace_all=true to replace all occurrences. Search:\n{search}"
                                        )
                        except FileNotFoundError as e:
                            error_msg = f"File '{path}' not found for editing: {str(e)}"
                            logger.info(
                                f"File not found error editing file {path}: {str(e)}"
                            )
                            result.append(
                                ToolUseResult.from_tool_use(
                                    block, error_msg, is_error=True
                                )
                            )
                        except PermissionError as e:
                            error_msg = f"Permission denied editing file '{path}': {str(e)}. Probably this file is out of scope for this particular task."
                            logger.info(
                                f"Permission error editing file {path}: {str(e)}"
                            )
                            result.append(
                                ToolUseResult.from_tool_use(
                                    block, error_msg, is_error=True
                                )
                            )
                        except ValueError as e:
                            error_msg = str(e)
                            logger.info(f"Value error editing file {path}: {error_msg}")
                            result.append(
                                ToolUseResult.from_tool_use(
                                    block, error_msg, is_error=True
                                )
                            )

                    case "delete_file":
                        self.workspace = self.workspace.rm(block.input["path"])  # pyright: ignore[reportIndexIssue]
                        result.append(ToolUseResult.from_tool_use(block, "success"))

                    case "complete":
                        result.append(
                            ToolUseResult.from_tool_use(block, "success")
                        )
                        is_completed = True

                    case _:
                        raise ValueError(
                            f"Invalid input type for tool {block.name}: {type(block.input)}"
                        )

            except FileNotFoundError as e:
                logger.info(f"File not found: {e}")
                result.append(ToolUseResult.from_tool_use(block, str(e), is_error=True))
            except PermissionError as e:
                logger.info(f"Permission error: {e}")
                result.append(ToolUseResult.from_tool_use(block, str(e), is_error=True))
            except ValueError as e:
                logger.info(f"Value error: {e}")
                result.append(ToolUseResult.from_tool_use(block, str(e), is_error=True))
            except Exception as e:
                # handle ExceptionGroup by unpacking recursively
                if isinstance(e, BaseExceptionGroup):
                    all_exceptions = self._unpack_exception_group(e)
                    error_messages = []
                    for exc in all_exceptions:
                        logger.error(f"Exception in group: {type(exc).__name__}: {exc}")
                        error_messages.append(f"{type(exc).__name__}: {str(exc)}")
                    combined_error = "Multiple errors occurred:\n" + "\n".join(
                        error_messages
                    )
                    result.append(
                        ToolUseResult.from_tool_use(
                            block, combined_error, is_error=True
                        )
                    )
                else:
                    logger.error(f"Unknown error: {e}")
                    result.append(
                        ToolUseResult.from_tool_use(block, str(e), is_error=True)
                    )

        return result, is_completed


