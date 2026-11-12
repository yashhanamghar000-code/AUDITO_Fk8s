from typing import List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from add_ai_core.interfaces.llm_client import ILLMClient


class GeminiLlmClient(ILLMClient):

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.1,
    ):
        self._llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )

    def complete(self, messages: List[Tuple[str, str]]) -> str:
        lc_messages = []

        for role, content in messages:
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        response = self._llm.invoke(lc_messages)

        return response.content
