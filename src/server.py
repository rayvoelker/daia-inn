"""MCP server entry point — registers resources and runs transport."""

import json

from mcp.server.fastmcp import FastMCP

from src.config import Config
from src.health import build_health_report
from src.ollama import OllamaClient
from src.system import get_gpu_stats, get_ram_stats

config = Config()

mcp = FastMCP(
    name="daia-inn",
    instructions="daia workstation AI infrastructure — the medieval inn",
    host="0.0.0.0",
    port=config.port,
)


@mcp.resource("inn://health")
async def health() -> str:
    """Model status, GPU/RAM usage, Ollama health."""
    client = OllamaClient(config.ollama_url)
    try:
        ollama_ps = await client.get_running_models()
        ollama_version = await client.get_version()
    finally:
        await client.close()

    gpu = await get_gpu_stats()
    ram = await get_ram_stats(config.meminfo_path)

    report = build_health_report(
        ollama_ps=ollama_ps,
        ollama_version=ollama_version,
        gpu=gpu,
        ram=ram,
        config=config,
    )
    return json.dumps(report, indent=2)
