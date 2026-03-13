"""
gemini_client.py — Google Gemini Vision API integration.
Sends screenshot to Gemini and returns the solution text.
Includes automatic retry with backoff on 429 rate-limit errors.
"""

import re
import time
from google import genai
from google.genai import types
from PIL import Image

PROMPT = """You are an expert programming assistant evaluating a screenshot for a competitive programming platform.

CRITICAL INSTRUCTIONS - YOU MUST OBEY THESE OR THE SYSTEM WILL FAIL:
1. Output ONLY the raw, executable code. ABSOLUTELY NO EXPLANATIONS, NO PROBLEM SUMMARY, NO INTRODUCTORY TEXT (e.g., "Here is the code"), and NO CONCLUDING TEXT.
2. DO NOT use markdown code blocks (e.g., do not use ```c or ```python). Just output the plain text code.
3. DO NOT output ANY code comments (no //, /* */, or #) anywhere in your response.
4. Identify the active programming language from the screenshot and write the solution in THAT language exactly. If no language is specified, default to ANSI C.
5. ALL code must be written WITHOUT ANY INDENTATION AT ALL. Every single line of code must start exactly at column 0. Do not use any spaces or tabs for indentation.
6. If the problem asks you to "fill the function", provide ONLY that requested function.

YOUR OUTPUT MUST BE 100% EXECUTABLE CODE WITH ZERO EXTRA CHARACTERS AND ZERO COMMENTS."""

ERROR_PROMPT = """You are an expert programming assistant evaluating a screenshot of a failed test case or compilation error for a competitive programming platform.
You are also provided with the PREVIOUS CODE that was executed.

CRITICAL INSTRUCTIONS - YOU MUST OBEY THESE OR THE SYSTEM WILL FAIL:
1. Output ONLY the raw, executable FIXED code. ABSOLUTELY NO EXPLANATIONS, NO PROBLEM SUMMARY, NO INTRODUCTORY TEXT (e.g., "Here is the code"), and NO CONCLUDING TEXT.
2. DO NOT use markdown code blocks (e.g., do not use ```c or ```python). Just output the plain text code.
3. DO NOT output ANY code comments (no //, /* */, or #) anywhere in your response.
4. You MUST retain the exact same programming language as the PREVIOUS CODE provided. Even if the screenshot implies something else or looks like Python, if previous code is C, output C.
5. Pay EXTREMELY close attention to the Expected Output vs Your Program Output strings. If cases differ (like 'Iannehc' vs 'iannehC'), adjust your logic to match the Expected Output exactly.
6. ALL code must be written WITHOUT ANY INDENTATION AT ALL. Every single line of code must start exactly at column 0. Do not use any spaces or tabs for indentation.
7. If the problem asks you to "fill the function", provide ONLY that requested function.

YOUR OUTPUT MUST BE 100% EXECUTABLE CODE WITH ZERO EXTRA CHARACTERS AND ZERO COMMENTS."""

def _handle_api_error(e: Exception):
    """Specific handling for known API errors."""
    error_str = str(e)
    if "429" in error_str:
        if "GenerateRequestsPerDayPerProjectPerModel" in error_str and "limit: 0" in error_str:
            raise RuntimeError(
                "Daily quota exhausted for this API key.\n\n"
                "Please:\n"
                "1. Get a new API key from a DIFFERENT Google account.\n"
                "2. Paste it into config.json under \"api_key\""
            ) from e
        raise RuntimeError("Rate limit hit. Please wait a minute and try again.") from e
    raise e

def get_solution(
    api_key: str,
    model_name: str,
    image: Image.Image,
    progress_callback=None
) -> str:
    """
    Sends a PIL image to Gemini Vision and returns the text response.
    Uses the modern google-genai SDK.
    """
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=3)
    ))
    
    try:
        if progress_callback:
            progress_callback(f"Querying Gemini ({model_name})...")

        response = client.models.generate_content(
            model=model_name,
            contents=[PROMPT, image],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8192,
            )
        )
        
        if not response.text:
            # Handle cases where response might be blocked or empty
            if response.candidates and response.candidates[0].finish_reason:
                reason = response.candidates[0].finish_reason
                raise RuntimeError(f"Gemini returned no text. Finish reason: {reason}")
            raise RuntimeError("Gemini returned an empty response.")
            
        return response.text

    except Exception as e:
        _handle_api_error(e)

def get_fixed_solution(
    api_key: str,
    model_name: str,
    image: Image.Image,
    previous_code: str,
    progress_callback=None
) -> str:
    """
    Sends a PIL image with previous code to Gemini Vision and returns the fixed text response.
    """
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=3)
    ))

    try:
        if progress_callback:
            progress_callback(f"Querying Gemini for Fix ({model_name})...")
        
        prompt_content = f"{ERROR_PROMPT}\n\nPREVIOUS CODE:\n{previous_code}"

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt_content, image],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8192,
            )
        )
        
        if not response.text:
            if response.candidates and response.candidates[0].finish_reason:
                reason = response.candidates[0].finish_reason
                raise RuntimeError(f"Gemini returned no text. Finish reason: {reason}")
            raise RuntimeError("Gemini returned an empty response.")

        return response.text

    except Exception as e:
        _handle_api_error(e)

