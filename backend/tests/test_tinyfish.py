import pytest
from app.services.tinyfish_service import retrieve_and_summarize

@pytest.mark.asyncio
async def test_tinyfish_fallback_no_key():
    # If API key is missing, it should use the deterministic dump
    res = await retrieve_and_summarize("What is the flood protocol?")
    
    assert res["demo"] == True
    assert "protocol" in res["content_preview"].lower() or "guidance" in res["content_preview"].lower()
    assert res["title"] == "Local Council Waterlogging Protocol 2026"
    assert res["source"] == "Local System Cache"
