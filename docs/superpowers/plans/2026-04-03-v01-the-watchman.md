# daia-inn v0.1 "The Watchman" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server that exposes one resource (`inn://health`) reporting loaded Ollama models, GPU/RAM usage, and Ollama status — running in docker-compose alongside Ollama.

**Architecture:** FastMCP server with three modules — config (role map, env vars), health (data collection from Ollama API, nvidia-smi, /proc/meminfo), and server (entry point that wires the resource and handles transport). Runs as a Docker service with nvidia utility access for GPU stats. Accessible locally via stdio and remotely via SSE over Tailscale.

**Tech Stack:** Python 3.10, `mcp` SDK (FastMCP), `httpx` (async HTTP), `uv` (package management), Docker, docker-compose

---

## File Structure

```
daia-inn/
├── pyproject.toml              # uv project — deps: mcp, httpx
├── docker-compose.yml          # Ollama + inn services
├── Dockerfile                  # inn service image
├── src/
│   ├── __init__.py             # empty
│   ├── config.py               # ROLE_MAP, env-based config (Ollama URL, port)
│   ├── health.py               # collect_health() — queries Ollama, GPU, RAM
│   └── server.py               # FastMCP entry point, registers inn://health
└── tests/
    ├── __init__.py             # empty
    ├── test_config.py          # config defaults and env override tests
    ├── test_health.py          # health collection with mocked externals
    └── test_server.py          # MCP resource registration integration test
```

**Design decisions:**
- `pyproject.toml` instead of `requirements.txt` — the project uses `uv` for package management
- Three source modules keep each file under 80 lines and single-responsibility
- `health.py` owns all data collection; `server.py` only wires MCP; `config.py` only holds settings
- Tests mock external dependencies (Ollama API, nvidia-smi, /proc/meminfo) — no Docker needed to test

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "daia-inn"
version = "0.1.0"
description = "MCP server exposing daia workstation AI infrastructure"
requires-python = ">=3.10"
dependencies = [
    "mcp",
    "httpx",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
]
```

- [ ] **Step 2: Create empty `__init__.py` files**

Create `src/__init__.py` and `tests/__init__.py` as empty files.

- [ ] **Step 3: Install dependencies**

Run: `uv sync --all-extras`

Expected: dependencies install successfully, `.venv/` created

- [ ] **Step 4: Verify imports work**

Run: `uv run python -c "from mcp.server.fastmcp import FastMCP; import httpx; print('ok')"`

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/__init__.py tests/__init__.py
git commit -m "chore: scaffold project with uv, mcp, httpx deps"
```

---

## Task 2: Configuration Module

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
from src.config import Config


def test_defaults():
    config = Config()
    assert config.ollama_url == "http://ollama:11434"
    assert config.inn_port == 3001
    assert config.meminfo_path == "/host/meminfo"


