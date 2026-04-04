from src.server import mcp


def test_server_has_health_resource():
    """Verify the server registered the inn://health resource."""
    resources = mcp._resource_manager._resources
    assert "inn://health" in resources
