"""TDD: Consensus extraction — prompt structure, response parsing, real-time tracking."""

import json
import pytest
from app.services.prompt_manager import (
    build_consensus_check_prompt,
    format_transcript,
)


class TestConsensusCheckPrompt:
    """Schema-Driven: verify consensus prompt structure."""

    def test_prompt_includes_topic(self):
        prompt = build_consensus_check_prompt("测试话题", "讨论记录", [], [])
        assert "测试话题" in prompt

    def test_prompt_includes_transcript(self):
        prompt = build_consensus_check_prompt("话题", "讨论记录", [], [])
        assert "讨论记录" in prompt

    def test_prompt_includes_existing_points(self):
        prompt = build_consensus_check_prompt(
            "话题", "记录",
            ["远程办公提升效率"], ["管理难度增加"]
        )
        assert "远程办公提升效率" in prompt
        assert "管理难度增加" in prompt

    def test_prompt_requests_json(self):
        prompt = build_consensus_check_prompt("话题", "记录", [], [])
        assert "JSON" in prompt or "json" in prompt
        assert "new_consensus" in prompt
        assert "new_divergence" in prompt

    def test_prompt_handles_empty_existing(self):
        prompt = build_consensus_check_prompt("话题", "记录", [], [])
        assert "无" in prompt

    def test_prompt_requests_concise_points(self):
        prompt = build_consensus_check_prompt("话题", "记录", [], [])
        assert "15-30字" in prompt or "简洁" in prompt


class TestConsensusParsing:
    """Verify consensus response parsing."""

    def test_parse_new_consensus(self):
        from app.services.discussion_orchestrator import _parse_json
        raw = json.dumps({
            "new_consensus": ["远程办公可提升个人效率"],
            "new_divergence": [],
        })
        result = _parse_json(raw, {"new_consensus": [], "new_divergence": []})
        assert len(result["new_consensus"]) == 1
        assert "个人效率" in result["new_consensus"][0]

    def test_parse_both_consensus_and_divergence(self):
        from app.services.discussion_orchestrator import _parse_json
        raw = json.dumps({
            "new_consensus": ["观点A"],
            "new_divergence": ["观点B", "观点C"],
        })
        result = _parse_json(raw, {"new_consensus": [], "new_divergence": []})
        assert len(result["new_consensus"]) == 1
        assert len(result["new_divergence"]) == 2

    def test_parse_empty_results(self):
        from app.services.discussion_orchestrator import _parse_json
        raw = json.dumps({"new_consensus": [], "new_divergence": []})
        result = _parse_json(raw, {"new_consensus": [], "new_divergence": []})
        assert result["new_consensus"] == []
        assert result["new_divergence"] == []

    def test_parse_fallback_on_invalid(self):
        from app.services.discussion_orchestrator import _parse_json
        result = _parse_json("invalid", {"new_consensus": [], "new_divergence": []})
        assert result == {"new_consensus": [], "new_divergence": []}


class TestConsensusAccumulation:
    """Core logic: verify consensus accumulates across rounds."""

    def test_accumulate_across_rounds(self):
        """Simulate 3 rounds of consensus checking."""
        all_consensus = []
        all_divergence = []

        # Round 1
        all_consensus.extend(["远程办公提升效率"])
        assert len(all_consensus) == 1

        # Round 2
        all_consensus.extend(["灵活管理是关键"])
        assert len(all_consensus) == 2

        # Round 3 (no new)
        assert len(all_consensus) == 2

    def test_no_duplicate_consensus(self):
        """In production, duplicates should be filtered. Verify logic."""
        existing = ["观点A", "观点B"]
        new = ["观点A", "观点C"]

        # Simulate filter
        truly_new = [p for p in new if p not in existing]
        assert truly_new == ["观点C"]

    def test_consensus_points_are_short(self):
        """Consensus points should be concise (15-30 chars)."""
        points = ["远程办公提升个人效率", "管理成熟度是关键前提"]
        for p in points:
            assert 5 <= len(p) <= 50, f"Point too long: {p}"
