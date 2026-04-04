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
        vram_used_gb=round(vram_used_gb, 2),
        vram_total_gb=round(vram_total_gb, 2),
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
