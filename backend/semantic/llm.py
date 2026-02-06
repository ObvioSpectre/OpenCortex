from __future__ import annotations

import json
from typing import Any, Dict

import requests

from backend.config import settings


class LLMClient:
    def is_configured(self) -> bool:
        return bool(settings.llm_api_base and settings.llm_api_key)

    def complete_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("LLM provider is not configured")

        response = requests.post(
            f"{settings.llm_api_base.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=45,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
