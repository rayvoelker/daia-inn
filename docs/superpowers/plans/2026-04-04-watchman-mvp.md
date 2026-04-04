# Watchman MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the v0.1 MCP server with one resource (`inn://health`) that reports Ollama model status, GPU VRAM, and system RAM.

**Architecture:** A Python MCP server using the `mcp` SDK's `FastMCP` class. The server registers one resource (`inn://health`) that queries Ollama's API (via `httpx`), parses `nvidia-smi` output for GPU stats, and reads `/proc/meminfo` (or `/host/meminfo` in Docker) for RAM. Runs in Docker alongside Ollama, accessible via stdio locally and SSE over Tailscale.

**Tech Stack:** Python 3.10+, `mcp` SDK (FastMCP), `httpx`, Docker, nvidia-smi

---

## File Structure

```
src/
├── __init__.py          (exists, empty)
├── server.py            — MCP server entry point, registers resources, runs transport
├── health.py            — inn://health resource: queries Ollama, GPU, RAM, formats response
├── ollama.py            — async Ollama API client (httpx wrapper for /api/ps, /api/version)
├── system.py            — GPU and RAM stats (nvidia-smi parser, /proc/meminfo reader)
├── config.py            — role map, Ollama URL, port, meminfo path
tests/
├── __init__.py          (exists, empty)
├── test_config.py       — config defaults and env overrides
├── test_system.py       — GPU/RAM parsing from known output strings
├── test_ollama.py       — Ollama client with mocked httpx responses
├── test_health.py       — health resource assembly (mocked ollama + system)
├── test_server.py       — server registers resource at inn://health
Dockerfile               — Python 3.10 slim image, pip install, runs src.server
docker-compose.yml       — Ollama + inn services
```

---

### Task 1: Config Module

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
from src.config import Config


def test_defaults():
    cfg = Config()
    assert cfg.ollama_url == "http://ollama:11434"
    assert cfg.port == 3001
    assert cfg.meminfo_path == "/host/meminfo"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("INN_PORT", "9999")
    cfg = Config()
    assert cfg.ollama_url == "http://localhost:11434"
    assert cfg.port == 9999


def test_role_map():
    cfg = Config()
    assert cfg.role_map["gemma4:26b"] == "line_cook"
    assert cfg.role_map["gemma4:e4b-cpu"] == "scout"
    assert cfg.role_map.get("unknown:model") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'Config' from 'src.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/config.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config module with env overrides and role map"
```

---

### Task 2: System Stats Module (GPU + RAM parsing)

**Files:**
- Create: `src/system.py`
- Test: `tests/test_system.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_system.py
import pytest
from src.system import parse_nvidia_smi, parse_meminfo, GpuStats, RamStats


def test_parse_nvidia_smi_normal():
    output = "NVIDIA GeForce RTX 4090, 23100, 24564, 96\n"
    result = parse_nvidia_smi(output)
    assert result.name == "NVIDIA GeForce RTX 4090"
    assert result.vram_used_gb == pytest.approx(22.56, abs=0.01)
    assert result.vram_total_gb == pytest.approx(23.99, abs=0.01)
    assert result.utilization_pct == 96


def test_parse_nvidia_smi_empty():
    result = parse_nvidia_smi("")
    assert result is None


def test_parse_meminfo():
    content = (
        "MemTotal:       130048000 kB\n"
        "MemFree:         5000000 kB\n"
        "MemAvailable:   90112000 kB\n"
        "Buffers:         1000000 kB\n"
    )
    result = parse_meminfo(content)
    assert result.ram_total_gb == pytest.approx(124.0, abs=0.5)
    assert result.ram_used_gb == pytest.approx(38.0, abs=0.5)


def test_parse_meminfo_empty():
    result = parse_meminfo("")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_system.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/system.py
import asyncio
from dataclasses import dataclass


@dataclass
class GpuStats:
    name: str
    vram_used_gb: float
    vram_total_gb: float
    utilization_pct: int


@dataclass
class RamStats:
    ram_used_gb: float
    ram_total_gb: float
    utilization_pct: int


