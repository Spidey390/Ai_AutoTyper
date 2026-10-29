import re

def patch_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    old_func = """def _handle_api_error(e: Exception):
    \"\"\"Specific handling for known API errors.\"\"\"
    error_str = str(e)
    if "429" in error_str:
        if "GenerateRequestsPerDayPerProjectPerModel" in error_str and "limit: 0" in error_str:
            raise RuntimeError(
                "Daily quota exhausted for this API key.\\n\\n"
                "Please:\\n"
                "1. Get a new API key from a DIFFERENT Google account.\\n"
                "2. Paste it into config.json under \\"api_key\\""
            ) from e
        raise RuntimeError("Rate limit hit. Please wait a minute and try again.") from e
    raise e"""

    new_func = """def _handle_api_error(e: Exception):
    \"\"\"Specific handling for known API errors.\"\"\"
    error_str = str(e)
    if "429" in error_str:
        if "GenerateRequestsPerDayPerProjectPerModel" in error_str and "limit: 0" in error_str:
            raise RuntimeError("Daily quota exhausted for this API key. Please use a different account.") from e
        raise RuntimeError("Rate limit hit. Please wait a minute and try again.") from e
    elif "UNAUTHENTICATED" in error_str or "API_KEY_INVALID" in error_str:
        raise RuntimeError("Invalid API Key! Please check your settings.") from e
    
    if len(error_str) > 100:
        raise RuntimeError(f"API Error: {error_str[:97]}...") from e
    raise e"""

    content = content.replace(old_func, new_func)

    with open(filepath, "w") as f:
        f.write(content)

patch_file("gemini_client.py")
patch_file("Ai_AutoTyper_Windows/gemini_client.py")
