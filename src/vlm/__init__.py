"""
VLM (Vision Language Model) module for game validation.

This module provides:
- VLMClient: Client for interacting with Gemini Vision API
- Validation functions for playables and test cases
- VLM prompt templates
"""

from src.vlm.client import VLMClient
from src.vlm.validation import (
    validate_playable_with_vlm,
    validate_test_case_with_vlm,
    save_test_case_error
)
from src.vlm.prompts import (
    VLM_PLAYABLE_VALIDATION_PROMPT,
    VLM_TEST_CASE_VALIDATION_PROMPT
)

__all__ = [
    'VLMClient',
    'validate_playable_with_vlm',
    'validate_test_case_with_vlm',
    'save_test_case_error',
    'VLM_PLAYABLE_VALIDATION_PROMPT',
    'VLM_TEST_CASE_VALIDATION_PROMPT',
]

