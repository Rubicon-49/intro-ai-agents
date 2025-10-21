# Agent CLI with Tool Calling

This guide explains a small agentic CLI that:

1. loads tools and rules from config.json,
2. loads standard LLM defaults from a parent-level config.toml,
3. runs an agent loop via LiteLLM tool-calling,
4. uses Click for a clean CLI,
5. logs to a timestamped file under logs/, and
6. keeps the code friendly to static analyzers with TypedDict.

## 1. What This Agent Does

At a high level, the agent:

- Reads structured configuration:
  - `config.json`(next to the script): tool spec + system rules
  - `config.toml` (in a parent directory): model defaults (e.g., model, max_tokens, etc.)
- Accepts a task via the CLI (`--task "..."`) or an interactive prompt.
- Builds a conversation (`agent_rules + memory`) and calls the LLM.
- If the LLM issues a tool call, the agent:
  - Dipatches to the matching local Python fucntion (`list_files`, `read_files`, `terminate`)
  - Returns the result back into the conversation (so the model can iterate)
- Stops on `terminate` or when there are no further tool calls.

## 1.1 Tool Implementation & Registry

We keep local Python functions minimal and register them by name for safe dispatch.
