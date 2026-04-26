from typing import TypedDict


class ModelConfig(TypedDict):
    id: str
    temperature: float
    max_tokens: int


MODELS: dict[str, ModelConfig] = {
    "gpt-4o-mini": {"id": "openai/gpt-4o-mini", "temperature": 0.0, "max_tokens": 2048},
    "gpt-4o": {"id": "openai/gpt-4o", "temperature": 0.0, "max_tokens": 2048},
    "claude-sonnet": {"id": "vertex_ai/claude-sonnet-4-5", "temperature": 0.0, "max_tokens": 2048},
    "gemini-flash": {"id": "vertex_ai/gemini-2.5-flash", "temperature": 0.0, "max_tokens": 2048},
    "gemini-pro": {"id": "vertex_ai/gemini-2.5-pro", "temperature": 0.0, "max_tokens": 2048},
    "llama3": {"id": "huggingface/meta-llama/Llama-3.3-70B-Instruct", "temperature": 0.0, "max_tokens": 2048},
}


def resolve_model_key(key: str | None) -> str | None:
    """모델 키를 LiteLLM 모델 ID로 변환. 키가 MODELS에 없으면 원본 반환."""
    if key and key in MODELS:
        return MODELS[key]["id"]
    return key
