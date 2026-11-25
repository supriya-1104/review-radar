"""Hide names reviewers write about themselves inside the review text (D16).

The reviewer name field is never stored (only a hash, see D11). But some people
introduce themselves in the text ("Hello, this is KRISHNA") or sign off
("Regards, Priya"). Those are hidden before any review text is shown on the
dashboard or sent to the summary model.

Deliberately narrow: names of staff ("the waiter, Sandeep was great") are NOT
hidden; they matter for coaching (PRD J10) and are a separate decision.
"""

import re

HIDDEN = "[name hidden]"

# Words that can follow "I am" / "this is" capitalised but aren't names.
NOT_NAMES = {
    "a", "an", "the", "very", "so", "not", "really", "extremely", "totally", "truly",
    "happy", "sorry", "disappointed", "satisfied", "glad", "impressed", "here",
    "writing", "from", "visiting", "regular", "vegetarian", "back", "also", "still",
    "just", "never", "always", "sure", "honestly", "definitely", "my", "our", "your",
    "it", "this", "that", "one", "first", "best", "worst", "good", "bad", "amazing",
    "awesome", "great", "nice", "ok", "okay", "i", "we", "you", "he", "she", "they",
}

_NAME = r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)"
_INTRO = re.compile(r"(?i:\b(?:this is|my name is|myself|i am|i'm|im)\s+)" + _NAME)
_SIGN = re.compile(r"(?:(?i:regards|thanks|thank you|cheers|best)\s*,?\s*\n?\s*|[-–—]\s*)"
                   + _NAME + r"\s*[.!]*\s*$")


def _is_name(candidate: str, text: str, end: int, exclude: set[str]) -> bool:
    first = candidate.split()[0]
    if first.lower() in NOT_NAMES or first.lower() in exclude:
        return False
    return not text[end:end + 2].startswith("'s")  # "this is Meghana's best" = a place


def hide_names(text: str | None, exclude_words: str = "") -> str:
    """Replace self-introduced and signed-off reviewer names with [name hidden].
    `exclude_words`: e.g. the place name, so "This is Meghana" isn't hidden."""
    if not text:
        return text or ""
    exclude = {w.lower() for w in re.findall(r"[A-Za-z]+", exclude_words)}

    def sub(pattern, s):
        out, last = [], 0
        for m in pattern.finditer(s):
            if _is_name(m.group(1), s, m.end(1), exclude):
                out.append(s[last:m.start(1)] + HIDDEN)
                last = m.end(1)
        out.append(s[last:])
        return "".join(out)

    return sub(_SIGN, sub(_INTRO, text))
