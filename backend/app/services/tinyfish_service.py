import httpx
import logging
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

async def retrieve_and_summarize(query: str) -> dict:
    """Uses TinyFish to run search and grab the most relevant civic doc."""
    api_key = settings.TINYFISH_API_KEY
    if not api_key:
        return _deterministic_civic_mock(query)
    
    headers = {"X-API-Key": api_key}
    
    try:
        # 1. Search
        async with httpx.AsyncClient(timeout=10.0) as client:
            search_url = "https://api.search.tinyfish.ai"
            sr = await client.get(search_url, params={"q": query, "limit": 3}, headers=headers)
            sr.raise_for_status()
            results = sr.json().get("results", [])
            
            if not results:
                return {"error": "No documents found", "demo": False}

            best_doc = results[0]
            target_url = best_doc.get("url")
            title = best_doc.get("title", "Unknown Title")
            
            # 2. Fetch
            fetch_url = "https://api.fetch.tinyfish.ai"
            fr = await client.get(fetch_url, params={"url": target_url}, headers=headers)
            fr.raise_for_status()
            
            # Typically a structured response with text or markdown
            f_resp = fr.json()
            fetched_content = f_resp.get("content", best_doc.get("snippet", "No snippet available"))
            
            return {
                "title": title,
                "url": target_url,
                "content_preview": fetched_content[:500] if fetched_content else "",
                "timestamp": datetime.utcnow().isoformat(),
                "demo": False,
                "source": "TinyFish Civic Search"
            }
            
    except httpx.HTTPError as e:
        logger.error(f"TinyFish HTTP error: {str(e)}")
        return {"error": f"Failed to retrieve data: {str(e)}", "demo": False}
    except Exception as e:
        logger.error(f"TinyFish Exception: {str(e)}")
        return {"error": str(e), "demo": False}


def _deterministic_civic_mock(query: str) -> dict:
    """Offline cache for hackathon prototypes when API Key missing"""
    return {
        "title": "Local Council Waterlogging Protocol 2026",
        "url": "https://civic.local/mock-doc-103",
        "content_preview": "Generic Guidance: Ensure 300mm surface accumulation invokes pump dispatch protocol. Not to be used blindly; evaluate live conditions against this advisory framework. Protect civilian routes.",
        "timestamp": datetime.utcnow().isoformat(),
        "demo": True,
        "source": "Local System Cache"
    }
