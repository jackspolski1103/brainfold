from oif.verification import verify_example


async def test_shared_http_service_and_real_mcp():
    result = await verify_example()
    assert result["status"] == "passed"
    assert "single_correction_both_agents_v2" in result["checks"]
    assert "consistent_tool_errors" in result["checks"]
    assert "capability_revocation_no_fallback" in result["checks"]
    assert "permissioned_memory_navigation" in result["checks"]
    assert "memory_revocation_clears_old_context" in result["checks"]
    assert result["model_reasoning_verified"] is False
