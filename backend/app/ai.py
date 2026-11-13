import httpx
from fastapi import HTTPException
from .config import settings

async def complete(agent, messages):
    if settings.ai_provider == "disabled":
        raise HTTPException(503, "AI chat is disabled on this deployment; configure an inference provider to enable it")
    if settings.ai_provider == "cloud" and not settings.openai_api_key:
        raise HTTPException(503, "AI provider is not configured")
    headers = {}
    if settings.ai_provider == "cloud":
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"
    try:
        async with httpx.AsyncClient(timeout=180 if settings.ai_provider == "local" else 60, follow_redirects=False, trust_env=settings.ai_provider == "cloud") as client:
            response = await client.post(settings.openai_base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                json={"model": agent.model, "messages": messages, "temperature": agent.temperature, "max_tokens": agent.max_tokens})
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data["usage"]
            prompt, completion = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
            if not isinstance(content, str) or prompt < 0 or completion < 0: raise ValueError()
            return content, prompt, completion
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
        raise HTTPException(502, "AI provider failed or returned invalid usage")
