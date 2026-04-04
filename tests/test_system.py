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
