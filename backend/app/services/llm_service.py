"""LLM API abstraction — uses langchain-openai ChatOpenAI for DeepSeek,
with httpx fallback for Anthropic and OpenAI providers."""

import httpx
from app.config import settings
from app.exceptions import LLMAPIException


class LLMService:
    """
    Unified LLM client.

    Supports three backends:
    - deepseek (primary): langchain-openai ChatOpenAI
    - anthropic: httpx → Anthropic Messages API
    - openai: httpx → OpenAI Chat Completions API
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self._client: httpx.AsyncClient | None = None
        self._langchain_llm = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return self._client

    def _get_langchain_llm(self):
        """Lazily create ChatOpenAI for DeepSeek."""
        if self._langchain_llm is None:
            from langchain_openai import ChatOpenAI

            self._langchain_llm = ChatOpenAI(
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=0.8,
                max_tokens=800,
            )
        return self._langchain_llm

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate_stream(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 800,
    ):
        """Generate with streaming — yields text chunks as they arrive."""
        if self.provider == "deepseek":
            async for chunk in self._stream_deepseek(system_prompt, user_message, temperature, max_tokens):
                yield chunk
        elif self.provider == "anthropic":
            # Anthropic via httpx: fallback to non-streaming for now
            text = await self._generate_anthropic(system_prompt, user_message, temperature, max_tokens)
            yield text
        elif self.provider == "openai":
            text = await self._generate_openai(system_prompt, user_message, temperature, max_tokens)
            yield text
        else:
            raise LLMAPIException(f"Unsupported provider: {self.provider}")

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 800,
    ) -> str:
        """Generate a single message. Returns the full text response."""
        if self.provider == "deepseek":
            return await self._generate_deepseek(
                system_prompt, user_message, temperature, max_tokens
            )
        elif self.provider == "anthropic":
            return await self._generate_anthropic(
                system_prompt, user_message, temperature, max_tokens
            )
        elif self.provider == "openai":
            return await self._generate_openai(
                system_prompt, user_message, temperature, max_tokens
            )
        else:
            raise LLMAPIException(f"不支持的 LLM provider: {self.provider}")

    # ── DeepSeek (langchain-openai) ──────────────────────────────

    async def _stream_deepseek(
        self, system_prompt: str, user_message: str, temperature: float, max_tokens: int
    ):
        """Stream from DeepSeek — yields text chunks."""
        if not settings.deepseek_available:
            raise LLMAPIException("DeepSeek API Key not configured")

        try:
            llm = self._get_langchain_llm()
            llm.temperature = temperature
            llm.max_tokens = max_tokens
            llm.streaming = True

            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]

            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            raise LLMAPIException(f"DeepSeek stream failed: {str(e)}")

    async def _generate_deepseek(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call DeepSeek API via langchain-openai ChatOpenAI."""
        if not settings.deepseek_available:
            raise LLMAPIException("DeepSeek API Key 未配置")

        try:
            llm = self._get_langchain_llm()
            # Override temperature/max_tokens per request
            llm.temperature = temperature
            llm.max_tokens = max_tokens

            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]
            response = await llm.ainvoke(messages)
            return response.content.strip() if response.content else ""

        except Exception as e:
            raise LLMAPIException(f"DeepSeek API 调用失败: {str(e)}")

    # ── Anthropic (httpx) ────────────────────────────────────────

    async def _generate_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Anthropic Messages API."""
        if not settings.anthropic_available:
            raise LLMAPIException("Anthropic API Key 未配置")

        client = await self._get_http_client()
        url = f"{settings.ANTHROPIC_BASE_URL}/v1/messages"

        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content_blocks = data.get("content", [])
            text = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text += block.get("text", "")
            return text.strip()

        except httpx.HTTPStatusError as e:
            raise LLMAPIException(
                f"Anthropic API 调用失败 (HTTP {e.response.status_code}): "
                f"{e.response.text[:200]}"
            )
        except httpx.RequestError as e:
            raise LLMAPIException(f"Anthropic API 请求失败: {str(e)}")

    # ── OpenAI (httpx) ───────────────────────────────────────────

    async def _generate_openai(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call OpenAI-compatible Chat Completions API."""
        if not settings.openai_available:
            raise LLMAPIException("OpenAI API Key 未配置")

        client = await self._get_http_client()
        url = f"{settings.OPENAI_BASE_URL}/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "content-type": "application/json",
        }

        payload = {
            "model": settings.OPENAI_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }

        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
            return ""

        except httpx.HTTPStatusError as e:
            raise LLMAPIException(
                f"OpenAI API 调用失败 (HTTP {e.response.status_code}): "
                f"{e.response.text[:200]}"
            )
        except httpx.RequestError as e:
            raise LLMAPIException(f"OpenAI API 请求失败: {str(e)}")


# Global singleton
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
