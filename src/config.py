"""Configuration defaults and role map for daia-inn."""

import os
from dataclasses import dataclass, field


ROLE_MAP: dict[str, str] = {
    "gemma4:26b": "line_cook",
    "gemma4:e4b-cpu": "scout",
    "gemma4:e4b": "scout_gpu",
    "gemma4:31b": "head_chef",
}


@dataclass
class Config:
    ollama_url: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    )
    port: int = field(
        default_factory=lambda: int(os.environ.get("INN_PORT", "3001"))
    )
    meminfo_path: str = field(
        default_factory=lambda: os.environ.get("MEMINFO_PATH", "/host/meminfo")
    )
    role_map: dict[str, str] = field(default_factory=lambda: dict(ROLE_MAP))
