"""Health resource: assembles system and Ollama data into the inn://health report."""

from typing import Any

from src.config import Config
from src.system import GpuStats, RamStats


def parse_ollama_ps(data: dict[str, Any], role_map: dict[str, str]) -> list[dict[str, Any]]:
    """Parse Ollama /api/ps response into model status list."""
    models = []
    for m in data.get("models", []):
        size_bytes = m["size"]
        vram_bytes = m.get("size_vram", 0)
        location = "GPU" if vram_bytes > 0 else "CPU/RAM"
        name = m["name"]
        models.append({
            "name": name,
            "role": role_map.get(name, "unknown"),
            "location": location,
            "size_gb": round(size_bytes / (1024 ** 3), 1),
            "status": "loaded",
        })
    return models


def parse_ollama_version(data: dict[str, Any]) -> str | None:
    """Extract version string from Ollama /api/version response."""
    return data.get("version")


def build_health_report(
    ollama_ps: dict[str, Any] | None,
    ollama_version: dict[str, Any] | None,
    gpu: GpuStats | None,
    ram: RamStats | None,
    config: Config,
) -> dict[str, Any]:
    """Assemble the full inn://health JSON report from collected data."""
    if ollama_ps is not None:
        ollama_status = "running"
        models = parse_ollama_ps(ollama_ps, config.role_map)
    else:
        ollama_status = "unreachable"
        models = []

    version = parse_ollama_version(ollama_version) if ollama_version else None

    return {
        "ollama": {
            "status": ollama_status,
            "version": version,
            "url": config.ollama_url,
        },
        "models": models,
        "gpu": {
            "name": gpu.name,
            "vram_used_gb": gpu.vram_used_gb,
            "vram_total_gb": gpu.vram_total_gb,
            "utilization_pct": gpu.utilization_pct,
        } if gpu else None,
        "system": {
            "ram_used_gb": ram.ram_used_gb,
            "ram_total_gb": ram.ram_total_gb,
            "utilization_pct": ram.utilization_pct,
        } if ram else None,
    }
