"""
Benji Ollama integration — thin async wrapper around the ollama Python client.
Gemma4 is the default model (set in config.py).
"""

from __future__ import annotations

import ollama as _ollama

from benji.config import OLLAMA_MODEL
from benji.logger import log


async def ask_ollama(prompt: str, model: str | None = None) -> str:
    """
    Send a prompt to Ollama and return the response text.
    Uses the model defined in config.py by default.
    """
    _model = model or OLLAMA_MODEL
    log.debug(f"[ollama] → {_model}: {prompt[:120]}")

    response = await _ollama.AsyncClient().generate(
        model=_model,
        prompt=prompt,
    )
    text: str = response.response.strip()
    log.debug(f"[ollama] ← {text[:120]}")
    return text


async def chat_ollama(messages: list[dict[str, str]], model: str | None = None) -> str:
    """
    Multi-turn chat with Ollama.
    messages: [{"role": "user"|"assistant"|"system", "content": "..."}]
    """
    _model = model or OLLAMA_MODEL
    response = await _ollama.AsyncClient().chat(
        model=_model,
        messages=messages,
    )
    text: str = response.message.content.strip()
    return text
