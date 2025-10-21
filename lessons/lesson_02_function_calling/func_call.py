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
        
    json_path = base_dir / "config.json"
    toml_path = base_dir.parent.parent / "config.toml"
        
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

def get_data_path() -> Path:
    """
    Locate the shared 'data' directory at the project root.
    Works even when running from 'lessons/lesson_02_function_calling/'.
    """
    base_dir = Path(__file__).resolve().parent
    
    data_path = base_dir.parent.parent / "data"
    
    if not data_path.exists():
        logger.error(f"Data directory not found: {data_path}")
        raise FileNotFoundError(f"Data directory not found: {data_path}")
    
    return data_path

# -----------------------------------------------------------------------------
# Tool Implementations
# -----------------------------------------------------------------------------

def list_files() -> list[str]:
    """
    List available financial data files in the root 'data' directory.
    Returns filenames only (e.g., 'aapl_balance_sheet.json').
    """
    data_path = get_data_path()
    files = [p.name for p in sorted(data_path.iterdir()) if p.is_file()]
    logger.info(f"Files in {data_path}:\n" + "\n".join(files))
    return files

def read_structured_file(file_name: str) -> dict:
    """
    Read a structured data file (JSON or CSV) from the 'data' directory.
    Returns parsed Python objects where possible.
    """
    data_path = get_data_path()
    file_path = data_path / file_name
    ext = file_path.suffix.lower()
    
    try:
        if not file_path.exists():
            return {"error": f"file '{file_name}' not found in {data_path}."}
        
        if ext == ".json":
            return json.loads(file_path.read_text(encoding="utf-8"))
        elif ext== ".csv":
            import csv
            with open(file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return {"rows": list(reader)}
        else:
            return {"error": f"Unsupported structured format: {ext}"}
            
    except Exception as e:
        logger.exception(f"Error reading structured file {file_name}")
        return {"error": str(e), "file_name": file_name}
    
def read_text_file(file_name:str) -> str:
    data_path = get_data_path()
    file_path = data_path / file_name
    ext = file_path.suffix.lower()
    
    try:
        if not file_path.exists():
            return f"Error: file '{file_path}' not found."
        
        if ext in {".txt", ".md"}:
            return file_path.read_text(encoding="utf-8")
        else:
            return f"Unsupported text format: {file_name}"
        
    except Exception as e:
        logger.exception(f"Error reading text file {file_name}")
        return f"Error reading {file_name}: {e}"
               
def terminate(message: str) -> None:
    """Terminate the agent loop and provide a summary message."""
    logger.info(f"Termination message: {message}")

# -----------------------------------------------------------------------------
# Tool Registry
# -----------------------------------------------------------------------------
 
tool_functions = {
    "list_files": list_files,
    "rread_structured_file": read_structured_file,
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