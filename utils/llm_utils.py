"""
Shared LLM utilities with multi-provider fallback and retry logic.

Provider chain: NVIDIA → Google Gemini → Groq
VLM (Vision): NVIDIA only (meta/llama-3.2-11b-vision-instruct)
"""
import os
import time
import random
import base64
import logging
from typing import Any, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from config import (
    NVIDIA_API_KEY, MODEL_NAME, VLM_MODEL_NAME,
    GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODEL_NAME,
    LLM_CONFIG, CALL_GAP,
)

logger = logging.getLogger(__name__)

# ─── Global rate-limit state ───
_last_call_time = 0


# ═══════════════════════════════════════
# LLM Provider Factory (Text)
# ═══════════════════════════════════════

def _try_nvidia(api_key: str = None):
    """Attempt to create NVIDIA ChatNVIDIA instance."""
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        key = api_key or NVIDIA_API_KEY
        if key:
            return ChatNVIDIA(
                model=MODEL_NAME,
                api_key=key,
                temperature=LLM_CONFIG["temperature"],
                top_p=LLM_CONFIG["top_p"],
                max_tokens=LLM_CONFIG["max_tokens"],
            ), "nvidia"
    except Exception as e:
        logger.debug("NVIDIA LLM unavailable: %s", e)
    return None, None


def _try_gemini():
    """Attempt to create Google Gemini instance."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = GEMINI_API_KEY
        if key:
            os.environ.setdefault("GOOGLE_API_KEY", key)
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=LLM_CONFIG["temperature"],
                max_output_tokens=LLM_CONFIG["max_tokens"],
            ), "gemini"
    except Exception as e:
        logger.debug("Gemini LLM unavailable: %s", e)
    return None, None


def _try_groq():
    """Attempt to create Groq instance."""
    try:
        from langchain_groq import ChatGroq
        key = GROQ_API_KEY
        if key:
            return ChatGroq(
                model=GROQ_MODEL_NAME,
                api_key=key,
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"],
            ), "groq"
    except Exception as e:
        logger.debug("Groq LLM unavailable: %s", e)
    return None, None


def get_llm(api_key: str = None) -> Tuple[Any, str]:
    """
    Create an LLM instance using the first available provider.
    Returns (llm_instance, provider_name).
    Fallback chain: NVIDIA → Gemini → Groq.
    """
    # Try NVIDIA first
    llm, provider = _try_nvidia(api_key)
    if llm:
        return llm, provider

    # Fallback to Gemini
    llm, provider = _try_gemini()
    if llm:
        logger.info("Using Gemini as fallback LLM provider")
        return llm, provider

    # Fallback to Groq
    llm, provider = _try_groq()
    if llm:
        logger.info("Using Groq as fallback LLM provider")
        return llm, provider

    raise RuntimeError(
        "No LLM provider available. Set at least one of: "
        "NVIDIA_API_KEY, GEMINI_API_KEY, GROQ_API_KEY"
    )


# ═══════════════════════════════════════
# VLM Provider Factory (Vision)
# ═══════════════════════════════════════

def get_vlm(api_key: str = None):
    """Create a Vision-Language Model instance (NVIDIA only)."""
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        key = api_key or NVIDIA_API_KEY
        if key:
            return ChatNVIDIA(
                model=VLM_MODEL_NAME,
                api_key=key,
                temperature=0.2,
                max_tokens=LLM_CONFIG["max_tokens"],
            )
    except Exception as e:
        logger.warning("VLM unavailable: %s", e)

    # Fallback: try Gemini vision
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = GEMINI_API_KEY
        if key:
            os.environ.setdefault("GOOGLE_API_KEY", key)
            logger.info("Using Gemini as fallback VLM provider")
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.2,
                max_output_tokens=LLM_CONFIG["max_tokens"],
            )
    except Exception as e:
        logger.warning("Gemini VLM fallback unavailable: %s", e)

    return None


def invoke_vlm_with_image(vlm, image_bytes: bytes, prompt: str, image_format: str = "png"):
    """
    Send an image + text prompt to a VLM.
    image_bytes: raw image bytes (PNG/JPEG)
    Returns the LLM response object.
    """
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    mime = f"image/{image_format}"

    message = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}"}},
    ])

    return invoke_with_retry(vlm, [message])


# ═══════════════════════════════════════
# Retry Logic with Rate Limiting
# ═══════════════════════════════════════

def invoke_with_retry(llm, messages, max_retries=5, progress_callback=None):
    """
    Invoke LLM with exponential backoff retry on 429 errors.
    Enforces a minimum gap between calls to avoid rate limits.

    progress_callback: optional callable(status_str) for UI updates
    """
    global _last_call_time

    for attempt in range(max_retries):
        # Enforce minimum gap between calls
        elapsed = time.time() - _last_call_time
        if elapsed < CALL_GAP:
            wait_time = CALL_GAP - elapsed
            if progress_callback:
                progress_callback(f"⏳ Cooling down ({wait_time:.0f}s)...")
            time.sleep(wait_time)

        try:
            _last_call_time = time.time()
            response = llm.invoke(messages)
            # Small cooldown after successful call
            time.sleep(1)
            return response
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Too Many Requests" in error_str or "rate" in error_str.lower():
                wait = (2 ** attempt) * 3 + random.uniform(1, 3)
                msg = f"⏳ Waiting {wait:.0f}s before retry ({attempt+1}/{max_retries})..."
                logger.warning(msg)
                if progress_callback:
                    progress_callback(msg)
                time.sleep(wait)
            else:
                raise e

    raise Exception(f"Failed after {max_retries} retries due to rate limiting")


def try_invoke_with_fallback(messages, api_key: str = None, max_retries=3, progress_callback=None):
    """
    Try invoking with the primary LLM. If rate-limited after all retries,
    automatically fall back to the next provider.
    Returns (response, provider_used).
    """
    providers = []

    # Build provider list in priority order
    llm_nvidia, _ = _try_nvidia(api_key)
    if llm_nvidia:
        providers.append((llm_nvidia, "nvidia"))

    llm_gemini, _ = _try_gemini()
    if llm_gemini:
        providers.append((llm_gemini, "gemini"))

    llm_groq, _ = _try_groq()
    if llm_groq:
        providers.append((llm_groq, "groq"))

    if not providers:
        raise RuntimeError("No LLM providers available")

    last_error = None
    for llm, provider_name in providers:
        try:
            response = invoke_with_retry(llm, messages, max_retries=max_retries, progress_callback=progress_callback)
            return response, provider_name
        except Exception as e:
            last_error = e
            logger.warning("Provider %s failed: %s. Trying next...", provider_name, e)
            if progress_callback:
                progress_callback("⏳ Switching to fallback provider...")
            continue

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