def parse_nvidia_smi(output: str) -> GpuStats | None:
    """Parse nvidia-smi CSV output: name, memory.used (MiB), memory.total (MiB), utilization.gpu (%)."""
    output = output.strip()
    if not output:
        return None
    parts = [p.strip() for p in output.split(",")]
    if len(parts) < 4:
        return None
    name = parts[0]
    vram_used_gb = int(parts[1]) / 1024
    vram_total_gb = int(parts[2]) / 1024
    utilization_pct = int(parts[3])
    return GpuStats(
        name=name,
        vram_used_gb=round(vram_used_gb, 1),
        vram_total_gb=round(vram_total_gb, 1),
        utilization_pct=utilization_pct,
    )


def parse_meminfo(content: str) -> RamStats | None:
    """Parse /proc/meminfo content for total and available memory."""
    if not content.strip():
        return None
    info: dict[str, int] = {}
    for line in content.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            # Value is in kB, parse the numeric part
            num = int(val.strip().split()[0])
            info[key] = num
    total_kb = info.get("MemTotal", 0)
    available_kb = info.get("MemAvailable", 0)
    used_kb = total_kb - available_kb
    total_gb = round(total_kb / 1024 / 1024, 0)
    used_gb = round(used_kb / 1024 / 1024, 0)
    utilization = int((used_kb / total_kb) * 100) if total_kb else 0
    return RamStats(ram_used_gb=used_gb, ram_total_gb=total_gb, utilization_pct=utilization)


