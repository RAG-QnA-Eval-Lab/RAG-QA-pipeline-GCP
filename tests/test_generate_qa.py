"""scripts/generate_qa.py 단위 테스트."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from src.generation import LLMResponse

sys_path_fix = Path(__file__).parent.parent
sys.path.insert(0, str(sys_path_fix))

from scripts.generate_qa import (  # noqa: E402
    assemble_output,
    build_qa_prompt,
    generate_qa_for_policy,
    load_qa_prompt,
    parse_qa_response,
    plan_difficulty_assignments,
    score_policy_richness,
    select_policies,
)


def _make_policy(
    *,
    category: str = "housing",
    raw_content: str = "x" * 600,
    summary: str = "요약",
    description: str = "설명",
    eligibility: str = "자격",
    benefits: str = "혜택",
    how_to_apply: str = "신청방법",
    application_period: str = "상시",
    managing_department: str = "부서",
    title: str = "테스트 정책",
    policy_id: str = "P001",
) -> dict:
    return {
        "policy_id": policy_id,
        "title": title,
        "category": category,
        "summary": summary,
        "description": description,
        "eligibility": eligibility,
        "benefits": benefits,
        "how_to_apply": how_to_apply,
        "application_period": application_period,
        "managing_department": managing_department,
        "raw_content": raw_content,
        "source_name": "data_portal",
    }


class TestScorePolicyRichness:
    def test_full_policy(self) -> None:
        p = _make_policy()
        assert score_policy_richness(p) >= 6

    def test_minimal_policy(self) -> None:
        p = _make_policy(
            summary="", description="", eligibility="",
            benefits="", how_to_apply="", application_period="",
            managing_department="", raw_content="짧음",
        )
        assert score_policy_richness(p) < 4

    def test_medium_policy(self) -> None:
        p = _make_policy(
            summary="요약", description="", eligibility="",
            benefits="혜택", how_to_apply="", application_period="",
            managing_department="", raw_content="x" * 300,
        )
        score = score_policy_richness(p)
        assert 3 <= score <= 5


class TestSelectPolicies:
    def _policies_pool(self) -> list[dict]:
        policies = []
        for cat in ["housing", "employment", "education", "welfare"]:
            for i in range(20):
                policies.append(_make_policy(
                    category=cat, policy_id=f"{cat}_{i}", title=f"{cat} 정책 {i}",
                ))
        for i in range(10):
            policies.append(_make_policy(
                category="participation", policy_id=f"part_{i}", title=f"참여 정책 {i}",
            ))
        return policies

    def test_excludes_participation(self) -> None:
        selected = select_policies(self._policies_pool(), target_count=40, qa_per_policy=2)
        cats = {p["category"] for p in selected}
        assert "participation" not in cats

    def test_category_balance(self) -> None:
        selected = select_policies(self._policies_pool(), target_count=40, qa_per_policy=2)
        cats = {p["category"] for p in selected}
        assert cats == {"housing", "employment", "education", "welfare"}

    def test_respects_target(self) -> None:
        selected = select_policies(self._policies_pool(), target_count=20, qa_per_policy=2)
        assert 8 <= len(selected) <= 12

    def test_empty_on_no_rich_policies(self) -> None:
        sparse = [
            _make_policy(
                summary="", description="", eligibility="",
                benefits="", how_to_apply="", application_period="",
                managing_department="", raw_content="짧",
            )
        ]
        selected = select_policies(sparse, target_count=10, qa_per_policy=2, min_richness=4)
        assert selected == []


class TestParseQaResponse:
    def test_valid_json(self) -> None:
        data = [
            {
                "question": "질문1",
                "ground_truth": "답1",
                "difficulty": "easy",
                "qa_type": "factual",
            }
        ]
        result = parse_qa_response(json.dumps(data, ensure_ascii=False))
        assert result is not None
        assert len(result) == 1
        assert result[0]["question"] == "질문1"

    def test_markdown_fenced(self) -> None:
        inner = json.dumps([{
            "question": "Q", "ground_truth": "A",
            "difficulty": "medium", "qa_type": "reasoning",
        }], ensure_ascii=False)
        raw = f"```json\n{inner}\n```"
        result = parse_qa_response(raw)
        assert result is not None
        assert len(result) == 1

    def test_invalid_json(self) -> None:
        assert parse_qa_response("이것은 JSON이 아닙니다") is None

    def test_partial_valid(self) -> None:
        data = [
            {"question": "Q1", "ground_truth": "A1", "difficulty": "easy", "qa_type": "factual"},
            {"question": "Q2"},  # missing fields
            {"question": "Q3", "ground_truth": "A3", "difficulty": "invalid", "qa_type": "factual"},
        ]
        result = parse_qa_response(json.dumps(data))
        assert result is not None
        assert len(result) == 1

    def test_empty_fields_rejected(self) -> None:
        data = [{"question": "", "ground_truth": "A", "difficulty": "easy", "qa_type": "factual"}]
        assert parse_qa_response(json.dumps(data)) is None

    def test_not_array(self) -> None:
        assert parse_qa_response('{"question": "Q"}') is None


class TestPlanDifficultyAssignments:
    def test_distribution(self) -> None:
        assignments = plan_difficulty_assignments(100, 40)
        flat = [d for group in assignments for d in group]
        from collections import Counter
        counts = Counter(flat)
        assert counts["easy"] == 40
        assert counts["medium"] == 40
        assert counts["hard"] == 20

    def test_chunk_sizes(self) -> None:
        assignments = plan_difficulty_assignments(50, 20)
        for group in assignments:
            assert 2 <= len(group) <= 3


class TestBuildQaPrompt:
    def test_includes_policy_content(self) -> None:
        p = _make_policy(title="청년 주거 지원", raw_content="지원 내용 상세")
        msgs = build_qa_prompt(p, 2, ["easy", "medium"], "system prompt")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "system prompt"
        assert "청년 주거 지원" in msgs[1]["content"]
        assert "easy 1개" in msgs[1]["content"]

    def test_truncates_long_content(self) -> None:
        p = _make_policy(raw_content="가" * 5000)
        msgs = build_qa_prompt(p, 2, ["easy", "medium"], "system prompt")
        assert len(msgs[1]["content"]) < 5000


class TestLoadQaPrompt:
    @patch("scripts.generate_qa.GCSClient")
    def test_loads_prompt_from_gcs(self, mock_gcs_cls) -> None:
        mock_gcs = mock_gcs_cls.return_value
        mock_gcs.download_text.return_value = "prompt body"

        prompt, metadata = load_qa_prompt()

        assert prompt == "prompt body"
        assert metadata["gcs_uri"].endswith("/prompts/qa_generation_system.txt")
        assert len(metadata["sha256"]) == 64


class TestAssembleOutput:
    def test_structure(self) -> None:
        pairs = [
            {
                "question": "Q1", "ground_truth": "A1",
                "difficulty": "easy", "qa_type": "factual",
                "category": "housing", "policy_title": "T1",
                "policy_id": "P1", "reference_doc": "d.json",
                "reference_source": "data_portal",
            },
            {
                "question": "Q2", "ground_truth": "A2",
                "difficulty": "medium", "qa_type": "reasoning",
                "category": "employment", "policy_title": "T2",
                "policy_id": "P2", "reference_doc": "d.json",
                "reference_source": "data_portal",
            },
        ]
        result = assemble_output(pairs, "openai/gpt-4o-mini", {"gcs_uri": "gs://bucket/prompts/x.txt", "sha256": "abc"})
        assert result["version"] == "1.0"
        assert result["total_count"] == 2
        assert result["domain"] == "youth_policy"
        assert result["prompt"]["gcs_uri"] == "gs://bucket/prompts/x.txt"
        assert set(result["categories"]) == {"housing", "employment"}

    def test_sequential_ids(self) -> None:
        pairs = [
            {"question": f"Q{i}", "ground_truth": f"A{i}",
             "difficulty": "easy", "qa_type": "factual",
             "category": "housing", "policy_title": "T", "policy_id": "P",
             "reference_doc": "d", "reference_source": "s"}
            for i in range(5)
        ]
        result = assemble_output(pairs, "m", {"gcs_uri": "gs://bucket/prompts/x.txt", "sha256": "abc"})
        ids = [s["id"] for s in result["samples"]]
        assert ids == ["q001", "q002", "q003", "q004", "q005"]


class TestGenerateQaForPolicy:
    def test_success(self) -> None:
        mock_content = json.dumps([
            {"question": "Q", "ground_truth": "A", "difficulty": "easy", "qa_type": "factual"},
        ], ensure_ascii=False)
        mock_resp = LLMResponse(
            content=mock_content, model="openai/gpt-4o-mini",
            prompt_tokens=100, completion_tokens=50, total_tokens=150, latency=0.5,
        )
        with patch("scripts.generate_qa.generate", return_value=mock_resp):
            result = generate_qa_for_policy(
                _make_policy(), qa_count=1, difficulties=["easy"], system_prompt="prompt",
            )
        assert result is not None
        assert len(result) == 1
        assert result[0]["category"] == "housing"
        assert result[0]["policy_title"] == "테스트 정책"
        assert result[0]["reference_doc"] == "data_portal/latest.json"

    def test_failure(self) -> None:
        with patch("scripts.generate_qa.generate", side_effect=RuntimeError("API error")):
            result = generate_qa_for_policy(
                _make_policy(), qa_count=1, difficulties=["easy"], system_prompt="prompt",
            )
        assert result is None
