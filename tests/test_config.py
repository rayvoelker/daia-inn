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
