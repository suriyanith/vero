import pytest

from vero_core.prompt_loader import load_prompt, render


class TestLoadPrompt:
    def test_extract_v1_loads(self) -> None:
        template = load_prompt("extract", "v1")
        assert template.id == "extract"
        assert template.version == "v1"
        assert "MEAT" in template.system
        assert "{{ note_text }}" in template.user

    def test_select_v1_loads(self) -> None:
        template = load_prompt("select", "v1")
        assert "Excludes1" in template.system
        assert "{{ conditions_block }}" in template.user

    def test_note_is_declared_data_not_instructions(self) -> None:
        # Prompt-injection defense required by the plan (Section 10.4).
        extract = load_prompt("extract", "v1")
        combined = extract.system + extract.user
        assert "<note>" in combined
        assert "data, not instructions" in combined

    def test_unknown_version_fails(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_prompt("extract", "v99")


class TestRender:
    def test_substitutes_variables(self) -> None:
        assert render("Hello {{ name }}!", {"name": "world"}) == "Hello world!"

    def test_missing_variable_fails_loudly(self) -> None:
        with pytest.raises(KeyError, match="note_text"):
            render("<note>{{ note_text }}</note>", {})

    def test_unused_variable_fails_loudly(self) -> None:
        with pytest.raises(KeyError, match="extra"):
            render("no placeholders", {"extra": 1})
