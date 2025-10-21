import json
import csv
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Tool Implementations
# -----------------------------------------------------------------------------

def get_data_path() -> Path:
    """
    Locate the shared 'data' directory at the project root.
    Works even when running from 'lessons/lesson_02_function_calling/'.
    """
    base_dir = Path(__file__).resolve().parent
    
    data_path = base_dir.parent.parent / "data" # two levels up
    
    if not data_path.exists():
        logger.error(f"Data directory not found: {data_path}")
        raise FileNotFoundError(f"Data directory not found: {data_path}")
    
    return data_path

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
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return {
                "type": "json",
                "file_name": file_name,
                "data": data
            }
        elif ext== ".csv":
            import csv
            with open(file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                data = list(reader)
                return {
                    "type": "csv",
                    "file_name": file_name,
                    "data": data
                }
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