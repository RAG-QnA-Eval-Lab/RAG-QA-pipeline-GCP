"""pydantic-settings 값을 os.environ으로 내보내는 부트스트랩.

pydantic-settings는 .env를 Settings 객체로 읽지만 os.environ에는 쓰지 않는다.
LiteLLM은 os.environ에서 API 키를 찾으므로, 앱 시작 시 1회 호출해야 한다.
"""

from __future__ import annotations

import os

from config.settings import settings


def apply_litellm_env() -> None:
    """LiteLLM이 필요로 하는 환경변수를 os.environ에 설정."""
    os.environ.setdefault("VERTEXAI_PROJECT", settings.vertexai_project)
    os.environ.setdefault("VERTEXAI_LOCATION", settings.vertexai_location)
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    if settings.anthropic_api_key:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    if settings.google_api_key:
        os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
    if settings.huggingface_api_key:
        os.environ.setdefault("HUGGINGFACE_API_KEY", settings.huggingface_api_key)
