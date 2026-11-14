"""Shared sanitiser for text that comes from outside (RFCs, Wikipedia, .unl names): remove characters that can hide or spoof content.

Removed: C0/C1 controls except tab and newline, soft hyphen, combining grapheme joiner, Arabic letter mark, Hangul/Khmer/Mongolian fillers
and selectors, zero-width and bidi marks and overrides (U+200B-200F, U+2028-202E, U+2060-206F), variation selectors (FE00-FE0F, E0100-E01EF),
lone surrogates, BOM, interlinear annotation marks, Unicode TAG characters (U+E0000-E0FFF), and invisible musical/shorthand format characters.
This lowers the chance of hidden instructions reaching a model; it does not make untrusted text trustworthy.
"""
import re

_HIDDEN = re.compile(
    "[\x00-\x08\x0b-\x1f\x7f-\x9f\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180f\u200b-\u200f\u2028-\u202e\u2060-\u206f"
    "\u3164\ufe00-\ufe0f\ufeff\uffa0\ufff9-\ufffb\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0000-\U000e0fff\ud800-\udfff]")


def strip_hidden(text) -> str:
    return _HIDDEN.sub("", str(text))


def flatten(text) -> str:
    """strip_hidden plus tab/newline/carriage return turned into spaces: for names and titles that must stay on one line."""
    return re.sub(r"[\t\n\r]+", " ", strip_hidden(text))
