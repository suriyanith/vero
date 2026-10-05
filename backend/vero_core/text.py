"""Text normalization with an offset map back to the original string.

Quotes returned by the AI are matched against the *normalized* note, but the
offsets we store must slice the *original* note exactly. Every normalized
character therefore remembers which original character(s) it came from.
"""

import unicodedata
from dataclasses import dataclass

# Typographic characters normalized to plain ASCII equivalents before NFKC.
_TRANSLATE = {
    "‘": "'",  # left single quote
    "’": "'",  # right single quote
    "‚": "'",
    "‛": "'",
    "“": '"',  # left double quote
    "”": '"',  # right double quote
    "„": '"',
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # minus sign
    " ": " ",  # non-breaking space
}


@dataclass(frozen=True)
class NormalizedText:
    """A normalized string plus, per normalized char, its original span."""

    text: str
    starts: tuple[int, ...]  # starts[i] = original index where normalized char i begins
    ends: tuple[int, ...]  # ends[i] = original index just past normalized char i

    def original_span(self, start: int, end: int) -> tuple[int, int]:
        """Map a normalized [start, end) slice to original offsets."""
        if not 0 <= start < end <= len(self.text):
            raise ValueError(f"Invalid normalized span [{start}, {end})")
        return self.starts[start], self.ends[end - 1]


def normalize(text: str) -> NormalizedText:
    """Unicode NFKC, plain quotes/dashes/spaces, whitespace collapsed, trimmed."""
    chars: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    for i, original_char in enumerate(text):
        translated = _TRANSLATE.get(original_char, original_char)
        # NFKC may expand one char into several (e.g. ligature "ﬁ" -> "fi");
        # each expanded char maps back to the same original index.
        for normalized_char in unicodedata.normalize("NFKC", translated):
            chars.append(normalized_char)
            starts.append(i)
            ends.append(i + 1)

    # Collapse every whitespace run into a single space that spans the run.
    out_chars: list[str] = []
    out_starts: list[int] = []
    out_ends: list[int] = []
    i = 0
    while i < len(chars):
        if chars[i].isspace():
            j = i
            while j < len(chars) and chars[j].isspace():
                j += 1
            out_chars.append(" ")
            out_starts.append(starts[i])
            out_ends.append(ends[j - 1])
            i = j
        else:
            out_chars.append(chars[i])
            out_starts.append(starts[i])
            out_ends.append(ends[i])
            i += 1

    # Trim leading/trailing space.
    begin, finish = 0, len(out_chars)
    if out_chars and out_chars[0] == " ":
        begin = 1
    if finish > begin and out_chars[finish - 1] == " ":
        finish -= 1

    return NormalizedText(
        text="".join(out_chars[begin:finish]),
        starts=tuple(out_starts[begin:finish]),
        ends=tuple(out_ends[begin:finish]),
    )


def normalize_plain(text: str) -> str:
    """Normalization without the offset map (for quotes, not the note)."""
    return normalize(text).text


@dataclass(frozen=True)
class QuoteMatch:
    start: int  # offset into the ORIGINAL note
    end: int
    text: str  # exact substring of the original note
    match_type: str  # "exact" or "case_insensitive"
    ambiguous: bool


def find_quote(note: str, normalized_note: NormalizedText, quote: str) -> QuoteMatch | None:
    """Locate a quote in the note, tolerating formatting but never wording.

    Exact match on the normalized text first, then a case-insensitive
    fallback (``str.lower`` keeps offsets aligned; ``casefold`` can change
    string length). No fuzzy matching: a quote that is not present verbatim
    is dropped by the caller.
    """
    normalized_quote = normalize_plain(quote)
    if not normalized_quote:
        return None

    haystack = normalized_note.text
    index = haystack.find(normalized_quote)
    if index >= 0:
        match_type = "exact"
        ambiguous = haystack.count(normalized_quote) > 1
    else:
        lowered_haystack = haystack.lower()
        lowered_quote = normalized_quote.lower()
        if len(lowered_haystack) != len(haystack) or len(lowered_quote) != len(normalized_quote):
            return None  # lowering shifted offsets; treat as unverifiable
        index = lowered_haystack.find(lowered_quote)
        if index < 0:
            return None
        match_type = "case_insensitive"
        ambiguous = lowered_haystack.count(lowered_quote) > 1

    start, end = normalized_note.original_span(index, index + len(normalized_quote))
    return QuoteMatch(
        start=start,
        end=end,
        text=note[start:end],
        match_type=match_type,
        ambiguous=ambiguous,
    )
