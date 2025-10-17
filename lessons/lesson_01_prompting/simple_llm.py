"""
json_prompt_finance.py

An example demonstrating how to call an LLM using litellm
and send structured data (JSON) as part of the message.

This illustrates how to provide the model with a data object—
for instance, a financial portfolio—to analyze or reason about.
"""

import os
import json
from dotenv import load_dotenv
from litellm import completion
from typing import List, Dict, TypedDict, cast

# 1. Define structural types for strong static checking
class Message(TypedDict):
    role: str
    content: str

class Choice(TypedDict):
    message: Message
    
class CompletionResponse(TypedDict):
    choices: List[Choice]

# 1. Load environment variables
# Ensure your .env file includes: OPENAI_API_KEY=sk-...
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables.")

# 2. Define a helper function to query the model
def generate_response(messages: List[Dict[str, str]]) -> str:
    """
    Calls the LLM with the provided message sequence and returns its response text.
    """
    response: CompletionResponse = cast(
        CompletionResponse,
        completion(
            model="openai/gpt-4o",
            messages=messages,
            max_tokens=1024,
            stream=False,
        ),
    )
    try:
        content = getattr(response["choices"][0]["message"], "content", None)
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Unexpected response format from LLM")
    
    if not isinstance(content, str):
        raise RuntimeError("Expected a string content from model response.")
    
    return content


# 3. Define structured data to include in the prompt
portfolio_summary = {
    "portfolio_id": "123-XYZ",
    "description": "Client investment portfolio summary",
    "holdings": [
        {"symbol": "AAPL", "shares": 25, "price": 180.25},
        {"symbol": "TSLA", "shares": 10, "price": 240.10},
        {"symbol": "MSFT", "shares": 15, "price": 330.45},
    ],
    "goal": "Provide a concise risk assessment and suggest diversification improvements."
}


# 4. Construct messages using system and user roles
messages = [
    {
        "role": "system",
        "content": (
            "You are a quantitative financial analyst with expertise in risk management "
            "and portfolio optimization. You always justify your recommendations clearly."
        ),
    },
    {
        "role": "user",
        "content": f"Analyze the following portfolio: {json.dumps(portfolio_summary)}",
    },
]


# 5. Query the model and print the response
if __name__ == "__main__":
    response = generate_response(messages)
    print("\n--- Model Response ---\n")
    print(response)
