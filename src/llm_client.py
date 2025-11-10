import os
from anthropic import Anthropic
from src.custom_types import Tool, ToolUse, TextRaw, ThinkingBlock, ContentBlock
import logging
from dotenv import load_dotenv
from src.prompts import SYSTEM_PIXI_GAME_DEVELOPER_PROMPT

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Anthropic Claude."""
    
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = Anthropic(api_key=self.api_key)
        # Use model from: parameter > LLM_BEST_CODING_MODEL env > ANTHROPIC_MODEL env > default
        self.model = (
            model 
            or os.environ.get("LLM_BEST_CODING_MODEL")
        )
    
    def format_tools_for_anthropic(self, tools: list[Tool]) -> list[dict]:
        """Convert our Tool format to Anthropic's format.
        
        Note: Passing tools via API parameter (not just in prompt) enables:
        1. Structured tool calling - Claude returns tool_use blocks
        2. Tool validation - API validates tool calls match schema
        3. Better reliability - Reduces hallucinated tool calls
        4. Automatic formatting - Claude knows exact JSON structure to return
        
        Without this parameter, Claude would just generate text about using tools,
        not actual structured tool calls we can execute.
        """
        return tools  # Our format already matches Anthropic's
    
    def parse_anthropic_response(self, response) -> list[ContentBlock]:
        """Parse Anthropic response into our custom types."""
        result = []
        
        for block in response.content:
            if block.type == "text":
                result.append(TextRaw(text=block.text))
            elif block.type == "tool_use":
                result.append(ToolUse(
                    name=block.name,
                    input=block.input,
                    id=block.id
                ))
            elif block.type == "thinking":
                result.append(ThinkingBlock(thinking=block.thinking))
        
        return result
    
    def convert_messages_for_anthropic(self, messages: list) -> list[dict]:
        """Convert LangGraph messages to Anthropic format.
        
        Handles various message types from LangGraph state.
        
        Important: Groups consecutive tool messages into a single user message,
        as required by Anthropic's API.
        """
        anthropic_messages = []
        tool_results_buffer = []  # Buffer for grouping consecutive tool results
        
        for i, msg in enumerate(messages):
            # Handle different message formats
            if hasattr(msg, 'type'):
                # LangGraph message object
                if msg.type == "human":
                    # Flush any buffered tool results first
                    if tool_results_buffer:
                        anthropic_messages.append({
                            "role": "user",
                            "content": tool_results_buffer
                        })
                        tool_results_buffer = []
                    
                    anthropic_messages.append({
                        "role": "user",
                        "content": msg.content
                    })
                elif msg.type == "ai":
                    # Flush any buffered tool results first
                    if tool_results_buffer:
                        anthropic_messages.append({
                            "role": "user",
                            "content": tool_results_buffer
                        })
                        tool_results_buffer = []
                    
                    # AI message with possible tool calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        content = []
                        if msg.content:
                            content.append({"type": "text", "text": msg.content})
                        for tool_call in msg.tool_calls:
                            content.append({
                                "type": "tool_use",
                                "id": tool_call.get("id", ""),
                                "name": tool_call.get("name", ""),
                                "input": tool_call.get("args", {})
                            })
                        anthropic_messages.append({
                            "role": "assistant",
                            "content": content
                        })
                    else:
                        anthropic_messages.append({
                            "role": "assistant",
                            "content": msg.content
                        })
                elif msg.type == "tool":
                    # Buffer tool result to group with other consecutive tool results
                    tool_results_buffer.append({
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content
                    })
            elif isinstance(msg, dict):
                # Flush any buffered tool results first
                if tool_results_buffer:
                    anthropic_messages.append({
                        "role": "user",
                        "content": tool_results_buffer
                    })
                    tool_results_buffer = []
                
                # Already in dict format
                anthropic_messages.append(msg)
        
        # Flush any remaining tool results
        if tool_results_buffer:
            anthropic_messages.append({
                "role": "user",
                "content": tool_results_buffer
            })
        
        return anthropic_messages
    
    def call(
        self,
        messages: list,
        tools: list[Tool],
        max_tokens: int = 8000,
        system: str = None,
        temperature: float = 1.0
    ):
        """Call Claude with messages and tools."""
        if system is None:
            raise ValueError("System prompt must be provided")
            
        anthropic_messages = self.convert_messages_for_anthropic(messages)
        anthropic_tools = self.format_tools_for_anthropic(tools)
        
        # Add prompt caching to system prompt
        # System prompt is large and consistent, perfect for caching
        system_with_cache = None
        if system:
            system_with_cache = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        
        # Add prompt caching to tools
        # Tools don't change during conversation, cache them independently
        if len(anthropic_tools) > 0:
            anthropic_tools[-1]["cache_control"] = {"type": "ephemeral"}
        
        # Add prompt caching to conversation history
        # Cache the entire conversation including the current request
        # This allows the next request to reuse this cached context
        if len(anthropic_messages) > 0:
            # Add cache_control to the last message
            # This caches everything for the NEXT request
            msg = anthropic_messages[-1]
            
            # Convert content to list format if needed to add cache_control
            if isinstance(msg["content"], str):
                msg["content"] = [
                    {
                        "type": "text",
                        "text": msg["content"],
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            elif isinstance(msg["content"], list):
                # Add cache_control to the last content block
                msg["content"][-1]["cache_control"] = {"type": "ephemeral"}
        
        logger.info(f"Calling Claude with {len(anthropic_messages)} messages and {len(anthropic_tools)} tools")
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_with_cache,
            messages=anthropic_messages,
            tools=anthropic_tools
        )
        
        # Log token usage
        usage = response.usage
        cache_info = ""
        if hasattr(usage, 'cache_creation_input_tokens') or hasattr(usage, 'cache_read_input_tokens'):
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)
            cache_read = getattr(usage, 'cache_read_input_tokens', 0)
            if cache_creation or cache_read:
                cache_info = f" (cache_write: {cache_creation}, cache_read: {cache_read})"
        
        logger.info(
            f"Token usage - Input: {usage.input_tokens}{cache_info}, "
            f"Output: {usage.output_tokens}, Total: {usage.input_tokens + usage.output_tokens}"
        )
        
        return response


