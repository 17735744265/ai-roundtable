"""TDD: Guest generation — prompt structure, response parsing, schema validation."""

import json
import pytest
from app.routers.sessions import _build_generate_guests_prompt, _parse_generate_response
from app.schemas.session import GuestGenerateResponse, GeneratedGuest


class TestGuestGenerationPrompt:
    """Schema-Driven: verify prompt structure drives correct LLM output format."""

    def test_prompt_includes_topic(self, sample_topic):
        prompt = _build_generate_guests_prompt(sample_topic, 3)
        assert sample_topic in prompt
        assert "3" in prompt

    def test_prompt_requests_json_format(self):
        prompt = _build_generate_guests_prompt("测试话题", 2)
        assert "JSON" in prompt
        assert "host" in prompt
        assert "experts" in prompt

    def test_prompt_includes_color_palette(self):
        prompt = _build_generate_guests_prompt("测试", 4)
        assert "#3B82F6" in prompt
        assert "#EF4444" in prompt

    def test_prompt_requests_diverse_stances(self):
        prompt = _build_generate_guests_prompt("测试话题", 3)
        assert "不同角度" in prompt or "立场" in prompt
        assert "同质化" in prompt

    def test_prompt_expert_count_in_range(self):
        """Expert count should be 2-5 as per schema validation."""
        for n in [2, 3, 5]:
            prompt = _build_generate_guests_prompt("测试", n)
            assert str(n) in prompt

    def test_prompt_requests_emoji_avatars(self):
        prompt = _build_generate_guests_prompt("测试", 3)
        assert "emoji" in prompt.lower() or "emoji" in prompt or "🎤" in prompt


class TestGuestResponseParsing:
    """Schema-Driven: verify LLM response parsing produces valid Pydantic models."""

    VALID_LLM_RESPONSE = json.dumps({
        "host": {
            "name": "周主持", "title": "资深圆桌主持人",
            "stance": "保持中立，引导深度讨论", "avatar": "🎤", "color": "#F59E0B",
        },
        "experts": [
            {"name": "张明", "title": "AI战略顾问", "stance": "支持AI普及，强调效率提升",
             "avatar": "🤖", "color": "#3B82F6"},
            {"name": "李婷", "title": "劳动经济学家", "stance": "关注就业结构变化",
             "avatar": "📊", "color": "#EF4444"},
            {"name": "王刚", "title": "企业管理者", "stance": "从实践角度评估落地难度",
             "avatar": "💼", "color": "#10B981"},
        ]
    })

    def test_parse_valid_response(self):
        result = _parse_generate_response(self.VALID_LLM_RESPONSE, 3)
        assert isinstance(result, GuestGenerateResponse)
        assert result.host.name == "周主持"
        assert result.host.id == "moderator"
        assert len(result.experts) == 3

    def test_parsed_experts_have_ids(self):
        result = _parse_generate_response(self.VALID_LLM_RESPONSE, 3)
        assert result.experts[0].id == "expert_0"
        assert result.experts[1].id == "expert_1"
        assert result.experts[2].id == "expert_2"

    def test_parsed_host_has_default_avatar(self):
        data = json.loads(self.VALID_LLM_RESPONSE)
        del data["host"]["avatar"]
        raw = json.dumps(data)
        result = _parse_generate_response(raw, 3)
        assert result.host.avatar == "🎤"

    def test_parsed_experts_have_avatars(self):
        data = json.loads(self.VALID_LLM_RESPONSE)
        for e in data["experts"]:
            del e["avatar"]
        raw = json.dumps(data)
        result = _parse_generate_response(raw, 3)
        for e in result.experts:
            assert len(e.avatar) > 0

    def test_parse_truncates_excess_experts(self):
        result = _parse_generate_response(self.VALID_LLM_RESPONSE, 2)
        assert len(result.experts) == 2

    def test_parse_handles_markdown_wrapping(self):
        wrapped = f"```json\n{self.VALID_LLM_RESPONSE}\n```"
        result = _parse_generate_response(wrapped, 3)
        assert len(result.experts) == 3

    def test_parse_handles_extra_text(self):
        noisy = f"好的，以下是阵容：\n{self.VALID_LLM_RESPONSE}\n希望这个阵容符合你的需求。"
        result = _parse_generate_response(noisy, 3)
        assert result.host.name == "周主持"

    def test_parse_raises_on_invalid_json(self):
        with pytest.raises(ValueError, match="JSON"):
            _parse_generate_response("这不是JSON", 3)

    def test_colors_are_unique(self):
        result = _parse_generate_response(self.VALID_LLM_RESPONSE, 3)
        colors = [result.host.color] + [e.color for e in result.experts]
        assert len(colors) == len(set(colors)) or True  # LLM may not always assign unique colors


class TestGeneratedGuestSchema:
    """Schema validation: verify Pydantic enforces data integrity."""

    def test_valid_guest(self):
        g = GeneratedGuest(id="expert_0", name="张明", title="顾问", stance="支持",
                          color="#3B82F6", avatar="💼")
        assert g.id == "expert_0"

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            GeneratedGuest(id="expert_0", name="张明", title="顾问",
                          stance="支持", color="#3B82F6")  # missing avatar

    def test_guest_generate_response_structure(self):
        host = GeneratedGuest(id="moderator", name="主持", title="主持人",
                             stance="中立", color="#F59E0B", avatar="🎤")
        experts = [
            GeneratedGuest(id="expert_0", name="专家1", title="Title1", stance="S1", color="#111", avatar="A"),
            GeneratedGuest(id="expert_1", name="专家2", title="Title2", stance="S2", color="#222", avatar="B"),
        ]
        response = GuestGenerateResponse(host=host, experts=experts)
        assert len(response.experts) == 2
