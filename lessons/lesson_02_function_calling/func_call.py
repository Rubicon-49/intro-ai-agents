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
from tools import (
    list_files,
    read_structured_file,
    read_text_file,
    terminate
)

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
log_dir.mkdir(exist_ok=True)
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
# Utility: Load Configurations and CLI Print Helpers
# -----------------------------------------------------------------------------

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY missing. Please set it in your environment or .env file.")
    sys.exit(1)


def load_configs() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load configuration files:
      - config.json (local, for agent tools and rules)
      - config.toml (parent directory, for LLM/system config)
    """
    base_dir = Path(__file__).resolve().parent
        
    json_path = base_dir / "config.json"
    toml_path = base_dir.parent.parent / "config.toml" # two levels up
        
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

def cli_info(msg: str):
    """Print concise status messages to the console."""
    click.echo(click.style(msg, fg="cyan"))
    
def cli_success(msg: str):
    """Print success or completion messages."""
    click.echo(click.style(msg, fg="green"))
    
def cli_warning(msg: str):
    """Print warning or error messages."""
    click.echo(click.style(msg, fg="yellow"))
    
# -----------------------------------------------------------------------------
# Tool Registry
# -----------------------------------------------------------------------------
 
tool_functions = {
    "list_files": list_files,
    "read_structured_file": read_structured_file,
    "read_text_file": read_text_file,
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
        cli_info(f"[{iterations}] Iteration:")
        logger.info(f"--- Iteration {iterations} ---")
        
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
            logger.exception(f"Completion error: {e}")
            break
          
        if tool_calls:
            tool_call = tool_calls[0]
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            
            arg_str = ", ".join(f"{k}={v}" for k, v in tool_args.items()) or "no arguments"
            cli_info(f"→ Calling tool {tool_name}({arg_str})")
            
            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
            
            if tool_name == "terminate":
                terminate_msg = tool_args.get("message", "")
                cli_success(f"💬 Terminated - {terminate_msg}")
                terminate(terminate_msg)
                break
            elif tool_name in tool_functions:
                try:
                    result = {"result": tool_functions[tool_name](**tool_args)}
                    # short line for console
                    if tool_name == "list_files":
                        cli_success(f"✅ Found {len(result["result"])} files")
                    elif tool_name == "read_structured_file":
                        res = result["result"]
                        cli_success(f"✅ Data type: {res.get('type', '?')} ({res.get('file_name', '')})")
                    elif tool_name == "read_text_file":
                        cli_success(f"--> Text file read: {tool_args['file_name']}")
                    else:
                        cli_success(f"✅ Tool {tool_name} executed successfully.")
                except Exception as e:
                    result = {"error": f"Error executing {tool_name}: {str(e)}"}
                    cli_warning(f"⚠️  Error executing {tool_name}: {e}")
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
    cli_success("Agent finished exedution.")
    
# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    run_agent() 