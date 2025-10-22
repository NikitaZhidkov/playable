import os
from anthropic import Anthropic
from custom_types import Tool, ToolUse, TextRaw
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from jinja2 import Template
from PIL import Image
import io
from playbook import SYSTEM_PIXI_GAME_DEVELOPER_PROMPT

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
    
    def parse_anthropic_response(self, response) -> list[ToolUse | TextRaw]:
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
        system: str = None
    ):
        """Call Claude with messages and tools."""
        if system is None:
            raise ValueError("System prompt must be provided")
            
        anthropic_messages = self.convert_messages_for_anthropic(messages)
        anthropic_tools = self.format_tools_for_anthropic(tools)
        
        logger.info(f"Calling Claude with {len(anthropic_messages)} messages and {len(anthropic_tools)} tools")
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=anthropic_messages,
            tools=anthropic_tools
        )
        
        return response


class VLMClient:
    """Client for interacting with Gemini Vision Language Model."""
    
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use model from: parameter > LLM_VISION_MODEL env > default
        self.model_name = (os.environ.get("LLM_VISION_MODEL"))
        
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"Initialized VLMClient with model: {self.model_name}")
    
    def validate_with_screenshot(
        self, 
        screenshot_bytes: bytes, 
        console_logs: str,
        user_prompt: str,
        template_str: str
    ) -> str:
        """
        Validate a playable using screenshot and console logs.
        
        Args:
            screenshot_bytes: PNG screenshot bytes from browser
            console_logs: Formatted console logs from browser
            user_prompt: Original user prompt that generated the playable
            template_str: Jinja2 template string for the validation prompt
        
        Returns:
            Raw response text from Gemini containing <answer> and <reason> tags
        """
        try:
            # Render the prompt template with Jinja2
            template = Template(template_str)
            rendered_prompt = template.render(
                user_prompt=user_prompt,
                console_logs=console_logs
            )
            
            logger.info(f"Validating with VLM using model: {self.model_name}")
            logger.debug(f"Rendered prompt: {rendered_prompt[:200]}...")
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(screenshot_bytes))
            
            # Generate content with image and prompt
            response = self.model.generate_content([rendered_prompt, image])
            
            logger.info("VLM validation response received")
            logger.debug(f"VLM response: {response.text[:200]}...")
            
            return response.text
            
        except Exception as e:
            error_msg = f"VLM validation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Return a safe fallback response that indicates failure
            return f"<reason>VLM validation error: {str(e)}</reason><answer>no</answer>"

