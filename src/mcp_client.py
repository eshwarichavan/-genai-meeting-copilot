"""MCP client (Session 6): the agent's only way to reach the real-world tools.

Every call spawns the MCP server as a subprocess and talks to it over the
stdio JSON-RPC transport, so this is a genuine MCP round trip, not a
hard-coded local function call.
"""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import config

_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "src.mcp_server"],
    cwd=str(config.BASE_DIR),
)


async def _call_tool_async(tool_name: str, arguments: dict) -> str:
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return "\n".join(block.text for block in result.content if hasattr(block, "text"))


async def _list_tools_async():
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            return listed.tools


def call_tool(tool_name: str, arguments: dict) -> str:
    return asyncio.run(_call_tool_async(tool_name, arguments))


def list_tools():
    return asyncio.run(_list_tools_async())
