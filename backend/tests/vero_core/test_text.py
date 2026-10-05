from hypothesis import given
from hypothesis import strategies as st

from vero_core.text import find_quote, normalize, normalize_plain


class TestNormalize:
    def test_collapses_whitespace_and_trims(self) -> None:
        assert normalize_plain("  a\n\n  b\tc  ") == "a b c"

    def test_curly_quotes_and_dashes(self) -> None:
        assert normalize_plain("patient’s “stable” — yes") == ('patient\'s "stable" - yes')

    def test_non_breaking_space(self) -> None:
        assert normalize_plain("a b") == "a b"

    def test_nfkc_expansion_keeps_offsets(self) -> None:
        original = "x ﬁnding y"  # "ﬁ" ligature expands to "fi"
        normalized = normalize(original)
        assert normalized.text == "x finding y"
        index = normalized.text.index("finding")
        start, end = normalized.original_span(index, index + len("finding"))
        assert original[start:end] == "ﬁnding"


class TestFindQuote:
    def test_exact_match_offsets_slice_original(self) -> None:
        note = "Assessment:\n1. CHF  stable on\n   furosemide."
        match = find_quote(note, normalize(note), "CHF stable on furosemide")
        assert match is not None
        assert match.match_type == "exact"
        assert note[match.start : match.end] == match.text
        assert match.text.startswith("CHF") and match.text.endswith("furosemide")

    def test_curly_quote_in_note_plain_in_quote(self) -> None:
        note = "patient’s edema improved"
        match = find_quote(note, normalize(note), "patient's edema")
        assert match is not None
        assert note[match.start : match.end] == "patient’s edema"

    def test_case_insensitive_fallback(self) -> None:
        note = "DENIES CHEST PAIN."
        match = find_quote(note, normalize(note), "denies chest pain")
        assert match is not None
        assert match.match_type == "case_insensitive"
        assert note[match.start : match.end] == "DENIES CHEST PAIN"

    def test_repeated_quote_is_ambiguous_first_occurrence(self) -> None:
        note = "edema noted. Later: edema noted."
        match = find_quote(note, normalize(note), "edema noted")
        assert match is not None
        assert match.ambiguous
        assert match.start == 0

    def test_missing_quote_returns_none(self) -> None:
        note = "No cardiac complaints."
        assert find_quote(note, normalize(note), "chest pain") is None

    def test_paraphrase_is_not_matched(self) -> None:
        note = "continue furosemide 40 mg daily"
        assert find_quote(note, normalize(note), "continue the diuretic") is None

    def test_empty_quote_returns_none(self) -> None:
        note = "anything"
        assert find_quote(note, normalize(note), "   ") is None


# The hard guarantee behind "Vero never invents evidence": any span the
# verifier reports must slice the original note to text that normalizes to
# the matched quote.
@given(
    note=st.text(min_size=1, max_size=200),
    start=st.integers(min_value=0, max_value=199),
    length=st.integers(min_value=1, max_value=60),
)
def test_offsets_always_round_trip(note: str, start: int, length: int) -> None:
    raw_quote = note[start : start + length]
    match = find_quote(note, normalize(note), raw_quote)
    if match is None:
        return
    sliced = note[match.start : match.end]
    assert sliced == match.text
    if match.match_type == "exact":
        assert normalize_plain(sliced) == normalize_plain(raw_quote)
    else:
        assert normalize_plain(sliced).lower() == normalize_plain(raw_quote).lower()
