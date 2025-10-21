# Agent CLI with Tool Calling

This guide explains a small agentic CLI that:

1. loads tools and rules from config.json,
2. loads standard LLM defaults from project-root config.toml,
3. runs an agent loop via LiteLLM tool-calling,
4. prints concise iteration progress in the CLI,
5. logs to a timestamped file under logs/

## Quick demo what the CLI shos

```bash
$ python func_call.py --task "What was Apple's total revenue in the most recent year?"

[1] Iteration:
22:04:25 - LiteLLM:INFO: utils.py:3373 - 
LiteLLM completion() model= gpt-4o; provider = openai
22:04:26 - LiteLLM:INFO: utils.py:1286 - Wrapper: Completed Call, calling success_handler
→ Calling tool list_files(no arguments)
✅ Found 10 files
[2] Iteration:
22:04:26 - LiteLLM:INFO: utils.py:3373 - 
LiteLLM completion() model= gpt-4o; provider = openai
22:04:28 - LiteLLM:INFO: utils.py:1286 - Wrapper: Completed Call, calling success_handler
→ Calling tool read_structured_file(file_name=aapl_income_statement.json)
✅ Data type: json (aapl_income_statement.json)
[3] Iteration:
22:04:28 - LiteLLM:INFO: utils.py:3373 - 
LiteLLM completion() model= gpt-4o; provider = openai
22:04:29 - LiteLLM:INFO: utils.py:1286 - Wrapper: Completed Call, calling success_handler
→ Calling tool terminate(message=Apple's total revenue for the most recent year (fiscal year ending on September 30, 2024) was $391.035 billion.)
💬 Terminated - Apple's total revenue for the most recent year (fiscal year ending on September 30, 2024) was $391.035 billion.
Agent finished exedution.

```

## Layout of Relevant Project Files

```arduino
project_root/
├── config.toml                 # model settings (parent-level)
├── data/                       # financial data files
│   ├── aapl_income_statement.json
│   ├── msft_income_statement.json
│   └── tsla_income_statement.json
└── lessons/
    └── lesson_02_function_calling/
        ├── func_call.py        # agent runner (Click CLI + agent loop)
        ├── tools.py            # tool implementations (optional refactor)
        ├── config.json         # tools + agent_rules for the model
        └── logs/               # timestamped run logs

```

### How to run

1. Set your API key (e.g., in `.env`at repo root):

    ```ìni
    OPENAI_API_KEY=sk-...
    ```

2. Install dependencies with `make install`

3. Run:

   ```lua 
   python func_call.py --task "What was Apple's total revenue in the most recent year?"
   ```

## The Three Key Ideas

### 1 Two config files (clean separation)

- `config.json`(next to the script): tool spec + system rules
- `config.toml` (in a repository root): LLM defaults (e.g., model, max_tokens, etc.)

```python
# func_call.py (excerpt)
json_config = json.load(open(base_dir / "config.json", "r", encoding="utf-8"))
toml_config = tomllib.load(open(base_dir.parent.parent / "config.toml", "rb"))
```

### 2 Tools the Agent Can Call

We expose exactly what the agent can do with the filesystem:

- `list_files()` → lists filenames in `/data`
- `read_structured_file(file_name)` → parses JSON/CSV and returns a consistent envelope:
  
```json
{"type": "json"|"csv", "file_name": "...", "data": {... or [...]}}
```

- `read_text_file(file_name)` → returns raw text (`.md`, `.txt`)
- `terminate(message)` → ends the loop with a summary

config.json (concise tool entries):

```json
{
  "type": "function",
  "function": {
    "name": "read_structured_file",
    "description": "Read structured data (.json, .csv) and return a parsed dictionary.",
    "parameters": { "type": "object", "properties": { "file_name": { "type": "string" } }, "required": ["file_name"] }
  }
},
{
  "type": "function",
  "function": {
    "name": "read_text_file",
    "description": "Read unstructured text (.md, .txt) and return plain text.",
    "parameters": { "type": "object", "properties": { "file_name": { "type": "string" } }, "required": ["file_name"] }
  }
}
```

The consistent envelope for structured data (`{"type","file_name","data"}`) makes it easier for the model (and for tests) to reason over the result.

### 3 The Agent Loop (How Reasoning Unfolds)

1. Build messages = `agent_rules + memory`.
2. Call `completion(..., tools=tools)`.
3. If the model returns `tool_calls`, execute the requested tool and feed the JSON result back into `memory`.
4. If the model returns a normal message, print it and stop.
5. Stop if `terminate(...)` is called or max iterations is reached.

```python
response = completion(model=..., messages=messages, tools=tools, max_tokens=...)
message = response["choices"][0]["message"]
tool_calls = message.get("tool_calls")

if tool_calls:
    tool = tool_calls[0]
    tool_name = tool["function"]["name"]
    tool_args = json.loads(tool["function"]["arguments"])
    result = tool_functions[tool_name](**tool_args)
    memory += [
      {"role": "assistant", "content": json.dumps({"tool_name": tool_name, "args": tool_args})},
      {"role": "user", "content": json.dumps({"result": result})}
    ]
else:
    print(message.get("content", ""))
    break
```

### Example

```lua
python func_call.py --task "What was Apple's total revenue in the most recent year?"
```

- Iter 1 → `list_files()`
- Iter 2 → `read_structured_file("aapl_income_statement.json")`
- Iter 3 → `terminate("Apple's total revenue for FY 20XX was …")`
