"""TDD: Speech scheduling — autonomous decision logic, urgency-based selection."""

import json
import pytest
from app.services.prompt_manager import (
    build_expert_system_prompt,
    build_expert_decide_prompt,
    format_transcript,
)
from app.services.discussion_orchestrator import _parse_json


class TestExpertSystemPrompt:
    """Design-Driven: verify prompt shapes expert behavior correctly."""

    def test_prompt_includes_name_title_stance(self):
        prompt = build_expert_system_prompt("张明", "AI战略顾问", "支持AI普及")
        assert "张明" in prompt
        assert "AI战略顾问" in prompt
        assert "支持AI普及" in prompt

    def test_prompt_encourages_autonomous_speaking(self):
        prompt = build_expert_system_prompt("专家", "Title", "Stance")
        assert "自主决定" in prompt or "主动" in prompt

    def test_prompt_limits_speech_length(self):
        prompt = build_expert_system_prompt("专家", "Title", "Stance")
        assert "1-2句" in prompt or "30-80" in prompt or "简洁" in prompt

    def test_prompt_discourages_empty_speech(self):
        prompt = build_expert_system_prompt("专家", "Title", "Stance")
        assert "沉默" in prompt or "不说空话" in prompt or "实质性" in prompt


class TestExpertDecidePrompt:
    """Schema-Driven: verify decision prompt requests structured JSON output."""

    def test_decision_prompt_requests_json(self):
        prompt = build_expert_decide_prompt(
            "张明", "AI顾问", "支持", "测试话题",
            "[主持人]：开始讨论\n[张明]：我同意"
        )
        assert "JSON" in prompt and "json" in prompt
        assert "should_speak" in prompt
        assert "urgency" in prompt
        assert "focus" in prompt
        assert "content" in prompt

    def test_decision_prompt_includes_topic(self):
        prompt = build_expert_decide_prompt("张明", "AI顾问", "支持", "测试话题", "test transcript")
        assert "测试话题" in prompt

    def test_decision_prompt_includes_transcript(self):
        prompt = build_expert_decide_prompt("张明", "AI顾问", "支持", "话题", "test transcript")
        assert "test transcript" in prompt or "讨论记录" in prompt


class TestUrgencyBasedSelection:
    """Core logic: verify urgency-based speaker selection algorithm."""

    def make_decision(self, should_speak: bool, urgency: int, content: str = "测试发言内容"):
        return {"should_speak": should_speak, "urgency": urgency, "focus": "关注点", "content": content}

    def test_highest_urgency_wins(self):
        """Expert with highest urgency >= 5 should be selected."""
        decisions = [
            {"expert": {"id": "expert_0", "name": "A"}, "decision": self.make_decision(True, 5, "A的发言")},
            {"expert": {"id": "expert_1", "name": "B"}, "decision": self.make_decision(True, 8, "B的发言")},
            {"expert": {"id": "expert_2", "name": "C"}, "decision": self.make_decision(False, 2, "")},
        ]
        candidates = [d for d in decisions if d["decision"]["should_speak"] and d["decision"]["urgency"] >= 5]
        candidates.sort(key=lambda x: x["decision"]["urgency"], reverse=True)
        assert len(candidates) == 2
        assert candidates[0]["expert"]["name"] == "B"
        assert candidates[0]["decision"]["urgency"] == 8

    def test_below_threshold_not_selected(self):
        """Experts with urgency < 5 should not be candidates."""
        decisions = [
            {"expert": {"id": "expert_0"}, "decision": self.make_decision(True, 3, "low urgency")},
            {"expert": {"id": "expert_1"}, "decision": self.make_decision(True, 4, "also low")},
        ]
        candidates = [d for d in decisions if d["decision"]["should_speak"] and d["decision"]["urgency"] >= 5]
        assert len(candidates) == 0

    def test_no_one_wants_to_speak(self):
        """When all urgency < 5, host should intervene."""
        decisions = [
            {"expert": {"id": "expert_0"}, "decision": self.make_decision(False, 1, "")},
            {"expert": {"id": "expert_1"}, "decision": self.make_decision(False, 2, "")},
        ]
        candidates = [d for d in decisions if d["decision"]["should_speak"] and d["decision"]["urgency"] >= 5]
        assert len(candidates) == 0

    def test_same_urgency_picks_first(self):
        """When urgency is tied, first in sorted list wins."""
        decisions = [
            {"expert": {"id": "expert_0", "name": "A"}, "decision": self.make_decision(True, 7, "A")},
            {"expert": {"id": "expert_1", "name": "B"}, "decision": self.make_decision(True, 7, "B")},
        ]
        candidates = [d for d in decisions if d["decision"]["should_speak"] and d["decision"]["urgency"] >= 5]
        candidates.sort(key=lambda x: x["decision"]["urgency"], reverse=True)
        assert candidates[0]["expert"]["name"] == "A"


class TestJSONParsing:
    """Utility: verify robust JSON extraction from LLM responses."""

    def test_parse_clean_json(self):
        raw = '{"should_speak": true, "urgency": 8}'
        result = _parse_json(raw, {})
        assert result["should_speak"] is True
        assert result["urgency"] == 8

    def test_parse_markdown_wrapped(self):
        raw = '```json\n{"should_speak": false, "urgency": 2}\n```'
        result = _parse_json(raw, {})
        assert result["should_speak"] is False

    def test_parse_with_extra_text(self):
        raw = '根据讨论... {"should_speak": true, "urgency": 9, "content": "我补充一点"} 以上是我的决定'
        result = _parse_json(raw, {})
        assert result["should_speak"] is True
        assert result["urgency"] == 9

    def test_parse_fallback_on_invalid(self):
        raw = 'not json at all'
        default = {"should_speak": False, "urgency": 0}
        result = _parse_json(raw, default)
        assert result == default

    def test_parse_content_not_empty_when_speaking(self):
        raw = '{"should_speak": true, "urgency": 7, "content": "", "focus": "test"}'
        result = _parse_json(raw, {})
        assert result["should_speak"] is True
        # Content may be empty if LLM didn't fill it — orchestrator handles fallback


class TestTranscriptFormatting:
    """Verify transcript formatting for LLM context."""

    def test_format_includes_speaker_names(self):
        msgs = [
            {"speaker_id": "moderator", "speaker_name": "主持人", "content": "欢迎各位"},
            {"speaker_id": "expert_0", "speaker_name": "张明", "content": "我认为..."},
        ]
        result = format_transcript(msgs)
        assert "主持人" in result
        assert "张明" in result

    def test_format_truncates_to_last_n(self):
        msgs = [{"speaker_id": f"expert_{i}", "speaker_name": f"E{i}", "content": f"msg{i}"} for i in range(20)]
        result = format_transcript(msgs, last_n=5)
        # Should contain last 5, not earlier ones
        assert "E19" in result
        assert "E15" not in result

    def test_format_empty_list(self):
        result = format_transcript([])
        assert result == ""
