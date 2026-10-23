"""Runs one agent on the Claude Agent SDK. The only module that imports `claude_agent_sdk`.

Each agent gets a fresh session whose only tools are its toolbox, served from an in-process MCP server.
Built-in tools (Bash, Read, Edit and the rest) are switched off, and no user or project settings load.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from src.agents.coordinator import AgentRunner
from src.agents.toolbox import RoleToolbox, ToolSpec, build_system_prompt
from src.domain import ROOT_DIR


SERVER_NAME = "fpa"


def _sdk_tool(toolbox: RoleToolbox, spec: ToolSpec) -> Any:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        return {"content": [{"type": "text", "text": toolbox.call(spec.name, args)}]}

    return tool(spec.name, spec.description, spec.input_schema)(handler)


async def _run_agent(role: str, task: str, toolbox: RoleToolbox, model: str, max_turns: int) -> Dict[str, Any]:
    allowed = [f"mcp__{SERVER_NAME}__{name}" for name in toolbox.specs]
    server = create_sdk_mcp_server(SERVER_NAME, tools=[_sdk_tool(toolbox, spec) for spec in toolbox.specs.values()])
    options = ClaudeAgentOptions(
        system_prompt=build_system_prompt(role),
        mcp_servers={SERVER_NAME: server},
        tools=[],
        allowed_tools=allowed,
        strict_mcp_config=True,
        setting_sources=[],
        model=model,
        max_turns=max_turns,
        cwd=str(ROOT_DIR),
    )
    stats: Dict[str, Any] = {}
    async for message in query(prompt=task, options=options):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            stats["model"] = message.data.get("model")
            offered = sorted(message.data.get("tools", []))
            if offered != sorted(allowed):
                raise RuntimeError(f"{role} session offered tools {offered}, expected {sorted(allowed)}")
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    toolbox.record({"type": "assistant_text", "text": block.text.strip()})
        elif isinstance(message, ResultMessage):
            stats.update(
                {
                    "turns": message.num_turns,
                    "cost_usd": message.total_cost_usd,
                    "stop": message.subtype,
                }
            )
    return stats


def make_sdk_runner(model: str = "sonnet", max_turns: int = 30) -> AgentRunner:
    """Return a coordinator runner that starts a new SDK session for each agent run."""

    def run(role: str, task: str, toolbox: RoleToolbox) -> Dict[str, Any]:
        return asyncio.run(_run_agent(role, task, toolbox, model, max_turns))

    return run
