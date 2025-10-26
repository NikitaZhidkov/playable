"""
VLM Client for interacting with Gemini Vision Language Model.
"""
import os
import io
import logging
from PIL import Image
from jinja2 import Template
import google.generativeai as genai
from dotenv import load_dotenv
from langfuse.decorators import observe, langfuse_context

load_dotenv()

logger = logging.getLogger(__name__)


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
    
    @observe(as_type="generation")
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
        # Render the prompt template with Jinja2
        template = Template(template_str)
        rendered_prompt = template.render(
            user_prompt=user_prompt,
            console_logs=console_logs
        )
        
        logger.info(f"Validating with VLM using model: {self.model_name}")
        logger.debug(f"Rendered prompt: {rendered_prompt[:200]}...")
        
        # Update Langfuse context with model and input
        langfuse_context.update_current_observation(
            model=self.model_name,
            input=rendered_prompt,
            metadata={
                "has_image": True,
                "console_logs_length": len(console_logs) if console_logs else 0,
                "user_prompt_length": len(user_prompt) if user_prompt else 0
            }
        )
        
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        # Generate content with image and prompt
        response = self.model.generate_content([rendered_prompt, image])
        
        # Track token usage with Langfuse
        # Following Langfuse best practices: explicitly ingest token counts
        # Do NOT calculate costs - let Langfuse handle that if configured
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage_metadata = response.usage_metadata
            
            # Prepare usage data for Langfuse (token counts only)
            usage_data = {
                "input": usage_metadata.prompt_token_count,
                "output": usage_metadata.candidates_token_count,
                "total": usage_metadata.total_token_count,
                "unit": "TOKENS"
            }
            
            # Include cache information if available (for Gemini context caching)
            # Langfuse can use this for accurate cost calculation if model pricing is configured
            if hasattr(usage_metadata, 'cached_content_token_count') and usage_metadata.cached_content_token_count:
                usage_data["cached_content_token_count"] = usage_metadata.cached_content_token_count
            
            # Log token usage
            cache_info = ""
            if hasattr(usage_metadata, 'cached_content_token_count') and usage_metadata.cached_content_token_count:
                cache_info = f" (cached: {usage_metadata.cached_content_token_count})"
            
            logger.info(
                f"Token usage - Input: {usage_metadata.prompt_token_count}{cache_info}, "
                f"Output: {usage_metadata.candidates_token_count}, "
                f"Total: {usage_metadata.total_token_count}"
            )
            
            langfuse_context.update_current_observation(
                output=response.text,
                usage=usage_data,
                metadata={
                    "provider": "google",
                    "includes_image": True
                }
            )
        else:
            langfuse_context.update_current_observation(output=response.text)
        
        logger.info("VLM validation response received")
        logger.debug(f"VLM response: {response.text[:200]}...")
        
        return response.text