async def get_gpu_stats() -> GpuStats | None:
    """Run nvidia-smi and parse output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return parse_nvidia_smi(stdout.decode())
    except FileNotFoundError:
        return None


async def get_ram_stats(meminfo_path: str = "/host/meminfo") -> RamStats | None:
    """Read meminfo file and parse."""
    try:
        with open(meminfo_path) as f:
            return parse_meminfo(f.read())
    except FileNotFoundError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_system.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/system.py tests/test_system.py
git commit -m "feat: add system stats module for GPU and RAM parsing"
```

---

### Task 3: Ollama Client Module

**Files:**
- Create: `src/ollama.py`
- Test: `tests/test_ollama.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ollama.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from src.ollama import OllamaClient, OllamaStatus, LoadedModel


@pytest.fixture
def client():
    return OllamaClient("http://ollama:11434")


@pytest.mark.asyncio
async def test_get_version(client):
    mock_response = httpx.Response(200, json={"version": "0.20.0"})
    with patch.object(client._http, "get", new_callable=AsyncMock, return_value=mock_response):
        version = await client.get_version()
    assert version == "0.20.0"


@pytest.mark.asyncio
async def test_get_running_models(client):
    mock_response = httpx.Response(200, json={
        "models": [
            {
                "name": "gemma4:26b",
                "size": 24805076992,
                "details": {},
                "size_vram": 24805076992,
            },
            {
                "name": "gemma4:e4b-cpu",
                "size": 12784553984,
                "details": {},
                "size_vram": 0,
            },
        ]
    })
    with patch.object(client._http, "get", new_callable=AsyncMock, return_value=mock_response):
        models = await client.get_running_models()
    assert len(models) == 2
    assert models[0].name == "gemma4:26b"
    assert models[0].size_gb == pytest.approx(23.1, abs=0.1)
    assert models[0].location == "GPU"
    assert models[1].name == "gemma4:e4b-cpu"
    assert models[1].location == "CPU/RAM"


@pytest.mark.asyncio
async def test_get_status(client):
    version_resp = httpx.Response(200, json={"version": "0.20.0"})
    ps_resp = httpx.Response(200, json={"models": []})
    with patch.object(client._http, "get", new_callable=AsyncMock, side_effect=[version_resp, ps_resp]):
        status = await client.get_status()
    assert status.status == "running"
    assert status.version == "0.20.0"
    assert status.models == []


@pytest.mark.asyncio
async def test_get_status_down(client):
    with patch.object(client._http, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
        status = await client.get_status()
    assert status.status == "unreachable"
    assert status.version is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ollama.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ollama.py
from dataclasses import dataclass
import httpx


@dataclass
class LoadedModel:
    name: str
    size_gb: float
    location: str  # "GPU" or "CPU/RAM"


@dataclass
class OllamaStatus:
    status: str  # "running" or "unreachable"
    version: str | None
    url: str
    models: list[LoadedModel]


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._http = httpx.AsyncClient(base_url=base_url, timeout=5.0)

    async def get_version(self) -> str:
        resp = await self._http.get("/api/version")
        return resp.json()["version"]

    async def get_running_models(self) -> list[LoadedModel]:
        resp = await self._http.get("/api/ps")
        data = resp.json()
        models = []
        for m in data.get("models", []):
            total_size = m.get("size", 0)
            vram_size = m.get("size_vram", 0)
            # If most of the model is in VRAM, it's on GPU
            location = "GPU" if vram_size > total_size * 0.5 else "CPU/RAM"
            models.append(LoadedModel(
                name=m["name"],
                size_gb=round(total_size / (1024 ** 3), 1),
                location=location,
            ))
        return models

    async def get_status(self) -> OllamaStatus:
        try:
            version = await self.get_version()
            models = await self.get_running_models()
            return OllamaStatus(
                status="running",
                version=version,
                url=self.base_url,
                models=models,
            )
        except (httpx.HTTPError, httpx.ConnectError):
            return OllamaStatus(
                status="unreachable",
                version=None,
                url=self.base_url,
                models=[],
            )

    async def close(self):
        await self._http.aclose()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ollama.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/ollama.py tests/test_ollama.py
git commit -m "feat: add Ollama async client with version, models, and status"
```

---

### Task 4: Health Resource Module

**Files:**
- Create: `src/health.py`
- Test: `tests/test_health.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_health.py
import json
import pytest
from unittest.mock import AsyncMock, patch
from src.health import get_health_report
from src.ollama import OllamaStatus, LoadedModel
from src.system import GpuStats, RamStats
from src.config import Config


@pytest.fixture
def config():
    return Config()


@pytest.mark.asyncio
async def test_health_report_full(config):
    ollama_status = OllamaStatus(
        status="running",
        version="0.20.0",
        url="http://ollama:11434",
        models=[
            LoadedModel(name="gemma4:26b", size_gb=23.1, location="GPU"),
            LoadedModel(name="gemma4:e4b-cpu", size_gb=11.9, location="CPU/RAM"),
        ],
    )
    gpu = GpuStats(name="NVIDIA GeForce RTX 4090", vram_used_gb=23.1, vram_total_gb=24.0, utilization_pct=96)
    ram = RamStats(ram_used_gb=38, ram_total_gb=124, utilization_pct=31)

    with (
        patch("src.health.OllamaClient") as MockClient,
        patch("src.health.get_gpu_stats", new_callable=AsyncMock, return_value=gpu),
        patch("src.health.get_ram_stats", new_callable=AsyncMock, return_value=ram),
    ):
        mock_instance = AsyncMock()
        mock_instance.get_status.return_value = ollama_status
        MockClient.return_value = mock_instance

        report = await get_health_report(config)

    data = json.loads(report)
    assert data["ollama"]["status"] == "running"
    assert data["ollama"]["version"] == "0.20.0"
    assert len(data["models"]) == 2
    assert data["models"][0]["role"] == "line_cook"
    assert data["models"][1]["role"] == "scout"
    assert data["gpu"]["name"] == "NVIDIA GeForce RTX 4090"
    assert data["system"]["ram_total_gb"] == 124


@pytest.mark.asyncio
async def test_health_report_no_gpu(config):
    ollama_status = OllamaStatus(
        status="running", version="0.20.0",
        url="http://ollama:11434", models=[],
    )
    ram = RamStats(ram_used_gb=10, ram_total_gb=124, utilization_pct=8)

    with (
        patch("src.health.OllamaClient") as MockClient,
        patch("src.health.get_gpu_stats", new_callable=AsyncMock, return_value=None),
        patch("src.health.get_ram_stats", new_callable=AsyncMock, return_value=ram),
    ):
        mock_instance = AsyncMock()
        mock_instance.get_status.return_value = ollama_status
        MockClient.return_value = mock_instance

        report = await get_health_report(config)

    data = json.loads(report)
    assert data["gpu"] is None
    assert data["system"]["ram_total_gb"] == 124
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_health.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/health.py
import json
from src.config import Config
from src.ollama import OllamaClient
from src.system import get_gpu_stats, get_ram_stats


async def get_health_report(config: Config) -> str:
    """Gather all health data and return as JSON string."""
    client = OllamaClient(config.ollama_url)
    try:
        ollama_status = await client.get_status()
    finally:
        await client.close()

    gpu = await get_gpu_stats()
    ram = await get_ram_stats(config.meminfo_path)

    models = []
    for m in ollama_status.models:
        models.append({
            "name": m.name,
            "role": config.role_map.get(m.name, "unknown"),
            "location": m.location,
            "size_gb": m.size_gb,
            "status": "loaded",
        })

    report = {
        "ollama": {
            "status": ollama_status.status,
            "version": ollama_status.version,
            "url": ollama_status.url,
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

    return json.dumps(report, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_health.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/health.py tests/test_health.py
git commit -m "feat: add health resource assembling Ollama, GPU, and RAM data"
```

---

### Task 5: MCP Server Entry Point

**Files:**
- Create: `src/server.py`
- Modify: `main.py` (replace placeholder)
- Test: `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_server.py
from src.server import mcp


def test_server_has_health_resource():
    """Verify the server registered the inn://health resource."""
    resources = mcp._resource_manager._resources
    assert "inn://health" in resources
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write the server module**

