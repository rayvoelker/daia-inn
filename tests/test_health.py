import pytest
from src.config import Config
from src.system import GpuStats, RamStats
from src.health import parse_ollama_ps, parse_ollama_version, build_health_report


# --- Ollama /api/ps parsing ---

def test_parse_ollama_ps_two_models():
    data = {
        "models": [
            {
                "name": "gemma4:26b",
                "size": 24826593280,  # ~23.1 GB
                "size_vram": 24826593280,
                "details": {},
            },
            {
                "name": "gemma4:e4b-cpu",
                "size": 12776557568,  # ~11.9 GB
                "size_vram": 0,
                "details": {},
            },
        ]
    }
    models = parse_ollama_ps(data, Config().role_map)
    assert len(models) == 2
    assert models[0]["name"] == "gemma4:26b"
    assert models[0]["role"] == "line_cook"
    assert models[0]["location"] == "GPU"
    assert models[0]["size_gb"] == pytest.approx(23.1, abs=0.1)
    assert models[0]["status"] == "loaded"
    assert models[1]["name"] == "gemma4:e4b-cpu"
    assert models[1]["role"] == "scout"
    assert models[1]["location"] == "CPU/RAM"


def test_parse_ollama_ps_empty():
    models = parse_ollama_ps({"models": []}, Config().role_map)
    assert models == []


def test_parse_ollama_ps_unknown_role():
    data = {
        "models": [
            {"name": "llama3:8b", "size": 8000000000, "size_vram": 8000000000, "details": {}},
        ]
    }
    models = parse_ollama_ps(data, Config().role_map)
    assert models[0]["role"] == "unknown"


# --- Ollama /api/version parsing ---

def test_parse_ollama_version():
    data = {"version": "0.20.0"}
    assert parse_ollama_version(data) == "0.20.0"


def test_parse_ollama_version_missing():
    assert parse_ollama_version({}) is None


# --- Full health report assembly ---

def test_build_health_report():
    models_data = {
        "models": [
            {"name": "gemma4:26b", "size": 24826593280, "size_vram": 24826593280, "details": {}},
        ]
    }
    version_data = {"version": "0.20.0"}
    gpu = GpuStats(name="NVIDIA GeForce RTX 4090", vram_used_gb=23.1, vram_total_gb=24.0, utilization_pct=96)
    ram = RamStats(ram_used_gb=38, ram_total_gb=124, utilization_pct=31)
    config = Config()

    report = build_health_report(
        ollama_ps=models_data,
        ollama_version=version_data,
        gpu=gpu,
        ram=ram,
        config=config,
    )

    assert report["ollama"]["status"] == "running"
    assert report["ollama"]["version"] == "0.20.0"
    assert len(report["models"]) == 1
    assert report["gpu"]["name"] == "NVIDIA GeForce RTX 4090"
    assert report["gpu"]["vram_used_gb"] == 23.1
    assert report["system"]["ram_total_gb"] == 124


def test_build_health_report_ollama_down():
    """When Ollama is unreachable, report should still assemble with degraded status."""
    gpu = GpuStats(name="NVIDIA GeForce RTX 4090", vram_used_gb=0.5, vram_total_gb=24.0, utilization_pct=2)
    ram = RamStats(ram_used_gb=10, ram_total_gb=124, utilization_pct=8)
    config = Config()

    report = build_health_report(
        ollama_ps=None,
        ollama_version=None,
        gpu=gpu,
        ram=ram,
        config=config,
    )

    assert report["ollama"]["status"] == "unreachable"
    assert report["ollama"]["version"] is None
    assert report["models"] == []


def test_build_health_report_no_gpu():
    """When nvidia-smi isn't available, GPU section is None."""
    config = Config()
    ram = RamStats(ram_used_gb=10, ram_total_gb=124, utilization_pct=8)

    report = build_health_report(
        ollama_ps={"models": []},
        ollama_version={"version": "0.20.0"},
        gpu=None,
        ram=ram,
        config=config,
    )

    assert report["gpu"] is None
    assert report["system"]["ram_total_gb"] == 124
