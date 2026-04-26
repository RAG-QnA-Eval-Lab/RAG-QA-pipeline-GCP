"""LLM 사용량 비용 추정.

정확한 과금은 공급자 콘솔을 기준으로 해야 한다. 여기서는 운영 대시보드와 실험
비교용으로 보수적인 추정치를 기록한다.
"""

from __future__ import annotations

# USD / 1M tokens. 알 수 없거나 Vertex Model Garden 계약형 모델은 0으로 둔다.
_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (5.00, 15.00),
    "vertex_ai/gemini-2.5-flash": (0.30, 2.50),
    "vertex_ai/gemini-2.5-pro": (1.25, 10.00),
    "vertex_ai/claude-sonnet-4-5": (3.00, 15.00),
    "huggingface/meta-llama/Llama-3.3-70B-Instruct": (0.00, 0.00),
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """토큰 사용량 기반 비용 추정치(USD)를 반환."""
    input_price, output_price = _PRICING_PER_1M.get(model, (0.0, 0.0))
    cost = (prompt_tokens / 1_000_000) * input_price + (completion_tokens / 1_000_000) * output_price
    return round(cost, 8)
