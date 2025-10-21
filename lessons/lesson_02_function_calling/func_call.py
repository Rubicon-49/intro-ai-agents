import json
import os
import sys
import logging
import tomllib
import click
from datetime import datetime
from pathlib import Path
from typing import cast, List, Dict, Any, TypedDict
from litellm import completion
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Define structural types for strong static checking
# -----------------------------------------------------------------------------

class Message(TypedDict):
    role: str
    content: str

class Choice(TypedDict):
    message: Message
    
class CompletionResponse(TypedDict):
    choices: List[Choice]

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
log_dir = Path(__file__).resolve().parent / "logs"
log_file = log_dir / f"agent_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename=log_file,
    encoding="utf-8",
    filemode="w"
)

logger = logging.getLogger(__name__)
logger.info(f"Logging initialized → {log_file}")

log_files = sorted(log_dir.glob("agent_*.log"), key=os.path.getmtime, reverse=True)
for old_log in log_files[5:]:
    old_log.unlink(missing_ok=True)
    
# -----------------------------------------------------------------------------
# Utility: Load Configurations
# -----------------------------------------------------------------------------

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

def load_configs() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load configuration files:
      - config.json (local, for agent tools and rules)
      - config.toml (parent directory, for LLM/system config)
    """
    base_dir = Path(__file__).resolve().parent
    parent_dir = base_dir.parent.parent
    
    json_path = base_dir / "config.json"
    toml_path = parent_dir / "config.toml"
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {json_path}: {e}")
        sys.exit(1)
        
    try:
        with open(toml_path, "rb") as f:
            toml_config = tomllib.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {toml_path}: {e}")
        toml_config = {}
        
    return json_config, toml_config

# -----------------------------------------------------------------------------
# Tool Implementations
# -----------------------------------------------------------------------------

def list_files() -> List[str]:
    """List files in the current directory."""
    return os.listdir(".")

def read_file(file_name: str) -> str:
    """Read a file's content."""
    try:
        with open(file_name, "r") as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: {file_name} not found."
    except Exception as e:
        return f"Error reading {file_name}: {str(e)}"
    
def terminate(message: str) -> None:
    """Terminate the agent loop and provide a summary message."""
    logger.info(f"Termination message: {message}")

# -----------------------------------------------------------------------------
# Tool Registry
# -----------------------------------------------------------------------------
 
tool_functions = {
    "list_files": list_files,
    "read_file": read_file,
    "terminate": terminate
}

# -----------------------------------------------------------------------------
# Agent Execution
# -----------------------------------------------------------------------------

@click.command()
@click.option(
    "--task",
    prompt="What would you like me to do?",
    help="Describe the task you want the AI agent to perform."
)

@click.option(
    "--max-iterations",
    default=10,
    show_default=True,
    help="Maximum number of reasoning iterations before termination."
)

def run_agent(task: str, max_iterations: int):
    """Main entrypoint for the AI agent using Click CLI."""
    
    json_config, toml_config = load_configs()
   
    tools = json_config.get("tools", [])
    agent_rules = json_config.get("agent_rules", [])
    
    iterations = 0
    memory = [{"role": "user", "content": task}]
    
    logger.info("Agent initialized. Starting main loop...")

    while iterations < max_iterations:
        iterations += 1
        logger.info(f"--- Iternation {iterations} ---")
        
        messages = agent_rules + memory
        
        try:
            response = cast(
                CompletionResponse,
                completion(
                    model=toml_config.get("model", "openai/gpt-4o"),
                    messages=messages,
                    tools=tools,
                    max_tokens=toml_config.get("max_tokens", 1024),
                )
            )
        
            choices = response.get("choices", [])
            if not choices:
                logger.error("No choices returned from completion.")
                break
            
            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls")
        
        except Exception as e:
            logger.exception(f"Completetion error: {e}")
            break
          
        if tool_calls:
            tool_call = tool_calls[0]
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            
            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
            
            if tool_name == "terminate":
                terminate(tool_args.get("message", ""))
                break
            elif tool_name in tool_functions:
                try:
                    result = {"result": tool_functions[tool_name](**tool_args)}
                except Exception as e:
                    result = {"error": f"Error executing {tool_name}: {str(e)}"}
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
                
            logger.info(f"Result: {result}")
            
            memory.extend([
                {"role": "assistant", "content": json.dumps({"tool_name": tool_name, "args": tool_args})},
                {"role": "user", "content": json.dumps(result)}
            ])
            
        else:
            # No tool call, just model output
            content = message.get("content", "")
            logger.info(f"Model response: {content}")
            break
    
    logger.info("Agent finished execution.")
    
# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    run_agent() 