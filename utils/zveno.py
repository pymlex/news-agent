import json
from typing import Any


import httpx
from tqdm.auto import tqdm


from utils.config import Settings, settings


CHEAP_MODELS = [
    "qwen/qwen3.7-flash",
    "qwen/qwen3-8b",
    "deepseek/deepseek-v4-flash",
    "qwen/qwen3-30b-a3b-instruct-2507",
    "deepseek/deepseek-chat",
]


class ZvenoClient:
    """OpenAI-compatible client for the Zveno AI chat completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialise HTTP client settings.

        Args:
            api_key: Bearer token for Zveno AI.
            base_url: API root ending with /v1.
            model: Default model slug.
        """

        self._api_key_override = api_key
        self.base_url = (base_url or settings.zvenoai_base_url).rstrip("/")
        self.model = model or settings.zvenoai_model


    def resolved_api_key(self) -> str:
        """Return the current API key from override or fresh settings."""

        if self._api_key_override is not None and self._api_key_override.strip():
            return self._api_key_override.strip()
        return Settings().zvenoai_api_key.strip()


    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call chat completions and return the raw JSON body.

        Args:
            messages: Chat messages in OpenAI format.
            model: Optional model override.
            temperature: Sampling temperature.
            tools: Optional tool schemas.
            tool_choice: Optional tool choice policy.
            response_format: Optional response format hint.

        Returns:
            Parsed JSON response from Zveno AI.
        """

        api_key = self.resolved_api_key()
        if not api_key:
            raise ValueError(
                "ZVENOAI_API_KEY is empty. Put the key into .env and restart."
            )

        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()


    def chat_text(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Return assistant text content from a chat completion.

        Args:
            messages: Chat messages.
            model: Optional model override.
            temperature: Sampling temperature.

        Returns:
            Assistant message content as a string.
        """

        data = self.chat(messages=messages, model=model, temperature=temperature)
        return str(data["choices"][0]["message"]["content"] or "")


    def chat_json(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.1,
    ) -> Any:
        """Request a JSON object and parse the assistant content.

        Args:
            messages: Chat messages that instruct JSON-only output.
            model: Optional model override.
            temperature: Sampling temperature.

        Returns:
            Parsed JSON value.
        """

        data = self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = str(data["choices"][0]["message"]["content"] or "{}")
        content = content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines)
        return json.loads(content)


    def map_json_batches(
        self,
        prompts: list[list[dict[str, Any]]],
        model: str | None = None,
        desc: str = "LLM batches",
    ) -> list[Any]:
        """Run several JSON chat calls with a progress bar.

        Args:
            prompts: Sequence of message lists.
            model: Optional model override.
            desc: tqdm description.

        Returns:
            List of parsed JSON results aligned with prompts.
        """

        outputs: list[Any] = []
        for messages in tqdm(prompts, desc=desc):
            outputs.append(self.chat_json(messages=messages, model=model))
        return outputs


zveno = ZvenoClient()
