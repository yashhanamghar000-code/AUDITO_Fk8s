from typing import List, Tuple

import httpx

from add_ai_core.interfaces.llm_client import ILLMClient


class MistralLlmClient(ILLMClient):
    def __init__(
        self,
        model: str,
        api_key: str,
        endpoint: str,
        temperature: float = 0.1,
        timeout_seconds: float = 60.0,
    ):
        self._model = model
        self._temperature = temperature
        self._chat_completions_url = f"{endpoint.rstrip('/')}/chat/completions"
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
        )

    def complete(self, messages: List[Tuple[str, str]]) -> str:
        response = self._client.post(
            self._chat_completions_url,
            json={
                "model": self._model,
                "messages": [
                    {"role": role, "content": content} for role, content in messages
                ],
                "temperature": self._temperature,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