```python
# src/server.py
from mcp.server.fastmcp import FastMCP
from src.config import Config
from src.health import get_health_report

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
    return await get_health_report(config)
```

- [ ] **Step 4: Write the __main__ entry point**

Replace `main.py` with:

```python
# main.py
from src.server import mcp

if __name__ == "__main__":
    mcp.run()
```

Also create `src/__main__.py` so `python -m src.server` works:

```python
# src/__main__.py
from src.server import mcp

mcp.run()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_server.py -v`
Expected: 1 passed

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All 11 tests passed

- [ ] **Step 7: Commit**

```bash
git add src/server.py src/__main__.py main.py tests/test_server.py
git commit -m "feat: add MCP server with inn://health resource"
```

---

### Task 6: Docker Setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Write the Dockerfile**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ ./src/

CMD ["python", "-m", "src"]
```

- [ ] **Step 2: Write docker-compose.yml**

```yaml
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  inn:
    build: .
    ports:
      - "3001:3001"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - INN_PORT=3001
      - MEMINFO_PATH=/host/meminfo
    depends_on:
      - ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [utility]
    volumes:
      - /proc/meminfo:/host/meminfo:ro
    restart: unless-stopped

volumes:
  ollama_data:
```

- [ ] **Step 3: Verify docker build**

Run: `docker build -t daia-inn-test . && echo "BUILD OK"`
Expected: BUILD OK

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose for Ollama + inn"
```

---

### Task 7: Integration Smoke Test

**Files:**
- None new — uses existing server

- [ ] **Step 1: Run the server locally against real Ollama**

Run: `OLLAMA_HOST=http://localhost:11434 MEMINFO_PATH=/proc/meminfo uv run python -c "import asyncio; from src.health import get_health_report; from src.config import Config; print(asyncio.run(get_health_report(Config())))"`

Expected: JSON output with real Ollama models, GPU stats, and RAM stats.

- [ ] **Step 2: Verify all tests pass**

Run: `uv run pytest tests/ -v`
Expected: All 11 tests passed

- [ ] **Step 3: Final commit with all remaining files**

```bash
git add -A
git commit -m "feat: daia-inn v0.1 — the Watchman MVP"
```
