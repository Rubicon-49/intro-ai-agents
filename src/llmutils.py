import toml
import re
import os
from pathlib import Path
from litellm import completion
from dotenv import load_dotenv
from typing import cast, TypedDict, List

# ------------------------------------------------------------------
# Load the .env file
# ------------------------------------------------------------------

load_dotenv()
# Get API key from environment variable
# (make sure the key is present in .env file in the project directory)
api_key = os.environ.get("OPENAI_API_KEY")

# ------------------------------------------------------------------
# Load config.toml dynamically
# ------------------------------------------------------------------

CFG_PATH = Path(__file__).parent.parent / "config.toml"
CFG = toml.load(CFG_PATH)
MODEL = CFG["general"].get("model", "gpt-3.5-turbo")
TEMPERATURE = CFG["general"].get("temperature", 0)


# ------------------------------------------------------------------
# LLM interaction function
# ------------------------------------------------------------------
# Define structural types for strong static checking
class Message(TypedDict):
    role: str
    content: str


class Choice(TypedDict):
    message: Message


class CompletionResponse(TypedDict):
    choices: List[Choice]


def generate_response(
    message: list[dict[str, str]], model: str = MODEL, temperature: float = TEMPERATURE
) -> str:
    """
    Calls LiteLLM to generate a response using the configured model and temperature.
    The 'messages' parameter should be a list of dicts with roles and content,
    compatible with the OpenAI / ChatCompletion message schema.
    """
    try:
        response = cast(
            CompletionResponse,
            completion(
                model=model,
                messages=message,
                temperature=temperature,
                max_tokens=CFG["general"].get("max_tokens", 1024),
            ),
        )
        content = response["choices"][0]["message"]["content"]
        return content.strip()
    except Exception as e:
        print(f"Error during LLM call: {e}")
        raise


# ----------------------------------
# Utility: Extract code blocks
# ----------------------------------


def extract_code_block(response_text: str) -> str:
    """
    Extract Python code from a Markdown-style response.
    If no code block is found, return the raw response test.
    """
    match = re.search(r"```python(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        # Also handle generic ``` blocks without language tags
        match = re.search(r"```(.*?)```", response_text, re.DOTALL)
        return match.group(1).strip() if match else response_text.strip()
