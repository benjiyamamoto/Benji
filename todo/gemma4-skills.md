# Benji Skills (via local MCP server)

## Goal
Give Benji a library of callable skills exposed as a **local MCP server**. Both Gemma4 and Claude Code connect to the same server — one skill library, two consumers, standard protocol. The weather check is the first concrete example.

## Architecture

```
~/.benji/skills/
  weather.py
  calendar.py
  reminders.py

         ┌─────────────────────┐
         │  Benji MCP Server   │  (local process, auto-discovers skills)
         └──────────┬──────────┘
                    │  MCP protocol
          ┌─────────┴──────────┐
          │                    │
          ▼                    ▼
   Gemma4 (Ollama)       Claude Code
   tool calling          MCP client
   (translated at        (native)
    startup)
```

The MCP server:
- Auto-discovers skills from `~/.benji/skills/*.py` at startup
- Exposes each as a standard MCP tool with name, description, and input schema
- Claude Code connects to it natively via `.mcp.json`
- Gemma4 connects via Ollama tool calling — at startup, Benji queries the MCP server's tool list and translates them into Ollama tool definitions. When Gemma4 calls a tool, Benji dispatches to the MCP server.

## How it fits the current architecture
Right now `benji/imessage.py` routes messages to Gemma4 or escalates to Claude. Skills extend Gemma4's reach: instead of escalating to Claude for things it *could* handle with a tool, it calls a skill and responds with the result. Claude Code benefits too — it gains access to the same skills when running in this repo.

## Skill file format
Each skill file exposes a standard MCP tool definition and a `run()` function:
```python
TOOL = {
    "name": "get_weather",
    "description": "Get the current weather for a city or location",
    "inputSchema": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City or place to check"}
        },
        "required": ["location"]
    }
}

async def run(location: str) -> str:
    ...  # return plain-text result the model will use in its reply
```

The MCP server auto-discovers these files, registers each `TOOL` definition, and dispatches `run()` when called.

## Claude Code integration
Add a `.mcp.json` at the repo root pointing to the local server:
```json
{
  "mcpServers": {
    "benji": {
      "command": "uv",
      "args": ["run", "benji", "mcp"]
    }
  }
}
```
`benji mcp` becomes a new CLI command that starts the MCP server in the foreground.

## Example: weather skill
- Call Open-Meteo API (no API key needed)
- Input: `location: str`
- Output: plain-text summary ("Sunny, 72°F, wind 8 mph SW")

## Self-building: what happens when no skill matches

When Gemma4 determines a request needs a tool but none exists, Benji should:

1. **Reply immediately** — "I don't have a skill for that yet, but I'm on it."
2. **Log the request** — append to `~/.benji/skills/requested.json` (intent, original message, timestamp).
3. **Delegate to Claude Code** — call `claude -p` with the intent and this skill spec as context, asking it to write a new skill file.
4. **Validate and install** — `ast.parse()`, `TOOL` dict present, `run()` callable. Drop into `~/.benji/skills/` and hot-reload the MCP server.
5. **Notify** — "Done — I've built a [skill name] skill and it's ready to use."

## Routing prompt requirements

Gemma4 will hallucinate answers to real-time questions (weather, news, sports scores, prices) when the routing prompt puts it in "answer mode" — even though it correctly refuses when asked directly. Observed in the wild: asked for Montreal temperature, replied 23°C (actual: 11°C max).

Two things the routing prompt must enforce:

1. **Explicit real-time data rule:** "If answering requires real-time data (weather, news, live prices, sports scores, current time), do not guess. Call a skill if one exists, otherwise escalate."
2. **Fallback until skills exist:** Until a matching skill is installed, real-time queries must escalate to Claude rather than be handled locally. Claude will honestly say it can't get live data; Gemma4 will make something up.

## Open questions
- Hot-reload vs restart: can the MCP server reload skills without dropping active connections, or does it need to restart?
- Gemma4 translation layer: query MCP at startup only, or re-query when new skills are installed?
- Should built-in skills live in `benji/skills/` (repo) while user skills live in `~/.benji/skills/`, mirroring the tasks pattern?
- Error handling: if a skill fails, does the model get the error string or does Benji short-circuit with a fixed message?

## Rejected approaches
- Custom `# benji:skill` header format: invented a protocol when MCP already exists
- Hardcoding tool logic inside `benji/ollama.py`: kills extensibility
- Skills only for Gemma4: leaves Claude Code without access to the same capabilities