def test_env_override(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("INN_PORT", "9999")
    config = Config()
    assert config.ollama_url == "http://localhost:11434"
    assert config.inn_port == 9999


def test_role_map():
    config = Config()
    assert config.role_map["gemma4:26b"] == "line_cook"
    assert config.role_map["gemma4:e4b-cpu"] == "scout"
    assert "gemma4:e4b" in config.role_map
    assert "gemma4:31b" in config.role_map
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`

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
    inn_port: int = field(
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
git commit -m "feat: add config module with role map and env-based settings"
```

---

## Task 3: Health Data Collection — Ollama Queries

**Files:**
- Create: `src/health.py`
- Create: `tests/test_health.py`

This task implements the Ollama API queries (loaded models via `/api/ps`, version via `/api/version`). GPU and RAM collection come in Task 4.

- [ ] **Step 1: Write the failing test for Ollama model listing**

```python
# tests/test_health.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from src.config import Config
from src.health import collect_health


@pytest.fixture
def config():
    return Config(ollama_url="http://test:11434")


OLLAMA_PS_RESPONSE = {
    "models": [
        {
            "name": "gemma4:26b",
            "size": 24_800_000_000,
            "details": {"family": "gemma4"},
            "size_vram": 24_800_000_000,
        },
        {
            "name": "gemma4:e4b-cpu",
            "size": 12_700_000_000,
            "details": {"family": "gemma4"},
            "size_vram": 0,
        },
    ]
}

OLLAMA_VERSION_RESPONSE = {"version": "0.20.0"}


@pytest.mark.asyncio
async def test_collect_health_models(config):
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    async def mock_get(url, **kwargs):
        resp = AsyncMock(spec=httpx.Response)
        resp.status_code = 200
        if "/api/ps" in url:
            resp.json.return_value = OLLAMA_PS_RESPONSE
        elif "/api/version" in url:
            resp.json.return_value = OLLAMA_VERSION_RESPONSE
        return resp

    mock_client.get = mock_get

    with patch("src.health._gpu_stats", return_value={"name": "NVIDIA RTX 4090", "vram_used_gb": 23.1, "vram_total_gb": 24.0, "utilization_pct": 96}), \
         patch("src.health._ram_stats", return_value={"ram_used_gb": 38, "ram_total_gb": 124, "utilization_pct": 31}):
        result = await collect_health(config, client=mock_client)

    assert result["ollama"]["status"] == "running"
    assert result["ollama"]["version"] == "0.20.0"
    assert len(result["models"]) == 2
    assert result["models"][0]["name"] == "gemma4:26b"
    assert result["models"][0]["role"] == "line_cook"
    assert result["models"][0]["location"] == "GPU"
    assert result["models"][1]["location"] == "CPU/RAM"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_health.py::test_collect_health_models -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.health'`

- [ ] **Step 3: Write the health module (Ollama queries + stubs for GPU/RAM)**

```python
# src/health.py
import asyncio
import httpx
from src.config import Config


async def collect_health(config: Config, client: httpx.AsyncClient | None = None) -> dict:
    """Collect full health report: Ollama status, models, GPU, and RAM."""
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=5.0)
    try:
        ollama = await _ollama_status(config, client)
        models = await _ollama_models(config, client)
        gpu = await _gpu_stats()
        ram = await _ram_stats(config)
    finally:
        if own_client:
            await client.aclose()

    return {
        "ollama": ollama,
        "models": models,
        "gpu": gpu,
        "system": ram,
    }


async def _ollama_status(config: Config, client: httpx.AsyncClient) -> dict:
    """Query Ollama version endpoint."""
    try:
        resp = await client.get(f"{config.ollama_url}/api/version")
        resp_json = resp.json()
        return {
            "status": "running",
            "version": resp_json.get("version", "unknown"),
            "url": config.ollama_url,
        }
    except (httpx.HTTPError, Exception):
        return {
            "status": "unreachable",
            "version": "unknown",
            "url": config.ollama_url,
        }


async def _ollama_models(config: Config, client: httpx.AsyncClient) -> list[dict]:
    """Query Ollama /api/ps for loaded models."""
    try:
        resp = await client.get(f"{config.ollama_url}/api/ps")
        data = resp.json()
    except (httpx.HTTPError, Exception):
        return []

    models = []
    for m in data.get("models", []):
        name = m["name"]
        size_bytes = m.get("size", 0)
        vram_bytes = m.get("size_vram", 0)
        on_gpu = vram_bytes > 0
        models.append({
            "name": name,
            "role": config.role_map.get(name, "unknown"),
            "location": "GPU" if on_gpu else "CPU/RAM",
            "size_gb": round(size_bytes / 1e9, 1),
            "status": "loaded",
        })
    return models


async def _gpu_stats() -> dict:
    """Read GPU stats from nvidia-smi."""
    # Stub — implemented in Task 4
    return {"name": "unknown", "vram_used_gb": 0, "vram_total_gb": 0, "utilization_pct": 0}


async def _ram_stats(config: Config) -> dict:
    """Read RAM stats from /proc/meminfo (or host-mounted path)."""
    # Stub — implemented in Task 4
    return {"ram_used_gb": 0, "ram_total_gb": 0, "utilization_pct": 0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_health.py::test_collect_health_models -v`

Expected: PASS

- [ ] **Step 5: Add test for Ollama-unreachable case**

Append to `tests/test_health.py`:

```python
@pytest.mark.asyncio
async def test_collect_health_ollama_unreachable(config):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    with patch("src.health._gpu_stats", return_value={"name": "unknown", "vram_used_gb": 0, "vram_total_gb": 0, "utilization_pct": 0}), \
         patch("src.health._ram_stats", return_value={"ram_used_gb": 0, "ram_total_gb": 0, "utilization_pct": 0}):
        result = await collect_health(config, client=mock_client)

    assert result["ollama"]["status"] == "unreachable"
    assert result["models"] == []
```

- [ ] **Step 6: Run all health tests**

Run: `uv run pytest tests/test_health.py -v`

Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add src/health.py tests/test_health.py
git commit -m "feat: add health collection — Ollama status and model listing"
```

---

## Task 4: Health Data Collection — GPU and RAM Stats

**Files:**
- Modify: `src/health.py` (replace `_gpu_stats` and `_ram_stats` stubs)
- Modify: `tests/test_health.py` (add GPU and RAM tests)

- [ ] **Step 1: Write the failing test for RAM stats**

Append to `tests/test_health.py`:

```python
@pytest.mark.asyncio
async def test_ram_stats():
    from src.health import _ram_stats

    fake_meminfo = (
        "MemTotal:       130054604 kB\n"
        "MemFree:         2048000 kB\n"
        "MemAvailable:   89600000 kB\n"
        "Buffers:          512000 kB\n"
        "Cached:         50000000 kB\n"
    )
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix="_meminfo", delete=False) as f:
        f.write(fake_meminfo)
        tmp_path = f.name

    config = Config(meminfo_path=tmp_path)
    try:
        result = await _ram_stats(config)
        assert result["ram_total_gb"] == 124  # 130054604 kB ~ 124 GB
        assert result["ram_used_gb"] > 0
        assert 0 <= result["utilization_pct"] <= 100
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_health.py::test_ram_stats -v`

Expected: FAIL (stub returns zeros, assertion fails on `ram_total_gb`)

- [ ] **Step 3: Implement `_ram_stats` in `src/health.py`**

Replace the `_ram_stats` stub:

```python
async def _ram_stats(config: Config) -> dict:
    """Read RAM stats from /proc/meminfo (or host-mounted path)."""
    try:
        with open(config.meminfo_path) as f:
            lines = f.readlines()

        mem = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                mem[key] = int(parts[1])  # value in kB

        total_kb = mem.get("MemTotal", 0)
        available_kb = mem.get("MemAvailable", 0)
        used_kb = total_kb - available_kb

        total_gb = round(total_kb / 1_048_576)  # kB to GB, rounded
        used_gb = round(used_kb / 1_048_576)
        pct = round(used_kb / total_kb * 100) if total_kb > 0 else 0

        return {"ram_used_gb": used_gb, "ram_total_gb": total_gb, "utilization_pct": pct}
    except (FileNotFoundError, Exception):
        return {"ram_used_gb": 0, "ram_total_gb": 0, "utilization_pct": 0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_health.py::test_ram_stats -v`

Expected: PASS

- [ ] **Step 5: Write the failing test for GPU stats**

Append to `tests/test_health.py`:

```python
@pytest.mark.asyncio
async def test_gpu_stats():
    from src.health import _gpu_stats

    fake_smi_output = "NVIDIA RTX 4090, 23100, 24564, 42\n"
    with patch("asyncio.subprocess.create_subprocess_exec") as mock_exec:
        proc = AsyncMock()
        proc.communicate.return_value = (fake_smi_output.encode(), b"")
        proc.returncode = 0
        mock_exec.return_value = proc

        result = await _gpu_stats()

    assert result["name"] == "NVIDIA RTX 4090"
    assert result["vram_used_gb"] == 22.6  # 23100 MiB ~ 22.6 GB
    assert result["vram_total_gb"] == 24.0  # 24564 MiB ~ 24.0 GB
    assert result["utilization_pct"] == 42


@pytest.mark.asyncio
async def test_gpu_stats_no_nvidia():
    from src.health import _gpu_stats

    with patch("asyncio.subprocess.create_subprocess_exec", side_effect=FileNotFoundError):
        result = await _gpu_stats()

    assert result["name"] == "unknown"
    assert result["vram_used_gb"] == 0
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_health.py::test_gpu_stats -v`

Expected: FAIL (stub returns zeros)

- [ ] **Step 7: Implement `_gpu_stats` in `src/health.py`**

Replace the `_gpu_stats` stub (note: `import asyncio` should already be at the top from the initial file):

```python
async def _gpu_stats() -> dict:
    """Read GPU stats from nvidia-smi."""
    try:
        proc = await asyncio.subprocess.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("nvidia-smi failed")

        line = stdout.decode().strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        name = parts[0]
        vram_used_mib = float(parts[1])
        vram_total_mib = float(parts[2])
        util_pct = int(parts[3])

        return {
            "name": name,
            "vram_used_gb": round(vram_used_mib / 1024, 1),
            "vram_total_gb": round(vram_total_mib / 1024, 1),
            "utilization_pct": util_pct,
        }
    except (FileNotFoundError, Exception):
        return {"name": "unknown", "vram_used_gb": 0, "vram_total_gb": 0, "utilization_pct": 0}
```

- [ ] **Step 8: Run all health tests**

Run: `uv run pytest tests/test_health.py -v`

Expected: 5 passed

- [ ] **Step 9: Commit**

```bash
git add src/health.py tests/test_health.py
git commit -m "feat: add GPU and RAM stats collection via nvidia-smi and /proc/meminfo"
```

---

## Task 5: MCP Server Entry Point

**Files:**
- Create: `src/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write the failing test for resource registration**

```python
# tests/test_server.py
import pytest
from unittest.mock import AsyncMock, patch
from src.server import mcp


def test_server_has_health_resource():
    """Verify the inn://health resource is registered."""
    resources = mcp._resource_manager._resources
    assert "inn://health" in resources


@pytest.mark.asyncio
async def test_health_resource_returns_json():
    """Call the health resource handler and verify it returns a dict."""
    fake_health = {
        "ollama": {"status": "running", "version": "0.20.0", "url": "http://ollama:11434"},
        "models": [],
        "gpu": {"name": "unknown", "vram_used_gb": 0, "vram_total_gb": 0, "utilization_pct": 0},
        "system": {"ram_used_gb": 0, "ram_total_gb": 0, "utilization_pct": 0},
    }

    with patch("src.server.collect_health", return_value=fake_health):
        handler = mcp._resource_manager._resources["inn://health"]
        result = await handler.fn()

    assert result == fake_health
    assert result["ollama"]["status"] == "running"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_server.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.server'`

- [ ] **Step 3: Write the server module**

```python
# src/server.py
import argparse
from mcp.server.fastmcp import FastMCP
from src.config import Config
from src.health import collect_health

config = Config()

mcp = FastMCP(
    "daia-inn",
    host="0.0.0.0",
    port=config.inn_port,
)


@mcp.resource("inn://health", name="health", description="Model status, GPU/RAM usage, Ollama health")
async def health() -> dict:
    return await collect_health(config)


def main():
    parser = argparse.ArgumentParser(description="daia-inn MCP server")
    parser.add_argument(
        "--stdio", action="store_true", help="Run in stdio mode (for local MCP clients)"
    )
    args = parser.parse_args()

    transport = "stdio" if args.stdio else "sse"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_server.py -v`

Expected: 2 passed

- [ ] **Step 5: Verify the server can start in stdio mode**

Run: `echo '{"jsonrpc":"2.0","method":"initialize","params":{"capabilities":{}},"id":1}' | timeout 3 uv run python -m src.server --stdio 2>/dev/null || true`

Expected: JSON-RPC response (or clean timeout). No crash.

- [ ] **Step 6: Commit**

```bash
git add src/server.py tests/test_server.py
git commit -m "feat: add MCP server entry point with inn://health resource"
```

---

## Task 6: Docker Setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY src/ ./src/

CMD ["uv", "run", "python", "-m", "src.server"]
```

- [ ] **Step 2: Create `docker-compose.yml`**

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

- [ ] **Step 3: Verify Docker build succeeds**

Run: `docker build -t daia-inn-test .`

Expected: image builds successfully

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose with Ollama + inn services"
```

---

## Task 7: Integration Smoke Test

**Files:**
- No new files — this validates the full stack

- [ ] **Step 1: Start the stack**

Run: `docker compose up -d`

Expected: Both `ollama` and `inn` containers start

- [ ] **Step 2: Check container health**

Run: `docker compose ps`

Expected: Both services show as `running`

- [ ] **Step 3: Test MCP resource via stdio**

Run: `docker exec -i daia-inn-inn-1 uv run python -m src.server --stdio` and send an `initialize` + `resources/read` request.

Alternatively, check logs:

Run: `docker compose logs inn --tail 20`

Expected: Server starts without errors

- [ ] **Step 4: Test Ollama connectivity from inn container**

Run: `docker exec daia-inn-inn-1 uv run python -c "import httpx; r = httpx.get('http://ollama:11434/api/version'); print(r.json())"`

Expected: `{"version": "..."}` response showing Ollama is reachable

- [ ] **Step 5: Stop the stack**

Run: `docker compose down`

- [ ] **Step 6: Commit any fixes if needed, then tag**

```bash
git tag v0.1.0
git commit --allow-empty -m "milestone: v0.1 The Watchman — health resource complete"
```

---

## Task 8: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md Commands section**

Add the test command:

```markdown
- `uv run pytest` — run tests
- `uv run pytest -v` — run tests verbose
```

- [ ] **Step 2: Update CLAUDE.md Architecture section if needed**

Verify the architecture section matches the actual implementation. Update any references to `requirements.txt` to `pyproject.toml`.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with test commands and architecture notes"
```
